# coding=utf-8

"""Provider code for Nebulance."""

from __future__ import unicode_literals

import logging
import re

from medusa import tv
from medusa.bs4_parser import BS4Parser
from medusa.helper.common import (
    convert_size,
    try_int,
)
from medusa.helper.exceptions import AuthException
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.compat import urljoin
from requests.utils import dict_from_cookiejar

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class NebulanceProvider(TorrentProvider):
    """Nebulance Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(NebulanceProvider, self).__init__('Nebulance')

        # Credentials
        self.username = None
        self.password = None

        # URLs
        self.url = 'https://nebulance.io/'
        self.urls = {
            'login': urljoin(self.url, '/login.php'),
            'search': urljoin(self.url, '/torrents.php'),
        }

        # Proper Strings

        # Miscellaneous Options
        self.freeleech = None

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

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {search}',
                              {'search': search_string})

                search_params = {
                    'searchtext': search_string,
                    'filter_freeleech': (0, 1)[self.freeleech is True],
                    'order_by': ('seeders', 'time')[mode == 'RSS'],
                    'order_way': 'desc',
                }

                if not search_string:
                    del search_params['searchtext']

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
            torrent_table = html.find('table', {'id': 'torrent_table'})

            # Continue only if at least one release is found
            if not torrent_table:
                log.debug('Data returned from provider does not contain any torrents')
                return items

            torrent_rows = torrent_table('tr', {'class': 'torrent'})

            # Continue only if one Release is found
            if not torrent_rows:
                log.debug('Data returned from provider does not contain any torrents')
                return items

            for row in torrent_rows:
                try:
                    freeleech = row.find('img', alt='Freeleech') is not None
                    if self.freeleech and not freeleech:
                        continue

                    download_item = row.find('a', {'title': [
                        'Download Torrent',  # Download link
                        'Previously Grabbed Torrent File',  # Already Downloaded
                        'Currently Seeding Torrent',  # Seeding
                        'Currently Leeching Torrent',  # Leeching
                    ]})

                    if not download_item:
                        continue

                    download_url = urljoin(self.url, download_item['href'])

                    temp_anchor = row.find('a', {'data-src': True})
                    title = temp_anchor['data-src']
                    if not all([title, download_url]):
                        continue

                    cells = row('td')
                    seeders = try_int(cells[5].text.strip())
                    leechers = try_int(cells[6].text.strip())

                    # Filter unseeded torrent
                    if seeders < self.minseed:
                        if mode != 'RSS':
                            log.debug("Discarding torrent because it doesn't meet the"
                                      ' minimum seeders: {0}. Seeders: {1}',
                                      title, seeders)
                        continue

                    torrent_size = cells[2].find('div').get_text(strip=True)
                    size = convert_size(torrent_size) or -1

                    pubdate_raw = cells[3].find('span')['title']
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
        """Login method used for logging in before doing search and torrent downloads."""
        if any(dict_from_cookiejar(self.session.cookies).values()):
            return True

        login_params = {
            'username': self.username,
            'password': self.password,
            'keeplogged': 'on',
            'login': 'Login'
        }

        response = self.session.post(self.urls['login'], data=login_params)
        if not response or not response.text:
            log.warning('Unable to connect to provider')
            return False

        if any([re.search('Username Incorrect', response.text),
                re.search('Password Incorrect', response.text), ]):
            log.warning('Invalid username or password. Check your settings')
            return False

        return True

    def _check_auth(self):
        """Check if user credentials."""
        if not self.username or not self.password:
            raise AuthException('Your authentication credentials for {0} are missing,'
                                ' check your config.'.format(self.name))

        return True


provider = NebulanceProvider()
