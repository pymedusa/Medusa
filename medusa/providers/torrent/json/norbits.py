# coding=utf-8

"""Provider code for Norbits."""

from __future__ import unicode_literals

import logging

from medusa import tv
from medusa.helper.common import (
    convert_size,
    try_int,
)
from medusa.helper.exceptions import AuthException
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.compat import urlencode, urljoin

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class NorbitsProvider(TorrentProvider):
    """Norbits Torrent provider."""

    def __init__(self):
        """.Initialize the class."""
        super(NorbitsProvider, self).__init__('Norbits')

        # Credentials
        self.username = None
        self.passkey = None

        # URLs
        self.url = 'https://norbits.net'
        self.urls = {
            'search': urljoin(self.url, 'api2.php?action=torrents'),
            'download': urljoin(self.url, 'download.php'),
        }

        # Proper Strings

        # Miscellaneous Options

        # Cache
        self.cache = tv.Cache(self, min_time=20)

    def search(self, search_strings, age=0, ep_obj=None, **kwargs):
        """
        Search a provider and parse the results.

        :param search_strings: A dict with mode (key) and the search value (value)
        :param age: Not used
        :param ep_obj: Not used
        :returns: A list of search results (structure)
        """
        results = []

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {search}',
                              {'search': search_string})

                post_data = {
                    'username': self.username,
                    'passkey': self.passkey,
                    'category': '2',  # TV Category
                    'search': search_string,
                }

                response = self.session.post(self.urls['search'], json=post_data)
                if not response or not response.content:
                    log.debug('No data returned from provider')
                    continue

                try:
                    jdata = response.json()
                except ValueError:
                    log.debug('No data returned from provider')
                    continue

                if not self._check_auth_from_data(jdata):
                    return results

                results += self.parse(jdata, mode)

        return results

    def parse(self, data, mode):
        """
        Parse search results for items.

        :param data: The raw response from a search
        :param mode: The current mode used to search, e.g. RSS

        :return: A list of items found
        """
        items = []
        json_data = data.get('data', {})
        torrent_rows = json_data.get('torrents', [])

        for row in torrent_rows:
            try:
                title = row.pop('name', '')
                download_url = '{0}?{1}'.format(
                    self.urls['download'],
                    urlencode({'id': row.pop('id', ''), 'passkey': self.passkey}))

                if not all([title, download_url]):
                    continue

                seeders = try_int(row.pop('seeders', 0))
                leechers = try_int(row.pop('leechers', 0))

                # Filter unseeded torrent
                if seeders < self.minseed:
                    if mode != 'RSS':
                        log.debug("Discarding torrent because it doesn't meet the"
                                  ' minimum seeders: {0}. Seeders: {1}',
                                  title, seeders)
                    continue

                size = convert_size(row.pop('size', None), default=-1)

                item = {
                    'title': title,
                    'link': download_url,
                    'size': size,
                    'seeders': seeders,
                    'leechers': leechers,
                    'pubdate': None,
                }
                if mode != 'RSS':
                    log.debug('Found result: {0} with {1} seeders and {2} leechers',
                              title, seeders, leechers)

                items.append(item)
            except (AttributeError, TypeError, KeyError, ValueError, IndexError):
                log.exception('Failed parsing provider.')

        return items

    def _check_auth(self):
        if not self.username or not self.passkey:
            raise AuthException('Your authentication credentials for {0} are missing,'
                                ' check your config.'.format(self.name))

        return True

    def _check_auth_from_data(self, parsed_json):
        """Check that we are authenticated."""
        if 'status' in parsed_json and 'message' in parsed_json:
            if parsed_json.get('status') == 3:
                log.warning('Invalid username or password.'
                            ' Check your settings')
                return False

        return True


provider = NorbitsProvider()
