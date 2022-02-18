# coding=utf-8

"""Provider code for CinemaZ."""

from __future__ import unicode_literals

import logging

from medusa import tv
from medusa.bs4_parser import BS4Parser
from medusa.helper.common import convert_size
from medusa.helper.exceptions import AuthException
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.compat import urljoin
from requests.utils import dict_from_cookiejar

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class CinemaZProvider(TorrentProvider):
    """CinemaZ Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(CinemaZProvider, self).__init__('CinemaZ')

        # Credentials
        self.username = None
        self.password = None

        # URLs
        self.url = 'https://cinemaz.to'
        self.urls = {
            'login': urljoin(self.url, 'auth/login'),
            'search': urljoin(self.url, 'torrents'),
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

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            for search_string in search_strings[mode]:
                if mode != 'RSS':
                    log.debug('Search string: {search}',
                              {'search': search_string})

                search_params = {
                    'in': 1,
                    'search': search_string,
                    'type': 2,
                    'discount[]': 1 if self.freeleech else None,
                    'tv_type[]': {'episode': 1, 'season': 2}.get(mode.lower())
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
                    title = row.find(class_='torrent-filename').get_text(strip=True)
                    download_url = row.find(class_='torrent-download-icon').get('href')
                    seeders = row.contents[13].get_text()
                    leechers = row.contents[15].get_text()
                    size = convert_size(row.contents[11].get_text(strip=True), default=-1)
                    pubdate = self.parse_pubdate(row.contents[7].contents[1].get('title'))

                    item = {
                        'title': title,
                        'link': download_url,
                        'size': size,
                        'seeders': seeders,
                        'leechers': leechers,
                        'pubdate': pubdate,
                    }
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

        if 'pass' in dict_from_cookiejar(self.session.cookies):
            return True

        login_html = self.session.get(self.urls['login'])
        if not login_html or not login_html.text:
            log.warning('Unable to connect to provider')
            return False
        with BS4Parser(login_html.text, 'html5lib') as html:
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

        if 'These credentials do not match our records.' in response.text:
            log.warning('Invalid username or password. Check your settings')
            return False

        return True

    def _check_auth(self):

        if not self.username or not self.password:
            raise AuthException('Your authentication credentials for {0} are missing,'
                                ' check your config.'.format(self.name))

        return True


provider = CinemaZProvider()
