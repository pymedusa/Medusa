# coding=utf-8
# Author: medariox <dariox@gmx.com>
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

import traceback

from requests.compat import urljoin
from ..TorrentProvider import TorrentProvider
from .... import logger, tvcache
from ....bs4_parser import BS4Parser
from ....helper.common import convert_size, try_int


class ZooqleProvider(TorrentProvider):  # pylint: disable=too-many-instance-attributes
    """Zooqle Torrent provider."""

    def __init__(self):

        # Provider Init
        TorrentProvider.__init__(self, 'Zooqle')

        # Credentials
        self.public = True

        # URLs
        self.url = 'https://zooqle.com/'
        self.urls = {
            'search': urljoin(self.url, '/search'),
        }

        # Proper Strings
        self.proper_strings = ['PROPER', 'REPACK', 'REAL']

        # Miscellaneous Options

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tvcache.TVCache(self, min_time=15)

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-locals, too-many-branches
        """
        Search a provider and parse the results

        :param search_strings: A dict with mode (key) and the search value (value)
        :param age: Not used
        :param ep_obj: Not used
        :returns: A list of search results (structure)
        """
        results = []

        # Search Params
        search_params = {
            'q': '* category:TV',
            's': 'dt',
            'v': 't',
            'sd': 'd',
        }

        for mode in search_strings:
            logger.log('Search mode: {0}'.format(mode), logger.DEBUG)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    logger.log('Search string: {search}'.format
                               (search=search_string), logger.DEBUG)
                    search_params = {'q': '{0} category:TV'.format(search_string)}

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
            torrent_table = html.find('div', class_='panel-body')
            torrent_rows = torrent_table('tr') if torrent_table else []

            # Continue only if at least one release is found
            if len(torrent_rows) < 2:
                logger.log('Data returned from provider does not contain any torrents', logger.DEBUG)
                return items

            # Skip column headers
            for row in torrent_rows[1:]:
                cells = row('td')

                try:
                    title = cells[1].find('a').get_text()
                    magnet = cells[2].find('a')['href']
                    download_url = '{magnet}{trackers}'.format(magnet=magnet,
                                                               trackers=self._custom_trackers)
                    if not all([title, download_url]):
                        continue

                    seeders = 1
                    leechers = 0
                    if len(cells) > 5:
                        peers = cells[5].find('div')
                        if peers and peers.get('title'):
                            peers = peers['title'].replace(',', '').split(' | ', 1)
                            seeders = try_int(peers[0][9:], 1)
                            leechers = try_int(peers[1][10:])

                    # Filter unseeded torrent
                    if seeders < min(self.minseed, 1):
                        if mode != 'RSS':
                            logger.log("Discarding torrent because it doesn't meet the "
                                       "minimum seeders: {0}. Seeders: {1}".format
                                       (title, seeders), logger.DEBUG)
                        continue

                    torrent_size = cells[3].get_text(strip=True)
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


provider = ZooqleProvider()
