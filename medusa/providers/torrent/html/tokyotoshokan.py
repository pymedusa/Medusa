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
"""Provider code for TokyoToshokan."""
from __future__ import unicode_literals

import re
import traceback

from medusa import (
    logger,
    tv,
)
from medusa.bs4_parser import BS4Parser
from medusa.helper.common import (
    convert_size,
    try_int,
)
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.compat import urljoin


class TokyoToshokanProvider(TorrentProvider):
    """TokyoToshokan Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(self.__class__, self).__init__('TokyoToshokan')

        # Credentials
        self.public = True

        # URLs
        self.url = 'http://tokyotosho.info/'
        self.urls = {
            'search': urljoin(self.url, 'search.php'),
            'rss': urljoin(self.url, 'rss.php'),
        }

        # Proper Strings

        # Miscellaneous Options
        self.supports_absolute_numbering = True
        self.anime_only = True

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tv.Cache(self, min_time=15)  # only poll TokyoToshokan every 15 minutes max

    def search(self, search_strings, age=0, ep_obj=None):
        """
        Search a provider and parse the results.

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
            'type': 1,  # get anime types
        }

        for mode in search_strings:
            logger.log('Search mode: {0}'.format(mode), logger.DEBUG)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    logger.log('Search string: {search}'.format
                               (search=search_string), logger.DEBUG)

                search_params['terms'] = search_string
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

        with BS4Parser(data, 'html5lib') as soup:
            torrent_table = soup.find('table', class_='listing')
            torrent_rows = torrent_table('tr') if torrent_table else []

            # Continue only if at least one release is found
            if len(torrent_rows) < 2:
                logger.log('Data returned from provider does not contain any torrents', logger.DEBUG)
                return items

            a = 1 if len(torrent_rows[0]('td')) < 2 else 0

            # Skip column headers
            for top, bot in zip(torrent_rows[a::2], torrent_rows[a + 1::2]):
                try:
                    desc_top = top.find('td', class_='desc-top')
                    title = desc_top.get_text(strip=True) if desc_top else None
                    download_url = desc_top.find('a')['href'] if desc_top else None
                    if not all([title, download_url]):
                        continue

                    stats = bot.find('td', class_='stats').get_text(strip=True)
                    sl = re.match(r'S:(?P<seeders>\d+)L:(?P<leechers>\d+)C:(?:\d+)ID:(?:\d+)', stats.replace(' ', ''))
                    seeders = try_int(sl.group('seeders')) if sl else 0
                    leechers = try_int(sl.group('leechers')) if sl else 0

                    # Filter unseeded torrent
                    if seeders < min(self.minseed, 1):
                        if mode != 'RSS':
                            logger.log("Discarding torrent because it doesn't meet the "
                                       "minimum seeders: {0}. Seeders: {1}".format
                                       (title, seeders), logger.DEBUG)
                        continue

                    desc_bottom = bot.find('td', class_='desc-bot').get_text(strip=True)
                    size = convert_size(desc_bottom.split('|')[1].strip('Size: ')) or -1

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


provider = TokyoToshokanProvider()
