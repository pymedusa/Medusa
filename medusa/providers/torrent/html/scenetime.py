# coding=utf-8
# Author: Idan Gutman
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
"""Provider code for SceneTime."""
from __future__ import unicode_literals

import re
import traceback

from medusa import (
    logger,
    tv,
)
from medusa.bs4_parser import BS4Parser
from medusa.helper.common import (
    convert_size,
    try_int,
)
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.compat import urljoin
from requests.utils import dict_from_cookiejar


class SceneTimeProvider(TorrentProvider):
    """SceneTime Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(self.__class__, self).__init__('SceneTime')

        # Credentials
        self.username = None
        self.password = None

        # URLs
        self.url = 'https://www.scenetime.com'
        self.urls = {
            'login': urljoin(self.url, 'login.php'),
            'search': urljoin(self.url, 'browse_API.php'),
            'download': urljoin(self.url, 'download.php/{0}/{1}'),
        }

        # Proper Strings
        # Provider always returns propers and non-propers in a show search
        self.proper_strings = ['']

        # Miscellaneous Options
        self.enable_cookies = True
        self.cookies = ''

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tv.Cache(self, min_time=20)  # only poll SceneTime every 20 minutes max

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
            'sec': 'jax',
            'cata': 'yes',
            'c2': 1,  # TV/XviD
            'c43': 1,  # TV/Packs
            'c9': 1,  # TV-HD
            'c63': 1,  # TV/Classic
            'c77': 1,  # TV/SD
            'c79': 1,  # Sports
            'c100': 1,  # TV/Non-English
            'c83': 1,  # TV/Web-Rip
            'search': '',
        }

        for mode in search_strings:
            logger.log('Search mode: {0}'.format(mode), logger.DEBUG)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    logger.log('Search string: {search}'.format
                               (search=search_string), logger.DEBUG)
                    search_params['search'] = search_string

                response = self.get_url(self.urls['search'], post_data=search_params, returns='response')
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
            torrent_rows = html.find_all('tr')

            # Continue only if at least one release is found
            if len(torrent_rows) < 2:
                logger.log('Data returned from provider does not contain any torrents', logger.DEBUG)
                return items

            # Scenetime apparently uses different number of cells in #torrenttable based
            # on who you are. This works around that by extracting labels from the first
            # <tr> and using their index to find the correct download/seeders/leechers td.
            labels = [label.get_text(strip=True) or label.img['title'] for label in torrent_rows[0]('td')]

            # Skip column headers
            for row in torrent_rows[1:]:
                cells = row('td')
                if len(cells) < len(labels):
                    continue

                try:
                    link = cells[labels.index('Name')].find('a')
                    torrent_id = link['href'].replace('details.php?id=', '').split('&')[0]
                    title = link.get_text(strip=True)
                    download_url = self.urls['download'].format(torrent_id,
                                                                '{0}.torrent'.format(title.replace(' ', '.')))
                    if not all([title, download_url]):
                        continue

                    seeders = try_int(cells[labels.index('Seeders')].get_text(strip=True))
                    leechers = try_int(cells[labels.index('Leechers')].get_text(strip=True))

                    # Filter unseeded torrent
                    if seeders < min(self.minseed, 1):
                        if mode != 'RSS':
                            logger.log("Discarding torrent because it doesn't meet the "
                                       "minimum seeders: {0}. Seeders: {1}".format
                                       (title, seeders), logger.DEBUG)
                        continue

                    torrent_size = cells[labels.index('Size')].get_text()
                    torrent_size = re.sub(r'(\d+\.?\d*)', r'\1 ', torrent_size)
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
                        logger.log('Found result: {0} with {1} seeders and {2} leechers'.format
                                   (title, seeders, leechers), logger.DEBUG)

                    items.append(item)
                except (AttributeError, TypeError, KeyError, ValueError, IndexError):
                    logger.log('Failed parsing provider. Traceback: {0!r}'.format
                               (traceback.format_exc()), logger.ERROR)

        return items

    def login(self):
        """Login method used for logging in before doing search and torrent downloads."""
        if dict_from_cookiejar(self.session.cookies).get('uid') and \
                dict_from_cookiejar(self.session.cookies).get('pass'):
            return True

        if self.cookies:
            self.add_cookies_from_ui()
        else:
            logger.log('Failed to login, you must add your cookies in the provider settings', logger.WARNING)
            return False

        login_params = {
            'username': self.username,
            'password': self.password,
            'submit.x': 0,
            'submit.y': 0,
        }

        response = self.get_url(self.urls['login'], post_data=login_params, returns='response')
        if not response or not response.text:
            logger.log('Unable to connect to provider', logger.WARNING)
            return False

        if re.search('Username or password incorrect', response.text):
            logger.log('Invalid username or password. Check your settings', logger.WARNING)
            return False

        if (dict_from_cookiejar(self.session.cookies).get('uid') and
                dict_from_cookiejar(self.session.cookies).get('uid') in response.text):
            return True
        else:
            logger.log('Failed to login, check your cookies', logger.WARNING)
            self.session.cookies.clear()
            return False


provider = SceneTimeProvider()
