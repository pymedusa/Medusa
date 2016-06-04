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

from __future__ import unicode_literals

from requests.compat import urljoin
from requests.utils import dict_from_cookiejar

from sickbeard import logger, tvcache
from sickbeard.bs4_parser import BS4Parser

from sickrage.helper.common import convert_size, try_int
from sickrage.providers.torrent.TorrentProvider import TorrentProvider


class BithdtvProvider(TorrentProvider):  # pylint: disable=too-many-instance-attributes
    """BIT-HDTV Torrent provider"""
    def __init__(self):

        # Provider Init
        TorrentProvider.__init__(self, 'BITHDTV')

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
            'login': urljoin(self.url, 'takelogin.php'),
            'search': urljoin(self.url, 'torrents.php'),
        }

        # Proper Strings

        # Cache
        self.cache = tvcache.TVCache(self, min_time=10)  # Only poll BitHDTV every 10 minutes max

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-locals, too-many-branches
        """
        BIT HDTV search and parsing

        :param search_string: A dict with mode (key) and the search value (value)
        :param age: Not used
        :param ep_obj: Not used
        :returns: A list of search results (structure)
        """
        results = []
        if not self.login():
            return results

        # Search Params
        search_params = {
            'cat': 10,
        }

        # Units
        units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']

        for mode in search_strings:
            items = []
            logger.log('Search mode: {0}'.format(mode), logger.DEBUG)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    search_params['search'] = search_string

                if mode == 'Season':
                    search_params['cat'] = 12

                response = self.get_url(self.urls['search'], params=search_params, returns='response')
                if not response.text:
                    logger.log('No data returned from provider', logger.DEBUG)
                    continue

                # Need the html.parser, as the html5parser has issues with this site.
                with BS4Parser(response.text, 'html.parser') as html:
                    torrent_table = html('table', width='750')[-1]  # Get the last table with a width of 750px.
                    torrent_rows = torrent_table('tr') if torrent_table else []

                    # Continue only if at least one Release is found
                    if len(torrent_rows) < 2:
                        logger.log('Data returned from provider does not contain any torrents', logger.DEBUG)
                        continue

                    # Skip column headers
                    for result in torrent_rows[1:]:
                        freeleech = result.get('bgcolor')
                        if self.freeleech and not freeleech:
                            continue

                        try:
                            cells = result('td')

                            title = cells[2].find('a')['title']
                            download_url = urljoin(self.url, cells[0].find('a')['href'])
                            if not all([title, download_url]):
                                continue

                            seeders = try_int(cells[8].get_text(strip=True))
                            leechers = try_int(cells[9].get_text(strip=True))

                            # Filter unseeded torrent
                            if seeders < min(self.minseed, 1):
                                if mode != 'RSS':
                                    logger.log('Discarding torrent because it doesn\'t meet the'
                                               ' minimum seeders: {0}. Seeders: {1})'.format
                                               (title, seeders), logger.DEBUG)
                                continue

                            torrent_size = '{size} {unit}'.format(size=cells[6].contents[0], unit=cells[6].contents[1].get_text())

                            size = convert_size(torrent_size, units=units) or -1

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
                        except StandardError:
                            continue

            # For each search mode sort all the items by seeders if available
            items.sort(key=lambda d: try_int(d.get('seeders', 0)), reverse=True)
            results += items

        return results

    def login(self):
        """Login method used for logging in before doing search and torrent downloads"""
        if any(dict_from_cookiejar(self.session.cookies).values()):
            return True

        login_params = {
            'username': self.username.encode('utf-8'),
            'password': self.password.encode('utf-8'),
        }

        response = self.get_url(self.urls['login'], post_data=login_params, returns='text')
        if not response:
            logger.log(u'Unable to connect to provider', logger.WARNING)
            self.session.cookies.clear()
            return False

        if '<h2>Login failed!</h2>' in response:
            logger.log(u'Invalid username or password. Check your settings', logger.WARNING)
            self.session.cookies.clear()
            return False

        return True


provider = BithdtvProvider()
