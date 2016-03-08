# coding=utf-8
# Author: raver2046 <raver2046@gmail.com>
#

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
import traceback

from sickbeard import logger, tvcache
from sickbeard.bs4_parser import BS4Parser

from sickrage.providers.auth import CookieAuth
from sickrage.providers.torrent.TorrentProvider import TorrentProvider


class BlueTigersProvider(TorrentProvider):  # pylint: disable=too-many-instance-attributes

    def __init__(self):

        # Provider Init
        TorrentProvider.__init__(self, "BLUETIGERS")

        # Torrent Stats
        self.ratio = None
        self.token = None

        # URLs
        self.url = 'https://www.bluetigers.ca/'
        self.urls = {
            'base_url': self.url,
            'login': urljoin(self.url, 'account-login.php'),
            'search': urljoin(self.url, 'torrents-search.php'),
            'download': urljoin(self.url, 'torrents-details.php?id=%s&hit=1'),
        }

        # Proper Strings

        # Cache
        self.cache = tvcache.TVCache(self, min_time=10)  # Only poll BLUETIGERS every 10 minutes max

        # Authentication
        self.login_params = {
            'username': None,
            'password': None,
            'take_login': '1'
        }
        self.session.auth = CookieAuth(self.session, self.urls['login'], self.login_params)

        # Miscellaneous
        self.search_params = {
            "c16": 1, "c10": 1, "c130": 1, "c131": 1, "c17": 1, "c18": 1, "c19": 1
        }

    @property
    def username(self):
        return self.login_params['username']

    @username.setter
    def username(self, value):
        self.login_params['username'] = value
        self.session.auth.payload.update(self.login_params)

    @property
    def password(self):
        return self.login_params['password']

    @password.setter
    def password(self, value):
        self.login_params['password'] = value
        self.session.auth.payload.update(self.login_params)

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-locals
        results = []

        for mode in search_strings:
            items = []
            logger.log(u"Search Mode: {}".format(mode), logger.DEBUG)
            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    logger.log(u"Search string: {}".format(search_string.decode("utf-8")),
                               logger.DEBUG)

                self.search_params['search'] = search_string

                data = self.get_url(self.urls['search'], params=self.search_params)
                if not data:
                    continue

                try:
                    with BS4Parser(data, 'html5lib') as html:
                        result_linkz = html.findAll('a', href=re.compile("torrents-details"))

                        if not result_linkz:
                            logger.log(u"Data returned from provider do not contains any torrent", logger.DEBUG)
                            continue

                        if result_linkz:
                            for link in result_linkz:
                                title = link.text
                                download_url = self.urls['base_url'] + link['href']
                                download_url = download_url.replace("torrents-details", "download")
                                # FIXME
                                size = -1
                                seeders = 1
                                leechers = 0

                                if not title or not download_url:
                                    continue

                                # Filter unseeded torrent
                                # if seeders < self.minseed or leechers < self.minleech:
                                #    if mode != 'RSS':
                                #        logger.log(u"Discarding torrent because it doesn't meet the minimum seeders or leechers: {} (S:{} L:{})".format
                                #                   (title, seeders, leechers), logger.DEBUG)
                                #    continue

                                item = title, download_url, size, seeders, leechers
                                if mode != 'RSS':
                                    logger.log(u"Found result: %s " % title, logger.DEBUG)

                                items.append(item)

                except Exception:
                    logger.log(u"Failed parsing provider. Traceback: %s" % traceback.format_exc(), logger.ERROR)

            # For each search mode sort all the items by seeders if available
            items.sort(key=lambda tup: tup[3], reverse=True)

            results += items

        return results

    def seed_ratio(self):
        return self.ratio

provider = BlueTigersProvider()
