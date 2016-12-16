# coding=utf-8
# Author: Idan Gutman
# Modified by jkaberg, https://github.com/jkaberg for SceneAccess
# Modified by 7ca for HDSpace
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
"""Provider code for HDSpace."""
from __future__ import unicode_literals

import re
import traceback

from requests.compat import urljoin
from requests.utils import dict_from_cookiejar

from ..torrent_provider import TorrentProvider
from .... import logger, tv_cache
from ....bs4_parser import BS4Parser
from ....helper.common import convert_size, try_int


class HDSpaceProvider(TorrentProvider):
    """HDSpace Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(self.__class__, self).__init__('HDSpace')

        # Credentials
        self.username = None
        self.password = None

        # URLs
        self.url = 'https://hd-space.org'
        self.urls = {
            'login': urljoin(self.url, 'index.php?page=login'),
            'search': urljoin(self.url, 'index.php'),
        }

        # Proper Strings

        # Miscellaneous Options

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tv_cache.TVCache(self, min_time=10)  # only poll HDSpace every 10 minutes max

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
            'page': 'torrents',
            'search': '',
            'active': 0,
            'options': 0,
            'category': '15;40;21;22;24;25;27;28',
        }

        for mode in search_strings:
            logger.log('Search mode: {0}'.format(mode), logger.DEBUG)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    logger.log('Search string: {search}'.format
                               (search=search_string), logger.DEBUG)
                    search_params['search'] = search_string

                response = self.get_url(self.urls['search'], params=search_params, returns='response')
                if not response or not response.text or 'please try later' in response.text:
                    logger.log('No data returned from provider', logger.DEBUG)
                    continue

                # Search result page contains some invalid html that prevents html parser from returning all data.
                # We cut everything before the table that contains the data we are interested in thus eliminating
                # the invalid html portions
                try:
                    index = response.text.index('<div id="information"')
                except ValueError:
                    logger.log('Could not find main torrent table', logger.DEBUG)
                    continue

                results += self.parse(response.text[index:], mode)

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
            if not html:
                logger.log('No html data parsed from provider', logger.DEBUG)
                return items

            torrents = html('tr')
            if not torrents or len(torrents) < 2:
                logger.log('Data returned from provider does not contain any torrents', logger.DEBUG)
                return items

            # Skip column headers
            for row in torrents[1:]:
                # Skip extraneous rows at the end
                if len(row.contents) < 10:
                    continue

                try:
                    comments_counter = row.find_all('td', class_='lista', attrs={'align': 'center'})[4].find('a')
                    if comments_counter:
                        title = comments_counter['title'][10:]
                    else:
                        title = row.find('td', class_='lista', attrs={'align': 'left'}).find('a').get_text()
                    dl_href = row.find('td', class_='lista', attrs={'width': '20',
                                       'style': 'text-align: center;'}).find('a').get('href')
                    download_url = urljoin(self.url, dl_href)
                    if not all([title, dl_href]):
                        continue

                    seeders = try_int(row.find('span', class_='seedy').find('a').get_text(), 1)
                    leechers = try_int(row.find('span', class_='leechy').find('a').get_text())

                    # Filter unseeded torrent
                    if seeders < min(self.minseed, 1):
                        if mode != 'RSS':
                            logger.log("Discarding torrent because it doesn't meet the "
                                       "minimum seeders: {0}. Seeders: {1}".format
                                       (title, seeders), logger.DEBUG)
                        continue

                    torrent_size = row.find('td', class_='lista222', attrs={'width': '100%'}).get_text()
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

        if 'pass' in dict_from_cookiejar(self.session.cookies):
            return True

        login_params = {
            'uid': self.username,
            'pwd': self.password,
            'submit': 'Confirm',
        }

        response = self.get_url(self.urls['login'], post_data=login_params, returns='response')
        if not response or not response.text:
            logger.log('Unable to connect to provider', logger.WARNING)
            return False

        if re.search('Automatic log off after 15 minutes inactivity', response.text):
            logger.log('Invalid username or password. Check your settings', logger.WARNING)
            return False

        return True

    def _check_auth(self):

        if not self.username or not self.password:
            logger.log('Invalid username or password. Check your settings', logger.WARNING)

        return True


provider = HDSpaceProvider()
