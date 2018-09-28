# coding=utf-8

"""Provider code for BTDB."""

from __future__ import unicode_literals

import logging

from medusa import tv
from medusa.bs4_parser import BS4Parser
from medusa.helper.common import convert_size
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.compat import urljoin

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class BTDBProvider(TorrentProvider):
    """BTDB Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(BTDBProvider, self).__init__('BTDB')

        # Credentials
        self.public = True

        # URLs
        self.url = 'https://btdb.to'
        self.urls = {
            'daily': urljoin(self.url, '/q/x264/?sort=time'),
            'search': urljoin(self.url, '/q/{query}/{page}?sort=popular'),
        }

        # Miscellaneous Options
        self.max_pages = 3

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

                    for page in range(1, self.max_pages + 1):
                        search_url = self.urls['search'].format(query=search_string, page=page)

                        response = self.session.get(search_url)
                        if not response or not response.text:
                            log.debug('No data returned from provider')
                            break

                        page_results = self.parse(response.text, mode)
                        results += page_results
                        if len(page_results) < 10:
                            break

                else:
                    response = self.session.get(self.urls['daily'])
                    if not response or not response.text:
                        log.debug('No data returned from provider')
                        continue

                    results += self.parse(response.text, mode)

                # We don't have the real seeds but we can sort results by popularity and
                # normalize seeds numbers so results can be sort in manual search
                results = self.calc_seeds(results)

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
            table_body = html.find('ul', class_='search-ret-list')

            # Continue only if at least one release is found
            if not table_body:
                log.debug('Data returned from provider does not contain any torrents')
                return items

            torrent_rows = table_body.find_all('li', class_='search-ret-item')
            for row in torrent_rows:
                try:

                    title = row.find('h2').find('a').get('title')
                    download_url = row.find('div').find('a').get('href')
                    if not all([title, download_url]):
                        continue

                    spans = row.find('div').find_all('span')

                    seeders = leechers = 0

                    torrent_size = spans[0].get_text()
                    size = convert_size(torrent_size, default=-1)

                    torrent_pubdate = spans[2].get_text()
                    pubdate = self.parse_pubdate(torrent_pubdate)

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

    def calc_seeds(self, results):
        """Normalize seeds numbers so results can be sort in manual search."""
        seeds = len(results)
        for result in results:
            result['seeders'] = seeds
            seeds -= 1
        return results


provider = BTDBProvider()
