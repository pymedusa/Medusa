# coding=utf-8

"""Provider code for HDTorrents."""

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


class HDTorrentsProvider(TorrentProvider):
    """HDTorrents Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(HDTorrentsProvider, self).__init__('HDTorrents')

        # Credentials
        self.username = None
        self.password = None

        # URLs
        self.url = 'https://hd-torrents.org/'
        self.urls = {
            'login': urljoin(self.url, 'login.php'),
            'search': urljoin(self.url, 'torrents.php'),
        }

        # Proper Strings
        self.proper_strings = ['PROPER', 'REPACK', 'REAL', 'RERIP']

        # Miscellaneous Options
        self.freeleech = None

        # Cache
        self.cache = tv.Cache(self, min_time=30)

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
            'active': 5 if self.freeleech else 1,
            'options': 0,
            'category[0]': 59,
            'category[1]': 60,
            'category[2]': 30,
            'category[3]': 38,
            'category[4]': 65,
        }

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    search_params['search'] = search_string
                    log.debug('Search string: {search}',
                              {'search': search_string})

                response = self.session.get(self.urls['search'], params=search_params)
                if not response or not response.text:
                    log.debug('No data returned from provider')
                    continue

                # Search result page contains some invalid html that prevents html parser from returning all data.
                # We cut everything before the table that contains the data we are interested in thus eliminating
                # the invalid html portions
                try:
                    index = response.text.index('<TABLE class="mainblockcontenttt"')
                except ValueError:
                    log.debug('Could not find table of torrents mainblockcontenttt')
                    continue

                results += self.parse(response.text[index:], mode)

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
            torrent_table = html.find('table', class_='mainblockcontenttt')
            torrent_rows = torrent_table('tr') if torrent_table else []

            if not torrent_rows or torrent_rows[2].find('td', class_='lista'):
                log.debug('Data returned from provider does not contain any torrents')
                return items

            # Cat., Active, Filename, Dl, Wl, Added, Size, Uploader, S, L, C
            labels = [label.a.get_text(strip=True) if label.a else label.get_text(strip=True) for label in
                      torrent_rows[0]('td')]

            # Skip column headers
            for row in torrent_rows[1:]:
                try:
                    cells = row.findChildren('td')[:len(labels)]
                    if len(cells) < len(labels):
                        continue

                    title = cells[labels.index('Filename')].a
                    title = title.get_text(strip=True) if title else None
                    link = cells[labels.index('Dl')].a
                    link = link.get('href') if link else None
                    download_url = urljoin(self.url, link) if link else None
                    if not all([title, download_url]):
                        continue

                    seeders = try_int(cells[labels.index('S')].get_text(strip=True))
                    leechers = try_int(cells[labels.index('L')].get_text(strip=True))

                    # Filter unseeded torrent
                    if seeders < self.minseed:
                        if mode != 'RSS':
                            log.debug("Discarding torrent because it doesn't meet the"
                                      ' minimum seeders: {0}. Seeders: {1}',
                                      title, seeders)
                        continue

                    torrent_size = cells[labels.index('Size')].get_text()
                    size = convert_size(torrent_size, units=units) or -1

                    pubdate_raw = cells[labels.index('Added')].get_text()
                    pubdate = self.parse_pubdate(pubdate_raw, dayfirst=True)

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
            'uid': self.username,
            'pwd': self.password,
            'submit': 'Confirm',
        }

        response = self.session.post(self.urls['login'], data=login_params)
        if not response or not response.text:
            log.warning('Unable to connect to provider')
            return False

        if re.search('You need cookies enabled to log in.', response.text):
            log.warning('Invalid username or password. Check your settings')
            return False

        return True

    def _check_auth(self):

        if not self.username or not self.password:
            raise AuthException('Your authentication credentials for {0} are missing,'
                                ' check your config.'.format(self.name))

        return True


provider = HDTorrentsProvider()
