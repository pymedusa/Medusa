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
"""Provider code for Womble provider."""
from __future__ import unicode_literals

from requests.compat import urljoin
from .nzb_provider import NZBProvider
from ... import logger, tv_cache


class WombleProvider(NZBProvider):
    """Womble Newznab provider."""

    def __init__(self):
        """Initialize the class."""
        super(self.__class__, self).__init__("Womble's Index")

        # Credentials
        self.public = True

        # URLs
        self.url = 'http://newshost.co.za'
        self.urls = {
            'rss': urljoin(self.url, 'rss'),
        }

        # Proper Strings

        # Miscellaneous Options
        self.supports_backlog = False

        # Cache
        self.cache = WombleCache(self, min_time=20)


class WombleCache(tv_cache.TVCache):
    """Provider cache class."""

    def update_cache(self):
        """Update provider cache."""
        if not self.should_update():
            return

        self._clear_cache()
        self.set_last_update()

        cl = []
        search_params_list = [
            {'sec': 'tv-x264'},
            {'sec': 'tv-hd'},
            {'sec': 'tv-sd'},
            {'sec': 'tv-dvd'}
        ]
        for search_params in search_params_list:
            search_params.update({'fr': 'false'})
            data = self.get_rss_feed(self.provider.urls['rss'], params=search_params)['entries']
            if not data:
                logger.log('No data returned from provider', logger.DEBUG)
                continue

            for item in data:
                ci = self._parse_item(item)
                if ci:
                    cl.append(ci)

        if cl:
            cache_db_con = self._get_db()
            cache_db_con.mass_action(cl)

    def _check_auth(self, data):
        return data if data['feed'] and data['feed']['title'] != 'Invalid Link' else None


provider = WombleProvider()
