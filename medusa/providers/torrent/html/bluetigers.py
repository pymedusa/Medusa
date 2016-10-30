# coding=utf-8
# Author: raver2046 <raver2046@gmail.com>
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
from ..TorrentProvider import TorrentProvider
from .... import logger, tv_cache
from ....bs4_parser import BS4Parser


class BlueTigersProvider(TorrentProvider):  # pylint: disable=too-many-instance-attributes
    """BlueTigers Torrent provider"""
    def __init__(self):

        # Provider Init
        TorrentProvider.__init__(self, 'BLUETIGERS')

        # Credentials
        self.username = None
        self.password = None
        self.token = None

        # URLs
        self.url = 'https://www.bluetigers.ca/'
        self.urls = {
            'base_url': self.url,
            'search': urljoin(self.url, 'torrents-search.php'),
            'login': urljoin(self.url, 'account-login.php'),
            'download': urljoin(self.url, 'torrents-details.php?id=%s&hit=1'),
        }

        # Proper Strings

        # Miscellaneous Options

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tv_cache.TVCache(self, min_time=10)  # Only poll BLUETIGERS every 10 minutes max

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-locals
        """
        Search a provider and parse the results

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
            'c9': 1,
            'c10': 1,
            'c16': 1,
            'c17': 1,
            'c18': 1,
            'c19': 1,
            'c130': 1,
            'c131': 1,
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
            torrent_rows = html('a', href=re.compile('torrents-details'))

            # Continue only if at least one release is found
            if not torrent_rows:
                logger.log('Data returned from provider does not contain any torrents', logger.DEBUG)
                return items

            for row in torrent_rows:
                try:
                    title = row.text
                    download_url = self.urls['base_url'] + row['href']
                    download_url = download_url.replace('torrents-details', 'download')
                    if not all([title, download_url]):
                        continue

                    # FIXME
                    seeders = 1
                    leechers = 0

                    # Filter unseeded torrent
                    if seeders < min(self.minseed, 1):
                        if mode != 'RSS':
                            logger.log("Discarding torrent because it doesn't meet the "
                                       "minimum seeders: {0}. Seeders: {1}".format
                                       (title, seeders), logger.DEBUG)
                        continue

                    # FIXME
                    size = -1

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
            'take_login': '1'
        }

        response = self.get_url(self.urls['login'], post_data=login_params, returns='response')
        if not response or not response.text:
            check_login = self.get_url(self.urls['base_url'], returns='response')
            if not re.search('account-logout.php', check_login.text):
                logger.log('Unable to connect to provider', logger.WARNING)
                return False
            else:
                return True

        if re.search('account-login.php', response.text):
            logger.log('Invalid username or password. Check your settings', logger.WARNING)
            return False

        return True


provider = BlueTigersProvider()
