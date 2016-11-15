# coding=utf-8
# Author: Nick Sologoub
#
# This file is part of Medusa.
#
# Medusa is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Medusa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Medusa. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import re
import traceback

from requests.compat import urljoin
from requests.utils import dict_from_cookiejar
from ..torrent_provider import TorrentProvider
from .... import logger, tv_cache
from ....bs4_parser import BS4Parser
from ....helper.common import convert_size, try_int


class PretomeProvider(TorrentProvider):
    """Pretome Torrent provider."""

    def __init__(self):
        """Provider Init."""
        TorrentProvider.__init__(self, 'Pretome')

        # Credentials
        self.username = None
        self.password = None
        self.pin = None

        # URLs
        self.url = 'https://pretome.info'
        self.urls = {
            'login': urljoin(self.url, 'takelogin.php'),
            'search': urljoin(self.url, 'browse.php'),
        }

        # Proper Strings
        self.proper_strings = ['PROPER', 'REPACK', 'REAL']

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tv_cache.TVCache(self)

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
            'search': '',
            'st': 1,
            'cat[]': 7,
        }

        for mode in search_strings:
            logger.log('Search mode: {0}'.format(mode), logger.DEBUG)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    logger.log('Search string: {search}'.format
                               (search=search_string), logger.DEBUG)

                search_params['search'] = search_string
                response = self.get_url(self.urls['search'], params=search_params, returns='response')
                if not response or not response.text:
                    logger.log('No data returned from provider', logger.DEBUG)
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
            # Continue only if at least one release is found
            empty = html.find('h2', text='No .torrents fit this filter criteria')
            if empty:
                logger.log('Data returned from provider does not contain any torrents', logger.DEBUG)
                return items

            torrent_table = html.find('table', attrs={'style': 'border: none; width: 100%;'})
            torrent_rows = torrent_table('tr', class_='browse') if torrent_table else []

            for row in torrent_rows:
                cells = row('td')

                try:
                    title = cells[1].find('a').get('title')
                    torrent_url = cells[2].find('a').get('href')
                    download_url = urljoin(self.url, torrent_url)
                    if not all([title, torrent_url]):
                        continue

                    seeders = try_int(cells[9].get_text(), 1)
                    leechers = try_int(cells[10].get_text())

                    # Filter unseeded torrent
                    if seeders < min(self.minseed, 1):
                        if mode != 'RSS':
                            logger.log("Discarding torrent because it doesn't meet the "
                                       "minimum seeders: {0}. Seeders: {1}".format
                                       (title, seeders), logger.DEBUG)
                        continue

                    torrent_size = self._norm_size(cells[7].get_text(strip=True))
                    size = convert_size(torrent_size) or -1

                    item = {
                        'title': title,
                        'link': download_url,
                        'size': size,
                        'seeders': seeders,
                        'leechers': leechers,
                        'pubdate': None,
                        'torrent_hash': None,
                    }
                    if mode != 'RSS':
                        logger.log('Found result: {0} with {1} seeders and {2} leechers'.format
                                   (title, seeders, leechers), logger.DEBUG)

                    items.append(item)
                except (AttributeError, TypeError, KeyError, ValueError, IndexError):
                    logger.log('Failed parsing provider. Traceback: {0!r}'.format
                               (traceback.format_exc()), logger.ERROR)

        return items

    def login(self):
        """Login method used for logging in before doing search and torrent downloads."""
        if any(dict_from_cookiejar(self.session.cookies).values()):
            return True

        login_params = {
            'username': self.username,
            'password': self.password,
            'login_pin': self.pin,
        }

        response = self.get_url(self.urls['login'], post_data=login_params, returns='response')
        if not response or not response.text:
            logger.log('Unable to connect to provider', logger.WARNING)
            return False

        if re.search('Username or password incorrect', response.text):
            logger.log('Invalid username or password. Check your settings', logger.WARNING)
            return False

        return True

    def _check_auth(self):
        if not all([self.username, self.password, self.pin]):
            logger.log('Invalid username, password or pin. Check your settings', logger.WARNING)

        return True

    @staticmethod
    def _norm_size(size_string):
        """Normalize the size from the parsed string."""
        if not size_string:
            return size_string
        return re.sub(r'(?P<unit>[A-Z]+)', ' \g<unit>', size_string)


provider = PretomeProvider()
