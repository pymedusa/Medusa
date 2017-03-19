# coding=utf-8

"""Daily searcher module."""

from __future__ import unicode_literals

import threading
from datetime import date, datetime, timedelta

from medusa.exceptions import MultipleShowObjectsException
from .queue import DailySearchQueueItem
from .. import app, common, logger
from ..db import DBConnection
from ..helper.common import try_int
from ..network_timezones import app_timezone, network_dict, parse_date_time, update_network_dict
from ..show.show import Show


class DailySearcher(object):  # pylint:disable=too-few-public-methods
    """Daily search class."""

    def __init__(self):
        """Initialize the class."""
        self.lock = threading.Lock()
        self.amActive = False

    def run(self, force=False):  # pylint:disable=too-many-branches
        """Run the daily searcher, queuing selected episodes for search.

        :param force: Force search
        """
        if self.amActive:
            logger.log('Daily search is still running, not starting it again', logger.DEBUG)
            return
        elif app.forced_search_queue_scheduler.action.is_forced_search_in_progress() and not force:
            logger.log('Manual search is running. Can\'t start Daily search', logger.WARNING)
            return

        self.amActive = True

        if not network_dict:
            update_network_dict()

        cur_time = datetime.now(app_timezone)
        cur_date = (
            date.today() + timedelta(days=1 if network_dict else 2)
        ).toordinal()

        main_db_con = DBConnection()
        episodes_from_db = main_db_con.select(
            b'SELECT showid, airdate, season, episode '
            b'FROM tv_episodes '
            b'WHERE status = ? AND (airdate <= ? and airdate > 1)',
            [common.UNAIRED, cur_date]
        )

        new_releases = []
        show = None

        for db_episode in episodes_from_db:
            try:
                show_id = int(db_episode[b'showid'])
                if not show or show_id != show.indexerid:
                    show = Show.find(app.showList, show_id)

                # for when there is orphaned series in the database but not loaded into our show list
                if not show or show.paused:
                    continue

            except MultipleShowObjectsException:
                logger.log('ERROR: expected to find a single show matching {id}'.format(id=show_id))
                continue

            if show.airs and show.network:
                # This is how you assure it is always converted to local time
                show_air_time = parse_date_time(db_episode[b'airdate'], show.airs, show.network)
                end_time = show_air_time.astimezone(app_timezone) + timedelta(minutes=try_int(show.runtime, 60))

                # filter out any episodes that haven't finished airing yet,
                if end_time > cur_time:
                    continue

            cur_ep = show.get_episode(db_episode[b'season'], db_episode[b'episode'])
            with cur_ep.lock:
                cur_ep.status = show.default_ep_status if cur_ep.season else common.SKIPPED
                logger.log('Setting status ({status}) for show airing today: {name} {special}'.format(
                    name=cur_ep.pretty_name(),
                    status=common.statusStrings[cur_ep.status],
                    special='(specials are not supported)' if not cur_ep.season else ''
                ))
                new_releases.append(cur_ep.get_sql())

        if new_releases:
            main_db_con = DBConnection()
            main_db_con.mass_action(new_releases)

        # queue episode for daily search
        app.search_queue_scheduler.action.add_item(
            DailySearchQueueItem()
        )

        self.amActive = False
