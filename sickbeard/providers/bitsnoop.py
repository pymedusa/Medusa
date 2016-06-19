# coding=utf-8
# Author: Gonçalo M. (aka duramato/supergonkas) <supergonkas@gmail.com>
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

import sickbeard
from sickbeard import logger, tvcache
from sickbeard.bs4_parser import BS4Parser

from sickrage.helper.common import convert_size, try_int
from sickrage.providers.torrent.TorrentProvider import TorrentProvider


class BitSnoopProvider(TorrentProvider):  # pylint: disable=too-many-instance-attributes
    """BitSnoop Torrent provider"""
    def __init__(self):

        # Provider Init
        TorrentProvider.__init__(self, 'BitSnoop')

        # Credentials
        self.public = True

        # URLs
        self.url = 'http://bitsnoop.com'
        self.urls = {
            'index': self.url,
            'search': urljoin(self.url, '/search/video/'),
            'rss': urljoin(self.url, '/new_video.html?fmt=rss'),
        }

        # Proper Strings
        self.proper_strings = ['PROPER', 'REPACK']

        # Miscellaneous Options

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tvcache.TVCache(self, search_params={'RSS': ['rss']})

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-branches,too-many-locals
        """
        BitSnoop search and parsing

        :param search_string: A dict with mode (key) and the search value (value)
        :param age: Not used
        :param ep_obj: Not used
        :returns: A list of search results (structure)
        """
        results = []

        for mode in search_strings:
            items = []
            logger.log('Search mode: {0}'.format(mode), logger.DEBUG)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    logger.log('Search string: {search}'.format
                               (search=search_string), logger.DEBUG)

                search_url = (self.urls['rss'], self.urls['search'] + search_string + '/s/d/1/?fmt=rss')[mode != 'RSS']
                data = self.get_url(search_url, returns='text')
                if not data:
                    logger.log('No data returned from provider', logger.DEBUG)
                    continue

                if not data.startswith('<?xml'):
                    logger.log('Expected xml but got something else, is your mirror failing?', logger.INFO)
                    continue

                with BS4Parser(data, 'html5lib') as html:
                    for item in html('item'):

                        try:
                            if not item.category.text.endswith(('TV', 'Anime')):
                                continue

                            title = item.title.text
                            # Use the torcache link bitsnoop provides,
                            # unless it is not torcache or we are not using blackhole
                            # because we want to use magnets if connecting direct to client
                            # so that proxies work.
                            download_url = item.enclosure['url']
                            if sickbeard.TORRENT_METHOD != 'blackhole' or 'torcache' not in download_url:
                                download_url = item.find('magneturi').next.replace('CDATA', '').strip('[]') + self._custom_trackers

                            if not (title and download_url):
                                continue

                            seeders = try_int(item.find('numseeders').text)
                            leechers = try_int(item.find('numleechers').text)

                            # Filter unseeded torrent
                            if seeders < min(self.minseed, 1):
                                if mode != 'RSS':
                                    logger.log("Discarding torrent because it doesn't meet the "
                                               "minimum seeders: {0}. Seeders: {1}".format
                                               (title, seeders), logger.DEBUG)
                                continue

                            torrent_size = item.find('size').text
                            size = convert_size(torrent_size) or -1
                            info_hash = item.find('infohash').text

                            item = {
                                'title': title,
                                'link': download_url,
                                'size': size,
                                'seeders': seeders,
                                'leechers': leechers,
                                'pubdate': None,
                                'hash': info_hash,
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


provider = BitSnoopProvider()
