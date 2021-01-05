# coding=utf-8

from __future__ import unicode_literals

import logging
import threading
from builtins import object
from datetime import date, datetime, timedelta
from math import ceil

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
from medusa.session.core import MedusaSession
from medusa.show.show import Show

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class EpisodeUpdater(object):
    def __init__(self):
        self.lock = threading.Lock()
        self.amActive = False
        self.session = MedusaSession()

    def run(self, force=False):

        self.amActive = True

        if not network_dict:
            update_network_dict()

        # The tvshows airdate_offset field is used to configure a search offset for specific shows.
        # This way we can search/accept results early or late, depending on the value.
        main_db_con = DBConnection()
        min_offset_show = main_db_con.select(
            'SELECT COUNT(*) as offsets, MIN(airdate_offset) AS min_offset '
            'FROM tv_shows '
            'WHERE paused = 0 AND airdate_offset < 0'
        )
        additional_search_offset = 0
        if min_offset_show and min_offset_show[0]['offsets'] > 0:
            additional_search_offset = int(ceil(abs(min_offset_show[0]['min_offset']) / 24.0))
            log.debug('Using an airdate offset of {min_offset_show} as we found show(s) with an airdate'
                      ' offset configured.', {'min_offset_show': min_offset_show[0]['min_offset']})

        cur_time = datetime.now(app_timezone)

        cur_date = (
            date.today() + timedelta(days=1 if network_dict else 2) + timedelta(days=additional_search_offset)
        ).toordinal()

        episodes_from_db = main_db_con.select(
            'SELECT indexer, showid, airdate, season, episode '
            'FROM tv_episodes '
            'WHERE status = ? AND (airdate <= ? and airdate > 1)',
            [common.UNAIRED, cur_date]
        )

        new_releases = []
        series_obj = None

        for db_episode in episodes_from_db:
            indexer_id = db_episode['indexer']
            series_id = db_episode['showid']
            try:
                if not series_obj or series_id != series_obj.indexerid:
                    series_obj = Show.find_by_id(app.showList, indexer_id, series_id)

                # for when there is orphaned series in the database but not loaded into our show list
                if not series_obj:
                    continue

                # update previous and next episode cache
                series_obj.prev_airdate
                series_obj.next_airdate

                # update xem_numbering
                series_obj.xem_numbering

                if series_obj.paused:
                    continue

            except MultipleShowObjectsException:
                log.info('ERROR: expected to find a single show matching {id}',
                         {'id': series_id})
                continue

            cur_ep = series_obj.get_episode(db_episode['season'], db_episode['episode'])

            if series_obj.airs and series_obj.network:
                # This is how you assure it is always converted to local time
                show_air_time = parse_date_time(db_episode['airdate'], series_obj.airs, series_obj.network)
                end_time = show_air_time.astimezone(app_timezone) + timedelta(minutes=try_int(series_obj.runtime, 60))

                if series_obj.airdate_offset != 0:
                    log.debug(
                        '{show}: Applying an airdate offset for the episode: {episode} of {offset} hours',
                        {'show': series_obj.name, 'episode': cur_ep.pretty_name(), 'offset': series_obj.airdate_offset})

                # filter out any episodes that haven't finished airing yet
                if end_time + timedelta(hours=series_obj.airdate_offset) > cur_time:
                    continue

            with cur_ep.lock:
                cur_ep.status = series_obj.default_ep_status if cur_ep.season else common.SKIPPED
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

        self.amActive = False
