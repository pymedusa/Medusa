# coding=utf-8
# Orginal author: Dustyn Gibson <miigotu@gmail.com>
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
from requests.utils import dict_from_cookiejar

from sickbeard import logger, tvcache
from sickbeard.bs4_parser import BS4Parser

from sickrage.helper.common import convert_size, try_int
from sickrage.helper.exceptions import AuthException
from sickrage.providers.torrent.TorrentProvider import TorrentProvider


class HDTorrentsProvider(TorrentProvider):  # pylint: disable=too-many-instance-attributes
    """HDTorrents Torrent provider"""
    def __init__(self):

        # Provider Init
        TorrentProvider.__init__(self, 'HDTorrents')

        # Credentials
        self.username = None
        self.password = None

        # URLs
        self.url = 'https://hd-torrents.org/'
        self.urls = {
            'login': urljoin(self.url, 'login.php'),
            'search': urljoin(self.url, 'torrents.php'),
        }

        # Proper Strings
        self.proper_strings = ['PROPER', 'REPACK', 'REAL']

        # Miscellaneous Options
        self.freeleech = None

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tvcache.TVCache(self, min_time=30)

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-locals, too-many-branches
        """
        HDTorrents search and parsing

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
            'search': '',
            'active': 5 if self.freeleech else 1,
            'options': 0,
            'category[0]': 59,
            'category[1]': 60,
            'category[2]': 30,
            'category[3]': 38,
            'category[4]': 65,
        }

        for mode in search_strings:
            items = []
            logger.log('Search mode: {0}'.format(mode), logger.DEBUG)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    search_params['search'] = search_string
                    logger.log('Search string: {search}'.format
                               (search=search_string), logger.DEBUG)

                response = self.get_url(self.urls['search'], params=search_params, returns='response')
                if not response or not response.text:
                    logger.log('No data returned from provider', logger.DEBUG)
                    continue

                # Search result page contains some invalid html that prevents html parser from returning all data.
                # We cut everything before the table that contains the data we are interested in thus eliminating
                # the invalid html portions
                try:
                    index = response.text.index('<TABLE class="mainblockcontenttt"')
                except ValueError:
                    logger.log('Could not find table of torrents mainblockcontenttt', logger.DEBUG)
                    continue

                with BS4Parser(response.text[index:], 'html5lib') as html:
                    torrent_table = html.find('table', class_='mainblockcontenttt')
                    torrent_rows = torrent_table('tr') if torrent_table else []

                    if not torrent_rows or torrent_rows[2].find('td', class_='lista'):
                        logger.log('Data returned from provider does not contain any torrents', logger.DEBUG)
                        continue

                    # Cat., Active, Filename, Dl, Wl, Added, Size, Uploader, S, L, C
                    labels = [label.a.get_text(strip=True) if label.a else label.get_text(strip=True) for label in torrent_rows[0]('td')]

                    # Skip column headers
                    for result in torrent_rows[1:]:
                        try:
                            cells = result.findChildren('td')[:len(labels)]
                            if len(cells) < len(labels):
                                continue

                            title = cells[labels.index('Filename')].a
                            title = title.get_text(strip=True) if title else None
                            link = cells[labels.index('Dl')].a
                            link = link.get('href') if link else None
                            download_url = urljoin(self.url, link) if link else None
                            if not all([title, download_url]):
                                continue

                            seeders = try_int(cells[labels.index('S')].get_text(strip=True))
                            leechers = try_int(cells[labels.index('L')].get_text(strip=True))

                            # Filter unseeded torrent
                            if seeders < min(self.minseed, 1):
                                if mode != 'RSS':
                                    logger.log("Discarding torrent because it doesn't meet the "
                                               "minimum seeders: {0}. Seeders: {1}".format
                                               (title, seeders), logger.DEBUG)
                                continue

                            torrent_size = cells[labels.index('Size')].get_text()
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

    def login(self):
        if any(dict_from_cookiejar(self.session.cookies).values()):
            return True

        login_params = {
            'uid': self.username,
            'pwd': self.password,
            'submit': 'Confirm'
        }

        response = self.get_url(self.urls['login'], post_data=login_params, returns='text')
        if not response:
            logger.log('Unable to connect to provider', logger.WARNING)
            return False

        if re.search('You need cookies enabled to log in.', response):
            logger.log('Invalid username or password. Check your settings', logger.WARNING)
            return False

        return True

    def _check_auth(self):

        if not self.username or not self.password:
            raise AuthException('Your authentication credentials for {0} are missing,'
                                ' check your config.'.format(self.name))

        return True


provider = HDTorrentsProvider()
