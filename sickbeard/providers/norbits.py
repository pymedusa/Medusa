# coding=utf-8
"""A Norbits (https://norbits.net) provider"""

# URL: https://sickrage.github.io
#
# This file is part of SickRage.
#
# SickRage is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# SickRage is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with SickRage. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import traceback
import json

from requests.compat import urlencode

from sickbeard import logger, tvcache

from sickrage.helper.exceptions import AuthException
from sickrage.helper.common import convert_size, try_int
from sickrage.providers.torrent.TorrentProvider import TorrentProvider


class NorbitsProvider(TorrentProvider):  # pylint: disable=too-many-instance-attributes
    """Main provider object"""

    def __init__(self):
        """ Initialize the class """
        TorrentProvider.__init__(self, 'Norbits')

        self.username = None
        self.passkey = None
        self.minseed = None
        self.minleech = None

        self.cache = tvcache.TVCache(self, min_time=20)  # only poll Norbits every 15 minutes max

        self.url = 'https://norbits.net'
        self.urls = {'search': self.url + '/api2.php?action=torrents',
                     'download': self.url + '/download.php?'}

    def _check_auth(self):

        if not self.username or not self.passkey:
            raise AuthException(('Your authentication credentials for %s are '
                                 'missing, check your config.') % self.name)

        return True

    def _checkAuthFromData(self, parsed_json):  # pylint: disable=invalid-name
        """ Check that we are authenticated. """

        if 'status' in parsed_json and 'message' in parsed_json:
            if parsed_json.get('status') == 3:
                logger.log('Invalid username or password. '
                           'Check your settings', logger.WARNING)

        return True

    def search(self, search_params, age=0, ep_obj=None):  # pylint: disable=too-many-locals
        """ Do the actual searching and JSON parsing"""

        results = []

        for mode in search_params:
            items = []
            logger.log('Search Mode: {0}'.format(mode), logger.DEBUG)

            for search_string in search_params[mode]:
                if mode != 'RSS':
                    logger.log('Search string: {0}'.format
                               (search_string), logger.DEBUG)

                post_data = {
                    'username': self.username,
                    'passkey': self.passkey,
                    'category': '2',  # TV Category
                    'search': search_string,
                }

                self._check_auth()
                parsed_json = self.get_url(self.urls['search'],
                                           post_data=json.dumps(post_data),
                                           returns='json')

                if not parsed_json:
                    return results

                if self._checkAuthFromData(parsed_json):
                    json_items = parsed_json.get('data', '')
                    if not json_items:
                        logger.log('Resulting JSON from provider is not correct, '
                                   'not parsing it', logger.ERROR)

                    for item in json_items.get('torrents', []):
                        try:
                            title = item.pop('name', '')
                            download_url = '{0}{1}'.format(
                                self.urls['download'],
                                urlencode({'id': item.pop('id', ''), 'passkey': self.passkey}))

                            if not all([title, download_url]):
                                continue

                            seeders = try_int(item.pop('seeders', 0))
                            leechers = try_int(item.pop('leechers', 0))

                            if seeders < min(self.minseed, 1):
                                logger.log('Discarding torrent because it does not meet '
                                           'the minimum seeders: {0}. Seeders: {1})'.format
                                           (title, seeders), logger.DEBUG)
                                continue

                            info_hash = item.pop('info_hash', '')
                            size = convert_size(item.pop('size', -1), -1)

                            item = {'title': title, 'link': download_url, 'size': size, 'seeders': seeders, 'leechers': leechers, 'pubdate': None, 'hash': info_hash}
                            if mode != 'RSS':
                                logger.log('Found result: {0} with {1} seeders and {2} leechers'.format(
                                    title, seeders, leechers), logger.DEBUG)

                            items.append(item)
                        except (AttributeError, TypeError, KeyError, ValueError, IndexError):
                            logger.log('Failed parsing provider. Traceback: {0!r}'.format
                                       (traceback.format_exc()), logger.ERROR)
                            continue

            results += items

        return results


provider = NorbitsProvider()  # pylint: disable=invalid-name
