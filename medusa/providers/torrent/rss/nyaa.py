# coding=utf-8

"""Provider code for Nyaa."""

from __future__ import unicode_literals

import logging

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
        super(NyaaProvider, self).__init__('Nyaa')

        # Credentials
        self.public = True

        # URLs
        self.url = 'https://nyaa.si'

        # Proper Strings

        # Miscellaneous Options
        self.supports_absolute_numbering = True
        self.confirmed = False

        # Cache
        self.cache = tv.Cache(self, min_time=20)

    def search(self, search_strings, age=0, ep_obj=None, **kwargs):
        """
        Search a provider and parse the results.

        :param search_strings: A dict with mode (key) and the search value (value)
        :param age: Not used
        :param ep_obj: An episode object
        :returns: A list of search results (structure)
        """
        results = []

        # Search Params
        category = '1_0'
        if ep_obj and not ep_obj.series.is_anime:
            category = '4_0'

        search_params = {
            'page': 'rss',
            'c': category,
            'f': 0,  # No filter
            'q': '',
        }

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            if self.confirmed:
                search_params['f'] = 2  # Trusted only
                log.debug('Searching only confirmed torrents')

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {search}',
                              {'search': search_string})
                    search_params['q'] = search_string

                data = self.cache.get_rss_feed(self.url, params=search_params)
                if not data:
                    log.debug('No data returned from provider')
                    continue
                if not data.get('entries'):
                    log.debug('Data returned from provider does not contain any {0}torrents',
                              'confirmed ' if self.confirmed else '')
                    continue

                results += self.parse(data['entries'], mode)

        return results

    def parse(self, data, mode):
        """
        Parse search results for items.

        :param data: The raw response from a search
        :param mode: The current mode used to search, e.g. RSS

        :return: A list of items found
        """
        # Units
        units = ['B', 'KIB', 'MIB', 'GIB', 'TIB', 'PIB']

        items = []

        for item in data:
            try:
                title = item['title']
                download_url = item['link']
                if not all([title, download_url]):
                    continue

                seeders = try_int(item['nyaa_seeders'])
                leechers = try_int(item['nyaa_leechers'])

                # Filter unseeded torrent
                if seeders < self.minseed:
                    if mode != 'RSS':
                        log.debug("Discarding torrent because it doesn't meet the"
                                  ' minimum seeders: {0}. Seeders: {1}',
                                  title, seeders)
                    continue

                size = convert_size(item['nyaa_size'], default=-1, units=units)

                pubdate = self.parse_pubdate(item['published'])

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


provider = NyaaProvider()
