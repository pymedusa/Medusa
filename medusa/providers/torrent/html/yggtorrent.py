# coding=utf-8

"""Provider code for Yggtorrent."""

from __future__ import unicode_literals

import logging
import re
import traceback

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


class YggtorrentProvider(TorrentProvider):
    """Yggtorrent Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(YggtorrentProvider, self).__init__('Yggtorrent')

        # Credentials
        self.username = None
        self.password = None

        # URLs
        self.url = 'https://yggtorrent.com/'
        self.urls = {
            'login': urljoin(self.url, 'user/login'),
            'search': urljoin(self.url, 'engine/search'),
        }

        # Proper Strings
        self.proper_strings = ['PROPER']

        # Miscellaneous Options

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tv.Cache(self, min_time=30)

    def search(self, search_strings, age=0, ep_obj=None):
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
        search_params = {}

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {search}',
                              {'search': search_string})

                search_params['q'] = re.sub(r'[()]', '', search_string)
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
            torrent_table = html.find(class_='table table-striped')
            torrent_rows = torrent_table('tr') if torrent_table else []

            # Continue only if at least one Release is found
            if len(torrent_rows) < 2:
                log.debug('Data returned from provider does not contain any torrents')
                return items

            # Skip column headers
            for result in torrent_rows[1:]:
                cells = result('td')
                if len(cells) < 5:
                    continue
                try:
                    title = cells[0].find('a', class_='torrent-name').get_text(strip=True)
                    download_url = urljoin(self.url, cells[0].find('a', target='_blank')['href'])
                    if not (title and download_url):
                        continue

                    seeders = try_int(cells[4].get_text(strip=True))
                    leechers = try_int(cells[5].get_text(strip=True))

                    torrent_size = cells[3].get_text()
                    size = convert_size(torrent_size, sep=None) or -1

                    # Filter unseeded torrent
                    if seeders < min(self.minseed, 1):
                        if mode != 'RSS':
                            log.debug("Discarding torrent because it doesn't meet the"
                                      " minimum seeders: {0}. Seeders: {1}",
                                      title, seeders)
                        continue

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

    def login(self):
        """Login method used for logging in before doing search and torrent downloads."""

        login_params = {
            'id': self.username,
            'pass': self.password,
            'submit': ''
        }

        self.session.post(self.urls['login'], data=login_params)
        response = self.session.get(self.url)
        if not response:
            log.warning('Unable to connect to provider')
            return False

        if 'Connexion' in response.text:
            log.warning('Invalid username or password. Check your settings')
            return False

        return True


provider = YggtorrentProvider()
