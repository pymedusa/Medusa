# coding=utf-8

"""Provider code for Nyaa."""

from __future__ import unicode_literals

import logging
import re
import traceback

from medusa import tv
from medusa.helper.common import convert_size, try_int
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.torrent.torrent_provider import TorrentProvider

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class NyaaProvider(TorrentProvider):
    """Nyaa Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(self.__class__, self).__init__('NyaaTorrents')

        # Credentials
        self.public = True

        # URLs
        self.url = 'http://www.nyaa.se'

        # Proper Strings

        # Miscellaneous Options
        self.supports_absolute_numbering = True
        self.anime_only = True
        self.confirmed = False
        self.regex = re.compile(r'(\d+) seeder\(s\), (\d+) leecher\(s\), \d+ download\(s\) - (\d+.?\d* [KMGT]iB)(.*)',
                                re.DOTALL)

        # Torrent Stats
        self.minseed = 0
        self.minleech = 0

        # Cache
        self.cache = tv.Cache(self, min_time=20)  # only poll NyaaTorrents every 20 minutes max

    def search(self, search_strings, age=0, ep_obj=None):
        """
        Search a provider and parse the results.

        :param search_strings: A dict with mode (key) and the search value (value)
        :param age: Not used
        :param ep_obj: Not used
        :returns: A list of search results (structure)
        """
        results = []
        if self.show and not self.show.is_anime:
            return results

        # Search Params
        search_params = {
            'page': 'rss',
            'cats': '1_0',  # All anime
            'sort': 2,  # Sort Descending By Seeders
            'order': 1,
        }

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {search}',
                              {'search': search_string})
                    if self.confirmed:
                        log.debug('Searching only confirmed torrents')

                    search_params['term'] = search_string
                data = self.cache.get_rss_feed(self.url, params=search_params)
                if not data:
                    log.debug('No data returned from provider')
                    continue
                if not data['entries']:
                    log.debug('Data returned from provider does not contain any {0}torrents',
                              'confirmed ' if self.confirmed else '')
                    continue

                results += self.parse(data, mode)

        return results

    def parse(self, data, mode):
        """
        Parse search results for items.

        :param data: The raw response from a search
        :param mode: The current mode used to search, e.g. RSS

        :return: A list of items found
        """
        items = []

        for result in data['entries']:
            try:
                title = result['title']
                download_url = result['link']
                if not all([title, download_url]):
                    continue

                item_info = self.regex.search(result['summary'])
                if not item_info:
                    log.debug('There was a problem parsing an item summary, skipping: {0}', title)
                    continue

                seeders, leechers, torrent_size, verified = item_info.groups()
                seeders = try_int(seeders)
                leechers = try_int(leechers)

                # Filter unseeded torrent
                if seeders < min(self.minseed, 1):
                    if mode != 'RSS':
                        log.debug("Discarding torrent because it doesn't meet the"
                                  " minimum seeders: {0}. Seeders: {1}", title, seeders)
                    continue

                if self.confirmed and not verified and mode != 'RSS':
                    log.debug("Found result {0} but that doesn't seem like a verified"
                              " result so I'm ignoring it", title)
                    continue

                size = convert_size(torrent_size) or -1

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


provider = NyaaProvider()
