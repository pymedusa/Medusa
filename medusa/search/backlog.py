# coding=utf-8
# Author: Nic Wolfe <nic@wolfeden.ca>
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


import datetime
import threading

from six import iteritems
from .queue import BacklogQueueItem

from .. import app, common, db, logger, scheduler, ui

from ..helper.common import episode_num


class BacklogSearchScheduler(scheduler.Scheduler):
    def forceSearch(self):
        self.action._set_last_backlog(1)
        self.lastRun = datetime.datetime.fromordinal(1)

    def next_run(self):
        if self.action._last_backlog <= 1:
            return datetime.date.today()
        else:
            return datetime.date.fromordinal(self.action._last_backlog + self.action.cycleTime)


class BacklogSearcher(object):
    def __init__(self):

        self._last_backlog = self._get_last_backlog()
        self.cycleTime = app.BACKLOG_FREQUENCY / 60 / 24
        self.lock = threading.Lock()
        self.amActive = False
        self.amPaused = False
        self.amWaiting = False
        self.currentSearchInfo = {}

        self._resetPI()

    def _resetPI(self):
        self.percentDone = 0
        self.currentSearchInfo = {'title': 'Initializing'}

    def get_progress_indicator(self):
        if self.amActive:
            return ui.ProgressIndicator(self.percentDone, self.currentSearchInfo)
        else:
            return None

    def am_running(self):
        logger.log(u"amWaiting: " + str(self.amWaiting) + ", amActive: " + str(self.amActive), logger.DEBUG)
        return (not self.amWaiting) and self.amActive

    def search_backlog(self, which_shows=None):

        if self.amActive:
            logger.log(u"Backlog is still running, not starting it again", logger.DEBUG)
            return

        if app.forcedSearchQueueScheduler.action.is_forced_search_in_progress():
            logger.log(u"Manual search is running. Can't start Backlog Search", logger.WARNING)
            return

        self.amActive = True
        self.amPaused = False

        if which_shows:
            show_list = which_shows
        else:
            show_list = app.showList

        self._get_last_backlog()

        curDate = datetime.date.today().toordinal()
        from_date = datetime.date.fromordinal(1)

        if not which_shows and not ((curDate - self._last_backlog) >= self.cycleTime):
            logger.log(u"Running limited backlog on missed episodes " + str(app.BACKLOG_DAYS) + " day(s) and older only")
            from_date = datetime.date.today() - datetime.timedelta(days=app.BACKLOG_DAYS)

        # go through non air-by-date shows and see if they need any episodes
        for cur_show in show_list:

            if cur_show.paused:
                continue

            segments = self._get_segments(cur_show, from_date)

            for season, segment in iteritems(segments):
                self.currentSearchInfo = {'title': cur_show.name + " Season " + str(season)}

                backlog_queue_item = BacklogQueueItem(cur_show, segment)
                app.searchQueueScheduler.action.add_item(backlog_queue_item)  # @UndefinedVariable

            if not segments:
                logger.log(u"Nothing needs to be downloaded for %s, skipping" % cur_show.name, logger.DEBUG)

        # don't consider this an actual backlog search if we only did recent eps
        # or if we only did certain shows
        if from_date == datetime.date.fromordinal(1) and not which_shows:
            self._set_last_backlog(curDate)

        self.amActive = False
        self._resetPI()

    def _get_last_backlog(self):

        logger.log(u"Retrieving the last check time from the DB", logger.DEBUG)

        main_db_con = db.DBConnection()
        sql_results = main_db_con.select("SELECT last_backlog FROM info")

        if not sql_results:
            last_backlog = 1
        elif sql_results[0]["last_backlog"] is None or sql_results[0]["last_backlog"] == "":
            last_backlog = 1
        else:
            last_backlog = int(sql_results[0]["last_backlog"])
            if last_backlog > datetime.date.today().toordinal():
                last_backlog = 1

        self._last_backlog = last_backlog
        return self._last_backlog

    def _get_segments(self, show, from_date):
        wanted = {}
        if show.paused:
            logger.log(u"Skipping backlog for %s because the show is paused" % show.name, logger.DEBUG)
            return wanted

        allowed_qualities, preferred_qualities = common.Quality.split_quality(show.quality)

        logger.log(u"Seeing if we need anything from %s" % show.name, logger.DEBUG)

        con = db.DBConnection()
        sql_results = con.select(
            "SELECT status, season, episode, manually_searched FROM tv_episodes WHERE airdate > ? AND showid = ?",
            [from_date.toordinal(), show.indexerid]
        )

        # check through the list of statuses to see if we want any
        for sql_result in sql_results:
            if not common.Quality.should_search(sql_result['status'], show, sql_result['manually_searched']):
                continue
            logger.log(u"Found needed backlog episodes for: {show} {ep}".format
                       (show=show.name, ep=episode_num(sql_result["season"], sql_result["episode"])), logger.INFO)
            ep_obj = show.get_episode(sql_result["season"], sql_result["episode"])

            if ep_obj.season not in wanted:
                wanted[ep_obj.season] = [ep_obj]
            else:
                wanted[ep_obj.season].append(ep_obj)

        return wanted

    def _set_last_backlog(self, when):

        logger.log(u"Setting the last backlog in the DB to " + str(when), logger.DEBUG)

        main_db_con = db.DBConnection()
        sql_results = main_db_con.select("SELECT last_backlog FROM info")

        if not sql_results:
            main_db_con.action("INSERT INTO info (last_backlog, last_indexer) VALUES (?,?)", [str(when), 0])
        else:
            main_db_con.action("UPDATE info SET last_backlog={0}".format(when))

    def run(self, force=False):
        try:
            self.search_backlog()
        except:
            self.amActive = False
            raise
