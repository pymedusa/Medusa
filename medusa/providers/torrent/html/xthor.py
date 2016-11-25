# coding=utf-8
# Author: adaur <adaur.underground@gmail.com>
# Rewrite: Dustyn Gibson (miigotu) <miigotu@gmail.com>
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
"""Provider code for Xthor."""
from __future__ import unicode_literals

import re
import traceback

from requests.utils import dict_from_cookiejar

from ..torrent_provider import TorrentProvider
from .... import logger, tv_cache
from ....bs4_parser import BS4Parser
from ....helper.common import convert_size, try_int


class XthorProvider(TorrentProvider):
    """Xthor Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(self.__class__, self).__init__('Xthor')

        # Credentials
        self.username = None
        self.password = None

        # URLs
        self.url = 'https://xthor.bz'
        self.urls = {
            'login': self.url + '/takelogin.php',
            'search': self.url + '/browse.php?',
        }

        # Proper Strings
        self.proper_strings = ['PROPER']

        # Miscellaneous Options
        self.freeleech = None

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tv_cache.TVCache(self, min_time=30)

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
            'only_free': try_int(self.freeleech),
            'searchin': 'title',
            'incldead': 0,
            'type': 'desc',
            'c13': 1,  # Séries / Pack TV 13
            'c14': 1,  # Séries / TV FR 14
            'c15': 1,  # Séries / HD FR 15
            'c16': 1,  # Séries / TV VOSTFR 16
            'c17': 1,  # Séries / HD VOSTFR 17
            'c32': 1,   # Mangas (Anime) 32
            'c34': 1,  # Sport 34
        }

        for mode in search_strings:
            results = []
            logger.log('Search mode: {0}'.format(mode), logger.DEBUG)

            # Sorting: 1: Name, 3: Comments, 5: Size, 6: Completed, 7: Seeders, 8: Leechers (4: Time ?)
            search_params['sort'] = (7, 4)[mode == 'RSS']

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
        # Units
        units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']

        def process_column_header(td):
            result = ''
            if td.a:
                result = td.a.get('title', td.a.get_text(strip=True))
            if not result:
                result = td.get_text(strip=True)
            return result

        items = []

        with BS4Parser(data, 'html5lib') as html:
            torrent_table = html.find('table', class_='table2 table-bordered2')
            torrent_rows = []
            if torrent_table:
                torrent_rows = torrent_table('tr')

            # Continue only if at least one release is found
            if len(torrent_rows) < 2:
                logger.log('Data returned from provider does not contain any torrents', logger.DEBUG)
                return items

            # Catégorie, Nom du Torrent, (Download), (Bookmark), Com., Taille, Compl�t�, Seeders, Leechers
            labels = [process_column_header(label) for label in torrent_rows[0]('td')]

            # Skip column headers
            for row in torrent_rows[1:]:
                cells = row('td')
                if len(cells) < len(labels):
                    continue

                try:
                    title = cells[labels.index('Nom du Torrent')].get_text(strip=True)
                    download_url = self.url + '/' + row.find('a', href=re.compile('download.php'))['href']
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

                    torrent_size = cells[labels.index('Taille')].get_text()
                    size = convert_size(torrent_size, units=units) or -1

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
            'submitme': 'X'
        }

        response = self.get_url(self.urls['login'], post_data=login_params, returns='response')
        if not response or not response.text:
            logger.log('Unable to connect to provider', logger.WARNING)
            return False

        if not re.search('donate.php', response.text):
            logger.log('Invalid username or password. Check your settings', logger.WARNING)
            return False

        return True


provider = XthorProvider()
