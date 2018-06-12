# coding=utf-8

"""Daily searcher module."""

from __future__ import unicode_literals

import logging
import threading
from builtins import object
from datetime import date, datetime, timedelta

from medusa import app, common
from medusa.db import DBConnection
from medusa.helper.common import try_int
from medusa.helper.exceptions import MultipleShowObjectsException
from medusa.logger.adapters.style import BraceAdapter
from medusa.network_timezones import (
    app_timezone,
    network_dict,
    parse_date_time,
    update_network_dict,
)
from medusa.search.queue import DailySearchQueueItem
from medusa.show.show import Show

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class DailySearcher(object):  # pylint:disable=too-few-public-methods
    """Daily search class."""

    def __init__(self):
        """Initialize the class."""
        self.lock = threading.Lock()
        self.amActive = False

    def run(self, force=False):  # pylint:disable=too-many-branches
        """
        Run the daily searcher, queuing selected episodes for search.

        :param force: Force search
        """
        if self.amActive:
            log.debug('Daily search is still running, not starting it again')
            return
        elif app.forced_search_queue_scheduler.action.is_forced_search_in_progress() and not force:
            log.warning('Manual search is running. Unable to start Daily search')
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
            b'SELECT indexer, showid, airdate, season, episode '
            b'FROM tv_episodes '
            b'WHERE status = ? AND (airdate <= ? and airdate > 1)',
            [common.UNAIRED, cur_date]
        )

        new_releases = []
        show_obj = None

        for db_episode in episodes_from_db:
            indexer_id = db_episode[b'indexer']
            show_id = db_episode[b'showid']
            try:
                if not show_obj or show_id != show_obj.indexerid:
                    show_obj = Show.find_by_id(app.showList, indexer_id, show_id)

                # for when there is orphaned show in the database but not loaded into our show list
                if not show_obj or show_obj.paused:
                    continue

            except MultipleShowObjectsException:
                log.info('ERROR: expected to find a single show matching {id}',
                         {'id': show_id})
                continue

            if show_obj.airs and show_obj.network:
                # This is how you assure it is always converted to local time
                show_air_time = parse_date_time(db_episode[b'airdate'], show_obj.airs, show_obj.network)
                end_time = show_air_time.astimezone(app_timezone) + timedelta(minutes=try_int(show_obj.runtime, 60))

                # filter out any episodes that haven't finished airing yet,
                if end_time > cur_time:
                    continue

            cur_ep = show_obj.get_episode(db_episode[b'season'], db_episode[b'episode'])
            with cur_ep.lock:
                cur_ep.status = show_obj.default_ep_status if cur_ep.season else common.SKIPPED
                log.info(
                    'Setting status ({status}) for show airing today: {name} {special}', {
                        'name': cur_ep.pretty_name(),
                        'status': common.statusStrings[cur_ep.status],
                        'special': '(specials are not supported)' if not cur_ep.season else '',
                    }
                )
                new_releases.append(cur_ep.get_sql())

        if new_releases:
            main_db_con = DBConnection()
            main_db_con.mass_action(new_releases)

        # queue episode for daily search
        app.search_queue_scheduler.action.add_item(
            DailySearchQueueItem(force=force)
        )

        self.amActive = False
