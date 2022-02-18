# coding=utf-8

"""Provider code for Zooqle."""

from __future__ import unicode_literals

import logging

from medusa import tv
from medusa.bs4_parser import BS4Parser
from medusa.helper.common import (
    convert_size,
    try_int,
)
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.compat import urljoin

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class ZooqleProvider(TorrentProvider):
    """Zooqle Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(ZooqleProvider, self).__init__('Zooqle')

        # Credentials
        self.public = True

        # URLs
        self.url = 'https://zooqle.com'
        self.urls = {
            'search': urljoin(self.url, '/search'),
        }

        # Proper Strings
        self.proper_strings = ['PROPER', 'REPACK', 'REAL']

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
        search_params = {
            'q': '* category:TV',
            's': 'dt',
            'v': 't',
            'sd': 'd',
        }

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {search}',
                              {'search': search_string})
                    search_params = {'q': '{0} category:TV'.format(search_string)}

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
            torrent_table = html('div', class_='panel-body', limit=2)
            if mode != 'RSS':
                torrent_rows = torrent_table[1]('tr') if torrent_table else []
            else:
                torrent_rows = torrent_table[0]('tr') if torrent_table else []

            # Continue only if at least one release is found
            if len(torrent_rows) < 2:
                log.debug('Data returned from provider does not contain any torrents')
                return items

            # Skip column headers
            for row in torrent_rows[1:]:
                cells = row('td')

                try:
                    title = cells[1].find('a').get_text()
                    magnet = cells[2].find('a', title='Magnet link')['href']
                    download_url = '{magnet}{trackers}'.format(magnet=magnet,
                                                               trackers=self._custom_trackers)
                    if not all([title, download_url]):
                        continue

                    seeders = 1
                    leechers = 0
                    if len(cells) > 5:
                        peers = cells[5].find('div')
                        if peers and peers.get('title'):
                            peers = peers['title'].replace(',', '').split(' | ', 1)
                            # Removes 'Seeders: '
                            seeders = try_int(peers[0][9:])
                            # Removes 'Leechers: '
                            leechers = try_int(peers[1][10:])

                    # Filter unseeded torrent
                    if seeders < self.minseed:
                        if mode != 'RSS':
                            log.debug("Discarding torrent because it doesn't meet the"
                                      ' minimum seeders: {0}. Seeders: {1}',
                                      title, seeders)
                        continue

                    torrent_size = cells[3].get_text().replace(',', '')
                    size = convert_size(torrent_size) or -1

                    pubdate_raw = cells[4].get_text().replace('yesterday', '24 hours')
                    # "long ago" can't be translated to a date
                    if pubdate_raw == 'long ago':
                        pubdate_raw = None
                    pubdate = self.parse_pubdate(pubdate_raw, human_time=True)

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


provider = ZooqleProvider()
