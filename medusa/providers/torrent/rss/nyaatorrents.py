# coding=utf-8
# Author: Mr_Orange
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

from ..TorrentProvider import TorrentProvider
from .... import logger, tvcache
from ....helper.common import convert_size, try_int


class NyaaProvider(TorrentProvider):  # pylint: disable=too-many-instance-attributes

    def __init__(self):

        # Provider Init
        TorrentProvider.__init__(self, 'NyaaTorrents')

        # Credentials
        self.public = True

        # URLs
        self.url = 'http://www.nyaa.se'

        # Proper Strings

        # Miscellaneous Options
        self.supports_absolute_numbering = True
        self.anime_only = True
        self.confirmed = False
        self.regex = re.compile(r'(\d+) seeder\(s\), (\d+) leecher\(s\), \d+ download\(s\) - (\d+.?\d* [KMGT]iB)(.*)', re.DOTALL)

        # Torrent Stats
        self.minseed = 0
        self.minleech = 0

        # Cache
        self.cache = tvcache.TVCache(self, min_time=20)  # only poll NyaaTorrents every 20 minutes max

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-locals, too-many-branches
        """
        Search a provider and parse the results

        :param search_strings: A dict with mode (key) and the search value (value)
        :param age: Not used
        :param ep_obj: Not used
        :returns: A list of search results (structure)
        """
        results = []
        if self.show and not self.show.is_anime:
            return results

        # Search Params
        search_params = {
            'page': 'rss',
            'cats': '1_0',  # All anime
            'sort': 2,  # Sort Descending By Seeders
            'order': 1,
        }

        for mode in search_strings:
            logger.log('Search mode: {0}'.format(mode), logger.DEBUG)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    logger.log('Search string: {search}'.format
                               (search=search_string), logger.DEBUG)
                    if self.confirmed:
                        logger.log('Searching only confirmed torrents', logger.DEBUG)

                    search_params['term'] = search_string
                data = self.cache.getRSSFeed(self.url, params=search_params)
                if not data:
                    logger.log('No data returned from provider', logger.DEBUG)
                    continue
                if not data['entries']:
                    logger.log('Data returned from provider does not contain any {0}torrents'.format(
                               'confirmed ' if self.confirmed else ''), logger.DEBUG)
                    continue

                results += self.parse(data, mode)

        return results

    def parse(self, data, mode):
        """
        Parse search results for items.

        :param data: The raw response from a search
        :param mode: The current mode used to search, e.g. RSS

        :return: A list of items found
        """

        items = []

        for result in data:
            try:
                title = result['title']
                download_url = result['link']
                if not all([title, download_url]):
                    continue

                item_info = self.regex.search(result['summary'])
                if not item_info:
                    logger.log('There was a problem parsing an item summary, skipping: {0}'.format
                               (title), logger.DEBUG)
                    continue

                seeders, leechers, torrent_size, verified = item_info.groups()
                seeders = try_int(seeders)
                leechers = try_int(leechers)

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

                size = convert_size(torrent_size) or -1

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


provider = NyaaProvider()
