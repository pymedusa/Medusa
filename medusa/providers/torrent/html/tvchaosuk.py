# coding=utf-8
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
"""Provider code for TVChaosUK."""
from __future__ import unicode_literals

import re
import traceback

from medusa import (
    logger,
    tv,
)
from medusa.bs4_parser import BS4Parser
from medusa.helper.common import (
    convert_size,
    try_int,
)
from medusa.helper.exceptions import AuthException
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.compat import urljoin


class TVChaosUKProvider(TorrentProvider):
    """TVChaosUK Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(self.__class__, self).__init__('TvChaosUK')

        # Credentials
        self.username = None
        self.password = None

        # URLs
        self.url = 'https://www.tvchaosuk.com'
        self.urls = {
            'login': urljoin(self.url, 'takelogin.php'),
            'index': urljoin(self.url, 'index.php'),
            'search': urljoin(self.url, 'browse.php'),
            'query': urljoin(self.url, 'scripts/autocomplete/query.php'),
        }

        # Proper Strings
        # Provider always returns propers and non-propers in a show search
        self.proper_strings = ['']

        # Miscellaneous Options
        self.freeleech = None

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
            'do': 'search',
            'search_type': 't_name',
            'category': 0,
            'include_dead_torrents': 'no',
            'submit': 'search',
        }

        for mode in search_strings:
            logger.log('Search mode: {0}'.format(mode), logger.DEBUG)

            for search_string in search_strings[mode]:

                if mode == 'Season':
                    search_string = re.sub(r'(.*)S0?', r'\1Series ', search_string)

                elif mode != 'RSS':
                    logger.log('Search string: {search}'.format
                               (search=search_string), logger.DEBUG)

                search_params['keywords'] = search_string
                response = self.get_url(self.urls['search'], post_data=search_params, returns='response')
                if not response or not response.text:
                    logger.log('No data returned from provider', logger.DEBUG)
                    continue

                results += self.parse(response.text, mode, keywords=search_string)

        return results

    def parse(self, data, mode, **kwargs):
        """
        Parse search results for items.

        :param data: The raw response from a search
        :param mode: The current mode used to search, e.g. RSS

        :return: A list of items found
        """
        # Units
        units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']

        items = []

        keywords = kwargs.pop('keywords', None)

        with BS4Parser(data, 'html5lib') as html:
            torrent_table = html.find(id='sortabletable')
            torrent_rows = torrent_table('tr') if torrent_table else []

            # Continue only if at least one release is found
            if len(torrent_rows) < 2:
                logger.log('Data returned from provider does not contain any torrents', logger.DEBUG)
                return items

            labels = [label.img['title'] if label.img else label.get_text(strip=True) for label in
                      torrent_rows[0]('td')]

            # Skip column headers
            for row in torrent_rows[1:]:
                try:
                    # Skip highlighted torrents
                    if mode == 'RSS' and row.get('class') == ['highlight']:
                        continue

                    if self.freeleech and not row.find('img', alt=re.compile('Free Torrent')):
                        continue

                    title = row.find(class_='tooltip-content')
                    title = title.div.get_text(strip=True) if title else None
                    download_url = row.find(title='Click to Download this Torrent!')
                    download_url = download_url.parent['href'] if download_url else None
                    if not all([title, download_url]):
                        continue

                    if title.endswith('...'):
                        title = self.get_full_title(title)

                    seeders = try_int(row.find(title='Seeders').get_text(strip=True))
                    leechers = try_int(row.find(title='Leechers').get_text(strip=True))

                    # Filter unseeded torrent
                    if seeders < min(self.minseed, 1):
                        if mode != 'RSS':
                            logger.log("Discarding torrent because it doesn't meet the "
                                       "minimum seeders: {0}. Seeders: {1}".format
                                       (title, seeders), logger.DEBUG)
                        continue

                    # Chop off tracker/channel prefix or we cant parse the result!
                    if mode != 'RSS' and keywords:
                        show_name_first_word = re.search(r'^[^ .]+', keywords).group()
                        if not title.startswith(show_name_first_word):
                            title = re.sub(r'.*(' + show_name_first_word + '.*)', r'\1', title)

                    # Change title from Series to Season, or we can't parse
                    if mode == 'Season':
                        title = re.sub(r'(.*)(?i)Series', r'\1Season', title)

                    # Strip year from the end or we can't parse it!
                    title = re.sub(r'(.*)[\. ]?\(\d{4}\)', r'\1', title)
                    title = re.sub(r'\s+', r' ', title)

                    torrent_size = row('td')[labels.index('Size')].get_text(strip=True)
                    size = convert_size(torrent_size, units=units) or -1

                    item = {
                        'title': title + '.hdtv.x264',
                        'link': download_url,
                        'size': size,
                        'seeders': seeders,
                        'leechers': leechers,
                        'pubdate': None,
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
        if len(self.session.cookies) >= 4:
            return True

        login_params = {
            'username': self.username,
            'password': self.password,
            'logout': 'no',
            'submit': 'LOGIN',
            'returnto': '/browse.php',
        }

        response = self.get_url(self.urls['login'], post_data=login_params, returns='response')
        if not response or not response.text:
            logger.log('Unable to connect to provider', logger.WARNING)
            return False

        if re.search('Error: Username or password incorrect!', response.text):
            logger.log('Invalid username or password. Check your settings', logger.WARNING)
            return False

        return True

    def _check_auth(self):
        if self.username and self.password:
            return True

        raise AuthException('Your authentication credentials for {0} are missing,'
                            ' check your config.'.format(self.name))

    def get_full_title(self, title):
        """Get full title of release as provider add a "..." in the end of title in the html."""
        # Strip trailing 3 dots
        title = title[:-3]
        search_params = {'input': title}
        result = self.get_url(self.urls['query'], params=search_params, returns='response')
        with BS4Parser(result.text, 'html5lib') as html:
            titles = html('results')
            for item in titles:
                title = item.text
        return title


provider = TVChaosUKProvider()
