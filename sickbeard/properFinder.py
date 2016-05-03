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
from sickbeard import helpers, logger
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
                curPropers = cur_provider.find_propers(search_date)
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
            for proper in curPropers:
                if not re.search(r'(^|[\. _-])(proper|repack|real)([\. _-]|$)', proper.name, re.I):
                    logger.log(u'Skipping non-proper: {name}'.format(name=proper.name))
                    continue

                name = self._genericName(proper.name)
                if name not in propers:
                    logger.log(u'Found new proper result: {name}'.format
                               (name=proper.name), logger.DEBUG)
                    proper.provider = cur_provider
                    propers[name] = proper

        threading.currentThread().name = original_thread_name

        # take the list of unique propers and get it sorted by
        sortedPropers = sorted(propers.values(), key=operator.attrgetter('date'), reverse=True)
        finalPropers = []

        for curProper in sortedPropers:
            try:
                parse_result = NameParser(False).parse(curProper.name)
            except (InvalidNameException, InvalidShowException) as error:
                logger.log(u'{}'.format(error), logger.DEBUG)
                continue

            if not parse_result.series_name:
                logger.log(u"Ignoring invalid show: {name}".format
                           (name=curProper.name), logger.DEBUG)
                continue

            if not parse_result.episode_numbers:
                logger.log(u"Ignoring full season instead of episode: {name}".format
                           (name=curProper.name), logger.DEBUG)
                continue

            logger.log(u'Successful match! Matched {} to show {}'.format
                       (parse_result.original_name, parse_result.show.name), logger.DEBUG)

            # set the indexerid in the db to the show's indexerid
            curProper.indexerid = parse_result.show.indexerid

            # set the indexer in the db to the show's indexer
            curProper.indexer = parse_result.show.indexer

            # populate our Proper instance
            curProper.show = parse_result.show
            curProper.season = parse_result.season_number if parse_result.season_number is not None else 1
            curProper.episode = parse_result.episode_numbers[0]
            curProper.release_group = parse_result.release_group
            curProper.version = parse_result.version
            curProper.quality = Quality.nameQuality(curProper.name, parse_result.is_anime)
            curProper.content = None

            # filter release
            bestResult = pickBestResult(curProper, parse_result.show)
            if not bestResult:
                logger.log(u'Rejected proper due to release filters: {name}'.format
                           (name=curProper.name))
                continue

            # only get anime proper if it has release group and version
            if bestResult.show.is_anime:
                if not bestResult.release_group and bestResult.version == -1:
                    logger.log(u"Ignoring proper without release group and version: {name}".format
                               (name=bestResult.name))
                    continue

            # check if we actually want this proper (if it's the right quality)
            main_db_con = db.DBConnection()
            sql_results = main_db_con.select('SELECT status FROM tv_episodes WHERE showid = ? AND season = ? AND episode = ?',
                                             [bestResult.indexerid, bestResult.season, bestResult.episode])
            if not sql_results:
                logger.log(u"Ignoring proper with incorrect quality: {name}".format
                           (name=bestResult.name))
                continue

            # only keep the proper if we have already retrieved the same quality ep (don't get better/worse ones)
            oldStatus, oldQuality = Quality.splitCompositeStatus(int(sql_results[0]['status']))
            if oldStatus not in (DOWNLOADED, SNATCHED) or oldQuality != bestResult.quality:
                logger.log(u"Ignoring proper already snatched or downloaded: {name}".format
                           (name=bestResult.name))
                continue

            # check if we actually want this proper (if it's the right release group and a higher version)
            if bestResult.show.is_anime:
                main_db_con = db.DBConnection()
                sql_results = main_db_con.select(
                    'SELECT release_group, version FROM tv_episodes WHERE showid = ? AND season = ? AND episode = ?',
                    [bestResult.indexerid, bestResult.season, bestResult.episode])

                old_version = int(sql_results[0]['version'])
                old_release_group = (sql_results[0]['release_group'])

                if -1 < old_version < bestResult.version:
                    logger.log(u'Found new anime version {new} to replace existing version {old}: {name}'.format
                               (old=old_version, new=bestResult.version, name=bestResult.name))
                else:
                    logger.log(u'Ignoring proper with the same or lower version: {name}'.format
                               (name=bestResult.name))
                    continue

                if old_release_group != bestResult.release_group:
                    logger.log(u"Ignoring proper from release group {new} instead of current group {old}".format
                               (new=bestResult.release_group, old=old_release_group))
                    continue

            # if the show is in our list and there hasn't been a proper already added for that particular episode then add it to our list of propers
            if bestResult.indexerid != -1 and (bestResult.indexerid, bestResult.season, bestResult.episode) not in map(
                    operator.attrgetter('indexerid', 'season', 'episode'), finalPropers):
                logger.log(u'Found a desired proper: {name}'.format(name=bestResult.name))
                finalPropers.append(bestResult)

        return finalPropers

    def _downloadPropers(self, properList):
        """
        Download proper (snatch it)

        :param properList:
        """

        for curProper in properList:

            historyLimit = datetime.datetime.today() - datetime.timedelta(days=30)

            # make sure the episode has been downloaded before
            main_db_con = db.DBConnection()
            historyResults = main_db_con.select(
                "SELECT resource FROM history " +
                "WHERE showid = ? AND season = ? AND episode = ? AND quality = ? AND date >= ? " +
                "AND action IN (" + ",".join([str(x) for x in Quality.SNATCHED + Quality.DOWNLOADED]) + ")",
                [curProper.indexerid, curProper.season, curProper.episode, curProper.quality,
                 historyLimit.strftime(History.date_format)])

            # make sure that none of the existing history downloads are the same proper we're trying to download
            clean_proper_name = self._genericName(helpers.remove_non_release_groups(curProper.name))
            isSame = False
            for curResult in historyResults:
                # if the result exists in history already we need to skip it
                if self._genericName(helpers.remove_non_release_groups(curResult["resource"])) == clean_proper_name:
                    isSame = True
                    break
            if isSame:
                logger.log(u"This proper is already in history, skipping it", logger.DEBUG)
                continue

            else:

                # make sure that none of the existing history downloads are the same proper we're trying to download
                clean_proper_name = self._genericName(helpers.remove_non_release_groups(curProper.name))
                isSame = False
                for curResult in historyResults:
                    # if the result exists in history already we need to skip it
                    if self._genericName(helpers.remove_non_release_groups(curResult["resource"])) == clean_proper_name:
                        isSame = True
                        break
                if isSame:
                    logger.log(u"This proper is already in history, skipping it", logger.DEBUG)
                    continue

                # get the episode object
                epObj = curProper.show.getEpisode(curProper.season, curProper.episode)

                # make the result object
                result = curProper.provider.get_result([epObj])
                result.show = curProper.show
                result.url = curProper.url
                result.name = curProper.name
                result.quality = curProper.quality
                result.release_group = curProper.release_group
                result.version = curProper.version
                result.content = curProper.content
                result.seeders = curProper.seeders
                result.leechers = curProper.leechers
                result.size = curProper.size
                result.pubdate = curProper.pubdate
                result.hash = curProper.hash

                # snatch it
                snatchEpisode(result, SNATCHED_PROPER)
                time.sleep(cpu_presets[sickbeard.CPU_PRESET])

    @staticmethod
    def _genericName(name):
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
