# coding=utf-8

"""Provider code for Danishbits."""

from __future__ import unicode_literals

import logging
import traceback

from dateutil import parser

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


class DanishbitsProvider(TorrentProvider):
    """Danishbits Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(self.__class__, self).__init__('Danishbits')

        # Credentials
        self.username = None
        self.password = None

        # URLs
        self.url = 'https://danishbits.org'
        self.urls = {
            'login': urljoin(self.url, 'login.php'),
            'search': urljoin(self.url, 'torrents.php'),
        }

        # Proper Strings

        # Miscellaneous Options
        self.freeleech = True

        # Torrent Stats
        self.minseed = 0
        self.minleech = 0

        # Cache
        self.cache = tv.Cache(self, min_time=10)  # Only poll Danishbits every 10 minutes max

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
        search_params = {
            'action': 'newbrowse',
            'group': 3,
            'search': '',
        }

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {search}',
                              {'search': search_string})

                search_params['search'] = search_string
                response = self.get_url(self.urls['search'], params=search_params, returns='response')
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
        units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']

        def process_column_header(td):
            result = ''
            if td.img:
                result = td.img.get('title')
            if not result:
                result = td.get_text(strip=True)
            return result

        items = []

        with BS4Parser(data, 'html5lib') as html:
            torrent_table = html.find('table', id='torrent_table')
            torrent_rows = torrent_table('tr') if torrent_table else []

            # Continue only if at least one release is found
            if len(torrent_rows) < 2:
                log.debug('Data returned from provider does not contain any torrents')
                return items

            # Literal:     Navn, Størrelse, Kommentarer, Tilføjet, Snatches, Seeders, Leechers
            # Translation: Name, Size,      Comments,    Added,    Snatches, Seeders, Leechers
            labels = [process_column_header(label) for label in torrent_rows[0]('td')]

            # Skip column headers
            for row in torrent_rows[1:]:
                cells = row('td')
                if len(cells) < len(labels):
                    continue

                try:
                    title = row.find(class_='croptorrenttext').get_text(strip=True)
                    download_url = urljoin(self.url, row.find(title='Direkte download link')['href'])
                    if not all([title, download_url]):
                        continue

                    seeders = try_int(cells[labels.index('Seeders')].get_text(strip=True))
                    leechers = try_int(cells[labels.index('Leechers')].get_text(strip=True))

                    # Filter unseeded torrent
                    if seeders < min(self.minseed, 1):
                        if mode != 'RSS':
                            log.debug("Discarding torrent because it doesn't meet the"
                                      " minimum seeders: {0}. Seeders: {1}",
                                      title, seeders)
                        continue

                    freeleech = row.find(class_='freeleech')
                    if self.freeleech and not freeleech:
                        continue

                    torrent_size = cells[labels.index('Størrelse')].contents[0]
                    size = convert_size(torrent_size, units=units) or -1
                    pubdate_raw = cells[labels.index('Tilføjet')].find('span')['title']
                    pubdate = parser.parse(pubdate_raw, fuzzy=True) if pubdate_raw else None

                    item = {
                        'title': title,
                        'link': download_url,
                        'size': size,
                        'seeders': seeders,
                        'leechers': leechers,
                        'pubdate': pubdate,
                    }
                    if mode != 'RSS':
                        log.log('Found result: {0} with {1} seeders and {2} leechers',
                                title, seeders, leechers)

                    items.append(item)
                except (AttributeError, TypeError, KeyError, ValueError, IndexError):
                    log.error('Failed parsing provider. Traceback: {0!r}',
                              traceback.format_exc())

        return items

    def login(self):
        """Login method used for logging in before doing search and torrent downloads."""
        if any(dict_from_cookiejar(self.session.cookies).values()):
            return True

        login_params = {
            'username': self.username,
            'password': self.password,
            'keeplogged': 1,
            'langlang': '',
            'login': 'Login',
        }

        response = self.get_url(self.urls['login'], post_data=login_params, returns='response')
        if not response or not response.text:
            log.warning('Unable to connect to provider')
            self.session.cookies.clear()
            return False

        if '<title>Login :: Danishbits.org</title>' in response.text:
            log.warning('Invalid username or password. Check your settings')
            self.session.cookies.clear()
            return False

        return True


provider = DanishbitsProvider()
