# coding=utf-8
# Author: Nic Wolfe <nic@wolfeden.ca>
# URL: http://code.google.com/p/sickbeard/
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


import datetime
import threading

import sickbeard

from sickbeard import db, scheduler
from sickbeard import search_queue
from sickbeard import logger
from sickbeard import ui
from sickbeard import common


class BacklogSearchScheduler(scheduler.Scheduler):
    def forceSearch(self):
        self.action._set_lastBacklog(1)
        self.lastRun = datetime.datetime.fromordinal(1)

    def nextRun(self):
        if self.action._lastBacklog <= 1:
            return datetime.date.today()
        else:
            return datetime.date.fromordinal(self.action._lastBacklog + self.action.cycleTime)


class BacklogSearcher(object):
    def __init__(self):

        self._lastBacklog = self._get_lastBacklog()
        self.cycleTime = sickbeard.BACKLOG_FREQUENCY / 60 / 24
        self.lock = threading.Lock()
        self.amActive = False
        self.amPaused = False
        self.amWaiting = False

        self._resetPI()

    def _resetPI(self):
        self.percentDone = 0
        self.currentSearchInfo = {'title': 'Initializing'}

    def getProgressIndicator(self):
        if self.amActive:
            return ui.ProgressIndicator(self.percentDone, self.currentSearchInfo)
        else:
            return None

    def am_running(self):
        logger.log(u"amWaiting: " + str(self.amWaiting) + ", amActive: " + str(self.amActive), logger.DEBUG)
        return (not self.amWaiting) and self.amActive

    def searchBacklog(self, which_shows=None):

        if self.amActive:
            logger.log(u"Backlog is still running, not starting it again", logger.DEBUG)
            return
        
        if sickbeard.searchQueueScheduler.action.is_manualsearch_in_progress():
            logger.log(u"Manual search is running. Can't start Backlog Search", logger.WARNING)
            return

        self.amActive = True
        self.amPaused = False

        if which_shows:
            show_list = which_shows
        else:
            show_list = sickbeard.showList

        self._get_lastBacklog()

        curDate = datetime.date.today().toordinal()
        fromDate = datetime.date.fromordinal(1)

        if not which_shows and not ((curDate - self._lastBacklog) >= self.cycleTime):
            logger.log(u"Running limited backlog on missed episodes " + str(sickbeard.BACKLOG_DAYS) + " day(s) and older only")
            fromDate = datetime.date.today() - datetime.timedelta(days=sickbeard.BACKLOG_DAYS)

        # go through non air-by-date shows and see if they need any episodes
        for curShow in show_list:

            if curShow.paused:
                continue

            segments = self._get_segments(curShow, fromDate)

            for season, segment in segments.iteritems():
                self.currentSearchInfo = {'title': curShow.name + " Season " + str(season)}

                backlog_queue_item = search_queue.BacklogQueueItem(curShow, segment)
                sickbeard.searchQueueScheduler.action.add_item(backlog_queue_item)  # @UndefinedVariable

            if not segments:
                logger.log(u"Nothing needs to be downloaded for %s, skipping" % curShow.name, logger.DEBUG)

        # don't consider this an actual backlog search if we only did recent eps
        # or if we only did certain shows
        if fromDate == datetime.date.fromordinal(1) and not which_shows:
            self._set_lastBacklog(curDate)

        self.amActive = False
        self._resetPI()

    def _get_lastBacklog(self):

        logger.log(u"Retrieving the last check time from the DB", logger.DEBUG)

        main_db_con = db.DBConnection()
        sql_results = main_db_con.select("SELECT last_backlog FROM info")

        if not sql_results:
            lastBacklog = 1
        elif sql_results[0]["last_backlog"] is None or sql_results[0]["last_backlog"] == "":
            lastBacklog = 1
        else:
            lastBacklog = int(sql_results[0]["last_backlog"])
            if lastBacklog > datetime.date.today().toordinal():
                lastBacklog = 1

        self._lastBacklog = lastBacklog
        return self._lastBacklog

    def _get_segments(self, show, fromDate):
        wanted = {}
        if show.paused:
            logger.log(u"Skipping backlog for %s because the show is paused" % show.name, logger.DEBUG)
            return wanted

        allowed_qualities, preferred_qualities = common.Quality.splitQuality(show.quality)

        logger.log(u"Seeing if we need anything from %s" % show.name, logger.DEBUG)

        con = db.DBConnection()
        sql_results = con.select(
            "SELECT status, season, episode FROM tv_episodes WHERE airdate > ? AND showid = ?",
            [fromDate.toordinal(), show.indexerid]
        )

        # check through the list of statuses to see if we want any
        for sql_result in sql_results:
            cur_status, cur_quality = common.Quality.splitCompositeStatus(int(sql_result["status"] or -1))

            if cur_status not in {common.WANTED, common.DOWNLOADED, common.SNATCHED, common.SNATCHED_PROPER}:
                continue

            if cur_status != common.WANTED:
                if preferred_qualities:
                    if cur_quality in preferred_qualities:
                        continue
                elif cur_quality in allowed_qualities:
                    continue

            ep_obj = show.getEpisode(sql_result["season"], sql_result["episode"])

            if ep_obj.season not in wanted:
                wanted[ep_obj.season] = [ep_obj]
            else:
                wanted[ep_obj.season].append(ep_obj)

        return wanted

    def _set_lastBacklog(self, when):

        logger.log(u"Setting the last backlog in the DB to " + str(when), logger.DEBUG)

        main_db_con = db.DBConnection()
        sql_results = main_db_con.select("SELECT last_backlog FROM info")

        if not sql_results:
            main_db_con.action("INSERT INTO info (last_backlog, last_indexer) VALUES (?,?)", [str(when), 0])
        else:
            main_db_con.action("UPDATE info SET last_backlog=" + str(when))

    def run(self, force=False):
        try:
            self.searchBacklog()
        except:
            self.amActive = False
            raise
