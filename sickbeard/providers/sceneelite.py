# coding=utf-8
# Author: Gonçalo M. (aka duramato/supergonkas) <supergonkas@gmail.com>
#
# URL: https://sickrage.github.io
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

from requests.compat import urljoin
from requests.utils import dict_from_cookiejar

from sickbeard import logger, tvcache
from sickbeard.bs4_parser import BS4Parser

from sickrage.helper.common import convert_size, try_int
from sickrage.providers.torrent.TorrentProvider import TorrentProvider


class SceneEliteProvider(TorrentProvider):  # pylint: disable=too-many-instance-attributes

    def __init__(self):

        # Provider Init
        TorrentProvider.__init__(self, "SceneElite")

        # Credentials
        self.username = None
        self.password = None

        # Torrent Stats
        self.minseed = None
        self.minleech = None
        self.freeleech = None

        # URLs
        self.url = "https://sceneelite.org/"
        self.urls = {
            "login": urljoin(self.url, "/api/v1/auth"),
            "search": urljoin(self.url, "/api/v1/torrents"),
            "download": urljoin(self.url, "/api/v1/torrents/download/"),
        }

        # Proper Strings
        self.proper_strings = ["PROPER", "REPACK", "REAL"]
        cache_params = {"RSS": [""]}
        # Cache
        self.cache = tvcache.TVCache(self, min_time=0.1, search_params=cache_params)

    def login(self):
        if any(dict_from_cookiejar(self.session.cookies).values()):
            return True

        login_params = {
            "username": self.username,
            "password": self.password
        }

        response = self.get_url(self.urls["login"], params=login_params, returns="json")
        if not response:
            logger.log("Unable to connect to provider", logger.WARNING)
            return False
        return True

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-locals, too-many-branches
        results = []
        if not self.login():
            return results

        # Search Params
        search_params = {
            "extendedSearch": 'false',
            "hideOld": 'false',
            "index": '0',
            "limit": '100',
            "order": 'asc',
            "page": 'search',
            "sort": 'n',
            "categories[0]": 3,
            "categories[1]": 6,
            "categories[2]": 7
        }

        for mode in search_strings:
            items = []
            logger.log("Search Mode: {0}".format(mode), logger.DEBUG)

            for search_string in search_strings[mode]:
                if mode != "RSS":
                    logger.log("Search string: {0}".format
                               (search_string.decode("utf-8")), logger.DEBUG)
                    search_params["searchText"] = search_string
                else: 
                    search_params["page"] = 'last_seriebrowse'
                results = []
                search_url = self.urls["search"]
                try:
                    jdata = self.get_url(search_url, params=search_params, returns="json") 
                except ValueError:
                    logger.log("No data returned from provider", logger.DEBUG)
                    continue
                for torrent in jdata:
                    try:
                        title = torrent.pop("name", "")
                        id = str(torrent.pop("id", ""))
                        if not id:
                            continue
                        seeders = try_int(torrent.pop("seeders", ""), 1)
                        leechers = try_int(torrent.pop("leechers", ""), 0)
                        freeleech = torrent.pop("frileech")
                        if self.freeleech and freeleech != 1:
                            continue
                        size = try_int(torrent.pop("size", ""), 0)
                        download_url = self.urls["download"] + id
                        if seeders < min(self.minseed, 1):
                            if mode != 'RSS':
                                logger.log(u"Torrent doesn't meet minimum seeds & leechers not selecting : {0}".format(title), logger.DEBUG)
                            continue
                        item = {'title': title, 'link': download_url, 'size': size, 'seeders': seeders, 'leechers': leechers, 'hash': None}
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


provider = SceneEliteProvider()
