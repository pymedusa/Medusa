# coding=utf-8
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

import traceback

from requests.utils import dict_from_cookiejar

from sickbeard import logger, tvcache
from sickbeard.bs4_parser import BS4Parser

from sickrage.helper.common import convert_size, try_int
from sickrage.providers.torrent.TorrentProvider import TorrentProvider


class DanishbitsProvider(TorrentProvider):  # pylint: disable=too-many-instance-attributes

    def __init__(self):

        # Provider Init
        TorrentProvider.__init__(self, 'Danishbits')

        # Credentials
        self.username = None
        self.password = None

        # Torrent Stats
        self.minseed = 0
        self.minleech = 0
        self.freeleech = True

        # URLs
        self.url = 'https://danishbits.org/'
        self.urls = {
            'login': self.url + 'login.php',
            'search': self.url + 'torrents.php',
        }

        # Proper Strings

        # Cache
        self.cache = tvcache.TVCache(self, min_time=10)  # Only poll Danishbits every 10 minutes max

    def login(self):
        if any(dict_from_cookiejar(self.session.cookies).values()):
            return True

        login_params = {
            'username': self.username.encode('utf-8'),
            'password': self.password.encode('utf-8'),
            'keeplogged': 1,
            'langlang': '',
            'login': 'Login',
        }

        response = self.get_url(self.urls['login'], post_data=login_params, returns='text')
        if not response:
            logger.log('Unable to connect to provider', logger.WARNING)
            self.session.cookies.clear()
            return False

        if '<title>Login :: Danishbits.org</title>' in response:
            logger.log('Invalid username or password. Check your settings', logger.WARNING)
            self.session.cookies.clear()
            return False

        return True

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-locals, too-many-branches
        results = []
        if not self.login():
            return results

        # Search Params
        search_params = {
            'action': 'newbrowse',
            'group': 3,
            'search': '',
        }

        # Units
        units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']

        def process_column_header(td):
            result = ''
            if td.img:
                result = td.img.get('title')
            if not result:
                result = td.get_text(strip=True)
            return result.encode('utf-8')

        for mode in search_strings:
            items = []
            logger.log('Search Mode: {0}'.format(mode), logger.DEBUG)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    logger.log('Search string: {0}'.format(search_string),
                               logger.DEBUG)

                search_params['search'] = search_string

                data = self.get_url(self.urls['search'], params=search_params, returns='text')
                if not data:
                    logger.log('No data returned from provider', logger.DEBUG)
                    continue

                with BS4Parser(data, 'html5lib') as html:
                    torrent_table = html.find('table', id='torrent_table')
                    torrent_rows = torrent_table('tr') if torrent_table else []

                    # Continue only if at least one release is found
                    if len(torrent_rows) < 2:
                        logger.log('Data returned from provider does not contain any torrents', logger.DEBUG)
                        continue

                    # Literal:     Navn, Størrelse, Kommentarer, Tilføjet, Snatches, Seeders, Leechers
                    # Translation: Name, Size,      Comments,    Added,    Snatches, Seeders, Leechers
                    labels = [process_column_header(label) for label in torrent_rows[0]('td')]

                    # Skip column headers
                    for result in torrent_rows[1:]:

                        try:
                            title = result.find(class_='croptorrenttext').get_text(strip=True)
                            download_url = self.url + result.find(title='Direkte download link')['href']
                            if not all([title, download_url]):
                                continue

                            cells = result('td')

                            seeders = try_int(cells[labels.index('Seeders')].get_text(strip=True))
                            leechers = try_int(cells[labels.index('Leechers')].get_text(strip=True))

                            # Filter unseeded torrent
                            if seeders < min(self.minseed, 1):
                                if mode != 'RSS':
                                    logger.log("Discarding torrent because it doesn't meet the"
                                               ' minimum seeders: {0}. Seeders: {1})'.format
                                               (title, seeders), logger.DEBUG)
                                continue

                            freeleech = result.find(class_='freeleech')
                            if self.freeleech and not freeleech:
                                continue

                            torrent_size = cells[labels.index('Størrelse')].contents[0]
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
                        except (AttributeError, TypeError, KeyError, ValueError, IndexError):
                            logger.log('Failed parsing provider. Traceback: {0!r}'.format
                                       (traceback.format_exc()), logger.ERROR)
                            continue

            results += items

        return results


provider = DanishbitsProvider()
