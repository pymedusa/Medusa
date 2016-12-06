# coding=utf-8
# Author: duramato
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
"""Provider code for SDBits."""
from __future__ import unicode_literals

import re
import datetime
import traceback
from pytimeparse import parse
from requests.compat import urljoin
from requests.utils import dict_from_cookiejar
from ..torrent_provider import TorrentProvider
from .... import logger, tv_cache
from ....bs4_parser import BS4Parser
from ....helper.common import convert_size, try_int
from ....indexers.indexer_config import mappings


class SDBitsProvider(TorrentProvider):
    """SDBits Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(self.__class__, self).__init__('SDBits')

        # Credentials
        self.username = None
        self.password = None

        # URLs
        self.url = 'http://sdbits.org/'
        self.urls = {
            'login': urljoin(self.url, 'takeloginn3.php'),
            'search': urljoin(self.url, 'browse.php'),
        }

        # Proper Strings
        self.proper_strings = ['']

        # Miscellaneous Options

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tv_cache.TVCache(self, min_time=30)

    def search(self, search_strings, age=0, ep_obj=None):
        """
        Search a provider and parse the results.

        :param search_strings: A dict with mode (key) and the search value (value)
        :param age: Not used
        :param ep_obj: Not used
        :returns: A list of search results (structure)
        """
        results = []
        if not self.login():
            return results

        # Search Params
        search_params = {
            'incldead': 0,
            'descriptions': 0,
            'from': '',
            'imdbgt': 0,
            'imdblt': 10,
            'imdb': '',
            'search': '',
        }
        for mode in search_strings:
            logger.log('Search mode: {0}'.format(mode), logger.DEBUG)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    imdb_id = self.show.externals.get(mappings[10])
                    if imdb_id:
                        search_params['imdb'] = imdb_id
                        logger.log('Search string (imdb id): {imdb_id}'.format(imdb_id=imdb_id), logger.DEBUG)
                    else:
                        search_params['search'] = search_string
                        logger.log('Search string: {search}'.format(search=search_string), logger.DEBUG)
                        
                response = self.get_url(self.urls['search'], params=search_params, returns='response')
                if not response or not response.text:
                    logger.log('No data returned from provider', logger.DEBUG)
                    continue

                results += self.parse(response.text, mode)

        return results

    def parse(self, data, mode):
        """
        Parse search results for items.

        :param data: The raw response from a search
        :param mode: The current mode used to search, e.g. RSS

        :return: A list of items found
        """
        # Units
        units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']

        items = []

        with BS4Parser(data, 'html5lib') as html:
            torrent_table = html.find('table', id='torrent-list')
            torrent_rows = torrent_table('tr') if torrent_table else []

            # Continue only if at least one release is found
            if len(torrent_rows) < 2:
                logger.log('Data returned from provider does not contain any torrents', logger.DEBUG)
                return items

            # Skip column headers
            for row in torrent_rows[1:]:
                cells = row('td')

                try:
                    title = cells[2].findAll('a')[0].get_text()
                    download = cells[2].findAll('a')[1]['href']
                    download_url = urljoin(self.url, download)
                    if not all([title, download_url]):
                        continue

                    seeders = try_int(cells[7].get_text(strip=True))
                    leechers = try_int(cells[8].get_text(strip=True))

                    # Filter unseeded torrent
                    if seeders < min(self.minseed, 1):
                        if mode != 'RSS':
                            logger.log("Discarding torrent because it doesn't meet the "
                                       "minimum seeders: {0}. Seeders: {1}".format
                                       (title, seeders), logger.DEBUG)
                        continue

                    torrent_size = cells[5].get_text(" ")
                    size = convert_size(torrent_size, units=units) or -1
                    pubdate_raw = cells[4].get_text("_").split("_")
                    if len(pubdate_raw) == 2:
                        pubdate_raw = parse(pubdate_raw[0]) + parse(pubdate_raw[1])
                    else:
                        pubdate_raw = parse(pubdate_raw[0])
                    pubdate = str(datetime.datetime.now() - datetime.timedelta(seconds=pubdate_raw)) if pubdate_raw else None
                    item = {
                        'title': title,
                        'link': download_url,
                        'size': size,
                        'seeders': seeders,
                        'leechers': leechers,
                        'pubdate': pubdate,
                        'torrent_hash': None,
                    }
                    if mode != 'RSS':
                        logger.log('Found result: {0} with {1} seeders and {2} leechers'.format
                                   (title, seeders, leechers), logger.DEBUG)

                    items.append(item)
                except (AttributeError, TypeError, KeyError, ValueError, IndexError):
                    logger.log('Failed parsing provider. Traceback: {0!r}'.format
                               (traceback.format_exc()), logger.ERROR)

        return items

    def login(self):
        """Login method used for logging in before doing search and torrent downloads."""
        if any(dict_from_cookiejar(self.session.cookies).values()):
            return True

        login_params = {
            'uname': self.username,
            'password': self.password,
            'Log in!': 'submit',
            'returnto': '/',
        }

        response = self.get_url(self.urls['login'], post_data=login_params, returns='response')
        if not response or not response.text:
            logger.log('Unable to connect to provider', logger.WARNING)
            return False
        if re.search('Username or password incorrect.', response.text):
            logger.log('Invalid username or password. Check your settings', logger.WARNING)
            return False
        return True


provider = SDBitsProvider()
