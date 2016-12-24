# coding=utf-8
# Author: medariox <dariox@gmx.com>
# based on Dustyn Gibson's <miigotu@gmail.com> work
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
"""Provider code for GFTracker."""
from __future__ import unicode_literals

import re
import traceback

from requests.compat import urljoin
from requests.utils import dict_from_cookiejar

from ..torrent_provider import TorrentProvider
from .... import logger, tv_cache
from ....bs4_parser import BS4Parser
from ....helper.common import convert_size, try_int
from ....helper.exceptions import AuthException


class GFTrackerProvider(TorrentProvider):
    """GFTracker Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(self.__class__, self).__init__('GFTracker')

        # Credentials
        self.username = None
        self.password = None

        # URLs
        self.url = 'https://www.thegft.org'
        self.urls = {
            'login': urljoin(self.url, 'loginsite.php'),
            'search': urljoin(self.url, 'browse.php'),
        }

        # Proper Strings
        self.proper_strings = ['PROPER', 'REPACK', 'REAL']

        # Miscellaneous Options

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

        # https://www.thegft.org/browse.php?view=0&c26=1&c37=1&c19=1&c47=1&c17=1&c4=1&search=arrow
        # Search Params
        search_params = {
            'view': 0,  # BROWSE
            'c4': 1,  # TV/XVID
            'c17': 1,  # TV/X264
            'c19': 1,  # TV/DVDRIP
            'c26': 1,  # TV/BLURAY
            'c37': 1,  # TV/DVDR
            'c47': 1,  # TV/SD
            'search': '',
        }

        for mode in search_strings:
            logger.log('Search mode: {0}'.format(mode), logger.DEBUG)

            for search_string in search_strings[mode]:

                if mode == 'Season':
                    search_params.update({
                        'view': 1,  # Browse/Gems a.k.a. Season packs
                        'c42': 1,  # TV/Gems
                    })

                elif mode != 'RSS':
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
            if td.a and td.a.img:
                result = td.a.img.get('title', td.a.get_text(strip=True))
            if not result:
                result = td.get_text(strip=True)
            return result

        items = []

        with BS4Parser(data, 'html5lib') as html:
            torrent_table = html.find('div', id='torrentBrowse')
            torrent_rows = torrent_table('tr') if torrent_table else []

            # Continue only if at least one release is found
            if len(torrent_rows) < 2:
                logger.log('Data returned from provider does not contain any torrents', logger.DEBUG)
                return items

            labels = [process_column_header(label) for label in torrent_rows[0]('td')]

            # Skip column headers
            for row in torrent_rows[1:]:
                cells = row('td')
                if len(cells) < len(labels):
                    continue

                try:

                    title_anchor = cells[labels.index('Name')].find('a').find_next('a') or \
                        cells[labels.index('Name')].find('a')
                    title = title_anchor.get('title') if title_anchor else None
                    download_url = urljoin(self.url, cells[labels.index('DL')].find('a')['href'])
                    if not all([title, download_url]):
                        continue

                    peers = cells[labels.index('S/L')].get_text(strip=True).split('/', 1)
                    seeders = try_int(peers[0])
                    leechers = try_int(peers[1])

                    # Filter unseeded torrent
                    if seeders < min(self.minseed, 1):
                        if mode != 'RSS':
                            logger.log("Discarding torrent because it doesn't meet the "
                                       "minimum seeders: {0}. Seeders: {1}".format
                                       (title, seeders), logger.DEBUG)
                        continue

                    torrent_size = cells[labels.index('Size/Snatched')].get_text(strip=True).split('/', 1)[0]
                    size = convert_size(torrent_size, units=units) or -1

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
        if any(dict_from_cookiejar(self.session.cookies).values()):
            return True

        login_params = {
            'username': self.username,
            'password': self.password,
        }

        # Initialize session with a GET to have cookies
        self.get_url(self.url, returns='response')
        response = self.get_url(self.urls['login'], post_data=login_params, returns='response')
        if not response or not response.text:
            logger.log('Unable to connect to provider', logger.WARNING)
            return False

        if re.search('Username or password incorrect', response.text):
            logger.log('Invalid username or password. Check your settings', logger.WARNING)
            return False

        return True

    def _check_auth(self):

        if not self.username or not self.password:
            raise AuthException('Your authentication credentials for {0} are missing,'
                                ' check your config.'.format(self.name))

        return True


provider = GFTrackerProvider()
