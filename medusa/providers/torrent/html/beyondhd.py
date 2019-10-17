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
from requests.utils import dict_from_cookiejar

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class BeyondHDProvider(TorrentProvider):
    """Beyond-hd Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(BeyondHDProvider, self).__init__('Beyond-HD')

        self.username = None
        self.password = None

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
            torrent_table = html.find('table', class_='table-striped')
            torrent_rows = torrent_table('tr') if torrent_table else []

            # Continue only if one release is found
            if len(torrent_rows) < 2:
                log.debug('Data returned from provider does not contain any torrents')
                return items

            for result in torrent_rows[1:]:
                cells = result('td')

                try:
                    link = cells[1].find('div')
                    download_url = urljoin(self.url, cells[2].find('a')['href'])
                    title = link.get_text(strip=True)
                    if not all([title, download_url]):
                        continue

                    seeders = int(cells[5].find('span').get_text())
                    leechers = int(cells[6].find('span').get_text())

                    # Filter unseeded torrent
                    if seeders < self.minseed:
                        if mode != 'RSS':
                            log.debug("Discarding torrent because it doesn't meet the"
                                      ' minimum seeders: {0}. Seeders: {1}',
                                      title, seeders)
                        continue

                    torrent_size = cells[4].find('span').get_text()
                    size = convert_size(torrent_size, units=units) or -1

                    pubdate_raw = cells[3].find('span').get_text()
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
        if any(dict_from_cookiejar(self.session.cookies).values()):
            return True

        if 'pass' in dict_from_cookiejar(self.session.cookies):
            return True

        login_html = self.session.get(self.urls['login'])
        with BS4Parser(login_html.text, 'html5lib') as html:
            token = html.find('input', attrs={'name': '_token'}).get('value')

        login_params = {
            '_token': token,
            'username': self.username,
            'password': self.password,
            'remember': 'on',
        }

        response = self.session.post(self.urls['login'], data=login_params)
        if not response or not response.text:
            log.warning('Unable to connect to provider')
            return False

        if 'These credentials do not match our records.' in response.text:
            log.warning('Invalid username or password. Check your settings')
            return False

        return True


provider = BeyondHDProvider()
