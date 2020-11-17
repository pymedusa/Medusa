# coding=utf-8

"""Provider code for TVChaosUK."""

from __future__ import unicode_literals

import logging
import re

from medusa import tv
from medusa.bs4_parser import BS4Parser
from medusa.helper.common import (
    convert_size,
)
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.compat import quote, urljoin

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class TVChaosUKProvider(TorrentProvider):
    """TVChaosUK Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(TVChaosUKProvider, self).__init__('TvChaosUK')

        # Credentials
        self.username = None
        self.password = None

        # URLs
        self.url = 'https://tvchaosuk.com'
        self.urls = {
            'login': urljoin(self.url, 'login'),
            'search': urljoin(self.url, 'torrents/filter')
        }

        # Proper Strings
        # Provider always returns propers and non-propers in a show search
        self.proper_strings = ['']

        # Miscellaneous Options
        self.freeleech = None

        # Cache
        self.cache = tv.Cache(self)

        # Store _token as it's needed for searches.
        self._token = ''

    def search(self, search_strings, age=0, ep_obj=None, **kwargs):
        """
        Search a provider and parse the results.

        :param search_strings: A dict with mode (key) and the search value (value)
        :param age: Not used
        :param ep_obj: Not used
        :returns: A list of search results (structure)
        """
        results = []
        if not self.login() or not self._token:
            return results

        # Search Params
        search_params = {
            '_token': self._token,
            'search': '',
            'description': '',
            'uploader': '',
            'imdb': '',
            'tvdb': '',
            'view': 'list',
            'tmdb': '',
            'start_year': '',
            'end_year': '',
            'page': 0,
            'qty': 100,
        }

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {search}',
                              {'search': search_string})

                    search_params['search'] = quote(search_string)

                response = self.session.get(self.urls['search'], params='&'.join('{}={}'.format(k, v) for k, v in search_params.items()))
                if not response or not response.text:
                    log.debug('No data returned from provider')
                    continue

                results += self.parse(response.text, mode, keywords=search_string)

        return results

    def parse(self, data, mode, **kwargs):
        """
        Parse search results for items.

        :param data: The raw response from a search
        :param mode: The current mode used to search, e.g. RSS

        :return: A list of items found
        """
        # Units
        units = ['B', 'KB', 'MIB', 'GIB', 'TB', 'PB']

        items = []

        with BS4Parser(data, 'html5lib') as html:
            torrent_table = html.find('table', class_='table')
            torrent_rows = torrent_table('tr') if torrent_table else []

            # Continue only if at least one release is found
            if len(torrent_rows) < 2:
                log.debug('Data returned from provider does not contain any torrents')
                return items

            labels = [label.get_text(strip=True) for label in torrent_rows[0]('th')]

            # Skip column headers
            for row in torrent_rows[1:]:
                try:
                    cells = row('td')

                    if self.freeleech:
                        badges = cells[labels.index('Name')]('span', class_='badge-extra')
                        if 'Freeleech' not in [badge.get_text(strip=True) for badge in badges]:
                            continue

                    title = cells[labels.index('Name')].find('a', class_='view-torrent').get_text(strip=True)
                    download_url = cells[labels.index('Name')].find('button').parent['href']

                    if not all([title, download_url]):
                        continue

                    seeders = int(cells[labels.index('S')].get_text(strip=True))
                    leechers = int(cells[labels.index('L')].get_text(strip=True))

                    # Filter unseeded torrent
                    if seeders < self.minseed:
                        if mode != 'RSS':
                            log.debug("Discarding torrent because it doesn't meet the"
                                      ' minimum seeders: {0}. Seeders: {1}',
                                      title, seeders)
                        continue

                    torrent_size = cells[labels.index('Size')].get_text(strip=True)
                    size = convert_size(torrent_size, units=units) or -1

                    pubdate_raw = cells[labels.index('Created at')].get_text(strip=True)
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
        if len(self.session.cookies) >= 4:
            return True

        # Get the _token
        response_token = self.session.get(self.urls['login'])
        if not response_token or not response_token.text:
            log.warning('Provider not reachable')
            return False

        match_token = re.search(r'<meta name="csrf-token" content="([^"]+)">', response_token.text)
        match_captcha = re.search(r'<input type="hidden" name="_captcha" value="([^"]+)" />', response_token.text)
        match_hash = re.search(r'<input type="hidden".+name="([^"]+)".+value="(\d+)"', response_token.text)

        if not match_token or not match_captcha or not match_hash:
            log.warning('Could not get token or captcha')
            return False

        self._token = match_token.group(1)
        captcha = match_captcha.group(1)
        hash_key = match_hash.group(1)
        hash_value = match_hash.group(2)

        login_params = {
            '_token': self._token,
            'username': self.username,
            'password': self.password,
            'remember': 'on',
            '_captcha': captcha,
            '_username': '',
            hash_key: hash_value
        }

        response = self.session.post(self.urls['login'], data=login_params)
        if not response or not response.text:
            log.warning('Unable to connect to provider')
            return False

        if re.search('These credentials do not match our records', response.text):
            log.warning('Invalid username or password. Check your settings')
            return False

        return True


provider = TVChaosUKProvider()
