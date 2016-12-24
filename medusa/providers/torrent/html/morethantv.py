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
"""Provider code for MoreThanTV."""
from __future__ import unicode_literals

import re
import time
import traceback

from dateutil import parser

from requests.compat import urljoin
from requests.utils import dict_from_cookiejar

from six.moves.urllib_parse import parse_qs

from ..torrent_provider import TorrentProvider
from .... import logger, tv_cache
from ....bs4_parser import BS4Parser
from ....helper.common import convert_size, try_int
from ....helper.exceptions import AuthException


class MoreThanTVProvider(TorrentProvider):
    """MoreThanTV Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(self.__class__, self).__init__('MoreThanTV')

        # Credentials
        self.username = None
        self.password = None
        self._uid = None
        self._hash = None

        # URLs
        self.url = 'https://www.morethan.tv/'
        self.urls = {
            'login': urljoin(self.url, 'login.php'),
            'search': urljoin(self.url, 'torrents.php'),
        }

        # Proper Strings
        self.proper_strings = ['PROPER', 'REPACK']

        # Miscellaneous Options

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tv_cache.TVCache(self)

    def search(self, search_strings, age=0, ep_obj=None):
        """Search a provider and parse the results.

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
            'tags_type': 1,
            'order_by': 'time',
            'order_way': 'desc',
            'action': 'basic',
            'group_results': 0,
            'searchsubmit': 1,
            'searchstr': '',
        }

        for mode in search_strings:
            logger.log('Search mode: {0}'.format(mode), logger.DEBUG)

            if mode == 'Season':
                additional_strings = []
                for search_string in search_strings[mode]:
                    additional_strings.append(re.sub(r'(.*)S0?', r'\1Season ', search_string))
                search_strings[mode].extend(additional_strings)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    logger.log('Search string: {search}'.format
                               (search=search_string), logger.DEBUG)

                search_params['searchstr'] = search_string

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
        def process_column_header(td):
            result = ''
            if td.a and td.a.img:
                result = td.a.img.get('title', td.a.get_text(strip=True))
            if not result:
                result = td.get_text(strip=True)
            return result

        items = []

        with BS4Parser(data, 'html5lib') as html:
            torrent_table = html.find('table', class_='torrent_table')
            torrent_rows = torrent_table('tr') if torrent_table else []

            # Continue only if at least one release is found
            if len(torrent_rows) < 2:
                logger.log('Data returned from provider does not contain any torrents', logger.DEBUG)
                return items

            labels = [process_column_header(label) for label in torrent_rows[0]('td')]

            # Skip column headers
            for row in torrent_rows[1:]:
                cells = row('td')
                if len(cells) < len(labels):
                    continue

                try:
                    # Skip if torrent has been nuked due to poor quality
                    if row.find('img', alt='Nuked'):
                        continue

                    title = row.find('a', title='View torrent').get_text(strip=True)
                    download_url = urljoin(self.url, row.find('span', title='Download').parent['href'])
                    if not all([title, download_url]):
                        continue

                    seeders = try_int(cells[labels.index('Seeders')].get_text(strip=True), 1)
                    leechers = try_int(cells[labels.index('Leechers')].get_text(strip=True))

                    # Filter unseeded torrent
                    if seeders < min(self.minseed, 1):
                        if mode != 'RSS':
                            logger.log("Discarding torrent because it doesn't meet the "
                                       "minimum seeders: {0}. Seeders: {1}".format
                                       (title, seeders), logger.DEBUG)
                        continue

                    # If it's a season search, query the torrent's detail page.
                    if mode == 'Season':
                        title = self._parse_season(row, download_url, title)

                    torrent_size = cells[labels.index('Size')].get_text(strip=True)
                    size = convert_size(torrent_size) or -1
                    pubdate_raw = cells[labels.index('Time')].find('span')['title']
                    pubdate = parser.parse(pubdate_raw, fuzzy=True) if pubdate_raw else None

                    item = {
                        'title': title,
                        'link': download_url,
                        'size': size,
                        'seeders': seeders,
                        'leechers': leechers,
                        'pubdate': pubdate,
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
            'username': self.username,
            'password': self.password,
            'keeplogged': '1',
            'login': 'Log in',
        }

        response = self.get_url(self.urls['login'], post_data=login_params, returns='response')
        if not response or not response.text:
            logger.log('Unable to connect to provider', logger.WARNING)
            return False

        if re.search('Your username or password was incorrect.', response.text):
            logger.log('Invalid username or password. Check your settings', logger.WARNING)
            return False

        return True

    def _check_auth(self):

        if not self.username or not self.password:
            raise AuthException('Your authentication credentials for {0} are missing,'
                                ' check your config.'.format(self.name))

        return True

    def _parse_season(self, row, download_url, title):
        """Parse the torrent's detail page and return the season pack title."""
        details_url = row.find('span').find_next(title='View torrent').get('href')
        torrent_id = parse_qs(download_url).get('id')
        if not all([details_url, torrent_id]):
            logger.log("Could't parse season pack details page for title: {0}".format(title), logger.DEBUG)
            return title

        # Take a break before querying the provider again
        time.sleep(0.5)
        response = self.get_url(urljoin(self.url, details_url), returns='response')
        if not response or not response.text:
            logger.log("Could't open season pack details page for title: {0}".format(title), logger.DEBUG)
            return title

        with BS4Parser(response.text, 'html5lib') as html:
            torrent_table = html.find('table', class_='torrent_table')
            torrent_row = torrent_table.find('tr', id='torrent_{0}'.format(torrent_id[0]))
            if not torrent_row:
                logger.log("Could't find season pack details for title: {0}".format(title), logger.DEBUG)
                return title

            # Strip leading and trailing slash
            season_title = torrent_row.find('div', class_='filelist_path')
            if not season_title or not season_title.get_text():
                logger.log("Could't parse season pack title for: {0}".format(title), logger.DEBUG)
                return title
            return season_title.get_text(strip=True).strip('/')


provider = MoreThanTVProvider()
