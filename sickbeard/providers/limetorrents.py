# coding=utf-8
# Author: Gonçalo M. (aka duramato/supergonkas) <supergonkas@gmail.com>
#
# This file is part of SickRage.
#
# SickRage is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# SickRage is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with SickRage. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import re
import requests
import traceback

from requests.compat import urljoin

from sickbeard import logger, tvcache
from sickbeard.bs4_parser import BS4Parser

from sickrage.helper.common import convert_size, try_int
from sickrage.providers.torrent.TorrentProvider import TorrentProvider

id_regex = re.compile(r'(?:torrent-([0-9]*).html)', re.I)
hash_regex = re.compile(r'(.*)([0-9a-f]{40})(.*)', re.I)


class LimeTorrentsProvider(TorrentProvider):  # pylint: disable=too-many-instance-attributes

    def __init__(self):

        # Provider Inits
        TorrentProvider.__init__(self, 'LimeTorrents')

        # URLs
        self.url = 'https://www.limetorrents.cc/'
        self.urls = {
            'index': self.url,
            'update': urljoin(self.url, '/post/updatestats.php'),
            'search': urljoin(self.url, '/search/tv/{query}/'),
            'rss': urljoin(self.url, '/browse-torrents/TV-shows/date/')
        }

        # Credentials
        self.public = True
        self.confirmed = False

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Proper Strings
        self.proper_strings = ['PROPER', 'REPACK', 'REAL']

        # Cache
        cache_params = {'RSS': ['1/', '2/', '3/']}
        self.cache = tvcache.TVCache(self, min_time=10, search_params=cache_params)

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-branches,too-many-locals
        results = []
        for mode in search_strings:
            items = []
            logger.log('Search Mode: {0}'.format(mode), logger.DEBUG)
            for search_string in search_strings[mode]:
                search_url = self.urls['rss'] if mode == 'RSS' else self.urls['search'].format(query=search_string)
                data = self.get_url(search_url, returns='text')
                if not data:
                        logger.log('No data returned from provider', logger.DEBUG)
                        continue
                with BS4Parser(data, 'html5lib') as html:
                    torrent_table = html('table', class_='table2')[0 if mode == 'RSS' else 1]
                    torrent_rows = torrent_table('tr')
                    for result in torrent_rows:
                        cells = result('td')
                        try:
                            verified = result('img', title='Verified torrent')
                            if self.confirmed and not verified:
                                continue
                            titleinfo = result('a')
                            info = titleinfo[1]['href']
                            torrent_id = id_regex.search(info).group(1)
                            url = result.find('a', rel='nofollow')
                            if not url:
                                continue
                            torrent_hash = hash_regex.search(url['href']).group(2)
                            try:
                                self.session.get(self.urls['update'], timeout=0.1,
                                                 params={'torrent_id': torrent_id,
                                                         'infohash': torrent_hash})
                            except requests.exceptions.Timeout:
                                pass
                            title = titleinfo[1].get_text(strip=True)
                            # Remove comma from larger number like 2,000 seeders = 2000
                            seeders = try_int(cells[3].get_text(strip=True).replace(',', ''))
                            leechers = try_int(cells[4].get_text(strip=True).replace(',', ''))
                            size = convert_size(cells[2].get_text(strip=True)) or -1
                            download_url = 'magnet:?xt=urn:btih:{hash}&dn={title}{trackers}' .format(
                                hash=torrent_hash, title=title, trackers=self._custom_trackers)

                            if seeders < min(self.minseed, 1):
                                if mode != 'RSS':
                                    logger.log('Discarding torrent because it doesn\'t meet the minimum '
                                               'seeders or leechers: {0} (S:{1} L:{2})'.format
                                               (title, seeders, leechers), logger.DEBUG)
                                continue

                            item = {
                                'title': title,
                                'link': download_url,
                                'size': size,
                                'seeders': seeders,
                                'leechers': leechers,
                                'hash': torrent_hash or ''
                            }
                            if mode != 'RSS':
                                logger.log('Found result: {0} with {1} seeders and {2} leechers'.format
                                           (title, seeders, leechers), logger.DEBUG)
                            items.append(item)

                        except StandardError:
                            logger.log(u"Failed parsing provider. Traceback: %r" % traceback.format_exc(), logger.ERROR)
                            continue

            # For each search mode sort all the items by seeders if available
            items.sort(key=lambda d: try_int(d.get('seeders', 0)), reverse=True)
            results += items

        return results


provider = LimeTorrentsProvider()
