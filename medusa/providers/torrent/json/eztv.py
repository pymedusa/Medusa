# coding=utf-8

"""Provider code for EZTV."""

from __future__ import unicode_literals

import logging

from medusa import tv
from medusa.helper.common import convert_size
from medusa.indexers.utils import mappings
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.compat import urljoin

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class EztvProvider(TorrentProvider):
    """EZTV Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(EztvProvider, self).__init__('Eztv')

        # Credentials
        self.public = True

        # URLs
        self.url = 'https://eztv.re'
        self.urls = {
            'api': urljoin(self.url, 'api/get-torrents')
        }

        # Proper Strings

        # Miscellaneous Options

        # Cache
        self.cache = tv.Cache(self, min_time=15)

    def search(self, search_strings, age=0, ep_obj=None, **kwargs):
        """
        Search a provider and parse the results.

        :param search_strings: A dict with mode (key) and the search value (value)
        :param age: Not used
        :param ep_obj: Not used
        :returns: A list of search results (structure)
        """
        results = []

        # Search Params
        search_params = {}

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    imdb_id = self.series.externals.get(mappings[10])
                    if imdb_id:
                        imdb_id = imdb_id[2:]  # strip two tt's of id as they are not used
                        search_params['imdb_id'] = imdb_id
                        log.debug('Search string (IMDb ID): {imdb_id}', {'imdb_id': imdb_id})
                    else:
                        log.debug('IMDb ID not found')
                        continue

                search_url = self.urls['api']
                data = self.session.get_json(search_url, params=search_params)
                if not data:
                    log.debug('No data returned from provider')
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

        torrent_rows = data.get('torrents', {})
        if not torrent_rows:
            log.debug('Data returned from provider does not contain any torrents')
            return items

        for row in torrent_rows:
            try:
                title = row.pop('title', None)
                download_url = row.pop('torrent_url', None)
                if not all([title, download_url]):
                    continue

                seeders = row.pop('seeds', 0)
                leechers = row.pop('peers', 0)

                # Filter unseeded torrent
                if seeders < self.minseed:
                    if mode != 'RSS':
                        log.debug("Discarding torrent because it doesn't meet the"
                                  ' minimum seeders: {0}. Seeders: {1}',
                                  title, seeders)
                    continue

                torrent_size = row.pop('size_bytes', None)
                size = convert_size(torrent_size, default=-1)

                pubdate_raw = row.pop('date_released_unix', None)
                pubdate = self.parse_pubdate(pubdate_raw, fromtimestamp=True)

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


provider = EztvProvider()
