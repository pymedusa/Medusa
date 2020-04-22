# coding=utf-8

"""Provider code for xBiT."""

from __future__ import unicode_literals

import logging
import re
import traceback

from medusa import tv
from medusa.helper.common import convert_size
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.compat import urljoin

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class xBiTProvider(TorrentProvider):
    """xBiT Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(xBiTProvider, self).__init__('xBiT')

        # URLs
        self.url = 'https://xbit.pw'
        self.urls = {
            'search': urljoin(self.url, '/api.php')
        }

        # Proper Strings

        # Miscellaneous Options
        self.freeleech = False

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tv.Cache(self, min_time=10)  # Only poll xBiT every 10 minutes max

    def search(self, search_strings, **kwargs):
        """
        Search a provider and parse the results.
        :param search_strings: A dict with mode (key) and the search value (value)
        :returns: A list of search results (structure)
        """
        results = []

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            string_separator = ['+', '.'] if mode != 'RSS' else [' ']

            for separator in string_separator:
                for search_string in search_strings[mode]:
                    search_url = self.urls['search']
                    if mode != 'RSS':
                        log.debug('Search string: {search}',
                                  {'search': search_string})
                        # Replaces spaces with either a dot or a plus
                        # Needed in order for it to return all results
                        search_string = search_string.replace(' ', separator)
                    search_params = {'search': search_string}

                    response = self.session.get(self.urls['search'], params=search_params)
                    if not response:
                        log.debug('No data returned from provider')
                        continue

                    try:
                        jdata = response.json()
                    except ValueError:
                        log.debug('No data returned from provider')
                        continue

                    results += self.parse(jdata, mode)



                try:
                    jdata = response.json()
                except ValueError:
                    log.debug('No data returned from provider')
                    continue

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
        torrent_rows = data.get('dht_results')
        if not torrent_rows:
            log.debug('Data returned from provider does not contain any torrents')
            return items
        for row in torrent_rows[:-1]:

            try:
                title = row['NAME']
                download_url = row['MAGNET']
                download_url = download_url + self._custom_trackers
                if not all([title, download_url]):
                    continue

                seeders = 1  # Provider does not provide seeders
                leechers = 0  # Provider does not provide leechers

                # Filter unseeded torrent
                if seeders < min(self.minseed, 1):
                    if mode != 'RSS':
                        log.debug("Discarding torrent because it doesn't meet the"
                                  " minimum seeders: {0}. Seeders: {1}",
                                  title, seeders)
                    continue

                torrent_size = row['SIZE']
                size = convert_size(torrent_size) or -1

                pubdate_raw = row['DISCOVERED']
                pubdate = self.parse_pubdate(pubdate_raw)

                item = {
                    'title': title,
                    'link': download_url,
                    'size': size,
                    'seeders': seeders,
                    'leechers': leechers,
                    'pubdate': pubdate,
                }

                if mode != 'RSS':
                    log.debug('Found result: {0} with {1} seeders and {2} leechers',
                              title, seeders, leechers)

                items.append(item)
            except (AttributeError, TypeError, KeyError, ValueError, IndexError):
                log.exception('Failed parsing provider.')

        return items


provider = xBiTProvider()