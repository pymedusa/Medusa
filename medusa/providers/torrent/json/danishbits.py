# coding=utf-8

"""Provider code for Danishbits."""

from __future__ import unicode_literals

import logging
import traceback

from medusa import tv
from medusa.helper.common import (
    try_int,
)
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.compat import urljoin

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class DanishbitsProvider(TorrentProvider):
    """Danishbits Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(DanishbitsProvider, self).__init__('Danishbits')

        # Credentials
        self.username = None
        self.passkey = None

        # URLs
        self.url = 'https://danishbits.org'
        self.urls = {
            'search': urljoin(self.url, 'couchpotato.php'),
        }

        # Proper Strings

        # Miscellaneous Options
        self.freeleech = True

        # Torrent Stats
        self.minseed = 0
        self.minleech = 0

        # Cache
        self.cache = tv.Cache(self, min_time=10)  # Only poll Danishbits every 10 minutes max

    def search(self, search_strings, age=0, ep_obj=None):
        """
        Search a provider and parse the results.

        :param search_strings: A dict with mode (key) and the search value (value)
        :param age: Not used
        :param ep_obj: Not used
        :returns: A list of search results (structure)
        """
        results = []
        results = []

        # Search Params
        search_params = {
            'user': self.username,
            'passkey': self.passkey,
            'search': '',
        }

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {search}',
                              {'search': search_string})

                search_params['search'] = search_string
                response = self.get_url(self.urls['search'], params=search_params, returns='json')
                if not response or response["total_results"] == 0:
                    log.debug('No data returned from provider')
                    continue

                results += self.parse(response, mode)

        return results

    def parse(self, data, mode):
        """
        Parse search results for items.

        :param data: The raw response from a search
        :param mode: The current mode used to search, e.g. RSS

        :return: A list of items found
        """
        items = []

        del data["total_results"]
        torrent_rows = data["results"]

        for row in torrent_rows:
            try:
                title = row.get('release_name')
                download_url = row.get('download_url')
                if not all([title, download_url]):
                    continue

                seeders = row.get('seeders')
                leechers = row.get('leechers')

                # Filter unseeded torrent
                if seeders < min(self.minseed, 1):
                    if mode != 'RSS':
                        log.debug("Discarding torrent because it doesn't meet the"
                                  " minimum seeders: {0}. Seeders: {1}",
                                  title, seeders)
                    continue

                freeleech = row.get('freeleech')
                if self.freeleech and not freeleech:
                    continue

                size = try_int(row.get('size')) or -1

                # Current API doesn't have it.
                # pubdate = row.get('publish_date')

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
                log.error('Failed parsing provider. Traceback: {0!r}',
                          traceback.format_exc())

        return items

provider = DanishbitsProvider()

