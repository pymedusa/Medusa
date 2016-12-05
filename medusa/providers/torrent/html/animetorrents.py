# coding=utf-8
# Author: CristianBB
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
"""Provider code for Animetorrents."""
from __future__ import unicode_literals

import re
import traceback

from dateutil import parser

from requests.compat import urljoin
from requests.utils import dict_from_cookiejar
from ..torrent_provider import TorrentProvider
from .... import logger, tv_cache
from ....bs4_parser import BS4Parser
from ....helper.common import convert_size, try_int
from ....helper.exceptions import AuthException


class AnimeTorrentsProvider(TorrentProvider):
    """AnimeTorrent Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(self.__class__, self).__init__('AnimeTorrents')

        # Credentials
        self.username = None
        self.password = None

        # URLs
        self.url = 'http://animetorrents.me'
        self.urls = {
            'base_url': self.url,
            'login': urljoin(self.url, 'login.php'),
            'search': urljoin(self.url, '/ajax/torrents_data.php')
        }

        # Proper Strings

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tv_cache.TVCache(self)  # Only poll AnimeTorrents every 20 minutes max

    def search(self, search_strings, age=0, ep_obj=None):
        """
        Search a provider and parse the results.

        :param search_strings: A dict with mode (key) and the search value (value)
        :param age: Not used
        :param ep_obj: Not used
        :returns: A list of search results (structure)
        """
        results = []
        # if not self.login():
        #     return results
        self.login()

        # Search Params
        search_params = {
            'search': '',
        }

        for mode in search_strings:
            logger.log('Search mode: {0}'.format(mode), logger.DEBUG)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    search_params['search'] = search_string
                    logger.log('Search string: {search}'.format
                               (search=search_string), logger.DEBUG)

                response = self.get_url(self.urls['search'], params=search_params, returns='response')
                if not response or not response.text or 'Access Denied!' in response.text:
                    logger.log('No data returned from provider', logger.DEBUG)
                    continue

                # Search result page contains some invalid html that prevents html parser from returning all data.
                # We cut everything before the table that contains the data we are interested in thus eliminating
                # the invalid html portions
                try:
                    index = response.text.index('<TABLE class="mainblockcontenttt"')
                except ValueError:
                    logger.log('Could not find table of torrents mainblockcontenttt', logger.DEBUG)
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
            torrent_table = html.find('table', class_='mainblockcontenttt')
            torrent_rows = torrent_table('tr') if torrent_table else []

            if not torrent_rows or torrent_rows[2].find('td', class_='lista'):
                logger.log('Data returned from provider does not contain any torrents', logger.DEBUG)
                return items

            # Cat., Active, Filename, Dl, Wl, Added, Size, Uploader, S, L, C
            labels = [label.a.get_text(strip=True) if label.a else label.get_text(strip=True) for label in
                      torrent_rows[0]('td')]

            # Skip column headers
            for row in torrent_rows[1:]:
                try:
                    cells = row.findChildren('td')[:len(labels)]
                    if len(cells) < len(labels):
                        continue

                    title = cells[labels.index('Filename')].a
                    title = title.get_text(strip=True) if title else None
                    link = cells[labels.index('Dl')].a
                    link = link.get('href') if link else None
                    download_url = urljoin(self.url, link) if link else None
                    if not all([title, download_url]):
                        continue

                    seeders = try_int(cells[labels.index('S')].get_text(strip=True))
                    leechers = try_int(cells[labels.index('L')].get_text(strip=True))

                    # Filter unseeded torrent
                    if seeders < min(self.minseed, 1):
                        if mode != 'RSS':
                            logger.log("Discarding torrent because it doesn't meet the "
                                       "minimum seeders: {0}. Seeders: {1}".format
                                       (title, seeders), logger.DEBUG)
                        continue

                    torrent_size = cells[labels.index('Size')].get_text()
                    size = convert_size(torrent_size) or -1

                    pubdate_raw = cells[labels.index('Added')].get_text() if cells[labels.index('Added')] else None
                    pubdate = parser.parse(pubdate_raw) if pubdate_raw else None

                    item = {
                        'title': title,
                        'link': download_url,
                        'size': size,
                        'seeders': seeders,
                        'leechers': leechers,
                        'pubdate': pubdate,
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
        cookies = dict_from_cookiejar(self.session.cookies)
        if all([any(cookies.values()),
                cookies.get('XTZ_USERNAME'),
                cookies.get('XTZ_PASSWORD'),
                cookies.get('XTZUID')]):
            return True

        login_params = {
            'username': self.username,
            'password': self.password,
            'form': 'login',
        }

        self.headers.update({
            'Upgrade - Insecure - Requests': '1',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, sdch',
            'Connection': 'keep-alive',
            'Host': 'animetorrents.me',
            'Cache-Control': 'max-age=0'
            })

        self.session.get(url=self.urls['login'], headers=self.headers)
        response = self.session.post(url=self.urls['login'], data=login_params, headers=self.headers)

        if not response:
            logger.log('Unable to connect to provider', logger.WARNING)
            return False

        cookies = dict_from_cookiejar(self.session.cookies)
        if not all([cookies.get('XTZ_USERNAME'),
                    cookies.get('XTZ_PASSWORD'),
                    cookies.get('XTZUID')]):
            return False

        # if re.search('Invalid username or password.', response.text):
        #     logger.log('Invalid username or password. Check your settings', logger.WARNING)
        #     return False

        return True

    def _check_auth(self):

        if not self.username or not self.password:
            raise AuthException('Your authentication credentials for {0} are missing,'
                                ' check your config.'.format(self.name))

        return True


provider = AnimeTorrentsProvider()
