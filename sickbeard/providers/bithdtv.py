# coding=utf-8
# Author: p0psicles
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

import re
from requests.utils import dict_from_cookiejar

from sickbeard import logger, tvcache
from sickbeard.bs4_parser import BS4Parser

from sickrage.helper.common import convert_size, try_int
from sickrage.providers.torrent.TorrentProvider import TorrentProvider


class BithdtvProvider(TorrentProvider):  # pylint: disable=too-many-instance-attributes

    def __init__(self):

        # Provider Init
        TorrentProvider.__init__(self, "BITHDTV")

        # Credentials
        self.username = None
        self.password = None

        # Torrent Stats
        self.minseed = 0
        self.minleech = 0
        self.freeleech = True

        # URLs
        self.url = 'https://www.bit-hdtv.com/'
        self.urls = {
            'login': self.url + 'takelogin.php',
            'search': self.url + 'torrents.php',
        }
        # Proper Strings

        # Cache
        self.cache = tvcache.TVCache(self, min_time=10)  # Only poll BitHDTV every 10 minutes max

    def login(self):
        if any(dict_from_cookiejar(self.session.cookies).values()):
            return True

        login_params = {
            'username': self.username.encode('utf-8'),
            'password': self.password.encode('utf-8'),
        }

        response = self.get_url(self.urls['login'], post_data=login_params, returns='text')
        if not response:
            logger.log(u"Unable to connect to provider", logger.WARNING)
            self.session.cookies.clear()
            return False

        if '<h2>Login failed!</h2>' in response:
            logger.log(u"Invalid username or password. Check your settings", logger.WARNING)
            self.session.cookies.clear()
            return False

        return True

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-locals, too-many-branches
        results = []
        if not self.login():
            return results

        # Search Params
        search_params = {'cat': '12'} if 'Season' in search_strings else {'cat': '10'}

        # Units
        units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']

        for mode in search_strings:
            items = []
            logger.log(u"Search Mode: {}".format(mode), logger.DEBUG)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    logger.log(u"Search string: {}".format(search_string.decode("utf-8")),
                               logger.DEBUG)

                    search_params['search'] = search_string

                search_params['cat'] = '12' if mode == 'Season' else '10'

                data = self.get_url(self.urls['search'], params=search_params, returns='text')
                if not data:
                    logger.log(u"No data returned from provider", logger.DEBUG)
                    continue

                with BS4Parser(data, 'html.parser') as html:
                    torrent_table = html.find('table', width='750')
                    torrent_rows = torrent_table('tr') if torrent_table else []

                    # Continue only if at least one Release is found
                    if len(torrent_rows) < 2:
                        logger.log(u"Data returned from provider does not contain any torrents", logger.DEBUG)
                        continue

                    # Skip column headers
                    for result in torrent_rows[1:]:

                        try:
                            cells = result.find_all('td')
                            title = cells[2].find('a')['title']
                            download_url = result.find_all('td')[0].find('a')['href']
                            if not all([title, download_url]):
                                continue

                            seeders = try_int(cells[8].get_text(strip=True))
                            leechers = try_int(cells[9].get_text(strip=True))

                            # Filter unseeded torrent
                            if seeders < min(self.minseed, 1):
                                if mode != 'RSS':
                                    logger.log(u"Discarding torrent because it doesn't meet the"
                                               u" minimum seeders: {0}. Seeders: {1})".format
                                               (title, seeders), logger.DEBUG)
                                continue

                            freeleech = bool(result.get('bgcolor'))
                            if self.freeleech and not freeleech:
                                continue

                            torrent_size = '{size} {unit}'.format(size=cells[6].contents[0], unit=cells[6].contents[1].get_text())

                            size = convert_size(torrent_size, units=units) or -1

                            item = {'title': title, 'link': download_url, 'size': size, 'seeders': seeders, 'leechers': leechers, 'pubdate': None, 'hash': None}
                            if mode != 'RSS':
                                logger.log(u"Found result: {0} with {1} seeders and {2} leechers".format
                                           (title, seeders, leechers), logger.DEBUG)

                            items.append(item)
                        except StandardError:
                            continue

            # For each search mode sort all the items by seeders if available
            items.sort(key=lambda d: try_int(d.get('seeders', 0)), reverse=True)
            results += items

        return results

provider = BithdtvProvider()
