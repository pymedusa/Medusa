# coding=utf-8
# Author: Idan Gutman
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
"""Provider code for TorrentBytes."""
from __future__ import unicode_literals

import re
import traceback

from dateutil import parser

from medusa import (
    logger,
    tv,
)
from medusa.bs4_parser import BS4Parser
from medusa.helper.common import (
    convert_size,
    try_int,
)
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.compat import urljoin
from requests.utils import dict_from_cookiejar


class TorrentBytesProvider(TorrentProvider):
    """TorrentBytes Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(self.__class__, self).__init__('TorrentBytes')

        # Credentials
        self.username = None
        self.password = None

        # URLs
        self.url = 'https://www.torrentbytes.net'
        self.urls = {
            'login': urljoin(self.url, 'takelogin.php'),
            'search': urljoin(self.url, 'browse.php'),
        }

        # Proper Strings
        self.proper_strings = ['PROPER', 'REPACK']

        # Miscellaneous Options
        self.freeleech = False

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tv.Cache(self)

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
            'c41': 1,
            'c33': 1,
            'c38': 1,
            'c32': 1,
            'c37': 1,
        }

        for mode in search_strings:
            logger.log('Search mode: {0}'.format(mode), logger.DEBUG)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    logger.log('Search string: {search}'.format
                               (search=search_string), logger.DEBUG)

                search_params['search'] = search_string
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
        items = []

        with BS4Parser(data, 'html5lib') as html:
            torrent_table = html.find('table', border='1')
            torrent_rows = torrent_table('tr') if torrent_table else []

            # Continue only if at least one release is found
            if len(torrent_rows) < 2:
                logger.log('Data returned from provider does not contain any torrents', logger.DEBUG)
                return items

            # "Type", "Name", Files", "Comm.", "Added", "TTL", "Size", "Snatched", "Seeders", "Leechers"
            labels = [label.get_text(strip=True) for label in torrent_rows[0]('td')]

            # Skip column headers
            for row in torrent_rows[1:]:
                cells = row('td')

                if len(cells) < len(labels):
                    continue

                try:
                    download_url = urljoin(self.url, cells[labels.index('Name')].find('a',
                                           href=re.compile(r'download.php\?id='))['href'])
                    title_element = cells[labels.index('Name')].find('a', href=re.compile(r'details.php\?id='))
                    title = title_element.get('title', '') or title_element.get_text(strip=True)
                    if not all([title, download_url]):
                        continue

                    # Free leech torrents are marked with green [F L] in the title
                    # (i.e. <font color=green>[F&nbsp;L]</font>)
                    freeleech = cells[labels.index('Name')].find('font', color='green')
                    if freeleech:
                        # \xa0 is a non-breaking space in Latin1 (ISO 8859-1)
                        freeleech_tag = '[F\xa0L]'
                        title = title.replace(freeleech_tag, '')
                        if self.freeleech and freeleech.get_text(strip=True) != freeleech_tag:
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

                    torrent_size = cells[labels.index('Size')].get_text(' ', strip=True)
                    size = convert_size(torrent_size) or -1

                    pubdate_raw = cells[labels.index('Added')].get_text(' ', strip=True)
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
            'login': 'Log in!',
        }

        response = self.get_url(self.urls['login'], post_data=login_params, returns='response')
        if not response or not response.text:
            logger.log('Unable to connect to provider', logger.WARNING)
            return False

        if re.search('Username or password incorrect', response.text):
            logger.log('Invalid username or password. Check your settings', logger.WARNING)
            return False

        return True


provider = TorrentBytesProvider()
