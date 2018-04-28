# coding=utf-8

"""Provider code for Speed.cd."""

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


class SpeedCDProvider(TorrentProvider):
    """SpeedCD Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(SpeedCDProvider, self).__init__('Speedcd')

        # Credentials
        self.username = None
        self.password = None

        # URLs
        self.url = 'https://speed.cd'
        self.urls = {
            'login': urljoin(self.url, 'login.php'),
            'search': urljoin(self.url, 'browse.php'),
            'login_post': None,
        }

        # Proper Strings
        self.proper_strings = ['PROPER', 'REPACK', 'REAL']

        # Miscellaneous Options
        self.freeleech = False

        # Torrent Stats
        self.minseed = None
        self.minleech = None

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

        # http://speed.cd/browse.php?c49=1&c50=1&c52=1&c41=1&c55=1&c2=1&c30=1&freeleech=on&search=arrow&d=on
        # Search Params
        search_params = {
            'c2': 1,  # TV/Episodes
            'c30': 1,  # Anime
            'c41': 1,  # TV/Packs
            'c49': 1,  # TV/HD
            'c50': 1,  # TV/Sports
            'c52': 1,  # TV/B-Ray
            'c55': 1,  # TV/Kids
            'search': '',
            'freeleech': 'on' if self.freeleech else None
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
        # Units
        units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']

        items = []

        with BS4Parser(data, 'html5lib') as html:
            torrent_table = html.find('div', class_='boxContent')
            torrent_table = torrent_table.find('table') if torrent_table else None
            torrent_rows = torrent_table('tr') if torrent_table else []

            # Continue only if at least one release is found
            if len(torrent_rows) < 2:
                log.debug('Data returned from provider does not contain any torrents')
                return items

            # Skip column headers
            for row in torrent_rows[1:]:
                cells = row('td')

                try:
                    title = cells[1].find('a', class_='torrent').get_text()
                    download_url = urljoin(self.url,
                                           cells[2].find(title='Download').parent['href'])
                    if not all([title, download_url]):
                        continue

                    seeders = try_int(cells[5].get_text(strip=True))
                    leechers = try_int(cells[6].get_text(strip=True))

                    # Filter unseeded torrent
                    if seeders < min(self.minseed, 1):
                        if mode != 'RSS':
                            log.debug("Discarding torrent because it doesn't meet the"
                                      " minimum seeders: {0}. Seeders: {1}",
                                      title, seeders)
                        continue

                    torrent_size = cells[4].get_text()
                    torrent_size = torrent_size[:-2] + ' ' + torrent_size[-2:]
                    size = convert_size(torrent_size, units=units) or -1

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
        if any(dict_from_cookiejar(self.session.cookies).values()):
            return True

        login_params = {
            'username': self.username,
            'password': self.password,
        }

        if not self.urls['login_post'] and not self.login_url():
            log.debug('Unable to get login URL')
            return False

        response = self.session.post(self.urls['login_post'], data=login_params)
        if not response or not response.text:
            log.debug('Unable to connect to provider using login URL: {url}',
                      {'url': self.urls['login_post']})
            return False
        if 'incorrect username or password. please try again' in response.text.lower():
            log.warning('Invalid username or password. Check your settings')
            return False
        return True

        log.warning('Unable to connect to provider')
        return

    def login_url(self):
        """Get the login url (post) as speed.cd keeps changing it."""
        response = self.session.get(self.urls['login'])
        if not response or not response.text:
            log.debug('Unable to connect to provider to get login URL')
            return
        data = BS4Parser(response.text, 'html5lib')
        login_post = data.soup.find('form', id='loginform').get('action')
        if login_post:
            self.urls['login_post'] = urljoin(self.url, login_post)
            return True


provider = SpeedCDProvider()
