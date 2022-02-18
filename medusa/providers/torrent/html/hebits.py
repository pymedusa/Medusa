# coding=utf-8

"""Provider code for HeBits."""

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
from requests.utils import dict_from_cookiejar

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class HeBitsProvider(TorrentProvider):
    """HeBits Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(HeBitsProvider, self).__init__('HeBits')

        # Credentials
        self.username = None
        self.password = None

        # URLs
        self.url = 'https://hebits.net'
        self.urls = {
            'login': urljoin(self.url, 'takeloginAjax.php'),
            'search': urljoin(self.url, 'browse.php'),
        }

        # Proper Strings
        self.proper_strings = ['PROPER', 'REPACK', 'REAL', 'RERIP']

        # Miscellaneous Options
        self.freeleech = False

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

        # Search Params
        # Israeli SD , English SD , Israeli HD , English HD
        # 7          , 24         , 37         , 1
        search_params = {
            'c1': '1',
            'c24': '1',
            'c37': '1',
            'c7': '1',
            'search': '',
            'cata': '0',
        }
        if self.freeleech:
            search_params['free'] = 'on'

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
        items = []

        with BS4Parser(data, 'html.parser') as html:
            torrent_table = html.find('div', class_='browse')
            torrent_rows = torrent_table('div', class_=re.compile('^line')) if torrent_table else []

            # Continue only if at least one release is found
            if len(torrent_rows) < 1:
                log.debug('Data returned from provider does not contain any torrents')
                return items

            for row in torrent_rows:
                try:
                    heb_eng_title = row.find('div', class_='bTitle').find(href=re.compile(r'details\.php')).find('b').get_text()
                    if '/' in heb_eng_title:
                        title = heb_eng_title.split('/')[1].strip()
                    elif '\\' in heb_eng_title:
                        title = heb_eng_title.split('\\')[1].strip()
                    else:
                        continue

                    download_id = row.find('div', class_='bTitle').find(href=re.compile(r'download\.php'))['href']

                    if not all([title, download_id]):
                        continue

                    download_url = urljoin(self.url, download_id)

                    seeders = try_int(row.find('div', class_='bUping').get_text(strip=True))
                    leechers = try_int(row.find('div', class_='bDowning').get_text(strip=True))

                    # Filter unseeded torrent
                    if seeders < self.minseed:
                        if mode != 'RSS':
                            log.debug("Discarding torrent because it doesn't meet the"
                                      ' minimum seeders: {0}. Seeders: {1}',
                                      title, seeders)
                        continue

                    torrent_size = row.find('div', class_='bSize').get_text(strip=True)
                    size = convert_size(torrent_size[5:], sep='') or -1

                    pubdate_raw = row.find('div', class_=re.compile('bHow')).find_all('span')[1].next_sibling.strip()
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
        }

        response = self.session.post(self.urls['login'], data=login_params)

        if not response or not response.text:
            log.warning('Unable to connect to provider')
            return False

        if response.text == 'OK':
            return True
        elif response.text == 'Banned':
            log.warning('User {0} is banned from HeBits', self.username)
            return False
        elif response.text == 'MaxAttempts':
            log.warning('Max number of login attempts exceeded - your IP is blocked')
            return False
        else:
            log.warning('Invalid username or password. Check your settings')
            return False


provider = HeBitsProvider()
