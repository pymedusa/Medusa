# coding=utf-8
# Author: Nic Wolfe <nic@wolfeden.ca>

# Git: https://github.com/PyMedusa/SickRage.git
#
# This file is part of SickRage.
#
# SickRage is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# SickRage is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with SickRage. If not, see <http://www.gnu.org/licenses/>.

import re
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
from guessit import guessit

class ProperFinder(object):  # pylint: disable=too-few-public-methods
    def __init__(self):
        self.amActive = False

    def run(self, force=False):  # pylint: disable=unused-argument
        """
        Start looking for new propers

        :param force: Start even if already running (currently not used, defaults to False)
        """
        logger.log(u"Beginning the search for new propers")

        if self.amActive:
            logger.log(u"Find propers is still running, not starting it again", logger.DEBUG)
            return

        if sickbeard.forcedSearchQueueScheduler.action.is_forced_search_in_progress():
            logger.log(u"Manual search is running. Can't start Find propers", logger.WARNING)
            return

        self.amActive = True

        propers = self._getProperList()

        if propers:
            self._downloadPropers(propers)

        self._set_lastProperSearch(datetime.datetime.today().toordinal())

        run_at = ""
        if None is sickbeard.properFinderScheduler.start_time:
            run_in = sickbeard.properFinderScheduler.lastRun + sickbeard.properFinderScheduler.cycleTime - datetime.datetime.now()
            hours, remainder = divmod(run_in.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            run_at = u", next check in approx. " + (
                "%dh, %dm" % (hours, minutes) if 0 < hours else "%dm, %ds" % (minutes, seconds))

        logger.log(u"Completed the search for new propers%s" % run_at)

        self.amActive = False

    def _getProperList(self):  # pylint: disable=too-many-locals, too-many-branches, too-many-statements
        """
        Walk providers for propers
        """
        propers = {}

        search_date = datetime.datetime.today() - datetime.timedelta(days=2)

        # for each provider get a list of the
        original_thread_name = threading.currentThread().name
        providers = enabled_providers('backlog')
        for cur_provider in providers:
            threading.currentThread().name = '{thread} :: [{provider}]'.format(thread=original_thread_name, provider=cur_provider.name)

            logger.log(u"Searching for any new PROPER releases from {provider}".format
                       (provider=cur_provider.name))

            try:
                cur_propers = cur_provider.find_propers(search_date)
            except AuthException as e:
                logger.log(u"Authentication error: {error}".format
                           (error=ex(e)), logger.DEBUG)
                continue
            except (SocketTimeout) as e:
                logger.log(u"Socket time out while searching for propers in {provider}, skipping: {error}".format
                           (provider=cur_provider.name, error=ex(e)), logger.DEBUG)
                continue
            except (requests_exceptions.HTTPError, requests_exceptions.TooManyRedirects) as e:
                logger.log(u"HTTP error while searching for propers in {provider}, skipping: {error}".format
                           (provider=cur_provider.name, error=ex(e)), logger.DEBUG)
                continue
            except requests_exceptions.ConnectionError as e:
                logger.log(u"Connection error while searching for propers in {provider}, skipping: {error}".format
                           (provider=cur_provider.name, error=ex(e)), logger.DEBUG)
                continue
            except requests_exceptions.Timeout as e:
                logger.log(u"Connection timed out while searching for propers in {provider}, skipping: {error}".format
                           (provider=cur_provider.name, error=ex(e)), logger.DEBUG)
                continue
            except requests_exceptions.ContentDecodingError as e:
                logger.log(u"Content-Encoding was gzip, but content was not compressed while searching for propers in {provider}, skipping: {error}".format
                           (provider=cur_provider.name, error=ex(e)), logger.DEBUG)
                continue
            except Exception as e:
                if u'ECONNRESET' in e or (hasattr(e, 'errno') and e.errno == errno.ECONNRESET):
                    logger.log(u"Connection reset by peer while searching for propers in {provider}, skipping: {error}".format
                               (provider=cur_provider.name, error=ex(e)), logger.DEBUG)
                else:
                    logger.log(u"Unknown exception while searching for propers in {provider}, skipping: {error}".format
                               (provider=cur_provider.name, error=ex(e)), logger.DEBUG)
                    logger.log(traceback.format_exc(), logger.DEBUG)
                continue

            # if they haven't been added by a different provider than add the proper to the list
            for proper in cur_propers:
                guess = guessit(proper.name)
                if not guess.get('proper_count'):
                    logger.log(u'Skipping non-proper: {name}'.format(name=proper.name))
                    continue

                name = self._genericName(proper.name, remove=False)
                if name not in propers:
                    logger.log(u'Found new proper result: {name}'.format
                               (name=proper.name), logger.DEBUG)
                    proper.provider = cur_provider
                    propers[name] = proper

        threading.currentThread().name = original_thread_name

        # take the list of unique propers and get it sorted by
        sorted_propers = sorted(propers.values(), key=operator.attrgetter('date'), reverse=True)
        final_propers = []

        for cur_proper in sorted_propers:
            try:
                parse_result = NameParser(False).parse(cur_proper.name)
            except (InvalidNameException, InvalidShowException) as error:
                logger.log(u'{}'.format(error), logger.DEBUG)
                continue

            if not parse_result.series_name:
                logger.log(u"Ignoring invalid show: {name}".format
                           (name=cur_proper.name), logger.DEBUG)
                continue

            if not parse_result.episode_numbers:
                logger.log(u"Ignoring full season instead of episode: {name}".format
                           (name=cur_proper.name), logger.DEBUG)
                continue

            logger.log(u'Successful match! Matched {} to show {}'.format
                       (parse_result.original_name, parse_result.show.name), logger.DEBUG)

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

            # filter release
            best_result = pickBestResult(cur_proper, parse_result.show)
            if not best_result:
                logger.log(u'Rejected proper due to release filters: {name}'.format
                           (name=cur_proper.name))
                continue

            # only get anime proper if it has release group and version
            if best_result.show.is_anime:
                if not best_result.release_group and best_result.version == -1:
                    logger.log(u"Ignoring proper without release group and version: {name}".format
                               (name=best_result.name))
                    continue

            # check if we actually want this proper (if it's the right quality)
            main_db_con = db.DBConnection()
            sql_results = main_db_con.select('SELECT status FROM tv_episodes WHERE showid = ? AND season = ? AND episode = ?',
                                             [best_result.indexerid, best_result.season, best_result.episode])
            if not sql_results:
                logger.log(u"Ignoring proper with incorrect quality: {name}".format
                           (name=best_result.name))
                continue

            # only keep the proper if we have already retrieved the same quality ep (don't get better/worse ones)
            old_status, old_quality = Quality.splitCompositeStatus(int(sql_results[0]['status']))
            if old_status not in (DOWNLOADED, SNATCHED) or old_quality != best_result.quality:
                logger.log(u"Ignoring proper because quality is different or episode is already archived: {name}".format
                           (name=best_result.name))
                continue

            # check if we actually want this proper (if it's the right release group and a higher version)
            if best_result.show.is_anime:
                main_db_con = db.DBConnection()
                sql_results = main_db_con.select(
                    'SELECT release_group, version FROM tv_episodes WHERE showid = ? AND season = ? AND episode = ?',
                    [best_result.indexerid, best_result.season, best_result.episode])

                old_version = int(sql_results[0]['version'])
                old_release_group = (sql_results[0]['release_group'])

                if -1 < old_version < best_result.version:
                    logger.log(u'Found new anime version {new} to replace existing version {old}: {name}'.format
                               (old=old_version, new=best_result.version, name=best_result.name))
                else:
                    logger.log(u'Ignoring proper with the same or lower version: {name}'.format
                               (name=best_result.name))
                    continue

                if old_release_group != best_result.release_group:
                    logger.log(u"Ignoring proper from release group {new} instead of current group {old}".format
                               (new=best_result.release_group, old=old_release_group))
                    continue

            # if the show is in our list and there hasn't been a proper already added for that particular episode then add it to our list of propers
            if best_result.indexerid != -1 and (best_result.indexerid, best_result.season, best_result.episode) not in map(
                    operator.attrgetter('indexerid', 'season', 'episode'), final_propers):
                logger.log(u'Found a desired proper: {name}'.format(name=best_result.name))
                final_propers.append(best_result)

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
                "SELECT resource FROM history "
                "WHERE showid = ? "
                "AND season = ? "
                "AND episode = ? "
                "AND quality = ? "
                "AND date >= ? "
                "AND (action LIKE '%2' OR action LIKE '%4')",
                [cur_proper.indexerid, cur_proper.season, cur_proper.episode, cur_proper.quality,
                 history_limit.strftime(History.date_format)])

            # make sure that none of the existing history downloads are the same proper we're trying to download
            # if the result exists in history already we need to skip it
            clean_proper_name = self._genericName(cur_proper.name, clean_proper=True)
            if any(clean_proper_name == self._genericName(cur_result[b'resource'], clean_proper=True)
                   for cur_result in history_results):
                logger.log(u'This proper {result!r} is already in history, skipping it'.format
                           (result=cur_proper.name), logger.DEBUG)
                continue
            else:
                # make sure that none of the existing history downloads are the same proper we're trying to download
                clean_proper_name = self._genericName(cur_proper.name)
                if any(clean_proper_name == self._genericName(cur_result[b'resource'])
                       for cur_result in history_results):
                    logger.log(u'This proper {result!r} is already in history, skipping it'.format
                               (result=cur_proper.name), logger.DEBUG)
                    continue

                # get the episode object
                ep_obj = cur_proper.show.getEpisode(cur_proper.season, cur_proper.episode)

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

                # snatch it
                snatchEpisode(result, SNATCHED_PROPER)
                time.sleep(cpu_presets[sickbeard.CPU_PRESET])

    @staticmethod
    def _genericName(name, **kwargs):
        if kwargs.pop('remove', True):
            name = remove_non_release_groups(name, clean_proper=kwargs.pop('clean_proper', False))
        return name.replace(".", " ").replace("-", " ").replace("_", " ").lower()

    @staticmethod
    def _set_lastProperSearch(when):
        """
        Record last propersearch in DB

        :param when: When was the last proper search
        """

        logger.log(u"Setting the last Proper search in the DB to " + str(when), logger.DEBUG)

        main_db_con = db.DBConnection()
        sql_results = main_db_con.select("SELECT last_proper_search FROM info")

        if not sql_results:
            main_db_con.action("INSERT INTO info (last_backlog, last_indexer, last_proper_search) VALUES (?,?,?)",
                               [0, 0, str(when)])
        else:
            main_db_con.action("UPDATE info SET last_proper_search=" + str(when))

    @staticmethod
    def _get_lastProperSearch():
        """
        Find last propersearch from DB
        """

        main_db_con = db.DBConnection()
        sql_results = main_db_con.select("SELECT last_proper_search FROM info")

        try:
            last_proper_search = datetime.date.fromordinal(int(sql_results[0]["last_proper_search"]))
        except Exception:
            return datetime.date.fromordinal(1)

        return last_proper_search
