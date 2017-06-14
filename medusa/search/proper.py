# coding=utf-8
# Author: Nic Wolfe <nic@wolfeden.ca>
#
#
# This file is part of Medusa.
#
# Medusa is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Medusa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Medusa. If not, see <http://www.gnu.org/licenses/>.
"""Proper finder module."""
from __future__ import unicode_literals

import datetime
import errno
import operator
import re
import threading
import traceback

from socket import timeout as socket_timeout

from requests import exceptions as requests_exceptions
import tornado.gen

from .. import app, db, helpers, logger
from ..common import Quality, cpu_presets
from ..helper.common import enabled_providers
from ..helper.exceptions import AuthException, ex
from ..name_parser.parser import InvalidNameException, InvalidShowException, NameParser
from ..search.core import pick_best_result, snatch_episode
from ..show.history import History


class ProperFinder(object):  # pylint: disable=too-few-public-methods
    """Proper finder class."""

    def __init__(self):
        """Initialize the class."""
        self.amActive = False
        self.processed_propers = []
        self.ignore_processed_propers = False

    def run(self, force=False):  # pylint: disable=unused-argument
        """
        Start looking for new propers.

        :param force: Start even if already running (currently not used, defaults to False)
        """
        logger.log('Beginning the search for new propers')

        if self.amActive:
            logger.log('Find propers is still running, not starting it again', logger.DEBUG)
            return

        if app.forced_search_queue_scheduler.action.is_forced_search_in_progress():
            logger.log("Manual search is running. Can't start Find propers", logger.WARNING)
            return

        self.amActive = True

        # If force we should ignore existing processed propers
        self.ignore_processed_propers = False
        if force:
            self.ignore_processed_propers = True
            logger.log("Ignoring already processed propers as it's a forced search", logger.DEBUG)

        logger.log('Using proper search days: {0}'.format(app.PROPERS_SEARCH_DAYS))

        propers = self._get_proper_results()

        if propers:
            self._download_propers(propers)

        self._set_last_proper_search(datetime.datetime.today().toordinal())

        run_at = ''
        if None is app.proper_finder_scheduler.start_time:
            run_in = app.proper_finder_scheduler.lastRun + \
                app.proper_finder_scheduler.cycleTime - datetime.datetime.now()
            hours, remainder = divmod(run_in.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            run_at = ', next check in approx. {0}'.format(
                '{0}h, {1}m'.format(hours, minutes) if 0 < hours else '{0}m, {1}s'.format(minutes, seconds))

        logger.log('Completed the search for new propers{0}'.format(run_at))

        self.amActive = False

    def _get_proper_results(self):  # pylint: disable=too-many-locals, too-many-branches, too-many-statements
        """Retrieve a list of recently aired episodes, and search for these episodes in the different providers."""
        propers = {}

        # For each provider get the list of propers
        original_thread_name = threading.currentThread().name
        providers = enabled_providers('backlog')

        search_date = datetime.datetime.today() - datetime.timedelta(days=app.PROPERS_SEARCH_DAYS)
        main_db_con = db.DBConnection()
        if not app.POSTPONE_IF_NO_SUBS:
            # Get the recently aired (last 2 days) shows from DB
            search_q_params = ','.join('?' for _ in Quality.DOWNLOADED)
            recently_aired = main_db_con.select(
                b'SELECT showid, season, episode, status, airdate'
                b' FROM tv_episodes'
                b' WHERE airdate >= ?'
                b' AND status IN ({0})'.format(search_q_params),
                [search_date.toordinal()] + Quality.DOWNLOADED
            )
        else:
            # Get recently subtitled episodes (last 2 days) from DB
            # Episode status becomes downloaded only after found subtitles
            last_subtitled = search_date.strftime(History.date_format)
            recently_aired = main_db_con.select(b'SELECT showid, season, episode FROM history '
                                                b"WHERE date >= ? AND action LIKE '%10'", [last_subtitled])

        if not recently_aired:
            logger.log('No recently aired new episodes, nothing to search for')
            return []

        # Loop through the providers, and search for releases
        for cur_provider in providers:
            threading.currentThread().name = '{thread} :: [{provider}]'.format(thread=original_thread_name,
                                                                               provider=cur_provider.name)

            logger.log('Searching for any new PROPER releases from {provider}'.format
                       (provider=cur_provider.name))

            try:
                cur_propers = cur_provider.find_propers(recently_aired)
            except AuthException as e:
                logger.log('Authentication error: {error}'.format
                           (error=ex(e)), logger.DEBUG)
                continue
            except socket_timeout as e:
                logger.log('Socket time out while searching for propers in {provider}, skipping: {error}'.format
                           (provider=cur_provider.name, error=ex(e)), logger.DEBUG)
                continue
            except (requests_exceptions.HTTPError, requests_exceptions.TooManyRedirects) as e:
                logger.log('HTTP error while searching for propers in {provider}, skipping: {error}'.format
                           (provider=cur_provider.name, error=ex(e)), logger.DEBUG)
                continue
            except requests_exceptions.ConnectionError as e:
                logger.log('Connection error while searching for propers in {provider}, skipping: {error}'.format
                           (provider=cur_provider.name, error=ex(e)), logger.DEBUG)
                continue
            except requests_exceptions.Timeout as e:
                logger.log('Connection timed out while searching for propers in {provider}, skipping: {error}'.format
                           (provider=cur_provider.name, error=ex(e)), logger.DEBUG)
                continue
            except requests_exceptions.ContentDecodingError as e:
                logger.log('Content-Encoding was gzip, but content was not compressed while'
                           ' searching for propers in {provider}, sipping: {error}'.format
                           (provider=cur_provider.name, error=ex(e)), logger.DEBUG)
                continue
            except Exception as e:
                if 'ECONNRESET' in e or getattr(e, 'errno', None) == errno.ECONNRESET:
                    logger.log('Connection reset by peer while searching for propers in {provider}. '
                               'Skipping: {error}'.format
                               (provider=cur_provider.name, error=ex(e)), logger.DEBUG)
                else:
                    logger.log('Unknown exception while searching for propers in {provider}, skipping: {error}'.format
                               (provider=cur_provider.name, error=ex(e)), logger.DEBUG)
                    logger.log(traceback.format_exc(), logger.DEBUG)
                continue

            # if they haven't been added by a different provider than add the proper to the list
            for proper in cur_propers:
                name = self._sanitize_name(proper.name)
                if name not in propers:
                    logger.log('Found new possible proper result: {name}'.format
                               (name=proper.name), logger.DEBUG)
                    propers[name] = proper

        threading.currentThread().name = original_thread_name

        # take the list of unique propers and get it sorted by
        sorted_propers = sorted(propers.values(), key=operator.attrgetter('date'), reverse=True)
        final_propers = []

        # Keep only items from last PROPER_SEARCH_DAYS setting in processed propers:
        latest_proper = datetime.datetime.now() - datetime.timedelta(days=app.PROPERS_SEARCH_DAYS)
        self.processed_propers = [p for p in self.processed_propers if p.get('date') >= latest_proper]

        # Get proper names from processed propers
        processed_propers_names = [proper.get('name') for proper in self.processed_propers if proper.get('name')]

        for cur_proper in sorted_propers:

            if not self.ignore_processed_propers and cur_proper.name in processed_propers_names:
                logger.log(u'Proper already processed. Skipping: {0}'.format(cur_proper.name), logger.DEBUG)
                continue

            try:
                cur_proper.parse_result = NameParser().parse(cur_proper.name)
            except (InvalidNameException, InvalidShowException) as error:
                logger.log('{0}'.format(error), logger.DEBUG)
                continue

            if not cur_proper.parse_result.proper_tags:
                logger.log('Skipping non-proper: {name}'.format(name=cur_proper.name))
                continue

            logger.log('Proper tags for {proper}: {tags}'.format
                       (proper=cur_proper.name, tags=cur_proper.parse_result.proper_tags), logger.DEBUG)

            if not cur_proper.parse_result.series_name:
                logger.log('Ignoring invalid show: {name}'.format
                           (name=cur_proper.name), logger.DEBUG)
                if cur_proper.name not in processed_propers_names:
                    self.processed_propers.append({'name': cur_proper.name, 'date': cur_proper.date})
                continue

            if not cur_proper.parse_result.episode_numbers:
                logger.log('Ignoring full season instead of episode: {name}'.format
                           (name=cur_proper.name), logger.DEBUG)
                if cur_proper.name not in processed_propers_names:
                    self.processed_propers.append({'name': cur_proper.name, 'date': cur_proper.date})
                continue

            logger.log('Successful match! Matched {original_name} to show {new_name}'.format
                       (original_name=cur_proper.parse_result.original_name, new_name=cur_proper.parse_result.show.name), logger.DEBUG)

            # Map the indexerid in the db to the show's indexerid
            cur_proper.indexerid = cur_proper.parse_result.show.indexerid

            # Map the indexer in the db to the show's indexer
            cur_proper.indexer = cur_proper.parse_result.show.indexer

            # Map our Proper instance
            cur_proper.show = cur_proper.parse_result.show
            cur_proper.actual_season = cur_proper.parse_result.season_number if cur_proper.parse_result.season_number is not None else 1
            cur_proper.actual_episodes = cur_proper.parse_result.episode_numbers
            cur_proper.release_group = cur_proper.parse_result.release_group
            cur_proper.version = cur_proper.parse_result.version
            cur_proper.quality = cur_proper.parse_result.quality
            cur_proper.content = None
            cur_proper.proper_tags = cur_proper.parse_result.proper_tags

            # filter release, in this case, it's just a quality gate. As we only send one result.
            best_result = pick_best_result(cur_proper)

            if not best_result:
                logger.log('Rejected proper: {name}'.format
                           (name=cur_proper.name))
                if cur_proper.name not in processed_propers_names:
                    self.processed_propers.append({'name': cur_proper.name, 'date': cur_proper.date})
                continue

            # only get anime proper if it has release group and version
            if best_result.show.is_anime:
                if not best_result.release_group and best_result.version == -1:
                    logger.log('Ignoring proper without release group and version: {name}'.format
                               (name=best_result.name))
                    if cur_proper.name not in processed_propers_names:
                        self.processed_propers.append({'name': cur_proper.name, 'date': cur_proper.date})
                    continue

            # check if we have the episode as DOWNLOADED
            main_db_con = db.DBConnection()
            sql_results = main_db_con.select(b"SELECT status, release_name FROM tv_episodes WHERE "
                                             b"showid = ? AND season = ? AND episode = ? AND status LIKE '%04'",
                                             [best_result.indexerid, best_result.actual_season, best_result.actual_episodes[0]])
            if not sql_results:
                logger.log("Ignoring proper because this episode doesn't have 'DOWNLOADED' status: {name}".format
                           (name=best_result.name))
                continue

            # only keep the proper if we have already downloaded an episode with the same quality
            _, old_quality = Quality.split_composite_status(int(sql_results[0][b'status']))
            if old_quality != best_result.quality:
                logger.log('Ignoring proper because quality is different: {name}'.format(name=best_result.name))
                if cur_proper.name not in processed_propers_names:
                    self.processed_propers.append({'name': cur_proper.name, 'date': cur_proper.date})
                continue

            # only keep the proper if we have already downloaded an episode with the same codec
            release_name = sql_results[0][b'release_name']
            if release_name:
                current_codec = NameParser()._parse_string(release_name).video_codec
                # Ignore proper if codec differs from downloaded release codec
                if all([current_codec, best_result.parse_result.video_codec, best_result.parse_result.video_codec != current_codec]):
                    logger.log('Ignoring proper because codec is different: {name}'.format(name=best_result.name))
                    if best_result.name not in processed_propers_names:
                        self.processed_propers.append({'name': best_result.name, 'date': best_result.date})
                    continue
            else:
                logger.log("Coudn't find a release name in database. Skipping codec comparison for: {name}".format
                           (name=best_result.name), logger.DEBUG)

            # check if we actually want this proper (if it's the right release group and a higher version)
            if best_result.show.is_anime:
                main_db_con = db.DBConnection()
                sql_results = main_db_con.select(
                    b'SELECT release_group, version FROM tv_episodes WHERE showid = ? AND season = ? AND episode = ?',
                    [best_result.indexerid, best_result.actual_season, best_result.actual_episodes[0]])

                old_version = int(sql_results[0][b'version'])
                old_release_group = (sql_results[0][b'release_group'])

                if -1 < old_version < best_result.version:
                    logger.log('Found new anime version {new} to replace existing version {old}: {name}'.format
                               (old=old_version, new=best_result.version, name=best_result.name))
                else:
                    logger.log('Ignoring proper with the same or lower version: {name}'.format
                               (name=best_result.name))
                    if cur_proper.name not in processed_propers_names:
                        self.processed_propers.append({'name': best_result.name, 'date': best_result.date})
                    continue

                if old_release_group != best_result.release_group:
                    logger.log('Ignoring proper from release group {new} instead of current group {old}'.format
                               (new=best_result.release_group, old=old_release_group))
                    if best_result.name not in processed_propers_names:
                        self.processed_propers.append({'name': best_result.name, 'date': best_result.date})
                    continue

            # if the show is in our list and there hasn't been a proper already added for that particular episode
            # then add it to our list of propers
            if best_result.indexerid != -1 and (
                best_result.indexerid, best_result.actual_season, best_result.actual_episodes[0]
            ) not in map(operator.attrgetter('indexerid', 'actual_season', 'actual_episode'), final_propers):
                logger.log('Found a desired proper: {name}'.format(name=best_result.name))
                final_propers.append(best_result)

            if best_result.name not in processed_propers_names:
                self.processed_propers.append({'name': best_result.name, 'date': best_result.date})

        return final_propers

    def _download_propers(self, proper_list):
        """
        Download proper (snatch it).

        :param proper_list:
        """
        for cur_proper in proper_list:

            history_limit = datetime.datetime.today() - datetime.timedelta(days=30)

            main_db_con = db.DBConnection()
            history_results = main_db_con.select(
                b'SELECT resource FROM history '
                b'WHERE showid = ? '
                b'AND season = ? '
                b'AND episode = ? '
                b'AND quality = ? '
                b'AND date >= ? '
                b"AND (action LIKE '%02' OR action LIKE '%04' OR action LIKE '%09' OR action LIKE '%12')",
                [cur_proper.indexerid, cur_proper.actual_season, cur_proper.actual_episode, cur_proper.quality,
                 history_limit.strftime(History.date_format)])

            # make sure that none of the existing history downloads are the same proper we're trying to download
            # if the result exists in history already we need to skip it
            clean_proper_name = self._canonical_name(cur_proper.name, clear_extension=True)
            if any(clean_proper_name == self._canonical_name(cur_result[b'resource'], clear_extension=True)
                   for cur_result in history_results):
                logger.log('This proper {result!r} is already in history, skipping it'.format
                           (result=cur_proper.name), logger.DEBUG)
                continue
            else:
                # make sure that none of the existing history downloads are the same proper we're trying to download
                clean_proper_name = self._canonical_name(cur_proper.name)
                if any(clean_proper_name == self._canonical_name(cur_result[b'resource'])
                       for cur_result in history_results):
                    logger.log('This proper {result!r} is already in history, skipping it'.format
                               (result=cur_proper.name), logger.DEBUG)
                    continue

                cur_proper.create_episode_object()

                # snatch it
                snatch_episode(cur_proper)
                tornado.gen.sleep(cpu_presets[app.CPU_PRESET])

    @staticmethod
    def _canonical_name(name, clear_extension=False):
        ignore_list = {'website', 'mimetype', 'parsing_time'} | {'container'} if clear_extension else {}
        return helpers.canonical_name(name, ignore_list=ignore_list).lower()

    @staticmethod
    def _sanitize_name(name):
        return re.sub(r'[._\-]', ' ', name).lower()

    @staticmethod
    def _set_last_proper_search(when):
        """Record last propersearch in DB.

        :param when: When was the last proper search
        """
        logger.log('Setting the last Proper search in the DB to {0}'.format(when), logger.DEBUG)

        main_db_con = db.DBConnection()
        sql_results = main_db_con.select(b'SELECT last_proper_search FROM info')

        if not sql_results:
            main_db_con.action(b'INSERT INTO info (last_backlog, last_indexer, last_proper_search) VALUES (?,?,?)',
                               [0, 0, str(when)])
        else:
            main_db_con.action(b'UPDATE info SET last_proper_search={0}'.format(when))

    @staticmethod
    def _get_last_proper_search():
        """Find last propersearch from DB."""
        main_db_con = db.DBConnection()
        sql_results = main_db_con.select(b'SELECT last_proper_search FROM info')

        try:
            last_proper_search = datetime.date.fromordinal(int(sql_results[0][b'last_proper_search']))
        except Exception:
            return datetime.date.fromordinal(1)

        return last_proper_search
