# coding=utf-8

"""Provider code for Pretome."""

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
from requests.utils import dict_from_cookiejar

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class PretomeProvider(TorrentProvider):
    """Pretome Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(PretomeProvider, self).__init__('Pretome')

        # Credentials
        self.username = None
        self.password = None
        self.pin = None

        # URLs
        self.url = 'https://pretome.info'
        self.urls = {
            'login': urljoin(self.url, 'takelogin.php'),
            'search': urljoin(self.url, 'browse.php'),
        }

        # Proper Strings
        self.proper_strings = ['PROPER', 'REPACK', 'REAL', 'RERIP']

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
            'search': '',
            'st': 1,
            'cat[]': 7,
        }

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {search}',
                              {'search': search_string})

                search_params['search'] = search_string
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
            # Continue only if at least one release is found
            empty = html.find('h2', text='No .torrents fit this filter criteria')
            if empty:
                log.debug('Data returned from provider does not contain any torrents')
                return items

            torrent_table = html.find('table', attrs={'style': 'border: none; width: 100%;'})
            torrent_rows = torrent_table('tr', class_='browse') if torrent_table else []

            for row in torrent_rows:
                cells = row('td')

                try:
                    title = cells[1].find('a').get('title')
                    torrent_url = cells[2].find('a').get('href')
                    download_url = urljoin(self.url, torrent_url)
                    if not all([title, torrent_url]):
                        continue

                    seeders = try_int(cells[9].get_text(), 1)
                    leechers = try_int(cells[10].get_text())

                    # Filter unseeded torrent
                    if seeders < self.minseed:
                        if mode != 'RSS':
                            log.debug("Discarding torrent because it doesn't meet the"
                                      ' minimum seeders: {0}. Seeders: {1}',
                                      title, seeders)
                        continue

                    torrent_size = self._norm_size(cells[7].get_text(strip=True))
                    size = convert_size(torrent_size) or -1

                    pubdate_raw = cells[5].get_text()
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

        login_params = {
            'username': self.username,
            'password': self.password,
            'login_pin': self.pin,
        }

        response = self.session.post(self.urls['login'], data=login_params)
        if not response or not response.text:
            log.warning('Unable to connect to provider')
            return False

        if re.search('Username or password incorrect', response.text):
            log.warning('Invalid username or password. Check your settings')
            return False

        return True

    def _check_auth(self):
        if not all([self.username, self.password, self.pin]):
            log.warning('Invalid username, password or pin. Check your settings')

        return True

    @staticmethod
    def _norm_size(size_string):
        """Normalize the size from the parsed string."""
        if not size_string:
            return size_string
        return re.sub(r'(?P<unit>[A-Z]+)', r' \g<unit>', size_string)


provider = PretomeProvider()
