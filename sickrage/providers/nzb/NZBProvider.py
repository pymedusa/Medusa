# coding=utf-8
# This file is part of SickRage.
#

# Git: https://github.com/PyMedusa/SickRage.git
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

import sickbeard

from datetime import datetime

from sickbeard import logger
from sickbeard.classes import NZBSearchResult
from sickbeard.common import Quality
from sickbeard.db import DBConnection
from sickbeard.classes import Proper
from sickrage.helper.common import try_int
from sickrage.show.Show import Show

from sickrage.providers.GenericProvider import GenericProvider


class NZBProvider(GenericProvider):
    def __init__(self, name):
        GenericProvider.__init__(self, name)

        self.provider_type = GenericProvider.NZB

    def find_propers(self, search_date=None):
        results = []
        db = DBConnection()
        placeholder = ','.join([str(x) for x in Quality.DOWNLOADED + Quality.SNATCHED + Quality.SNATCHED_BEST])
        sql_results = db.select(
            'SELECT s.show_name, e.showid, e.season, e.episode, e.status, e.airdate'
            ' FROM tv_episodes AS e'
            ' INNER JOIN tv_shows AS s ON (e.showid = s.indexer_id)'
            ' WHERE e.airdate >= ' + str(search_date.toordinal()) +
            ' AND e.status IN (' + placeholder + ')'
        )

        for result in sql_results or []:
            show = Show.find(sickbeard.showList, int(result['showid']))

            if show:
                episode = show.getEpisode(result['season'], result['episode'])

                for term in self.proper_strings:
                    search_strings = self._get_episode_search_strings(episode, add_string=term)

                    for item in self.search(search_strings[0], ep_obj=episode):
                        title, url = self._get_title_and_url(item)
                        seeders, leechers = self._get_result_info(item)
                        size = self._get_size(item)
                        pubdate = self._get_pubdate(item)
                        hash = self._get_hash(item)

                        results.append(Proper(title, url, datetime.today(), show, seeders, leechers, size, pubdate, hash))

        return results

    def is_active(self):
        return bool(sickbeard.USE_NZBS) and self.is_enabled()

    def _get_result(self, episodes):
        return NZBSearchResult(episodes)

    def _get_size(self, item):
        try:
            size = item.get('links')[1].get('length', -1)
        except (AttributeError, IndexError, TypeError):
            size = -1
        return try_int(size, -1)

    def _get_result_info(self, item):
        # Get seeders/leechers for Torznab
        seeders = item.get('seeders', -1)
        leechers = item.get('leechers', -1)
        return try_int(seeders, -1), try_int(leechers, -1)

    def _get_storage_dir(self):
        return sickbeard.NZB_DIR

    def _get_pubdate(self, item):
        """
        Return publish date of the item.
        """
        return item.get('pubdate')
