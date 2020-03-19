# coding=utf-8

"""Provider code for Beyond-hd."""

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


class BeyondHDProvider(TorrentProvider):
    """Beyond-hd Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(BeyondHDProvider, self).__init__('Beyond-HD')

        self.enable_cookies = True
        self.cookies = ''
        self.required_cookies = ('remember_web_[**long_hash**]',)

        self.url = 'https://beyond-hd.me'
        self.urls = {
            'login': urljoin(self.url, 'login'),
            'search': urljoin(self.url, 'torrents'),
        }

        # Proper Strings
        self.proper_strings = ['PROPER', 'REPACK', 'REAL', 'RERIP']

        # Miscellaneous Options

        # Cache
        self.cache = tv.Cache(self)

    def search(self, search_strings, *args, **kwargs):
        """
        Search a provider and parse the results.

        :param search_strings: A dict with mode (key) and the search value (value)
        :returns: A list of search results (structure)
        """
        results = []
        if not self.login():
            return results

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            for search_string in search_strings[mode]:

                search_params = {
                    'categories[]': 2,
                    'sorting': 'created_at',
                    'qty': '100',
                    'direction': 'desc',
                    'doSearch': 'Search'
                }

                if mode != 'RSS':
                    log.debug('Search string: {search}',
                              {'search': search_string})
                    search_params['search'] = search_string

                if mode == 'season':
                    search_params['pack'] = 1

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
        # Units
        units = ['B', 'KIB', 'MIB', 'GIB', 'TIB', 'PIB']

        items = []

        with BS4Parser(data, 'html5lib') as html:
            if html.find('div', class_='table-torrents'):
                theme = 'modern'
                torrent_table = html.find('div', class_='table-torrents').find('table')
            else:
                theme = 'classic'
                torrent_table = html.find('div', class_='table-responsive').find('table')

            torrent_rows = torrent_table('tr') if torrent_table else []
            labels = [label.get_text(strip=True) for label in torrent_rows[0]('th')]
            # For the classic theme, the tr don't match the td.
            if theme == 'classic':
                del labels[3]

            # Continue only if one release is found
            if len(torrent_rows) < 2:
                log.debug('Data returned from provider does not contain any torrents')
                return items

            for result in torrent_rows[1:]:
                cells = result('td')

                try:
                    if len(cells) < 2:
                        continue

                    link = cells[1].find('a')
                    download_url = urljoin(self.url, cells[2].find('a')['href'])
                    title = link.get_text(strip=True)
                    if not all([title, download_url]):
                        continue

                    seeders = int(cells[labels.index('S')].find('span').get_text())
                    leechers = int(cells[labels.index('L')].find('span').get_text())

                    # Filter unseeded torrent
                    if seeders < self.minseed:
                        if mode != 'RSS':
                            log.debug("Discarding torrent because it doesn't meet the"
                                      ' minimum seeders: {0}. Seeders: {1}',
                                      title, seeders)
                        continue

                    torrent_size = cells[labels.index('Size')].find('span').get_text()
                    size = convert_size(torrent_size, units=units) or -1

                    pubdate_raw = cells[labels.index('Age')].find('span').get_text()
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

    def login(self):
        """Login method used for logging in before doing search and torrent downloads."""
        return self.cookie_login('Login now')

    def check_required_cookies(self):
        """
        Check if we have the required cookies in the requests sessions object.

        Meaning that we've already successfully authenticated once, and we don't need to go through this again.
        Note! This doesn't mean the cookies are correct!
        """
        return False


provider = BeyondHDProvider()
