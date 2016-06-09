# coding=utf-8
# Author: Gonçalo M. (aka duramato/supergonkas) <supergonkas@gmail.com>
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
import sickbeard

from sickbeard import logger, tvcache
from sickbeard.bs4_parser import BS4Parser
from sickbeard.common import USER_AGENT

from sickrage.helper.common import convert_size, try_int
from sickrage.providers.torrent.TorrentProvider import TorrentProvider


class ExtraTorrentProvider(TorrentProvider):  # pylint: disable=too-many-instance-attributes

    def __init__(self):

        TorrentProvider.__init__(self, 'ExtraTorrent')

        self.urls = {
            'index': 'http://extratorrent.cc',
            'rss': 'http://extratorrent.cc/rss.xml',
        }

        self.url = self.urls['index']

        self.public = True
        self.minseed = None
        self.minleech = None
        self.custom_url = None

        self.cache = tvcache.TVCache(self, min_time=30)  # Only poll ExtraTorrent every 30 minutes max
        self.headers.update({'User-Agent': USER_AGENT})
        self.search_params = {'cid': 8}

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-locals, too-many-branches
        results = []
        for mode in search_strings:
            items = []
            logger.log('Search Mode: {0}'.format(mode), logger.DEBUG)
            for search_string in search_strings[mode]:
                if mode != 'RSS':
                    logger.log('Search string: {0}'.format(search_string.,
                               logger.DEBUG)

                self.search_params.update({'type': ('search', 'rss')[mode == 'RSS'], 'search': search_string})
                search_url = self.urls['rss'] if not self.custom_url else self.urls['rss'].replace(self.urls['index'], self.custom_url)

                data = self.get_url(search_url, params=self.search_params, returns='text')
                if not data:
                    logger.log('No data returned from provider', logger.DEBUG)
                    continue

                if not data.startswith('<?xml'):
                    logger.log('Expected xml but got something else, is your mirror failing?', logger.INFO)
                    continue

                with BS4Parser(data, 'html5lib') as html:
                    for item in html('item'):
                        try:
                            title = re.sub(r'^<!\[CDATA\[|\]\]>$', '', item.find('title').get_text(strip=True))
                            seeders = try_int(item.find('seeders').get_text(strip=True))
                            leechers = try_int(item.find('leechers').get_text(strip=True))
                            torrent_size = item.find('size').get_text()
                            size = convert_size(torrent_size) or -1

                            if sickbeard.TORRENT_METHOD == 'blackhole':
                                enclosure = item.find('enclosure')  # Backlog doesnt have enclosure
                                download_url = enclosure['url'] if enclosure else item.find('link').next.strip()
                                download_url = re.sub(r'(.*)/torrent/(.*).html', r'\1/download/\2.torrent', download_url)
                            else:
                                info_hash = item.find('info_hash').get_text(strip=True)
                                download_url = 'magnet:?xt=urn:btih:' + info_hash + '&dn=' + title + self._custom_trackers

                            if not all([title, download_url]):
                                continue

                                # Filter unseeded torrent
                            if seeders < min(self.minseed, 1):
                                if mode != 'RSS':
                                    logger.log("Discarding torrent because it doesn't meet the"
                                               ' minimum seeders: {0}. Seeders: {1})'.format
                                               (title, seeders), logger.DEBUG)
                                continue

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


provider = ExtraTorrentProvider()
