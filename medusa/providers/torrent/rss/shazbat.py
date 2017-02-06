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
"""Provider code for Shazbat."""
from __future__ import unicode_literals

from medusa import (
    logger,
    tv,
)
from medusa.helper.exceptions import AuthException
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.compat import urljoin


class ShazbatProvider(TorrentProvider):
    """Shazbat Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(self.__class__, self).__init__('Shazbat.tv')

        # Credentials
        self.passkey = None

        # URLs
        self.url = 'http://www.shazbat.tv'
        self.urls = {
            'login': urljoin(self.url, 'login'),
            'rss_recent': urljoin(self.url, 'rss/recent'),
            # 'rss_queue': urljoin(self.url, 'rss/download_queue'),
            # 'rss_followed': urljoin(self.url, 'rss/followed')
        }

        # Proper Strings

        # Miscellaneous Options
        self.supports_backlog = False
        self.options = None

        # Torrent Stats

        # Cache
        self.cache = ShazbatCache(self, min_time=20)

    def _check_auth(self):
        if not self.passkey:
            raise AuthException('Your authentication credentials are missing, check your config.')

        return True

    def _check_auth_from_data(self, data):
        if not self.passkey:
            self._check_auth()
        elif data.get('bozo') == 1 and not (data['entries'] and data['feed']):
            logger.log('Invalid username or password. Check your settings', logger.WARNING)

        return True


class ShazbatCache(tv.Cache):
    """Provider cache class."""

    def _get_rss_data(self):
        """Get RSS data."""
        params = {
            'passkey': self.provider.passkey,
            'fname': 'true',
            'limit': 100,
            'duration': '2 hours'
        }

        return self.get_rss_feed(self.provider.urls['rss_recent'], params=params)

    def _check_auth(self, data):
        """Check if we are autenticated."""
        return self.provider._check_auth_from_data(data)


provider = ShazbatProvider()
