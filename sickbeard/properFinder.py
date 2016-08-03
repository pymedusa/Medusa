# coding=utf-8
# Author: Nic Wolfe <nic@wolfeden.ca>
#
# Git: https://github.com/PyMedusa/SickRage.git
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

from __future__ import unicode_literals

import time
import datetime
import operator
import threading
import traceback
import errno
from socket import timeout as SocketTimeout
from requests import exceptions as requests_exceptions
import sickbeard

from sickbeard import db
from sickbeard import logger
from sickbeard.helpers import remove_non_release_groups
from sickbeard.search import snatchEpisode
from sickbeard.search import pickBestResult
from sickbeard.common import DOWNLOADED, SNATCHED, SNATCHED_PROPER, Quality, cpu_presets
from sickrage.helper.exceptions import AuthException, ex
from sickrage.show.History import History
from sickrage.helper.common import enabled_providers
from sickbeard.name_parser.parser import NameParser, InvalidNameException, InvalidShowException


class ProperFinder(object):  # pylint: disable=too-few-public-methods
    def __init__(self):
        self.amActive = False
        self.processed_propers = []

    def run(self, force=False):  # pylint: disable=unused-argument
        """
        Start looking for new propers

        :param force: Start even if already running (currently not used, defaults to False)
        """
        logger.log('Beginning the search for new propers')

        if self.amActive:
            logger.log('Find propers is still running, not starting it again', logger.DEBUG)
            return

        if sickbeard.forcedSearchQueueScheduler.action.is_forced_search_in_progress():
            logger.log("Manual search is running. Can't start Find propers", logger.WARNING)
            return

        self.amActive = True

        propers = self._get_proper_results()

        if propers:
            self._downloadPropers(propers)

        self._set_lastProperSearch(datetime.datetime.today().toordinal())

        run_at = ''
        if None is sickbeard.properFinderScheduler.start_time:
            run_in = sickbeard.properFinderScheduler.lastRun + sickbeard.properFinderScheduler.cycleTime - datetime.datetime.now()
            hours, remainder = divmod(run_in.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            run_at = ', next check in approx. {0}'.format(
                '{0}h, {1}m'.format(hours, minutes) if 0 < hours else '{0}m, {1}s'.format(minutes, seconds))

        logger.log('Completed the search for new propers{0}'.format(run_at))

        self.amActive = False

    def _get_proper_results(self):  # pylint: disable=too-many-locals, too-many-branches, too-many-statements
        """
        Retrieve a list of recently aired episodes, and search for these episodes in the different providers.
        """
        propers = {}

        # for each provider get a list of the
        original_thread_name = threading.currentThread().name
        providers = enabled_providers('backlog')

        # Get the recently aired (last 2 days) shows from db
        search_date = datetime.datetime.today() - datetime.timedelta(days=2)
        main_db_con = db.DBConnection()
        search_qualities = list(set(Quality.DOWNLOADED + Quality.SNATCHED + Quality.SNATCHED_BEST))
        search_q_params = ','.join('?' for _ in search_qualities)
        recently_aired = main_db_con.select(
            b'SELECT s.show_name, e.showid, e.season, e.episode, e.status, e.airdate'
            b' FROM tv_episodes AS e'
            b' INNER JOIN tv_shows AS s ON (e.showid = s.indexer_id)'
            b' WHERE e.airdate >= ?'
            b' AND e.status IN ({0})'.format(search_q_params),
            [search_date.toordinal()] + search_qualities
        )

        if not recently_aired:
            logger.log('No recently aired new episodes, nothing to search for')
            return []

        # Loop through the providers, and search for releases
        for cur_provider in providers:
            threading.currentThread().name = '{thread} :: [{provider}]'.format(thread=original_thread_name, provider=cur_provider.name)

            logger.log('Searching for any new PROPER releases from {provider}'.format
                       (provider=cur_provider.name))

            try:
                cur_propers = cur_provider.find_propers(recently_aired)
            except AuthException as e:
                logger.log('Authentication error: {error}'.format
                           (error=ex(e)), logger.DEBUG)
                continue
            except (SocketTimeout) as e:
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
                logger.log('Content-Encoding was gzip, but content was not compressed while searching for propers in {provider}, skipping: {error}'.format
                           (provider=cur_provider.name, error=ex(e)), logger.DEBUG)
                continue
            except Exception as e:
                if 'ECONNRESET' in e or (hasattr(e, 'errno') and e.errno == errno.ECONNRESET):
                    logger.log('Connection reset by peer while searching for propers in {provider}, skipping: {error}'.format
                               (provider=cur_provider.name, error=ex(e)), logger.DEBUG)
                else:
                    logger.log('Unknown exception while searching for propers in {provider}, skipping: {error}'.format
                               (provider=cur_provider.name, error=ex(e)), logger.DEBUG)
                    logger.log(traceback.format_exc(), logger.DEBUG)
                continue

            # if they haven't been added by a different provider than add the proper to the list
            for proper in cur_propers:
                name = self._genericName(proper.name, remove=False)
                if name not in propers:
                    logger.log('Found new possible proper result: {name}'.format
                               (name=proper.name), logger.DEBUG)
                    proper.provider = cur_provider
                    propers[name] = proper

        threading.currentThread().name = original_thread_name

        # take the list of unique propers and get it sorted by
        sorted_propers = sorted(propers.values(), key=operator.attrgetter('date'), reverse=True)
        final_propers = []

        # Keep only last 100 items of processed propers:
        self.processed_propers = self.processed_propers[-100:]

        for cur_proper in sorted_propers:

            if cur_proper.name in self.processed_propers:
                logger.log(u'Proper already processed. Skipping: {0}'.format(cur_proper.name), logger.DEBUG)
                continue

            try:
                parse_result = NameParser(False).parse(cur_proper.name)
            except (InvalidNameException, InvalidShowException) as error:
                logger.log('{0}'.format(error), logger.DEBUG)
                continue

            if not parse_result.proper_tags:
                logger.log('Skipping non-proper: {name}'.format(name=cur_proper.name))
                continue

            logger.log('Proper tags for {proper}: {tags}'.format
                       (proper=cur_proper.name, tags=parse_result.proper_tags), logger.DEBUG)

            if not parse_result.series_name:
                logger.log('Ignoring invalid show: {name}'.format
                           (name=cur_proper.name), logger.DEBUG)
                self.processed_propers.append(cur_proper.name)
                continue

            if not parse_result.episode_numbers:
                logger.log('Ignoring full season instead of episode: {name}'.format
                           (name=cur_proper.name), logger.DEBUG)
                self.processed_propers.append(cur_proper.name)
                continue

            logger.log('Successful match! Matched {original_name} to show {new_name}'.format
                       (original_name=parse_result.original_name, new_name=parse_result.show.name), logger.DEBUG)

            # set the indexerid in the db to the show's indexerid
            cur_proper.indexerid = parse_result.show.indexerid

            # set the indexer in the db to the show's indexer
            cur_proper.indexer = parse_result.show.indexer

            # populate our Proper instance
            cur_proper.show = parse_result.show
            cur_proper.season = parse_result.season_number if parse_result.season_number is not None else 1
            cur_proper.episode = parse_result.episode_numbers[0]
            cur_proper.release_group = parse_result.release_group
            cur_proper.version = parse_result.version
            cur_proper.quality = Quality.nameQuality(cur_proper.name, parse_result.is_anime)
            cur_proper.content = None
            cur_proper.proper_tags = parse_result.proper_tags

            # filter release
            best_result = pickBestResult(cur_proper, parse_result.show)
            if not best_result:
                logger.log('Rejected proper due to release filters: {name}'.format
                           (name=cur_proper.name))
                self.processed_propers.append(cur_proper.name)
                continue

            # only get anime proper if it has release group and version
            if best_result.show.is_anime:
                if not best_result.release_group and best_result.version == -1:
                    logger.log('Ignoring proper without release group and version: {name}'.format
                               (name=best_result.name))
                    self.processed_propers.append(cur_proper.name)
                    continue

            # check if we actually want this proper (if it's the right quality)
            main_db_con = db.DBConnection()
            sql_results = main_db_con.select(b'SELECT status FROM tv_episodes WHERE showid = ? AND season = ? AND episode = ?',
                                             [best_result.indexerid, best_result.season, best_result.episode])
            if not sql_results:
                logger.log('Ignoring proper with incorrect quality: {name}'.format
                           (name=best_result.name))
                self.processed_propers.append(cur_proper.name)
                continue

            # only keep the proper if we have already retrieved the same quality ep (don't get better/worse ones)
            old_status, old_quality = Quality.splitCompositeStatus(int(sql_results[0][b'status']))
            if old_status not in (DOWNLOADED, SNATCHED) or old_quality != best_result.quality:
                logger.log('Ignoring proper because quality is different or episode is already archived: {name}'.format
                           (name=best_result.name))
                self.processed_propers.append(cur_proper.name)
                continue

            # check if we actually want this proper (if it's the right release group and a higher version)
            if best_result.show.is_anime:
                main_db_con = db.DBConnection()
                sql_results = main_db_con.select(
                    b'SELECT release_group, version FROM tv_episodes WHERE showid = ? AND season = ? AND episode = ?',
                    [best_result.indexerid, best_result.season, best_result.episode])

                old_version = int(sql_results[0][b'version'])
                old_release_group = (sql_results[0][b'release_group'])

                if -1 < old_version < best_result.version:
                    logger.log('Found new anime version {new} to replace existing version {old}: {name}'.format
                               (old=old_version, new=best_result.version, name=best_result.name))
                else:
                    logger.log('Ignoring proper with the same or lower version: {name}'.format
                               (name=best_result.name))
                    self.processed_propers.append(cur_proper.name)
                    continue

                if old_release_group != best_result.release_group:
                    logger.log('Ignoring proper from release group {new} instead of current group {old}'.format
                               (new=best_result.release_group, old=old_release_group))
                    self.processed_propers.append(cur_proper.name)
                    continue

            # if the show is in our list and there hasn't been a proper already added for that particular episode then add it to our list of propers
            if best_result.indexerid != -1 and (best_result.indexerid, best_result.season, best_result.episode) not in map(
                    operator.attrgetter('indexerid', 'season', 'episode'), final_propers):
                logger.log('Found a desired proper: {name}'.format(name=best_result.name))
                final_propers.append(best_result)

            self.processed_propers.append(cur_proper.name)

        return final_propers

    def _downloadPropers(self, proper_list):
        """
        Download proper (snatch it)

        :param proper_list:
        """

        for cur_proper in proper_list:

            history_limit = datetime.datetime.today() - datetime.timedelta(days=30)

            # make sure the episode has been downloaded before
            main_db_con = db.DBConnection()
            history_results = main_db_con.select(
                b'SELECT resource FROM history '
                b'WHERE showid = ? '
                b'AND season = ? '
                b'AND episode = ? '
                b'AND quality = ? '
                b'AND date >= ? '
                b"AND (action LIKE '%2' OR action LIKE '%4')",
                [cur_proper.indexerid, cur_proper.season, cur_proper.episode, cur_proper.quality,
                 history_limit.strftime(History.date_format)])

            # make sure that none of the existing history downloads are the same proper we're trying to download
            # if the result exists in history already we need to skip it
            clean_proper_name = self._genericName(cur_proper.name, clean_proper=True)
            if any(clean_proper_name == self._genericName(cur_result[b'resource'], clean_proper=True)
                   for cur_result in history_results):
                logger.log('This proper {result!r} is already in history, skipping it'.format
                           (result=cur_proper.name), logger.DEBUG)
                continue
            else:
                # make sure that none of the existing history downloads are the same proper we're trying to download
                clean_proper_name = self._genericName(cur_proper.name)
                if any(clean_proper_name == self._genericName(cur_result[b'resource'])
                       for cur_result in history_results):
                    logger.log('This proper {result!r} is already in history, skipping it'.format
                               (result=cur_proper.name), logger.DEBUG)
                    continue

                # get the episode object
                ep_obj = cur_proper.show.get_episode(cur_proper.season, cur_proper.episode)

                # make the result object
                result = cur_proper.provider.get_result([ep_obj])
                result.show = cur_proper.show
                result.url = cur_proper.url
                result.name = cur_proper.name
                result.quality = cur_proper.quality
                result.release_group = cur_proper.release_group
                result.version = cur_proper.version
                result.content = cur_proper.content
                result.seeders = cur_proper.seeders
                result.leechers = cur_proper.leechers
                result.size = cur_proper.size
                result.pubdate = cur_proper.pubdate
                result.hash = cur_proper.hash
                result.proper_tags = cur_proper.proper_tags

                # snatch it
                snatchEpisode(result)
                time.sleep(cpu_presets[sickbeard.CPU_PRESET])

    @staticmethod
    def _genericName(name, **kwargs):
        if kwargs.pop('remove', True):
            name = remove_non_release_groups(name, clean_proper=kwargs.pop('clean_proper', False))
        return name.replace('.', ' ').replace('-', ' ').replace('_', ' ').lower()

    @staticmethod
    def _set_lastProperSearch(when):
        """
        Record last propersearch in DB

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
    def _get_lastProperSearch():
        """
        Find last propersearch from DB
        """

        main_db_con = db.DBConnection()
        sql_results = main_db_con.select(b'SELECT last_proper_search FROM info')

        try:
            last_proper_search = datetime.date.fromordinal(int(sql_results[0][b'last_proper_search']))
        except Exception:
            return datetime.date.fromordinal(1)

        return last_proper_search
