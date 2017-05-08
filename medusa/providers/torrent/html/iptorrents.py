# coding=utf-8

"""Provider code for IPTorrents."""

from __future__ import unicode_literals

import logging
import re
import traceback

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


class IPTorrentsProvider(TorrentProvider):
    """IPTorrents Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(self.__class__, self).__init__('IPTorrents')

        # Credentials
        self.username = None
        self.password = None

        # URLs
        self.url = 'https://iptorrents.eu'
        self.urls = {
            'base_url': self.url,
            'login': urljoin(self.url, 'torrents'),
            'search': urljoin(self.url, 't?%s%s&q=%s&qf=#torrents'),
        }

        # Proper Strings

        # Miscellaneous Options
        self.freeleech = False
        self.enable_cookies = True
        self.cookies = ''
        self.categories = '73=&60='

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tv.Cache(self, min_time=10)  # Only poll IPTorrents every 10 minutes max

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

        freeleech = '&free=on' if self.freeleech else ''

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {search}',
                              {'search': search_string})

                # URL with 50 tv-show results, or max 150 if adjusted in IPTorrents profile
                search_url = self.urls['search'] % (self.categories, freeleech, search_string)
                search_url += ';o=seeders' if mode != 'RSS' else ''

                response = self.session.get(search_url)
                if not response or not response.text:
                    log.debug('No data returned from provider')
                    continue

                data = re.sub(r'(?im)<button.+?<[/]button>', '', response.text, 0)

                results += self.parse(data, mode)

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
            torrent_table = html.find('table', id='torrents')
            torrents = torrent_table('tr') if torrent_table else []

            # Continue only if at least one release is found
            if len(torrents) < 2 or html.find(text='No Torrents Found!'):
                log.debug('Data returned from provider does not contain any torrents')
                return items

            # Skip column headers
            for row in torrents[1:]:
                try:
                    title = row('td')[1].find('a').text
                    download_url = self.urls['base_url'] + row('td')[3].find('a')['href']
                    if not all([title, download_url]):
                        continue

                    seeders = int(row.find('td', attrs={'class': 'ac t_seeders'}).text)
                    leechers = int(row.find('td', attrs={'class': 'ac t_leechers'}).text)

                    # Filter unseeded torrent
                    if seeders < min(self.minseed, 1):
                        if mode != 'RSS':
                            log.debug("Discarding torrent because it doesn't meet the"
                                      " minimum seeders: {0}. Seeders: {1}",
                                      title, seeders)
                        continue

                    torrent_size = row('td')[5].text
                    size = convert_size(torrent_size) or -1

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
            'login': 'submit',
            'submit.x': 0,
            'submit.y': 0,
        }

        # Initialize session with a GET to have cookies
        self.session.get(self.urls['login'])
        response = self.session.post(self.urls['login'], data=login_params)
        if not response or not response.text:
            log.warning('Unable to connect to provider')
            return False

        # Invalid username and password combination
        if re.search('Invalid username and password combination', response.text):
            log.warning('Invalid username or password. Check your settings')
            return False

        # You tried too often, please try again after 2 hours!
        if re.search('You tried too often', response.text):
            log.warning('You tried too often, please try again after 2 hours!'
                        ' Disable IPTorrents for at least 2 hours')
            return False

        if (dict_from_cookiejar(self.session.cookies).get('uid') and
                dict_from_cookiejar(self.session.cookies).get('uid') in response.text):
            return True
        else:
            log.warning('Failed to login, check your cookies')
            self.session.cookies.clear()
            return False

    def _check_auth(self):

        if not self.username or not self.password:
            raise AuthException('Your authentication credentials for {0} are missing,'
                                ' check your config.'.format(self.name))

        return True


provider = IPTorrentsProvider()
