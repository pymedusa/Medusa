# coding=utf-8

"""Provider code for NordicBits."""

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
from requests.utils import dict_from_cookiejar

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class NordicBitsProvider(TorrentProvider):
    """NordicBits Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(NordicBitsProvider, self).__init__('NordicBits')

        # Credentials
        self.username = None
        self.password = None

        # URLs
        self.url = 'https://nordicb.org'
        self.urls = {
            'login': urljoin(self.url, 'takelogin.php'),
            'search': urljoin(self.url, 'browse.php'),
        }

        # Proper Strings
        self.proper_strings = ['PROPER', 'REPACK', 'REAL', 'RERIP']

        # Miscellaneous Options
        self.freeleech = False

        # Cache
        self.cache = tv.Cache(self)

    def search(self, search_strings, **kwargs):
        """
        Search a provider and parse the results.

        :param search_strings: A dict with mode (key) and the search value (value)
        :returns: A list of search results (structure)
        """
        results = []
        if not self.login():
            return results

        search_params = {
            'cats2[]': [48, 57, 66, 11, 7, 5, 30, 31, 32],
            'searchin': 'title',
            'incldead': 0  # Fixed to not include dead torrents for now
        }

        if self.freeleech:
            search_params['only_free'] = 1

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

                results += self.parse(response.text, mode)

        return results

    def parse(self, data, mode):
        """
        Parse search results for items.

        :param data: The raw response from a search
        :param mode: The current mode used to search, e.g. RSS

        :return: A list of items found
        """
        def get_label_title(label):
            """Get table row header labels."""
            if label.get_text():
                return label.get_text(strip=True)
            if label.a and label.a.get_text(strip=True):
                return label.a.get_text(strip=True)
            if label.img:
                return label.img.get('title')

        items = []
        if '<h2>Nothing found!</h2>' in data:
            log.debug('Data returned from provider does not contain any torrents')
            return items

        with BS4Parser(data, 'html.parser') as html:
            torrent_table = html.find('table', width='100%')
            torrent_rows = torrent_table('tr') if torrent_table else []

            # Continue only if at least one release is found
            if len(torrent_rows) < 1:
                log.debug('Data returned from provider does not contain any torrents')
                return items

            # Cat., Active, Name, Download, Added, Size, Uploader, Seeders, Leechers
            labels = [get_label_title(label) for label in
                      torrent_rows[0]('td')]

            for row in torrent_rows[1:]:
                try:
                    cells = row.findChildren('td')[:len(labels)]
                    if len(cells) < len(labels):
                        continue

                    title = cells[labels.index('Name')].a
                    title = title.get_text(strip=True) if title else None
                    link = cells[labels.index('Download')].a
                    link = link.get('href') if link else None
                    download_url = urljoin(self.url, link) if link else None
                    if not all([title, download_url]):
                        continue

                    seeders = try_int(cells[labels.index('Seeders')].get_text(strip=True))
                    leechers = try_int(cells[labels.index('Leechers')].get_text(strip=True))

                    # Filter unseeded torrent
                    if seeders < self.minseed:
                        if mode != 'RSS':
                            log.debug("Discarding torrent because it doesn't meet the"
                                      ' minimum seeders: {0}. Seeders: {1}',
                                      title, seeders)
                        continue

                    torrent_size, _, unit = cells[labels.index('Size')].contents
                    size = convert_size('{0} {1}'.format(torrent_size, unit)) or -1

                    pubdate_raw = cells[labels.index('Added')].get_text()
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
        cookies = dict_from_cookiejar(self.session.cookies)
        if any(cookies.values()) and cookies.get('uid'):
            return True

        login_params = {
            'username': self.username,
            'password': self.password,
            'use_ssl': 1,
            'perm_ssl': 1
        }

        response = self.session.post(self.urls['login'], data=login_params)

        if not response or not response.text:
            log.warning('Unable to connect to provider')
            return False

        if 'Welcome back' in response.text:
            return True
        else:
            log.warning('Invalid username or password. Check your settings')
            return False


provider = NordicBitsProvider()
