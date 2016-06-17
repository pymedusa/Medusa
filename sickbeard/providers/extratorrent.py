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

from requests.compat import urljoin

import sickbeard
from sickbeard import logger, tvcache
from sickbeard.bs4_parser import BS4Parser
from sickbeard.common import USER_AGENT

from sickrage.helper.common import convert_size, try_int
from sickrage.providers.torrent.TorrentProvider import TorrentProvider


class ExtraTorrentProvider(TorrentProvider):  # pylint: disable=too-many-instance-attributes
    """ExtraTorrent Torrent provider"""
    def __init__(self):

        # Provider Init
        TorrentProvider.__init__(self, 'ExtraTorrent')

        # Credentials
        self.public = True

        # URLs
        self.url = 'http://extratorrent.cc'
        self.urls = {
            'index': self.url,
            'rss': urljoin(self.url, 'rss.xml'),
        }
        self.custom_url = None

        # Proper Strings

        # Miscellaneous Options
        self.headers.update({'User-Agent': USER_AGENT})
        self.search_params = {'cid': 8}

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tvcache.TVCache(self, min_time=30)  # Only poll ExtraTorrent every 30 minutes max

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-locals, too-many-branches
        """
        ExtraTorrent search and parsing

        :param search_string: A dict with mode (key) and the search value (value)
        :param age: Not used
        :param ep_obj: Not used
        :returns: A list of search results (structure)
        """
        results = []

        # Search Params
        search_params = {
            'cid': 8,
            'type': 'rss',
        }

        for mode in search_strings:
            items = []
            logger.log('Search mode: {0}'.format(mode), logger.DEBUG)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    search_params['type'] = 'search'
                    logger.log('Search string: {search}'.format
                               (search=search_string), logger.DEBUG)

                search_params['search'] = search_string
                search_url = self.urls['rss'] if not self.custom_url else self.urls['rss'].replace(self.urls['index'], self.custom_url)
                data = self.get_url(search_url, params=search_params, returns='text')
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

                            if sickbeard.TORRENT_METHOD == 'blackhole':
                                enclosure = item.find('enclosure')  # Backlog doesnt have enclosure
                                download_url = enclosure['url'] if enclosure else item.find('link').next.strip()
                                download_url = re.sub(r'(.*)/torrent/(.*).html', r'\1/download/\2.torrent', download_url)
                            else:
                                info_hash = item.find('info_hash')
                                if not info_hash:
                                    continue
                                info_hash = info_hash.get_text(strip=True)
                                download_url = 'magnet:?xt=urn:btih:' + info_hash + '&dn=' + title + self._custom_trackers

                            if not all([title, download_url]):
                                continue

                            seeders = item.find('seeders')
                            seeders = try_int(seeders.get_text(strip=True)) if seeders else 1
                            leechers = item.find('leechers')
                            leechers = try_int(leechers.get_text(strip=True)) if leechers else 0

                            # Filter unseeded torrent
                            if seeders < min(self.minseed, 1):
                                if mode != 'RSS':
                                    logger.log("Discarding torrent because it doesn't meet the "
                                               "minimum seeders: {0}. Seeders: {1}".format
                                               (title, seeders), logger.DEBUG)
                                continue

                            torrent_size = item.find('size')
                            torrent_size = torrent_size.get_text() if torrent_size else None
                            size = convert_size(torrent_size) or -1

                            item = {
                                'title': title,
                                'link': download_url,
                                'size': size,
                                'seeders': seeders,
                                'leechers': leechers,
                                'pubdate': None,
                                'hash': None,
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
