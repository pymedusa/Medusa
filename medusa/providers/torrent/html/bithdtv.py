# coding=utf-8

"""Provider code for Bithdtv."""

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


class BithdtvProvider(TorrentProvider):
    """BIT-HDTV Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(BithdtvProvider, self).__init__('BITHDTV')

        # URLs
        self.url = 'https://www.bit-hdtv.com/'
        self.urls = {
            'search': urljoin(self.url, 'torrents.php'),
        }

        # Proper Strings
        self.proper_strings = ['PROPER', 'REPACK', 'REAL']

        # Miscellaneous Options
        self.enable_cookies = True
        self.cookies = ''
        self.required_cookies = ('h_sl', 'h_sp', 'h_su')

        # Miscellaneous Options
        self.freeleech = False

        # Cache
        self.cache = tv.Cache(self)

    def search(self, search_strings, age=0, ep_obj=None, **kwargs):
        """
        Search a provider and parse the results.

        :param search_strings: A dict with mode (key) and the search value (value)
        :param age: Not used
        :param ep_obj: Not used
        :returns: A list of search results (structure)
        """
        results = []
        if not self.login():
            return results

        # Search Params
        search_params = {
            'cat': '10',
        }

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {search}',
                              {'search': search_string})
                search_params['search'] = search_string

                if mode == 'Season':
                    search_params['cat'] = 12
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

        with BS4Parser(data, 'html.parser') as html:  # Use html.parser, since html5parser has issues with this site.
            tables = html('table', width='800')  # Get the last table with a width of 800px.
            torrent_table = tables[-1] if tables else []
            torrent_rows = torrent_table('tr') if torrent_table else []

            # Continue only if at least one release is found
            if len(torrent_rows) < 2:
                log.debug('Data returned from provider does not contain any torrents')
                return items

            # Skip column headers
            for row in torrent_rows[1:]:
                cells = row('td')
                if len(cells) < 3:
                    # We must have cells[2] because it contains the title
                    continue

                if self.freeleech and not row.get('bgcolor'):
                    continue

                try:
                    title = cells[2].find('a')['title'] if cells[2] else None
                    download_url = urljoin(self.url, cells[0].find('a')['href']) if cells[0] else None
                    if not all([title, download_url]):
                        continue

                    seeders = try_int(cells[8].get_text(strip=True)) if len(cells) > 8 else 1
                    leechers = try_int(cells[9].get_text(strip=True)) if len(cells) > 9 else 0

                    # Filter unseeded torrent
                    if seeders < self.minseed:
                        if mode != 'RSS':
                            log.debug("Discarding torrent because it doesn't meet the"
                                      ' minimum seeders: {0}. Seeders: {1}',
                                      title, seeders)
                        continue

                    torrent_size = cells[6].get_text(' ') if len(cells) > 6 else None
                    size = convert_size(torrent_size) or -1

                    pubdate_raw = cells[5].get_text(' ')
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

    def login(self):
        """Login method used for logging in before doing a search and torrent downloads."""
        return self.cookie_login('login failed', check_url=self.urls['search'])


provider = BithdtvProvider()
