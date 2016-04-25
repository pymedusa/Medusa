# coding=utf-8
# Author: Jodi Jones <venom@gen-x.co.nz>
# Rewrite: Gonçalo M. (aka duramato/supergonkas) <supergonkas@gmail.com>

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

import validators

from sickbeard import logger, tvcache

from sickrage.helper.common import convert_size
from sickrage.providers.torrent.TorrentProvider import TorrentProvider


class BTDiggProvider(TorrentProvider):

    def __init__(self):
        
        # Provider Init
        TorrentProvider.__init__(self, "BTDigg")

        self.public = True
        
         # Torrent Stats
        self.minseed = None
        self.minleech = None

        # URLs
        self.url = "https://btdigg.org"
        self.urls = {"api": "https://api.btdigg.org/api/private-341ada3245790954/s02"}
        self.custom_url = None
        
        # Proper Strings
        self.proper_strings = ["PROPER", "REPACK"]

        # Use this hacky way for RSS search since most results will use this codecs
        cache_params = {"RSS": ["x264", "x264.HDTV", "720.HDTV.x264"]}

        # Only poll BTDigg every 30 minutes max, since BTDigg takes some time to crawl
        self.cache = tvcache.TVCache(self, min_time=30, search_params=cache_params)

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-locals
        results = []
        search_params = {"p": 0}
        for mode in search_strings:
            items = []
            logger.log("Search Mode: {}".format(mode), logger.DEBUG)
            for search_string in search_strings[mode]:
                search_params["q"] = search_string
                if mode != "RSS":
                    search_params["order"] = 0
                    logger.log("Search string: {}".format(search_string.decode("utf-8")),
                               logger.DEBUG)
                else:
                    search_params["order"] = 2
                if self.custom_url:
                    # if not validators.url(self.custom_url):
                        # logger.log("Invalid custom url set, please check your settings", logger.WARNING)
                        # return results
                    search_url = self.custom_url + "api/private-341ada3245790954/s02"
                else:
                    search_url = self.urls["api"]
                jdata = self.get_url(search_url, params=search_params, returns="json")
                if not jdata:
                    logger.log("Provider did not return data", logger.DEBUG)
                    continue

                for torrent in jdata:
                    try:
                        title = torrent.pop("name", "")
                        download_url = torrent.pop("magnet") + self._custom_trackers if torrent["magnet"] else None
                        if not all([title, download_url]):
                            continue

                        if float(torrent.pop("ff")):
                            logger.log("Ignoring result for {} since it's been reported as fake (level = {})".format
                                       (title, torrent["ff"]), logger.DEBUG)
                            continue

                        if not int(torrent.pop("files")):
                            logger.log("Ignoring result for {} because it has no files".format
                                       (title), logger.DEBUG)
                            continue
                        leechers = torrent.pop("leechers", 0)
                        seeders = torrent.pop("seeders", 1)

                        # Filter unseeded torrent
                        if seeders < min(self.minseed, 1):
                            if mode != "RSS":
                                logger.log("Discarding torrent because it doesn't meet the"
                                           " minimum seeders or leechers: {0} (S:{1} L:{2})".format
                                           (title, seeders, leechers), logger.DEBUG)
                                continue                        
                        torrent_size = torrent.pop("size")
                        size = convert_size(torrent_size) or -1

                        item = {'title': title, 'link': download_url, 'size': size, 'seeders': seeders, 'leechers': leechers, 'hash': None}
                        if mode != "RSS":
                            logger.log("Found result: %s " % title, logger.DEBUG)

                        items.append(item)

                    except StandardError:
                        continue

            results += items

        return results


provider = BTDiggProvider()
