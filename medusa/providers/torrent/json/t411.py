# coding=utf-8
# Author: djoole <bobby.djoole@gmail.com>
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
"""Provider code for T411."""
from __future__ import unicode_literals

import time
import traceback
from operator import itemgetter

from medusa import (
    logger,
    tv,
)
from medusa.common import USER_AGENT
from medusa.helper.common import (
    convert_size,
    try_int,
)
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.auth import AuthBase
from requests.compat import quote, urljoin


class T411Provider(TorrentProvider):
    """T411 Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(self.__class__, self).__init__("T411")

        # Credentials
        self.username = None
        self.password = None
        self.token = None
        self.tokenLastUpdate = None

        # URLs
        self.url = 'https://api.t411.ai'
        self.urls = {
            'search': urljoin(self.url, 'torrents/search/{search}'),
            'rss': urljoin(self.url, 'torrents/top/today'),
            'login_page': urljoin(self.url, 'auth'),
            'download': urljoin(self.url, 'torrents/download/{id}'),
        }

        # Proper Strings

        # Miscellaneous Options
        self.headers.update({'User-Agent': USER_AGENT})
        self.subcategories = [433, 637, 455, 639]
        self.confirmed = False

        # Torrent Stats
        self.minseed = 0
        self.minleech = 0

        # Cache
        self.cache = tv.Cache(self, min_time=10)  # Only poll T411 every 10 minutes max

    def search(self, search_strings, age=0, ep_obj=None):
        """Search a provider and parse the results.

        :param search_strings: A dict with mode (key) and the search value (value)
        :param age: Not used
        :param ep_obj: Not used
        :returns: A list of search results (structure)
        """
        results = []
        if not self.login():
            return results

        search_params = {}

        for mode in search_strings:
            logger.log('Search mode: {0}'.format(mode), logger.DEBUG)

            for search_string in search_strings[mode]:
                if mode != 'RSS':
                    logger.log('Search string: {search}'.format
                               (search=search_string), logger.DEBUG)
                    if self.confirmed:
                        logger.log('Searching only confirmed torrents', logger.DEBUG)

                    # use string formatting to safely coerce the search term
                    # to unicode then utf-8 encode the unicode string
                    term = '{term}'.format(term=search_string).encode('utf-8')
                    # build the search URL
                    search_url = self.urls['search'].format(
                        search=quote(term)  # URL encode the search term
                    )
                    categories = self.subcategories
                    search_params.update({'limit': 100})
                else:
                    search_url = self.urls['rss']
                    # Using None as a category removes it as a search param
                    categories = [None]  # Must be a list for iteration

                for category in categories:
                    search_params.update({'cid': category})
                    response = self.get_url(
                        search_url, params=search_params, returns='response'
                    )

                    if not response or not response.content:
                        logger.log('No data returned from provider', logger.DEBUG)
                        continue

                    try:
                        jdata = response.json()
                    except ValueError:  # also catches JSONDecodeError if simplejson is installed
                        logger.log('No data returned from provider', logger.DEBUG)
                        continue

                    results += self.parse(jdata, mode)

        return results

    def parse(self, data, mode):
        """Parse search results for items.

        :param data: The raw response from a search
        :param mode: The current mode used to search, e.g. RSS

        :return: A list of items found
        """
        items = []

        unsorted_torrent_rows = data.get('torrents') if mode != 'RSS' else data

        if not unsorted_torrent_rows:
            logger.log(
                'Data returned from provider does not contain any {torrents}'.format(
                    torrents='confirmed torrents' if self.confirmed else 'torrents'
                ), logger.DEBUG
            )
            return items

        torrent_rows = sorted(unsorted_torrent_rows, key=itemgetter('added'), reverse=True)

        for row in torrent_rows:
            if not isinstance(row, dict):
                logger.log('Invalid data returned from provider', logger.WARNING)
                continue

            if mode == 'RSS' and 'category' in row and try_int(row['category'], 0) not in self.subcategories:
                continue

            try:
                title = row['name']
                torrent_id = row['id']
                download_url = self.urls['download'].format(id=torrent_id)
                if not all([title, download_url]):
                    continue

                seeders = try_int(row['seeders'])
                leechers = try_int(row['leechers'])
                verified = bool(row['isVerified'])

                # Filter unseeded torrent
                if seeders < min(self.minseed, 1):
                    if mode != 'RSS':
                        logger.log("Discarding torrent because it doesn't meet the "
                                   "minimum seeders: {0}. Seeders: {1}".format
                                   (title, seeders), logger.DEBUG)
                    continue

                if self.confirmed and not verified and mode != 'RSS':
                    logger.log("Found result {0} but that doesn't seem like a verified"
                               " result so I'm ignoring it".format(title), logger.DEBUG)
                    continue

                torrent_size = row['size']
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
        """Log into provider."""
        if self.token is not None:
            if time.time() < (self.tokenLastUpdate + 30 * 60):
                return True

        login_params = {
            'username': self.username,
            'password': self.password,
        }

        response = self.get_url(self.urls['login_page'], post_data=login_params, returns='json')
        if not response:
            logger.log('Unable to connect to provider', logger.WARNING)
            return False

        if response and 'token' in response:
            self.token = response['token']
            self.tokenLastUpdate = time.time()
            # self.uid = response['uid'].encode('ascii', 'ignore')
            self.session.auth = T411Auth(self.token)
            return True
        else:
            logger.log('Token not found in authentication response', logger.WARNING)
            return False


class T411Auth(AuthBase):
    """Attach HTTP Authentication to the given Request object."""

    def __init__(self, token):
        """Init object."""
        self.token = token

    def __call__(self, r):
        """Add token to request header."""
        r.headers['Authorization'] = self.token
        return r


provider = T411Provider()
