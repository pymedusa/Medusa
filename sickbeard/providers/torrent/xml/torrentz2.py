# coding=utf-8
# Authorship: The Medusa Team
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

from requests.compat import urljoin

from sickbeard import logger, tvcache
from sickbeard.bs4_parser import BS4Parser

from sickrage.helper.common import convert_size
from sickrage.providers.torrent.TorrentProvider import TorrentProvider


class Torrentz2Provider(TorrentProvider):  # pylint: disable=too-many-instance-attributes
    """Torrentz2 Torrent provider"""
    def __init__(self):

        # Provider Init
        TorrentProvider.__init__(self, 'Torrentz2')

        # Credentials
        self.public = True

        # URLs
        self.url = 'https://torrentz2.eu/'
        self.urls = {
            'base': self.url,
            'verified': urljoin(self.url, 'feed_verified'),
            'feed': urljoin(self.url, 'feed'),
        }

        # Proper Strings

        # Miscellaneous Options
        # self.confirmed = True

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tvcache.TVCache(self, min_time=15)  # only poll Torrentz every 15 minutes max

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
            'f': 'tv added:2d',
        }

        for mode in search_strings:
            logger.log('Search mode: {0}'.format(mode), logger.DEBUG)

            for search_string in search_strings[mode]:
                if mode != 'RSS':
                    logger.log('Search string: {search}'.format
                               (search=search_string), logger.DEBUG)
                    search_params['f'] = search_string

                # search_url = self.urls['verified'] if self.confirmed else self.urls['feed']
                search_url = self.urls['feed']
                response = self.get_url(search_url, params=search_params, returns='response')
                if not response or not response.text:
                    logger.log('No data returned from provider', logger.DEBUG)
                    continue
                elif not response.text.startswith('<?xml'):
                    logger.log('Expected xml but got something else, is your mirror failing?', logger.INFO)
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
            torrent_rows = html('item')

            for row in torrent_rows:
                try:
                    if row.category and 'tv' not in row.category.get_text(strip=True).lower():
                        continue

                    title_raw = row.title.text
                    # Add "-" after codec and add missing "."
                    title = re.sub(r'([xh][ .]?264|xvid)( )', r'\1-', title_raw).replace(' ', '.') if title_raw else ''
                    torrent_hash = row.guid.text.rsplit('/', 1)[-1]
                    download_url = "magnet:?xt=urn:btih:" + torrent_hash + "&dn=" + title + self._custom_trackers
                    if not all([title, download_url]):
                        continue

                    torrent_size, seeders, leechers = self._split_description(row.find('description').text)
                    size = convert_size(torrent_size) or -1

                    # Filter unseeded torrent
                    if seeders < min(self.minseed, 1):
                        if mode != 'RSS':
                            logger.log("Discarding torrent because it doesn't meet the "
                                       "minimum seeders: {0}. Seeders: {1}".format
                                       (title, seeders), logger.DEBUG)
                        continue

                    item = {
                        'title': title,
                        'link': download_url,
                        'size': size,
                        'seeders': seeders,
                        'leechers': leechers,
                        'pubdate': None,
                        'hash': torrent_hash,
                    }
                    if mode != 'RSS':
                        logger.log('Found result: {0} with {1} seeders and {2} leechers'.format
                                   (title, seeders, leechers), logger.DEBUG)

                    items.append(item)
                except (AttributeError, TypeError, KeyError, ValueError, IndexError):
                    logger.log('Failed parsing provider. Traceback: {0!r}'.format
                               (traceback.format_exc()), logger.ERROR)

        return items

    @staticmethod
    def _split_description(description):
        match = re.findall(r'[0-9]+', description)
        return int(match[0]) * 1024 ** 2, int(match[1]), int(match[2])


provider = Torrentz2Provider()
