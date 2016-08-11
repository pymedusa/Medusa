# coding=utf-8
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

from requests.utils import dict_from_cookiejar
from requests.compat import urljoin

from sickbeard import logger, tvcache
from sickbeard.bs4_parser import BS4Parser

from sickrage.helper.common import try_int
from sickrage.helper.exceptions import AuthException
from sickrage.providers.torrent.TorrentProvider import TorrentProvider


class TransmitTheNetProvider(TorrentProvider):  # pylint: disable=too-many-instance-attributes
    """TransmitTheNet Torrent provider"""
    def __init__(self):

        # Provider Init
        TorrentProvider.__init__(self, 'TransmitTheNet')

        # Credentials
        self.username = None
        self.password = None

        # URLs
        self.url = 'https://transmithe.net/'
        self.urls = {
            'login': urljoin(self.url, '/login.php'),
            'search': urljoin(self.url, '/torrents.php'),
        }

        # Proper Strings

        # Miscellaneous Options
        self.freeleech = None

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tvcache.TVCache(self)

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

        for mode in search_strings:
            logger.log('Search mode: {0}'.format(mode), logger.DEBUG)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    logger.log('Search string: {search}'.format
                               (search=search_string), logger.DEBUG)

                search_params = {
                    'searchtext': search_string,
                    'filter_freeleech': (0, 1)[self.freeleech is True],
                    'order_by': ('seeders', 'time')[mode == 'RSS'],
                    'order_way': 'desc',
                }

                if not search_string:
                    del search_params['searchtext']

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
            torrent_table = html.find('table', {'id': 'torrent_table'})

            # Continue only if at least one release is found
            if not torrent_table:
                logger.log('Data returned from provider does not contain any torrents', logger.DEBUG)
                return items

            torrent_rows = torrent_table('tr', {'class': 'torrent'})

            # Continue only if one Release is found
            if not torrent_rows:
                logger.log('Data returned from provider does not contain any torrents', logger.DEBUG)
                return items

            for row in torrent_rows:
                try:
                    freeleech = row.find('img', alt='Freeleech') is not None
                    if self.freeleech and not freeleech:
                        continue

                    download_item = row.find('a', {'title': [
                        'Download Torrent',  # Download link
                        'Previously Grabbed Torrent File',  # Already Downloaded
                        'Currently Seeding Torrent',  # Seeding
                        'Currently Leeching Torrent',  # Leeching
                    ]})

                    if not download_item:
                        continue

                    download_url = urljoin(self.url, download_item['href'])

                    temp_anchor = row.find('a', {'data-src': True})
                    title = temp_anchor['data-src'].rsplit('.', 1)[0]
                    if not all([title, download_url]):
                        continue

                    cells = row('td')
                    seeders = try_int(cells[8].text.strip())
                    leechers = try_int(cells[9].text.strip())

                    # Filter unseeded torrent
                    if seeders < min(self.minseed, 1):
                        if mode != 'RSS':
                            logger.log("Discarding torrent because it doesn't meet the "
                                       "minimum seeders: {0}. Seeders: {1}".format
                                       (title, seeders), logger.DEBUG)
                        continue

                    size = temp_anchor['data-filesize'] or -1

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
            'keeplogged': 'on',
            'login': 'Login'
        }

        response = self.get_url(self.urls['login'], post_data=login_params, returns='response')
        if not response or not response.text:
            logger.log('Unable to connect to provider', logger.WARNING)
            return False

        if any([re.search('Username Incorrect', response.text),
                re.search('Password Incorrect', response.text), ]):
            logger.log('Invalid username or password. Check your settings', logger.WARNING)
            return False

        return True

    def _check_auth(self):

        if not self.username or not self.password:
            raise AuthException('Your authentication credentials for {0} are missing,'
                                ' check your config.'.format(self.name))

        return True


provider = TransmitTheNetProvider()
