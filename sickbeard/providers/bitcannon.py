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

from __future__ import unicode_literals

import validators
import traceback

from requests.compat import urljoin

from sickbeard import logger, tvcache

from sickrage.helper.common import convert_size, try_int
from sickrage.providers.torrent.TorrentProvider import TorrentProvider


class BitCannonProvider(TorrentProvider):
    """BitCannon Torrent provider"""
    def __init__(self):

        # Provider Init
        TorrentProvider.__init__(self, 'BitCannon')

        # Credentials
        self.api_key = None

        # URLs
        self.custom_url = None

        # Proper Strings

        # Miscellaneous Options

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tvcache.TVCache(self, search_params={'RSS': ['tv', 'anime']})

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-branches, too-many-locals
        """
        BitCannon search and parsing

        :param search_string: A dict with mode (key) and the search value (value)
        :param age: Not used
        :param ep_obj: Not used
        :returns: A list of search results (structure)
        """
        results = []
        url = 'http://localhost:3000/'
        if self.custom_url:
            if not validators.url(self.custom_url, require_tld=False):
                logger.log('Invalid custom url set, please check your settings', logger.WARNING)
                return results
            url = self.custom_url

        # Search Params
        search_params = {
            'category': 'anime' if ep_obj and ep_obj.show and ep_obj.show.anime else 'tv',
            'apiKey': self.api_key
        }

        for mode in search_strings:
            items = []
            logger.log('Search mode: {0}'.format(mode), logger.DEBUG)

            for search_string in search_strings[mode]:
                search_params['q'] = search_string
                if mode != 'RSS':
                    logger.log('Search string: {search}'.format
                               (search=search_string), logger.DEBUG)

                search_url = urljoin(url, 'api/search')
                parsed_json = self.get_url(search_url, params=search_params, returns='json')
                if not parsed_json:
                    logger.log('No data returned from provider', logger.DEBUG)
                    continue

                if not self._check_auth_from_data(parsed_json):
                    return results

                for result in parsed_json.pop('torrents', {}):
                    try:
                        title = result.pop('title', '')

                        info_hash = result.pop('infoHash', '')
                        download_url = 'magnet:?xt=urn:btih:' + info_hash
                        if not all([title, download_url, info_hash]):
                            continue

                        swarm = result.pop('swarm', None)
                        if swarm:
                            seeders = try_int(swarm.pop('seeders', 0))
                            leechers = try_int(swarm.pop('leechers', 0))
                        else:
                            seeders = leechers = 0

                        # Filter unseeded torrent
                        if seeders < min(self.minseed, 1):
                            if mode != 'RSS':
                                logger.log("Discarding torrent because it doesn't meet the "
                                           "minimum seeders: {0}. Seeders: {1}".format
                                           (title, seeders), logger.DEBUG)
                            continue

                        size = convert_size(result.pop('size', -1)) or -1

                        item = {
                            'title': title,
                            'link': download_url,
                            'size': size,
                            'seeders': seeders,
                            'leechers': leechers,
                            'pubdate': None,
                            'hash': None
                        }
                        if mode != 'RSS':
                            logger.log('Found result: {0} with {1} seeders and {2} leechers'.format
                                       (title, seeders, leechers), logger.DEBUG)

                        items.append(item)
                    except (AttributeError, TypeError, KeyError, ValueError, IndexError):
                        logger.log('Failed parsing provider. Traceback: {0!r}'.format
                                   (traceback.format_exc()), logger.ERROR)
                        continue

            results += items

        return results

    @staticmethod
    def _check_auth_from_data(data):
        if not all([isinstance(data, dict),
                    data.pop('status', 200) != 401,
                    data.pop('message', '') != 'Invalid API key']):

            logger.log('Invalid api key. Check your settings', logger.WARNING)
            return False

        return True


provider = BitCannonProvider()
