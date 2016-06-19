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

from __future__ import unicode_literals

import re
import traceback

from requests.compat import urljoin

from sickbeard import logger, tvcache
from sickbeard.bs4_parser import BS4Parser

from sickrage.helper.common import convert_size, try_int
from sickrage.helper.exceptions import AuthException
from sickrage.providers.torrent.TorrentProvider import TorrentProvider


class TVChaosUKProvider(TorrentProvider):  # pylint: disable=too-many-instance-attributes
    """TVChaosUK Torrent provider"""
    def __init__(self):

        # Provider Init
        TorrentProvider.__init__(self, 'TvChaosUK')

        # Credentials
        self.username = None
        self.password = None

        # URLs
        self.url = 'https://www.tvchaosuk.com'
        self.urls = {
            'login': urljoin(self.url, 'takelogin.php'),
            'index': urljoin(self.url, 'index.php'),
            'search': urljoin(self.url, 'browse.php'),
        }

        # Proper Strings

        # Miscellaneous Options
        self.freeleech = None

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tvcache.TVCache(self)

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-locals, too-many-branches
        """
        TVChaosUK search and parsing

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
            'do': 'search',
            'search_type': 't_name',
            'category': 0,
            'include_dead_torrents': 'no',
            'submit': 'search'
        }

        # Units
        units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']

        for mode in search_strings:
            items = []
            logger.log('Search mode: {0}'.format(mode), logger.DEBUG)

            for search_string in search_strings[mode]:

                if mode == 'Season':
                    search_string = re.sub(r'(.*)S0?', r'\1Series ', search_string)

                if mode != 'RSS':
                    logger.log('Search string: {search}'.format
                               (search=search_string), logger.DEBUG)

                search_params['keywords'] = search_string
                data = self.get_url(self.urls['search'], post_data=search_params, returns='text')
                if not data:
                    logger.log('No data returned from provider', logger.DEBUG)
                    continue

                with BS4Parser(data, 'html5lib') as html:
                    torrent_table = html.find(id='sortabletable')
                    torrent_rows = torrent_table('tr') if torrent_table else []

                    # Continue only if at least one release is found
                    if len(torrent_rows) < 2:
                        logger.log('Data returned from provider does not contain any torrents', logger.DEBUG)
                        continue

                    labels = [label.img['title'] if label.img else label.get_text(strip=True) for label in torrent_rows[0]('td')]
                    for torrent in torrent_rows[1:]:
                        try:
                            if self.freeleech and not torrent.find('img', alt=re.compile('Free Torrent')):
                                continue

                            title = torrent.find(class_='tooltip-content')
                            title = title.div.get_text(strip=True) if title else None
                            download_url = torrent.find(title='Click to Download this Torrent!')
                            download_url = download_url.parent['href'] if download_url else None
                            if not all([title, download_url]):
                                continue

                            seeders = try_int(torrent.find(title='Seeders').get_text(strip=True))
                            leechers = try_int(torrent.find(title='Leechers').get_text(strip=True))

                            # Filter unseeded torrent
                            if seeders < min(self.minseed, 1):
                                if mode != 'RSS':
                                    logger.log("Discarding torrent because it doesn't meet the "
                                               "minimum seeders: {0}. Seeders: {1}".format
                                               (title, seeders), logger.DEBUG)
                                continue

                            # Chop off tracker/channel prefix or we cant parse the result!
                            if mode != 'RSS' and search_params['keywords']:
                                show_name_first_word = re.search(r'^[^ .]+', search_params['keywords']).group()
                                if not title.startswith(show_name_first_word):
                                    title = re.sub(r'.*(' + show_name_first_word + '.*)', r'\1', title)

                            # Change title from Series to Season, or we can't parse
                            if mode == 'Season':
                                title = re.sub(r'(.*)(?i)Series', r'\1Season', title)

                            # Strip year from the end or we can't parse it!
                            title = re.sub(r'(.*)[\. ]?\(\d{4}\)', r'\1', title)
                            title = re.sub(r'\s+', r' ', title)

                            torrent_size = torrent('td')[labels.index('Size')].get_text(strip=True)
                            size = convert_size(torrent_size, units=units) or -1

                            item = {
                                'title': title + '.hdtv.x264',
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
        if len(self.session.cookies) >= 4:
            return True

        login_params = {
            'username': self.username,
            'password': self.password,
            'logout': 'no',
            'submit': 'LOGIN',
            'returnto': '/browse.php',
        }

        response = self.get_url(self.urls['login'], post_data=login_params, returns='text')
        if not response:
            logger.log('Unable to connect to provider', logger.WARNING)
            return False

        if re.search('Error: Username or password incorrect!', response):
            logger.log('Invalid username or password. Check your settings', logger.WARNING)
            return False

        return True

    def _check_auth(self):
        if self.username and self.password:
            return True

        raise AuthException('Your authentication credentials for {0} are missing,'
                            ' check your config.'.format(self.name))


provider = TVChaosUKProvider()
