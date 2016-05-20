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

from __future__ import unicode_literals

from datetime import (
    date,
    datetime,
    timedelta,
)
import threading

import sickbeard
from sickbeard import (
    common,
    logger,
)
from sickbeard.db import DBConnection
from sickbeard.network_timezones import (
    network_dict,
    update_network_dict,
    sb_timezone,
    parse_date_time,
)
from sickbeard.search_queue import DailySearchQueueItem
from sickrage.show.Show import Show
from sickrage.helper.exceptions import MultipleShowObjectsException
from sickrage.helper.common import try_int


class DailySearcher(object):  # pylint:disable=too-few-public-methods
    """
    Daily search thread
    """

    def __init__(self):
        self.lock = threading.Lock()
        self.amActive = False

    def run(self, force=False):  # pylint:disable=too-many-branches
        """
        Runs the daily searcher, queuing selected episodes for search

        :param force: Force search
        """
        if self.amActive:
            logger.log('Daily search is still running, not starting it again', logger.DEBUG)
            return
        elif sickbeard.forcedSearchQueueScheduler.action.is_forced_search_in_progress() and not force:
            logger.log('Manual search is running. Can\'t start Daily search', logger.WARNING)
            return

        self.amActive = True

        logger.log('Searching for newly released episodes ...')

        if not network_dict:
            update_network_dict()

        cur_time = datetime.now(sb_timezone)
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
                    show = Show.find(sickbeard.showList, show_id)

                # for when there is orphaned series in the database but not loaded into our show list
                if not show or show.paused:
                    continue

            except MultipleShowObjectsException:
                logger.log('ERROR: expected to find a single show matching {id}'.format(id=show_id))
                continue

            if show.airs and show.network:
                # This is how you assure it is always converted to local time
                show_air_time = parse_date_time(db_episode[b'airdate'], show.airs, show.network)
                end_time = show_air_time.astimezone(sb_timezone) + timedelta(minutes=try_int(show.runtime, 60))

                # filter out any episodes that haven't finished airing yet,
                if end_time > cur_time:
                    continue

            cur_ep = show.getEpisode(db_episode[b'season'], db_episode[b'episode'])
            with cur_ep.lock:
                cur_ep.status = show.default_ep_status if cur_ep.season else common.SKIPPED
                logger.log('Setting status ({status}) for show airing today: {name} {special}'.format(
                    name=cur_ep.prettyName(),
                    status=common.statusStrings[cur_ep.status],
                    special='(specials are not supported)' if not cur_ep.season else ''
                ))
                new_releases.append(cur_ep.get_sql())

        if new_releases:
            main_db_con = DBConnection()
            main_db_con.mass_action(new_releases)
        else:
            logger.log('No newly released episodes found ...')

        # queue episode for daily search
        sickbeard.searchQueueScheduler.action.add_item(
            DailySearchQueueItem()
        )

        self.amActive = False
