# coding=utf-8

"""Backlog module."""
from __future__ import unicode_literals

import datetime
import logging
import threading
from builtins import object
from builtins import str

from medusa import app, db, scheduler, ui
from medusa.common import Quality, UNSET
from medusa.helper.common import episode_num
from medusa.logger.adapters.style import BraceAdapter
from medusa.search.queue import BacklogQueueItem

from six import iteritems

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class BacklogSearchScheduler(scheduler.Scheduler):
    """Backlog search scheduler class."""

    def force_search(self):
        """Set the last backlog in the DB."""
        self.action._set_last_backlog(1)
        self.lastRun = datetime.datetime.fromordinal(1)

    def next_run(self):
        """Return when backlog should run next."""
        if self.action._last_backlog <= 1:
            return datetime.date.today()
        else:
            backlog_frequency_in_days = int(self.action.cycleTime)
            return datetime.date.fromordinal(self.action._last_backlog + backlog_frequency_in_days)


class BacklogSearcher(object):
    """Backlog Searcher class."""

    def __init__(self):
        """Initialize the class."""
        self._last_backlog = self._get_last_backlog()
        self.cycleTime = app.BACKLOG_FREQUENCY / 60.0 / 24
        self.lock = threading.Lock()
        self.amActive = False
        self.amPaused = False
        self.amWaiting = False
        self.forced = False
        self.currentSearchInfo = {}

        self._reset_pi()

    def _reset_pi(self):
        """Reset percent done."""
        self.percentDone = 0
        self.currentSearchInfo = {'title': 'Initializing'}

    def get_progress_indicator(self):
        """Get backlog search progress indicator."""
        if self.amActive:
            return ui.ProgressIndicator(self.percentDone, self.currentSearchInfo)
        else:
            return None

    def am_running(self):
        """Check if backlog is running."""
        log.debug(u'amWaiting: {0}, amActive: {1}', self.amWaiting, self.amActive)
        return (not self.amWaiting) and self.amActive

    def search_backlog(self, which_shows=None):
        """Run the backlog search for given shows."""
        if self.amActive:
            log.debug(u'Backlog is still running, not starting it again')
            return

        if app.forced_search_queue_scheduler.action.is_forced_search_in_progress():
            log.warning(u'Manual search is running. Unable to start Backlog Search')
            return

        self.amActive = True
        self.amPaused = False

        if which_shows:
            show_list = which_shows
        else:
            show_list = app.showList

        self._get_last_backlog()

        cur_date = datetime.date.today().toordinal()
        from_date = datetime.date.fromordinal(1)

        if not which_shows and self.forced:
            log.info(u'Running limited backlog search on missed episodes from last {0} days',
                     app.BACKLOG_DAYS)
            from_date = datetime.date.today() - datetime.timedelta(days=app.BACKLOG_DAYS)
        else:
            log.info(u'Running full backlog search on missed episodes for selected shows')

        # go through non air-by-date shows and see if they need any episodes
        for series_obj in show_list:

            if series_obj.paused:
                continue

            segments = self._get_segments(series_obj, from_date)

            for season, segment in iteritems(segments):
                self.currentSearchInfo = {'title': '{series_name} Season {season}'.format(series_name=series_obj.name,
                                                                                          season=season)}

                backlog_queue_item = BacklogQueueItem(series_obj, segment)
                app.search_queue_scheduler.action.add_item(backlog_queue_item)  # @UndefinedVariable

            if not segments:
                log.debug(u'Nothing needs to be downloaded for {0!r}, skipping', series_obj.name)

        # don't consider this an actual backlog search if we only did recent eps
        # or if we only did certain shows
        if from_date == datetime.date.fromordinal(1) and not which_shows:
            self._set_last_backlog(cur_date)

        self.amActive = False
        self._reset_pi()

    def _get_last_backlog(self):
        """Get the last time backloged runned."""
        log.debug(u'Retrieving the last check time from the DB')

        main_db_con = db.DBConnection()
        sql_results = main_db_con.select('SELECT last_backlog '
                                         'FROM info')

        if not sql_results:
            last_backlog = 1
        elif sql_results[0][b'last_backlog'] is None or sql_results[0][b'last_backlog'] == '':
            last_backlog = 1
        else:
            last_backlog = int(sql_results[0][b'last_backlog'])
            if last_backlog > datetime.date.today().toordinal():
                last_backlog = 1

        self._last_backlog = last_backlog
        return self._last_backlog

    @staticmethod
    def _get_segments(series_obj, from_date):
        """Get episodes that should be backlog searched."""
        wanted = {}
        if series_obj.paused:
            log.debug(u'Skipping backlog for {0} because the show is paused', series_obj.name)
            return wanted

        log.debug(u'Seeing if we need anything from {0}', series_obj.name)

        con = db.DBConnection()
        sql_results = con.select(
            'SELECT status, quality, season, episode, manually_searched '
            'FROM tv_episodes '
            'WHERE airdate > ?'
            ' AND indexer = ? '
            ' AND showid = ?',
            [from_date.toordinal(), series_obj.indexer, series_obj.series_id]
        )

        # check through the list of statuses to see if we want any
        for episode in sql_results:
            cur_status, cur_quality = int(episode[b'status'] or UNSET), int(episode[b'quality'] or Quality.NA)
            should_search, should_search_reason = Quality.should_search(
                cur_status, cur_quality, series_obj, episode[b'manually_searched']
            )
            if not should_search:
                continue
            log.debug(
                u'Found needed backlog episodes for: {show} {ep}. Reason: {reason}', {
                    'show': series_obj.name,
                    'ep': episode_num(episode[b'season'], episode[b'episode']),
                    'reason': should_search_reason,
                }
            )
            ep_obj = series_obj.get_episode(episode[b'season'], episode[b'episode'])

            if ep_obj.season not in wanted:
                wanted[ep_obj.season] = [ep_obj]
            else:
                wanted[ep_obj.season].append(ep_obj)

        return wanted

    @staticmethod
    def _set_last_backlog(when):
        """Set the last backlog in the DB."""
        log.debug(u'Setting the last backlog in the DB to {0}', when)

        main_db_con = db.DBConnection()
        sql_results = main_db_con.select('SELECT last_backlog '
                                         'FROM info')

        if not sql_results:
            main_db_con.action('INSERT INTO info (last_backlog, last_indexer) '
                               'VALUES (?,?)', [str(when), 0])
        else:
            main_db_con.action('UPDATE info '
                               'SET last_backlog={0}'.format(when))

    def run(self, force=False):
        """Run the backlog."""
        try:
            if force:
                self.forced = True
            self.search_backlog()
        except Exception:
            self.amActive = False
            raise
