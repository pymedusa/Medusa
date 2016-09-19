# coding=utf-8
# Author: seedboy
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
from ..TorrentProvider import TorrentProvider
from .... import logger, tvcache
from ....bs4_parser import BS4Parser
from ....helper.common import convert_size
from ....helper.exceptions import AuthException


class IPTorrentsProvider(TorrentProvider):  # pylint: disable=too-many-instance-attributes
    """IPTorrents Torrent provider"""
    def __init__(self):

        # Provider Init
        TorrentProvider.__init__(self, 'IPTorrents')

        # Credentials
        self.username = None
        self.password = None

        # URLs
        self.url = 'https://iptorrents.eu'
        self.urls = {
            'base_url': self.url,
            'login': urljoin(self.url, 'torrents'),
            'search': urljoin(self.url, 't?%s%s&q=%s&qf=#torrents'),
        }

        # Proper Strings

        # Miscellaneous Options
        self.freeleech = False
        self.categories = '73=&60='

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tvcache.TVCache(self, min_time=10)  # Only poll IPTorrents every 10 minutes max

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-locals, too-many-branches
        """
        Search a provider and parse the results

        :param search_strings: A dict with mode (key) and the search value (value)
        :param age: Not used
        :param ep_obj: Not used
        :returns: A list of search results (structure)
        """
        results = []
        if not self.login():
            return results

        freeleech = '&free=on' if self.freeleech else ''

        for mode in search_strings:
            logger.log('Search mode: {0}'.format(mode), logger.DEBUG)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    logger.log('Search string: {search}'.format
                               (search=search_string), logger.DEBUG)

                # URL with 50 tv-show results, or max 150 if adjusted in IPTorrents profile
                search_url = self.urls['search'] % (self.categories, freeleech, search_string)
                search_url += ';o=seeders' if mode != 'RSS' else ''

                response = self.get_url(search_url, returns='response')
                if not response or not response.text:
                    logger.log('No data returned from provider', logger.DEBUG)
                    continue

                data = re.sub(r'(?im)<button.+?<[/]button>', '', response.text, 0)

                results += self.parse(data, mode)

        return results

    def parse(self, data, mode):
        """
        Parse search results for items.

        :param data: The raw response from a search
        :param mode: The current mode used to search, e.g. RSS

        :return: A list of items found
        """

        items = []

        with BS4Parser(data, 'html5lib') as html:
            torrent_table = html.find('table', id='torrents')
            torrents = torrent_table('tr') if torrent_table else []

            # Continue only if at least one release is found
            if len(torrents) < 2 or html.find(text='No Torrents Found!'):
                logger.log('Data returned from provider does not contain any torrents', logger.DEBUG)
                return items

            # Skip column headers
            for row in torrents[1:]:
                try:
                    title = row('td')[1].find('a').text
                    download_url = self.urls['base_url'] + row('td')[3].find('a')['href']
                    if not all([title, download_url]):
                        continue

                    seeders = int(row.find('td', attrs={'class': 'ac t_seeders'}).text)
                    leechers = int(row.find('td', attrs={'class': 'ac t_leechers'}).text)

                    # Filter unseeded torrent
                    if seeders < min(self.minseed, 1):
                        if mode != 'RSS':
                            logger.log("Discarding torrent because it doesn't meet the "
                                       "minimum seeders: {0}. Seeders: {1}".format
                                       (title, seeders), logger.DEBUG)
                        continue

                    torrent_size = row('td')[5].text
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

        return items

    def login(self):
        """Login method used for logging in before doing search and torrent downloads."""
        if any(dict_from_cookiejar(self.session.cookies).values()):
            return True

        login_params = {
            'username': self.username,
            'password': self.password,
            'login': 'submit',
        }

        # Initialize session with a GET to have cookies
        self.get_url(self.urls['login'], returns='response')
        response = self.get_url(self.urls['login'], post_data=login_params, returns='response')
        if not response or not response.text:
            logger.log('Unable to connect to provider', logger.WARNING)
            return False

        # Invalid username and password combination
        if re.search('Invalid username and password combination', response.text):
            logger.log('Invalid username or password. Check your settings', logger.WARNING)
            return False

        # You tried too often, please try again after 2 hours!
        if re.search('You tried too often', response.text):
            logger.log('You tried too often, please try again after 2 hours!'
                       ' Disable IPTorrents for at least 2 hours', logger.WARNING)
            return False

        return True

    def _check_auth(self):

        if not self.username or not self.password:
            raise AuthException('Your authentication credentials for {0} are missing,'
                                ' check your config.'.format(self.name))

        return True


provider = IPTorrentsProvider()
