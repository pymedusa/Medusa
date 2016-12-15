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
"""Provider code for Extratorrent."""
from __future__ import unicode_literals

import traceback

from requests.compat import urljoin

import validators

from ..torrent_provider import TorrentProvider
from .... import logger, tv_cache
from ....bs4_parser import BS4Parser
from ....helper.common import convert_size, try_int


class ExtraTorrentProvider(TorrentProvider):
    """ExtraTorrent Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(self.__class__, self).__init__('ExtraTorrent')

        # Credentials
        self.public = True

        # URLs
        self.url = 'http://extratorrent.cc'
        self.custom_url = None

        # Proper Strings
        self.proper_strings = ['PROPER', 'REPACK', 'REAL']

        # Miscellaneous Options

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tv_cache.TVCache(self, min_time=30)  # Only poll ExtraTorrent every 30 minutes max

    def search(self, search_strings, age=0, ep_obj=None):
        """
        Search a provider and parse the results.

        :param search_strings: A dict with mode (key) and the search value (value)
        :param age: Not used
        :param ep_obj: Not used
        :returns: A list of search results (structure)
        """
        results = []

        if self.custom_url:
            if not validators.url(self.custom_url):
                logger.log('Invalid custom url: {0}'.format(self.custom_url), logger.WARNING)
                return results
            self.url = self.custom_url

        self.urls = {
            'search': urljoin(self.url, 'search/'),
            'rss': urljoin(self.url, 'view/today/TV.html'),
        }

        # Search Params
        search_params = {
            'search': '',
            'new': 1,
            'x': 0,
            'y': 0,
        }

        for mode in search_strings:
            logger.log('Search mode: {0}'.format(mode), logger.DEBUG)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    search_params['search'] = search_string
                    logger.log('Search string: {search}'.format
                               (search=search_string), logger.DEBUG)
                    search_url = self.urls['search']
                else:
                    search_params = None
                    search_url = self.urls['rss']

                response = self.get_url(search_url, params=search_params, returns='response')
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
            torrent_table = html.find('table', class_='tl')
            torrent_rows = torrent_table('tr') if torrent_table else []

            # Continue only if at least one release is found
            if len(torrent_rows) < 3 or (torrent_rows == 3 and torrent_rows[2].get_text() == 'No torrents'):
                logger.log('Data returned from provider does not contain any torrents', logger.DEBUG)
                return items

            # RSS search has one less column
            decrease = 1

            # Avoid parsing of 'related torrents'
            if mode != 'RSS':
                h2s = html.find_all('h2')
                if len(h2s) > 2 and h2s[1].get_text() == 'Related torrents':
                    logger.log('Data returned from provider does not contain any torrents', logger.DEBUG)
                    return items

                # Don't decrease column
                decrease = 0

            # Skip column headers
            for result in torrent_rows[2:]:
                try:
                    cells = result('td')

                    torrent_info = cells[0].find('a')
                    if not torrent_info:
                        continue

                    # Removes 'Download ' in the beginning and ' torrent' in the end
                    title = torrent_info.get('title')[9:-8]
                    download_url = urljoin(self.url, torrent_info.get('href').replace
                                           ('torrent_download', 'download'))

                    seeders = try_int(cells[5 - decrease].get_text(), 1)
                    leechers = try_int(cells[6 - decrease].get_text())

                    # Filter unseeded torrent
                    if seeders < min(self.minseed, 1):
                        if mode != 'RSS':
                            logger.log("Discarding torrent because it doesn't meet the "
                                       "minimum seeders: {0}. Seeders: {1}".format
                                       (title, seeders), logger.DEBUG)
                        continue

                    torrent_size = cells[4 - decrease].get_text().replace('\xa0', ' ')
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
                    continue

        return items


provider = ExtraTorrentProvider()
