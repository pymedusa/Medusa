# coding=utf-8

"""Provider code for AniDex."""

from __future__ import unicode_literals

import logging
import traceback

from medusa import tv
from medusa.bs4_parser import BS4Parser
from medusa.helper.common import convert_size
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.compat import urljoin

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class AniDexProvider(TorrentProvider):
    """AniDex Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(AniDexProvider, self).__init__('AniDex')

        # Credentials
        self.public = True

        # URLs
        self.url = 'https://anidex.info'
        self.urls = {
            'search': self.url,
        }

        # Miscellaneous Options
        self.supports_absolute_numbering = True
        self.anime_only = True
        self.headers = {
            'X-Requested-With': 'XMLHttpRequest',
        }

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tv.Cache(self, min_time=20)

    def search(self, search_strings, age=0, ep_obj=None):
        """
        Search a provider and parse the results.

        :param search_strings: A dict with mode (key) and the search value (value)
        :param age: Not used
        :param ep_obj: Not used
        :returns: A list of search results (structure)
        """
        results = []

        search_params = {
            'id': '1,2,3'
        }

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {search}',
                              {'search': search_string})

                    search_params.update({'q': search_string})

                response = self.session.get(self.urls['search'], params=search_params)
                if not response or not response.text:
                    log.debug('No data returned from provider')
                    continue

                results += self.parse(response.text, mode)

        return results

    def parse(self, data, mode):
        """
        Parse search results for items.

        :param data: The raw response from a search
        :param mode: The current mode used to search, e.g. RSS

        :return: A list of items found
        """
        items = []

        with BS4Parser(data, 'html5lib') as html:
            table_header = html.find('thead')

            # Continue only if at least one release is found
            if not table_header:
                log.debug('Data returned from provider does not contain any torrents')
                return items

            table_ths = table_header.find_all('th')
            # [u'Category', u'', u'Filename', u'Comments', u'Torrent', u'Magnet',
            #  u'File size', u'Age', u'Seeders', u'Leechers', u'Completed']
            labels = [label.span.get('title') if label.span else '' for label in table_ths]

            torrent_rows = html.find('tbody').find_all('tr')
            for row in torrent_rows:
                cells = row.find_all('td')

                try:
                    title = cells[labels.index('Filename')].span.get_text()
                    download_url = cells[labels.index('Torrent')].a.get('href')
                    if not all([title, download_url]):
                        continue

                    download_url = urljoin(self.url, download_url)

                    seeders = cells[labels.index('Seeders')].get_text()
                    leechers = cells[labels.index('Leechers')].get_text()

                    # Filter unseeded torrent
                    if seeders < min(self.minseed, 1):
                        if mode != 'RSS':
                            log.debug("Discarding torrent because it doesn't meet the"
                                      " minimum seeders: {0}. Seeders: {1}",
                                      title, seeders)
                        continue

                    torrent_size = cells[labels.index('File size')].get_text()
                    size = convert_size(torrent_size) or -1

                    pubdate_raw = cells[labels.index('Age')].get('title')
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
                    log.error('Failed parsing provider. Traceback: {0!r}',
                              traceback.format_exc())

        return items


provider = AniDexProvider()
