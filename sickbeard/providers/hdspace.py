# coding=utf-8
# Author: Idan Gutman
# Modified by jkaberg, https://github.com/jkaberg for SceneAccess
# Modified by 7ca for HDSpace
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

from requests.utils import dict_from_cookiejar
from requests.compat import quote_plus

from sickbeard import logger, tvcache
from sickbeard.bs4_parser import BS4Parser

from sickrage.helper.common import convert_size, try_int
from sickrage.providers.torrent.TorrentProvider import TorrentProvider


class HDSpaceProvider(TorrentProvider):  # pylint: disable=too-many-instance-attributes
    """HDSpace Torrent provider"""
    def __init__(self):

        # Provider Init
        TorrentProvider.__init__(self, 'HDSpace')

        # Credentials
        self.username = None
        self.password = None

        # URLs
        self.url = 'https://hd-space.org'
        self.urls = {
            'base_url': self.url,
            'login': 'https://hd-space.org/index.php',
            'search': 'https://hd-space.org/index.php?page=torrents&search=%s&active=1&options=0',
            'rss': 'https://hd-space.org/rss_torrents.php?feed=dl',
        }

        # Proper Strings

        # Miscellaneous Options
        self.categories = [15, 21, 22, 24, 25, 40]  # HDTV/DOC 1080/720, bluray, remux
        self.urls['search'] += '&category='
        for cat in self.categories:
            self.urls['search'] += str(cat) + '%%3B'
            self.urls['rss'] += '&cat[]=' + str(cat)
        self.urls['search'] = self.urls['search'][:-4]  # remove extra %%3B

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tvcache.TVCache(self, min_time=10)  # only poll HDSpace every 10 minutes max

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-locals, too-many-branches
        """
        HDSpace search and parsing

        :param search_string: A dict with mode (key) and the search value (value)
        :param age: Not used
        :param ep_obj: Not used
        :returns: A list of search results (structure)
        """
        results = []
        if not self.login():
            return results

        for mode in search_strings:
            items = []
            logger.log('Search mode: {0}'.format(mode), logger.DEBUG)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    logger.log('Search string: {search}'.format
                               (search=search_string), logger.DEBUG)
                    search_url = self.urls['search'] % (quote_plus(search_string.replace('.', ' ')),)
                else:
                    search_url = self.urls['search'] % ''

                data = self.get_url(search_url, returns='text')
                if not data or 'please try later' in data:
                    logger.log('No data returned from provider', logger.DEBUG)
                    continue

                # Search result page contains some invalid html that prevents html parser from returning all data.
                # We cut everything before the table that contains the data we are interested in thus eliminating
                # the invalid html portions
                try:
                    data = data.split('<div id="information"></div>')[1]
                    index = data.index('<table')
                except ValueError:
                    logger.log('Could not find main torrent table', logger.ERROR)
                    continue

                with BS4Parser(data[index:], 'html5lib') as html:
                    if not html:
                        logger.log('No html data parsed from provider', logger.DEBUG)
                        continue

                    torrents = html('tr')
                    if not torrents:
                        continue

                    # Skip column headers
                    for result in torrents[1:]:
                        if len(result.contents) < 10:
                            # skip extraneous rows at the end
                            continue

                        try:
                            dl_href = result.find('a', attrs={'href': re.compile(r'download.php.*')})['href']
                            title = re.search('f=(.*).torrent', dl_href).group(1).replace('+', '.')
                            download_url = self.urls['base_url'] + dl_href
                            if not all([title, download_url]):
                                continue

                            seeders = int(result.find('span', attrs={'class': 'seedy'}).find('a').text)
                            leechers = int(result.find('span', attrs={'class': 'leechy'}).find('a').text)

                            # Filter unseeded torrent
                            if seeders < min(self.minseed, 1):
                                if mode != 'RSS':
                                    logger.log("Discarding torrent because it doesn't meet the "
                                               "minimum seeders: {0}. Seeders: {1}".format
                                               (title, seeders), logger.DEBUG)
                                continue

                            torrent_size = re.match(r'.*?([0-9]+,?\.?[0-9]* [KkMmGg]+[Bb]+).*', str(result), re.DOTALL).group(1)
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

        if 'pass' in dict_from_cookiejar(self.session.cookies):
            return True

        login_params = {
            'uid': self.username,
            'pwd': self.password,
            'page': 'login',
        }

        response = self.get_url(self.urls['login'], post_data=login_params, returns='text')
        if not response:
            logger.log('Unable to connect to provider', logger.WARNING)
            return False

        if re.search('Password Incorrect', response):
            logger.log('Invalid username or password. Check your settings', logger.WARNING)
            return False

        return True

    def _check_auth(self):

        if not self.username or not self.password:
            logger.log('Invalid username or password. Check your settings', logger.WARNING)

        return True


provider = HDSpaceProvider()
