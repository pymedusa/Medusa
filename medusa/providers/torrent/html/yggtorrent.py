# coding=utf-8

"""Provider code for Yggtorrent."""

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


class YggtorrentProvider(TorrentProvider):
    """Yggtorrent Torrent provider."""

    torrent_id_pattern = re.compile(r'\/(\d+)-')

    def __init__(self):
        """Initialize the class."""
        super(YggtorrentProvider, self).__init__('Yggtorrent')

        # Credentials
        self.username = None
        self.password = None

        # URLs
        self.url = 'https://ww3.yggtorrent.is'
        self.urls = {
            'login': urljoin(self.url, 'user/login'),
            'search': urljoin(self.url, 'engine/search'),
            'download': urljoin(self.url, 'engine/download_torrent?id={0}')
        }

        # Proper Strings
        self.proper_strings = ['PROPER', 'REPACK', 'REAL', 'RERIP']

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
        if not self.login():
            return results

        # Search Params
        search_params = {
            'category': 2145,
            'do': 'search'
        }

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {search}',
                              {'search': search_string})

                    search_params['name'] = re.sub(r'[()]', '', search_string)

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
        units = ['O', 'KO', 'MO', 'GO', 'TO', 'PO']

        items = []

        with BS4Parser(data, 'html5lib') as html:
            torrent_table = html.find(class_='table-responsive results')
            torrent_rows = torrent_table('tr') if torrent_table else []

            # Continue only if at least one Release is found
            if len(torrent_rows) < 2:
                log.debug('Data returned from provider does not contain any torrents')
                return items

            # Skip column headers
            for result in torrent_rows[1:]:
                cells = result('td')
                if len(cells) < 9:
                    continue

                try:
                    info = cells[1].find('a')
                    title = info.get_text(strip=True)
                    download_url = info.get('href')
                    if not (title and download_url):
                        continue

                    torrent_id = self.torrent_id_pattern.search(download_url)
                    download_url = self.urls['download'].format(torrent_id.group(1))

                    seeders = try_int(cells[7].get_text(strip=True), 0)
                    leechers = try_int(cells[8].get_text(strip=True), 0)

                    # Filter unseeded torrent
                    if seeders < min(self.minseed, 1):
                        if mode != 'RSS':
                            log.debug("Discarding torrent because it doesn't meet the"
                                      ' minimum seeders: {0}. Seeders: {1}',
                                      title, seeders)
                        continue

                    torrent_size = cells[5].get_text()
                    size = convert_size(torrent_size, sep='', units=units, default=-1)

                    pubdate_raw = cells[4].find('div', class_='hidden').get_text(strip=True)
                    pubdate = self.parse_pubdate(pubdate_raw, fromtimestamp=True)

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
        login_params = {
            'id': self.username,
            'pass': self.password
        }

        login_resp = self.session.post(self.urls['login'], data=login_params)
        if not login_resp:
            log.warning('Invalid username or password. Check your settings')
            return False

        response = self.session.get(self.url)
        if not response:
            log.warning('Unable to connect to provider')
            return False

        if 'Bienvenue' not in response.text:
            log.warning('Unable to login to provider')
            return False

        return True


provider = YggtorrentProvider()
