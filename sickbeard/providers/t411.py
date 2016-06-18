# coding=utf-8
# Author: djoole <bobby.djoole@gmail.com>
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

import time
import traceback

from requests.compat import urljoin
from requests.auth import AuthBase

from sickbeard import logger, tvcache
from sickbeard.common import USER_AGENT

from sickrage.helper.common import try_int
from sickrage.helper.common import convert_size
from sickrage.providers.torrent.TorrentProvider import TorrentProvider


class T411Provider(TorrentProvider):  # pylint: disable=too-many-instance-attributes
    """T411 Torrent provider"""
    def __init__(self):

        # Provider Init
        TorrentProvider.__init__(self, "T411")

        # Credentials
        self.username = None
        self.password = None
        self.token = None
        self.tokenLastUpdate = None

        # URLs
        self.url = 'https://api.t411.ch'
        self.urls = {
            'base_url': 'http://www.t411.ch/',
            'search': urljoin(self.url, 'torrents/search/%s*?cid=%s&limit=100'),
            'rss': urljoin(self.url, 'torrents/top/today'),
            'login_page': urljoin(self.url, 'auth'),
            'download': urljoin(self.url, 'torrents/download/%s'),
        }

        # Proper Strings

        # Miscellaneous Options
        self.headers.update({'User-Agent': USER_AGENT})
        self.subcategories = [433, 637, 455, 639]
        self.confirmed = False

        # Torrent Stats
        self.minseed = 0
        self.minleech = 0

        # Cache
        self.cache = tvcache.TVCache(self, min_time=10)  # Only poll T411 every 10 minutes max

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-locals, too-many-branches
        """
        T411 search and parsing

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

                search_urls = ([self.urls['search'] % (search_string, u) for u in self.subcategories], [self.urls['rss']])[mode == 'RSS']
                for search_url in search_urls:
                    data = self.get_url(search_url, returns='json')
                    if not data:
                        logger.log('No data returned from provider', logger.DEBUG)
                        continue

                    if 'torrents' not in data and mode != 'RSS':
                        logger.log('Data returned from provider does not contain any torrents', logger.DEBUG)
                        continue

                    torrents = data['torrents'] if mode != 'RSS' else data

                    if not torrents:
                        logger.log('Data returned from provider does not contain any torrents', logger.DEBUG)
                        continue

                    for torrent in torrents:
                        if mode == 'RSS' and 'category' in torrent and try_int(torrent['category'], 0) not in self.subcategories:
                            continue

                        try:
                            title = torrent['name']
                            torrent_id = torrent['id']
                            download_url = (self.urls['download'] % torrent_id)
                            if not all([title, download_url]):
                                continue

                            seeders = try_int(torrent['seeders'])
                            leechers = try_int(torrent['leechers'])
                            verified = bool(torrent['isVerified'])

                            # Filter unseeded torrent
                            if seeders < min(self.minseed, 1):
                                if mode != 'RSS':
                                    logger.log("Discarding torrent because it doesn't meet the "
                                               "minimum seeders: {0}. Seeders: {1}".format
                                               (title, seeders), logger.DEBUG)
                                continue

                            if self.confirmed and not verified and mode != 'RSS':
                                logger.log("Found result {0} but that doesn't seem like a verified"
                                           " result so I'm ignoring it".format(title), logger.DEBUG)
                                continue

                            torrent_size = torrent['size']
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
        if self.token is not None:
            if time.time() < (self.tokenLastUpdate + 30 * 60):
                return True

        login_params = {
            'username': self.username,
            'password': self.password,
        }

        response = self.get_url(self.urls['login_page'], post_data=login_params, returns='json')
        if not response:
            logger.log('Unable to connect to provider', logger.WARNING)
            return False

        if response and 'token' in response:
            self.token = response['token']
            self.tokenLastUpdate = time.time()
            # self.uid = response['uid'].encode('ascii', 'ignore')
            self.session.auth = T411Auth(self.token)
            return True
        else:
            logger.log('Token not found in authentication response', logger.WARNING)
            return False


class T411Auth(AuthBase):  # pylint: disable=too-few-public-methods
    """Attaches HTTP Authentication to the given Request object."""
    def __init__(self, token):
        self.token = token

    def __call__(self, r):
        r.headers['Authorization'] = self.token
        return r


provider = T411Provider()
