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

import re
import traceback

from sickbeard import logger, tvcache
from sickbeard.bs4_parser import BS4Parser
from sickbeard.common import USER_AGENT

from sickrage.helper.common import convert_size, try_int
from sickrage.providers.torrent.TorrentProvider import TorrentProvider


class TorrentzProvider(TorrentProvider):  # pylint: disable=too-many-instance-attributes
    """Torrentz Torrent provider"""
    def __init__(self):

        # Provider Init
        TorrentProvider.__init__(self, "Torrentz")

        # Credentials
        self.public = True
        self.confirmed = True

        # URLs
        self.url = 'https://torrentz.eu/'
        self.urls = {
            'verified': 'https://torrentz.eu/feed_verified',
            'feed': 'https://torrentz.eu/feed',
            'base': self.url,
        }

        # Proper Strings
        self.headers.update({'User-Agent': USER_AGENT})

        # Miscellaneous Options

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tvcache.TVCache(self, min_time=15)  # only poll Torrentz every 15 minutes max

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-locals
        results = []

        for mode in search_strings:
            items = []
            logger.log('Search mode: {0}'.format(mode), logger.DEBUG)

            for search_string in search_strings[mode]:
                search_url = self.urls['verified'] if self.confirmed else self.urls['feed']
                if mode != 'RSS':
                    logger.log('Search string: {search}'.format
                               (search=search_string), logger.DEBUG)

                data = self.get_url(search_url, params={'q': search_string}, returns='text')
                if not data:
                    logger.log('No data returned from provider', logger.DEBUG)
                    continue

                if not data.startswith("<?xml"):
                    logger.log("Expected xml but got something else, is your mirror failing?", logger.INFO)
                    continue

                with BS4Parser(data, 'html5lib') as parser:
                    for item in parser('item'):
                        try:
                            if item.category and 'tv' not in item.category.get_text(strip=True):
                                continue

                            title_raw = item.title.text
                            # Add "-" after codec and add missing "."
                            title = re.sub(r'([xh][ .]?264|xvid)( )', r'\1-', title_raw).replace(' ', '.') if title_raw else ''
                            torrent_hash = item.guid.text.rsplit('/', 1)[-1]
                            if not all([title, torrent_hash]):
                                continue

                            download_url = "magnet:?xt=urn:btih:" + torrent_hash + "&dn=" + title + self._custom_trackers
                            torrent_size, seeders, leechers = self._split_description(item.find('description').text)
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
                            continue

            results += items

        return results

    @staticmethod
    def _split_description(description):
        match = re.findall(r'[0-9]+', description)
        return int(match[0]) * 1024 ** 2, int(match[1]), int(match[2])


provider = TorrentzProvider()
