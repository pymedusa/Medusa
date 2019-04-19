# coding=utf-8

"""Provider code for Bitcannon."""

from __future__ import unicode_literals

import logging

from medusa import tv
from medusa.helper.common import (
    convert_size,
    try_int,
)
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.compat import urljoin

import validators

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class BitCannonProvider(TorrentProvider):
    """BitCannon Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(BitCannonProvider, self).__init__('BitCannon')

        # Credentials
        self.api_key = None

        # URLs
        self.url = 'http://localhost:3000/'
        self.custom_url = None

        # Proper Strings

        # Miscellaneous Options

        # Cache
        cache_params = {'RSS': ['tv', 'anime']}
        self.cache = tv.Cache(self, search_params=cache_params)

    def search(self, search_strings, age=0, ep_obj=None, **kwargs):
        """
        Search a provider and parse the results.

        :param search_strings: A dict with mode (key) and the search value (value)
        :param age: Not used
        :param ep_obj: Not used
        :returns: A list of search results (structure)
        """
        results = []

        if self.custom_url:
            if not validators.url(self.custom_url):
                log.warning('Invalid custom url: {0}', self.custom_url)
                return results
            self.url = self.custom_url

        # Search Params
        search_params = {
            'category': 'anime' if ep_obj and ep_obj.series and ep_obj.series.anime else 'tv',
            'apiKey': self.api_key,
        }

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            for search_string in search_strings[mode]:
                search_params['q'] = search_string
                if mode != 'RSS':
                    log.debug('Search string: {search}',
                              {'search': search_string})

                search_url = urljoin(self.url, 'api/search')

                response = self.session.get(search_url, params=search_params)
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
        torrent_rows = data.pop('torrents', {})

        # Skip column headers
        for row in torrent_rows:
            try:
                title = row.pop('title', '')
                info_hash = row.pop('infoHash', '')
                download_url = 'magnet:?xt=urn:btih:' + info_hash
                if not all([title, download_url, info_hash]):
                    continue

                swarm = row.pop('swarm', {})
                seeders = try_int(swarm.pop('seeders', 0))
                leechers = try_int(swarm.pop('leechers', 0))

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

    @staticmethod
    def _check_auth_from_data(data):
        if not all([isinstance(data, dict),
                    data.pop('status', 200) != 401,
                    data.pop('message', '') != 'Invalid API key']):

            log.warning('Invalid api key. Check your settings')
            return False

        return True


provider = BitCannonProvider()
