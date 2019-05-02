# coding=utf-8

"""Provider code for GimmePeers."""

from __future__ import unicode_literals

import re

from requests.utils import dict_from_cookiejar

from medusa import logger, tv
from medusa.bs4_parser import BS4Parser
from medusa.helper.common import convert_size
from medusa.providers.torrent.torrent_provider import TorrentProvider


class GimmePeersProvider(TorrentProvider):
    """GimmePeers Torrent provider."""

    def __init__(self):

        TorrentProvider.__init__(self, 'GimmePeers')

        self.urls = {
            'base_url': 'https://www.gimmepeers.com',
            'login': 'https://www.gimmepeers.com/takelogin.php',
            'detail': 'https://www.gimmepeers.com/details.php?id=%s',
            'search': 'https://www.gimmepeers.com/browse.php',
            'download': 'https://gimmepeers.com/%s',
        }

        self.url = self.urls['base_url']

        self.username = None
        self.password = None
        self.minseed = None
        self.minleech = None

        self.cache = tv.Cache(self)

        self.search_params = {
            # c20=1&c21=1&c25=1&c24=1&c23=1&c22=1&c1=1
            'c20': 1, 'c21': 1, 'c25': 1, 'c24': 1, 'c23': 1, 'c22': 1, 'c1': 1
        }

    def _check_auth(self):
        if not self.username or not self.password:
            logger.log(u'Invalid username or password. Check your settings', logger.WARNING)

        return True

    def login(self):
        """Login method used for logging in before doing search and torrent downloads."""
        if any(dict_from_cookiejar(self.session.cookies).values()):
            return True

        login_params = {
            'username': self.username,
            'password': self.password,
            'ssl': 'yes'
        }

        response = self.session.post(self.urls['login'], data=login_params)
        if not response or not response.text:
            logger.log(u'Unable to connect to provider', logger.WARNING)
            return False

        if re.search('Username or password incorrect!', response.text):
            logger.log(u'Invalid username or password. Check your settings', logger.WARNING)
            return False

        return True

    def search(self, search_strings, age=0, ep_obj=None, **kwargs):  # pylint: disable=too-many-locals
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

            logger.log(u'Search Mode: {0}'.format(mode), logger.DEBUG)
            for search_string in search_strings[mode]:
                if mode != 'RSS':
                    logger.log(u'Search string: {0}'.format
                               (search_string.decode('utf-8')), logger.DEBUG)

                self.search_params['search'] = search_string

                data = self.session.get(self.urls['search'], params=self.search_params)
                if not data:
                    continue

                results += self.parse(data.text, mode)

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

            # Continue only if one Release is found
            if len(torrent_rows) < 2:
                logger.log(u'Data returned from provider does not contain any torrents', logger.DEBUG)
                return items

            for result in torrent_rows[1:]:
                try:
                    cells = result('td')

                    link = cells[1].find('a')
                    download_url = self.urls['download'] % cells[2].find('a')['href']

                    title = link.getText()
                    seeders = int(cells[10].getText().replace(',', ''))
                    leechers = int(cells[11].getText().replace(',', ''))
                    torrent_size = cells[8].getText()
                    size = convert_size(torrent_size) or -1
                    # except (AttributeError, TypeError):
                    #     continue

                    if not all([title, download_url]):
                        continue

                        # Filter unseeded torrent
                    if seeders < self.minseed or leechers < self.minleech:
                        if mode != 'RSS':
                            logger.log(u"Discarding torrent because it doesn't meet the minimum seeders or leechers: {0} (S:{1} L:{2})".format
                                       (title, seeders, leechers), logger.DEBUG)
                        continue

                    if seeders >= 32768 or leechers >= 32768:
                        continue

                    item = {'title': title, 'link': download_url, 'size': size, 'seeders': seeders, 'leechers': leechers, 'hash': ''}
                    if mode != 'RSS':
                        logger.log(u'Found result: {0} with {1} seeders and {2} leechers'.format(title, seeders, leechers), logger.DEBUG)

                    items.append(item)

                except (AttributeError, TypeError, KeyError, ValueError, IndexError):
                    logger.exception('Failed parsing provider.')

        return items


provider = GimmePeersProvider()
