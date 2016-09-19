# coding=utf-8
# Author: medariox (dariox@gmx.com)
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
from .... import logger, tvcache
from ....bs4_parser import BS4Parser
from ....helper.common import convert_size, try_int


class TorrentShackProvider(TorrentProvider):  # pylint: disable=too-many-instance-attributes
    """TorrentShack Torrent provider"""
    def __init__(self):

        # Provider Init
        TorrentProvider.__init__(self, 'TorrentShack')

        # Credentials
        self.username = None
        self.password = None

        # URLs
        self.url = 'https://www.torrentshack.me'
        self.urls = {
            'login': urljoin(self.url, 'login.php'),
            'search': urljoin(self.url, 'torrents.php'),
        }

        # Proper Strings
        self.proper_strings = ['PROPER', 'REPACK', 'REAL']

        # Miscellaneous Options

        # Torrent Stats
        self.minseed = 0
        self.minleech = 0

        # Cache
        self.cache = tvcache.TVCache(self, min_time=20)  # Only poll TorrentShack every 20 minutes max

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-locals, too-many-branches
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
            'searchstr': '',
            'release_type': 'both',
            'searchtags': '',
            'tags_type': 0,
            'order_by': 's3',
            'order_way': 'desc',
            'torrent_preset': 'all',
            'filter_cat[600]': 1,
            'filter_cat[960]': 1,
            'filter_cat[620]': 1,
            'filter_cat[320]': 1,
            'filter_cat[700]': 1,
            'filter_cat[970]': 1,
            'filter_cat[981]': 1,
            'filter_cat[850]': 1,
            'filter_cat[980]': 1,
        }

        for mode in search_strings:
            logger.log('Search mode: {0}'.format(mode), logger.DEBUG)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    logger.log('Search string: {search}'.format
                               (search=search_string), logger.DEBUG)
                    search_params['searchstr'] = search_string

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
        # Units
        units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']

        items = []

        with BS4Parser(data, 'html5lib') as html:
            torrent_rows = html.find_all('tr', class_='torrent')

            # Continue only if at least one release is found
            if not torrent_rows:
                logger.log('Data returned from provider does not contain any torrents', logger.DEBUG)
                return items

            for result in torrent_rows:
                cells = result('td')

                try:
                    title = cells[1].find('span', class_='torrent_name_link').get_text()
                    download_url = cells[1].find('span', class_='torrent_handle_links')
                    download_url = download_url.find('a').find_next('a').get('href')
                    download_url = urljoin(self.url, download_url)
                    if not all([title, download_url]):
                        continue

                    seeders = try_int(cells[6].get_text())
                    leechers = try_int(cells[7].get_text())

                    # Filter unseeded torrent
                    if seeders < min(self.minseed, 1):
                        if mode != 'RSS':
                            logger.log("Discarding torrent because it doesn't meet the "
                                       "minimum seeders: {0}. Seeders: {1}".format
                                       (title, seeders), logger.DEBUG)
                        continue

                    torrent_size = cells[4].get_text()
                    torrent_size = re.search('\d+.\d+.\w+', torrent_size).group(0)
                    size = convert_size(torrent_size, units=units) or -1

                    item = {
                        'title': title,
                        'link': download_url,
                        'size': size,
                        'seeders': seeders,
                        'leechers': leechers,
                        'pubdate': None,
                        'hash': None,
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
            'login': 'Login',
        }

        response = self.get_url(self.urls['login'], post_data=login_params, returns='response')
        if not response or not response.text:
            logger.log('Unable to connect to provider', logger.WARNING)
            return False

        if '<title>Login :: TorrentShack.me</title>' in response.text:
            logger.log('Invalid username or password. Check your settings', logger.WARNING)
            return False

        return True


provider = TorrentShackProvider()
