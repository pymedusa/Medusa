# coding=utf-8

"""Provider code for SCC."""

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


class SCCProvider(TorrentProvider):
    """SceneAccess Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(SCCProvider, self).__init__('SceneAccess')

        # Credentials
        self.username = None
        self.password = None

        # URLs
        self.url = 'https://sceneaccess.eu'
        self.urls = {
            'login': urljoin(self.url, 'login'),
            'search': urljoin(self.url, 'all?search={string}&method=1&{cats}'),
        }

        # Proper Strings
        self.proper_strings = ['PROPER', 'REPACK', 'REAL']

        # Miscellaneous Options
        self.categories = {
            # Archive, non-scene HD, non-scene SD;
            # need to include non-scene because WEB-DL packs get added to those categories
            'Season': 'c26=26&c44=44&c45=45',
            # TV HD, TV SD, non-scene HD, non-scene SD, foreign XviD, foreign x264
            'Episode': 'c11=11&c17=17&c27=27&c33=33&c34=34&c44=44&c45=45',
            # Season + Episode
            'RSS': 'c11=11&c17=17&c26=26&c27=27&c33=33&c34=34&c44=44&c45=45',
        }

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tv.Cache(self, min_time=20)

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

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {search}',
                              {'search': search_string})

                search_url = self.urls['search'].format(string=self._strip_year(search_string),
                                                        cats=self.categories[mode])
                response = self.get_url(search_url, returns='response')
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
            torrent_table = html.find('table', attrs={'id': 'torrents-table'})
            torrent_rows = torrent_table('tr') if torrent_table else []

            # Continue only if at least one release is found
            if len(torrent_rows) < 2:
                log.debug('Data returned from provider does not contain any torrents')
                return items

            for row in torrent_rows[1:]:
                try:
                    title = row.find('td', class_='ttr_name').find('a').get('title')
                    torrent_url = row.find('td', class_='td_dl').find('a').get('href')
                    download_url = urljoin(self.url, torrent_url)
                    if not all([title, torrent_url]):
                        continue

                    seeders = try_int(row.find('td', class_='ttr_seeders').get_text(), 1)
                    leechers = try_int(row.find('td', class_='ttr_leechers').get_text())

                    # Filter unseeded torrent
                    if seeders < min(self.minseed, 1):
                        if mode != 'RSS':
                            log.debug("Discarding torrent because it doesn't meet the"
                                      " minimum seeders: {0}. Seeders: {1}",
                                      title, seeders)
                        continue

                    torrent_size = row.find('td', class_='ttr_size').contents[0]
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
        if any(dict_from_cookiejar(self.session.cookies).values()):
            return True

        login_params = {
            'username': self.username,
            'password': self.password,
            'submit': 'come on in',
        }

        response = self.get_url(self.urls['login'], post_data=login_params, returns='response')
        if not response or not response.text:
            log.warning('Unable to connect to provider')
            return False

        if any([re.search(r'Username or password incorrect', response.text),
                re.search(r'<title>SceneAccess \| Login</title>', response.text), ]):
            log.warning('Invalid username or password. Check your settings')
            return False

        return True

    @staticmethod
    def _strip_year(search_string):
        """Remove brackets from search string year."""
        if not search_string:
            return search_string
        return re.sub(r'\((?P<year>\d{4})\)', '\g<year>', search_string)


provider = SCCProvider()
