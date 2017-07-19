# coding=utf-8

"""Provider code for Torrenting."""

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
from requests.utils import dict_from_cookiejar

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class TorrentingProvider(TorrentProvider):
    """Torrenting Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(TorrentingProvider, self).__init__('Torrenting')

        # Credentials
        self.username = None
        self.password = None

        # URLs
        self.url = 'https://www.torrenting.com/'
        self.urls = {
            'login': urljoin(self.url, 'login.php'),
            'search': urljoin(self.url, 'browse.php'),
        }

        # Proper Strings
        # Provider always returns propers and non-propers in a show search
        self.proper_strings = ['']

        # Miscellaneous Options
        self.enable_cookies = True
        self.cookies = ''

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tv.Cache(self, min_time=0.1)  # only poll Torrenting every 20 minutes max

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
            'c4': 1,  # TV/SD-x264
            'c5': 1,  # TV/X264 HD
            'c18': 1,  # TV/Packs
            'c49': 1,  # x265 (HEVC)
            'search': '',
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
            torrent_rows = html.find("table", {"id": "torrentsTable"}).find_all('tr')

            # Continue only if at least one release is found
            if len(torrent_rows) < 1:
                log.debug('Data returned from provider does not contain any torrents')
                return items

            # Skip column headers
            for row in torrent_rows[1:]:
                try:
                    torrent_items = row.find_all('td')
                    title = torrent_items[1].find('a').get_text(strip=True)
                    download_url = urljoin(self.url, torrent_items[2].find('a')['href'])
                    if not all([title, download_url]):
                        continue

                    seeders = try_int(torrent_items[5].get_text(strip=True))
                    leechers = try_int(torrent_items[6].get_text(strip=True))

                    # Filter unseeded torrent
                    if seeders < min(self.minseed, 1):
                        if mode != 'RSS':
                            log.debug("Discarding torrent because it doesn't meet the"
                                      " minimum seeders: {0}. Seeders: {1}",
                                      title, seeders)
                        continue

                    torrent_size = torrent_items[4].get_text()
                    size = convert_size(torrent_size) or -1

                    pubdate_raw = torrent_items[1].find('div').get_text()
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
                    log.error('Failed parsing provider. Traceback: {0!r}',
                              traceback.format_exc())

        return items

    def login(self):
        """Login method used for logging in before doing search and torrent downloads."""
        if dict_from_cookiejar(self.session.cookies).get('uid') and \
                dict_from_cookiejar(self.session.cookies).get('pass'):
            return True

        if self.cookies:
            self.add_cookies_from_ui()
        else:
            log.warning('Failed to login, you must add your cookies in the provider settings')
            return False

        login_params = {
            'username': self.username,
            'password': self.password,
            'submit.x': 0,
            'submit.y': 0,
        }

        response = self.session.post(self.urls['login'], data=login_params)
        if not response or not response.text:
            log.warning('Unable to connect to provider')
            return False

        if re.search('Username or password incorrect', response.text):
            log.warning('Invalid username or password. Check your settings')
            return False

        if (dict_from_cookiejar(self.session.cookies).get('uid') and
                dict_from_cookiejar(self.session.cookies).get('uid') in response.text):
            return True
        else:
            log.warning('Failed to login, check your cookies')
            self.session.cookies.clear()
            return False


provider = TorrentingProvider()
