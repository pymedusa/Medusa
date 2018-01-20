# coding=utf-8

"""Provider code for HDSpace."""

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

class PrivateHDProvider(TorrentProvider):
    """PrivateHD Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(PrivateHDProvider, self).__init__('PrivateHD')

        # Credentials
        self.username = None
        self.password = None

        # URLs
        self.url = 'https://privatehd.to'
        self.urls = {
            'login': urljoin(self.url, 'auth/login'),
            'search': urljoin(self.url, 'torrents'),
        }

        # Proper Strings

        # Miscellaneous Options

        # Torrent Stats

        # Cache
        self.cache = tv.Cache(self)  # only poll PrivateHD every 10 minutes max

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
                print("Search string:" + search_string)

                if mode != 'RSS':
                    log.debug('Search string: {search}',
                              {'search': search_string})

                search_params = {
                    'in': 1,
                    'search': search_string,
                    'type': 2
                }

                if not search_string:
                    del search_params['search']

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
            if not html:
                log.debug('No html data parsed from provider')
                return items

            torrents = html('tr')
            if not torrents or len(torrents) < 2:
                log.debug('Data returned from provider does not contain any torrents')
                return items

            # Skip column headers
            for row in torrents[1:]:
                # Skip extraneous rows at the end
                if len(row.contents) < 10:
                    continue

                try:
                    title = row.find(class_='torrent-filename').text.strip()
                    download_url = row.find(class_='torrent-download-icon').get('href')
                    size = convert_size(row.contents[11].text.strip(), -1)
                    seeders = row.contents[13].text
                    leechers = row.contents[15].text
                    pubdate = self.parse_pubdate(row.contents[7].findChild().get('title'))

                    item = {
                        'title': title,
                        'link': download_url,
                        'size': size,
                        'seeders': seeders,
                        'leechers': leechers,
                        'pubdate': pubdate,
                    }
                    if mode != 'RSS':
                        pass
                    log.debug('Found result: {0} with {1} seeders and {2} leechers',
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

        if 'pass' in dict_from_cookiejar(self.session.cookies):
            return True

        with BS4Parser(self.session.get(self.urls['login']).text, 'html5lib') as html:
            token = html.find('input', attrs={'name': '_token'}).get('value')

        login_params = {
            '_token': token,
            'email_username': self.username,
            'password': self.password,
            'remember': 1,
            'submit': 'Login',
        }

        response = self.session.post(self.urls['login'], data=login_params)
        if not response or not response.text:
            log.warning('Unable to connect to provider')
            return False

        if re.search('These credentials do not match our records.', response.text):
            log.warning('Invalid username or password. Check your settings')
            return False

        return True

    def _check_auth(self):

        if not self.username or not self.password:
            log.warning('Invalid username or password. Check your settings')

        return True


provider = PrivateHDProvider()
