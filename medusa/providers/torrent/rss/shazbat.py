# coding=utf-8

"""Provider code for Shazbat."""

from __future__ import unicode_literals

import logging

from medusa import tv
from medusa.helper.exceptions import AuthException
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.compat import urljoin

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class ShazbatProvider(TorrentProvider):
    """Shazbat Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(ShazbatProvider, self).__init__('Shazbat.tv')

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
            log.warning('Invalid username or password. Check your settings')

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
