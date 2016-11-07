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

import json
import traceback

from requests.compat import urlencode, urljoin
from ..torrent_provider import TorrentProvider
from .... import logger, tv_cache
from ....helper.common import convert_size, try_int
from ....helper.exceptions import AuthException


class NorbitsProvider(TorrentProvider):  # pylint: disable=too-many-instance-attributes
    """Main provider object"""

    def __init__(self):
        """ Initialize the class """

        # Provider Init
        TorrentProvider.__init__(self, 'Norbits')

        # Credentials
        self.username = None
        self.passkey = None

        # URLs
        self.url = 'https://norbits.net'
        self.urls = {
            'search': urljoin(self.url, 'api2.php?action=torrents'),
            'download': urljoin(self.url, 'download.php?'),
        }

        # Proper Strings

        # Miscellaneous Options

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tv_cache.TVCache(self, min_time=20)  # only poll Norbits every 15 minutes max

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-branches, too-many-locals
        """
        Search a provider and parse the results

        :param search_strings: A dict with mode (key) and the search value (value)
        :param age: Not used
        :param ep_obj: Not used
        :returns: A list of search results (structure)
        """
        results = []

        for mode in search_strings:
            logger.log('Search mode: {0}'.format(mode), logger.DEBUG)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    logger.log('Search string: {search}'.format
                               (search=search_string), logger.DEBUG)

                post_data = {
                    'username': self.username,
                    'passkey': self.passkey,
                    'category': '2',  # TV Category
                    'search': search_string,
                }

                response = self.get_url(self.urls['search'], post_data=json.dumps(post_data),
                                        returns='response')
                if not response or not response.content:
                    logger.log('No data returned from provider', logger.DEBUG)
                    continue

                try:
                    jdata = response.json()
                except ValueError:  # also catches JSONDecodeError if simplejson is installed
                    logger.log('No data returned from provider', logger.DEBUG)
                    continue

                if self._check_auth_from_data(jdata):
                    return results

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
        data.get('data', '')
        torrent_rows = data.get('torrents', [])

        # Skip column headers
        for row in torrent_rows:
            try:
                title = row.pop('name', '')
                download_url = '{0}{1}'.format(
                    self.urls['download'],
                    urlencode({'id': row.pop('id', ''), 'passkey': self.passkey}))

                if not all([title, download_url]):
                    continue

                seeders = try_int(row.pop('seeders', 0))
                leechers = try_int(row.pop('leechers', 0))

                # Filter unseeded torrent
                if seeders < min(self.minseed, 1):
                    if mode != 'RSS':
                        logger.log("Discarding torrent because it doesn't meet the "
                                   "minimum seeders: {0}. Seeders: {1}".format
                                   (title, seeders), logger.DEBUG)
                    continue

                info_hash = row.pop('info_hash', '')
                size = convert_size(row.pop('size', -1), -1)

                item = {
                    'title': title,
                    'link': download_url,
                    'size': size,
                    'seeders': seeders,
                    'leechers': leechers,
                    'pubdate': None,
                    'torrent_hash': info_hash,
                }
                if mode != 'RSS':
                    logger.log('Found result: {0} with {1} seeders and {2} leechers'.format
                               (title, seeders, leechers), logger.DEBUG)

                items.append(item)
            except (AttributeError, TypeError, KeyError, ValueError, IndexError):
                logger.log('Failed parsing provider. Traceback: {0!r}'.format
                           (traceback.format_exc()), logger.ERROR)

        return items

    def _check_auth(self):

        if not self.username or not self.passkey:
            raise AuthException(('Your authentication credentials for %s are '
                                 'missing, check your config.') % self.name)

        return True

    def _check_auth_from_data(self, parsed_json):  # pylint: disable=invalid-name
        """ Check that we are authenticated. """

        if 'status' in parsed_json and 'message' in parsed_json:
            if parsed_json.get('status') == 3:
                logger.log('Invalid username or password. '
                           'Check your settings', logger.WARNING)

        return True


provider = NorbitsProvider()  # pylint: disable=invalid-name
