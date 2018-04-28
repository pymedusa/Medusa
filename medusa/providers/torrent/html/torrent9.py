# coding=utf-8

"""Provider code for Torrent9."""

from __future__ import unicode_literals

import logging
import re

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


class Torrent9Provider(TorrentProvider):
    """Torrent9 Torrent provider."""

    non_words = re.compile(r'\W')

    def __init__(self):
        """Initialize the class."""
        super(Torrent9Provider, self).__init__('Torrent9')

        # Credentials
        self.public = True

        # URLs
        self.url = 'http://www.torrent9.red'
        self.urls = {
            'search': urljoin(self.url, '/search_torrent/{query}.html'),
            'daily': urljoin(self.url, '/torrents_series.html,trie-date-d'),
            'download': urljoin(self.url, '/get_torrent/{name}.torrent'),
        }

        # Proper Strings
        self.proper_strings = ['PROPER', 'REPACK']

        # Miscellaneous Options

        # Torrent Stats
        self.minseed = None
        self.minleech = None

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
                    search_query = Torrent9Provider.non_words.sub('-', search_string)
                    search_url = self.urls['search'].format(query=search_query)
                else:
                    search_url = self.urls['daily']

                response = self.session.get(search_url)
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
        # Units
        units = ['O', 'KO', 'MO', 'GO', 'TO', 'PO']

        items = []

        with BS4Parser(data, 'html5lib') as html:
            table_body = html.find('tbody')

            # Continue only if at least one release is found
            if not table_body:
                log.debug('Data returned from provider does not contain any torrents')
                return items

            for row in table_body('tr'):
                cells = row('td')
                if len(cells) < 4:
                    continue

                try:
                    info_cell = cells[0].a
                    title = info_cell.get_text()
                    download_url = info_cell.get('href')
                    if not all([title, download_url]):
                        continue

                    title = '{name} {codec}'.format(name=title, codec='x264')

                    download_name = download_url.rsplit('/', 1)[1]
                    download_url = self.urls['download'].format(name=download_name)

                    seeders = try_int(cells[2].get_text(strip=True))
                    leechers = try_int(cells[3].get_text(strip=True))

                    # Filter unseeded torrent
                    if seeders < min(self.minseed, 1):
                        if mode != 'RSS':
                            log.debug("Discarding torrent because it doesn't meet the"
                                      " minimum seeders: {0}. Seeders: {1}",
                                      title, seeders)
                        continue

                    torrent_size = cells[1].get_text()
                    size = convert_size(torrent_size, units=units) or -1

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


provider = Torrent9Provider()
