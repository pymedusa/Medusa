# coding=utf-8
# Author: Dustyn Gibson <miigotu@gmail.com>
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
"""Provider code for RARBG."""
from __future__ import unicode_literals

import datetime
import time
import traceback

from dateutil import parser

from medusa import (
    app,
    logger,
    tv,
)
from medusa.helper.common import convert_size, try_int
from medusa.providers.torrent.torrent_provider import TorrentProvider


class RarbgProvider(TorrentProvider):
    """RARBG Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(self.__class__, self).__init__('Rarbg')

        # Credentials
        self.public = True
        self.token = None
        self.token_expires = None

        # URLs
        self.url = 'https://rarbg.com'  # Spec: https://torrentapi.org/apidocs_v2.txt
        self.urls = {
            'api': 'http://torrentapi.org/pubapi_v2.php',
        }

        # Proper Strings
        self.proper_strings = ['{{PROPER|REPACK|REAL|RERIP}}']

        # Miscellaneous Options
        self.ranked = None
        self.sorting = None

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tv.Cache(self, min_time=10)  # only poll RARBG every 10 minutes max

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
            'app_id': app.RARBG_APPID,
            'category': 'tv',
            'min_seeders': try_int(self.minseed),
            'min_leechers': try_int(self.minleech),
            'limit': 100,
            'format': 'json_extended',
            'ranked': try_int(self.ranked),
            'token': self.token,
            'sort': 'last',
            'mode': 'list',
        }

        for mode in search_strings:
            logger.log('Search mode: {0}'.format(mode), logger.DEBUG)

            if mode == 'RSS':
                search_params['search_string'] = None
                search_params['search_tvdb'] = None
            else:
                search_params['sort'] = self.sorting if self.sorting else 'seeders'
                search_params['mode'] = 'search'
                search_params['search_tvdb'] = self._get_tvdb_id()

            for search_string in search_strings[mode]:
                if mode != 'RSS':
                    logger.log('Search string: {search}'.format
                               (search=search_string), logger.DEBUG)
                    if self.ranked:
                        logger.log('Searching only ranked torrents', logger.DEBUG)

                search_params['search_string'] = search_string

                # Check if token is still valid before search
                if not self.login():
                    continue

                # Maximum requests allowed are 1req/2sec
                # Changing to 5 because of server clock desync
                time.sleep(5)

                search_url = self.urls['api']
                response = self.get_url(search_url, params=search_params, returns='response')
                if not response or not response.content:
                    logger.log('No data returned from provider', logger.DEBUG)
                    continue

                try:
                    jdata = response.json()
                except ValueError:
                    logger.log('No data returned from provider', logger.DEBUG)
                    continue

                error = jdata.get('error')
                error_code = jdata.get('error_code')
                if error:
                    # List of errors: https://github.com/rarbg/torrentapi/issues/1#issuecomment-114763312
                    if error_code == 5:
                        # 5 = Too many requests per second
                        log_level = logger.INFO
                    elif error_code not in (4, 8, 10, 12, 14, 20):
                        # 4 = Invalid token. Use get_token for a new one!
                        # 8, 10, 12, 14 = Cant find * in database. Are you sure this * exists?
                        # 20 = No results found
                        log_level = logger.WARNING
                    else:
                        log_level = logger.DEBUG
                    logger.log('{msg} Code: {code}'.format(msg=error, code=error_code), log_level)
                    continue

                results += self.parse(jdata, mode)

        return results

    def parse(self, data, mode):
        """
        Parse search results for items.

        :param data: The raw response from a search
        :param mode: The current mode used to search, e.g. RSS

        :return: A list of items found
        """
        items = []

        torrent_rows = data.get('torrent_results', {})

        if not torrent_rows:
            logger.log('Data returned from provider does not contain any torrents', logger.DEBUG)
            return items

        # Skip column headers
        for row in torrent_rows:
            try:
                title = row.pop('title')
                download_url = row.pop('download')
                if not all([title, download_url]):
                    continue

                seeders = row.pop('seeders')
                leechers = row.pop('leechers')

                # Filter unseeded torrent
                if seeders < min(self.minseed, 1):
                    if mode != 'RSS':
                        logger.log("Discarding torrent because it doesn't meet the "
                                   "minimum seeders: {0}. Seeders: {1}".format
                                   (title, seeders), logger.DEBUG)
                    continue

                torrent_size = row.pop('size', -1)
                size = convert_size(torrent_size) or -1

                pubdate = row.pop('pubdate')
                pubdate = parser.parse(pubdate, fuzzy=True)

                item = {
                    'title': title,
                    'link': download_url,
                    'size': size,
                    'seeders': seeders,
                    'leechers': leechers,
                    'pubdate': pubdate,
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
        if self.token and self.token_expires and datetime.datetime.now() < self.token_expires:
            return True

        login_params = {
            'get_token': 'get_token',
            'format': 'json',
            'app_id': app.RARBG_APPID,
        }

        response = self.get_url(self.urls['api'], params=login_params, returns='json')
        if not response:
            logger.log('Unable to connect to provider', logger.WARNING)
            return False

        self.token = response.get('token')
        self.token_expires = datetime.datetime.now() + datetime.timedelta(minutes=14) if self.token else None
        return self.token is not None


provider = RarbgProvider()
