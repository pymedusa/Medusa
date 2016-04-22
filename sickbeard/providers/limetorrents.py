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

import re
import traceback
import sickbeard
import requests
from socket import timeout as SocketTimeout

from sickbeard import logger, tvcache
from sickbeard.bs4_parser import BS4Parser

from sickrage.helper.common import convert_size, try_int
from sickrage.providers.torrent.TorrentProvider import TorrentProvider

id_regex = re.compile(r"(?:torrent-([0-9]*).html)", re.I)
hash_regex = re.compile(r"(.*)([0-9a-f]{40})(.*)", re.I)

class LimeTorrentsProvider(TorrentProvider):  # pylint: disable=too-many-instance-attributes

    def __init__(self):

        # Provider Inits
        TorrentProvider.__init__(self, "LimeTorrents")

        # URLs
        self.urls = {
            'index': 'https://www.limetorrents.cc/',
            'search': 'https://www.limetorrents.cc/search/tv/',
            'rss': 'https://www.limetorrents.cc/browse-torrents/TV-shows/date/'
        }

        self.url = self.urls['index']

        # Credentials
        self.public = True
        self.confirmed = False

        # Torrent Stats
        self.minseed = None
        self.minleech = None
        
        # Proper Strings
        self.proper_strings = ['PROPER', 'REPACK', 'REAL']
        
        # Cache
        cache_params = {"RSS": ["1/", "2/", "3/"]}
        self.cache = tvcache.TVCache(self, search_params=cache_params)

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-branches,too-many-locals
        results = []
        for mode in search_strings:
            items = []
            logger.log(u"Search Mode: {0}".format(mode), logger.DEBUG)
            for search_string in search_strings[mode]:
                search_url = (self.urls['rss'], self.urls['search'] + search_string + '/')[mode != 'RSS']  # Needs a trailing '/' to avoid a triple redirect. 
                data = self.get_url(search_url, returns='text')
                if not data:
                        logger.log(u"No data returned from provider", logger.DEBUG)
                        continue
                with BS4Parser(data, "html5lib") as html:
                    if mode == 'RSS':
                        torrent_table = html.find("table", {"class":"table2"})
                    else:
                        torrent_table = (html.find_all("table", {"class":"table2"}))[1]
                    torrent_rows = torrent_table("tr")
                    for result in torrent_rows:
                        cells = result.find_all("td")
                        try:                          
                            verified = result.find_all('img', title='Verified torrent')
                            if self.confirmed and not verified:
                                continue
                            titleinfo = result.find_all("a")
                            info = titleinfo[1]['href']
                            torrent_id = id_regex.search(info).group(1)
                            url = result.find("a", {"rel":"nofollow"})['href']
                            torrent_hash = hash_regex.search(url).group(2)
                            infourl = self.urls['index'] + "post/updatestats.php?" + "torrent_id=" + torrent_id + "&infohash=" + torrent_hash
                            try:
                                self.session.get(infourl, timeout=0.1)
                            except (SocketTimeout, requests.exceptions.Timeout):
                                pass
                            title = titleinfo[1].get_text(strip=True)
                            seeders = try_int(cells[3].get_text(strip=True))
                            leechers = try_int(cells[4].get_text(strip=True))
                            size = convert_size(cells[2].get_text(strip=True)) or -1
                            download_url = "magnet:?xt=urn:btih:" + torrent_hash + "&dn=" + title + self._custom_trackers
                            
                            if seeders < self.minseed or leechers < self.minleech:
                                if mode != 'RSS':
                                    logger.log(u"Discarding torrent because it doesn't meet the minimum seeders or leechers: {0} (S:{1} L:{2})".format
                                            (title, seeders, leechers), logger.DEBUG)
                                continue
                                
                            item = {'title': title, 'link': download_url, 'size': size, 'seeders': seeders, 'leechers': leechers, 'hash': ''}
                            if mode != "RSS":
                                logger.log("Found result: {0} with {1} seeders and {2} leechers".format
                                           (title, seeders, leechers), logger.DEBUG)
                            items.append(item)
                            
                        except StandardError:
                            continue

            # For each search mode sort all the items by seeders if available
            items.sort(key=lambda d: try_int(d.get('seeders', 0)), reverse=True)
            results += items

        return results


provider = LimeTorrentsProvider()
