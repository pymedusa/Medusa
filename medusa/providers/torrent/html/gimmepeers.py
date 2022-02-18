# coding=utf-8

"""Provider code for GimmePeers."""

from __future__ import unicode_literals

import logging
import re

from medusa import tv
from medusa.bs4_parser import BS4Parser
from medusa.helper.common import convert_size
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.compat import urljoin
from requests.utils import dict_from_cookiejar

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class GimmePeersProvider(TorrentProvider):
    """GimmePeers Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(GimmePeersProvider, self).__init__('GimmePeers')

        self.username = None
        self.password = None

        self.url = 'https://www.gimmepeers.com'
        self.urls = {
            'login': urljoin(self.url, 'takelogin.php'),
            'search': urljoin(self.url, 'browse.php'),
        }

        # Proper Strings
        self.proper_strings = ['PROPER', 'REPACK', 'REAL', 'RERIP']

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

        search_params = {
            'c20': 1,
            'c21': 1,
            'c25': 1,
            'c24': 1,
            'c23': 1,
            'c22': 1,
            'c1': 1,
        }

        for mode in search_strings:
            log.debug('Search Mode: {0}', mode)

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
            torrent_table = html.find('table', class_='browsetable')
            torrent_rows = torrent_table('tr') if torrent_table else []

            # Continue only if one release is found
            if len(torrent_rows) < 2:
                log.debug('Data returned from provider does not contain any torrents')
                return items

            for result in torrent_rows[1:]:
                cells = result('td')

                try:
                    link = cells[1].find('a')
                    download_url = urljoin(self.url, cells[2].find('a')['href'])
                    title = link.get_text()
                    if not all([title, download_url]):
                        continue

                    seeders = int(cells[10].get_text().replace(',', ''))
                    leechers = int(cells[11].get_text().replace(',', ''))

                    # Filter unseeded torrent
                    if seeders < self.minseed:
                        if mode != 'RSS':
                            log.debug("Discarding torrent because it doesn't meet the"
                                      ' minimum seeders: {0}. Seeders: {1}',
                                      title, seeders)
                        continue

                    torrent_size = cells[5].get_text(' ')
                    size = convert_size(torrent_size) or -1

                    pubdate_raw = cells[6].get_text()
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
        if any(dict_from_cookiejar(self.session.cookies).values()):
            return True

        login_params = {
            'username': self.username,
            'password': self.password,
            'ssl': 'yes',
        }

        response = self.session.post(self.urls['login'], data=login_params)
        if not response or not response.text:
            log.debug('Unable to connect to provider')
            return False

        if re.search('Username or password incorrect!', response.text):
            log.debug('Invalid username or password. Check your settings')
            return False

        return True


provider = GimmePeersProvider()
