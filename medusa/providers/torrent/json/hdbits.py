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
"""Provider code for HDBits."""
from __future__ import unicode_literals

import json
import logging

from medusa import tv
from medusa.helper.exceptions import AuthException
from medusa.logger.style.adapter import BraceAdapter
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.compat import urlencode, urljoin

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())

class HDBitsProvider(TorrentProvider):
    """HDBits Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(self.__class__, self).__init__('HDBits')

        # Credentials
        self.username = None
        self.passkey = None

        # URLs
        self.url = 'https://hdbits.org'
        self.urls = {
            'search': urljoin(self.url, '/api/torrents'),
            'download': urljoin(self.url, '/download.php?{0}'),
        }

        # Proper Strings
        self.proper_strings = ['PROPER', 'REPACK']

        # Miscellaneous Options

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tv.Cache(self, min_time=10)  # only poll HDBits every 10 minutes max

    def search(self, search_strings, age=0, ep_obj=None):
        """
        Search a provider and parse the results.
        :param search_strings: A dict with mode (key) and the search value (value)
        :param age: Not used
        :param ep_obj: Not used
        :returns: A list of search results (structure)
        """

        results = []

        log.debug('Search strings {0}', search_strings)

        self._check_auth()

        post_data = {
            'username': self.username,
            'passkey': self.passkey,
            'category': [2, 3, 5],    # (1 Movie, 2 TV, 3 Documentary, 4 Music, 5 Sport, 6 Audio Track, 7 XXX, 8 Misc/Demo)
        }

        for mode in search_strings:
            log.debug('Search mode {0}', mode)

            for search_string in search_strings[mode]:
                if mode != 'RSS':
                    log.debug('Search string {search}', {'search': search_string})
                    post_data['search'] = search_string
                response = self.get_url(self.urls['search'], post_data=json.dumps(post_data), returns='response')
                if not response or not response.content:
                    log.debug('No data returned from provider')
                    return results

                if not self._check_auth_from_data(response):
                    return results
                try:
                    jdata = response.json()
                except ValueError:  # also catches JSONDecodeError if simplejson is installed
                    log.debug('No data returned from provider')
                    return results

                results += self.parse(jdata, None)

        results += self.parse(jdata, None)

        return results

    def parse(self, data, mode):
        """
        Parse search results for items.
        :param data: The raw response from a search
        :param mode: The current mode used to search, e.g. RSS
        :return: A list of items found
        """
        items = []

        torrent_rows = data.get('data')
        if not torrent_rows:
            log.error('Resulting JSON from provider isn\'t correct, not parsing it')

        for row in torrent_rows:

            title = row.get('name', '')
            torrent_id = row.get('id', '')
            download_url = self.urls['download'].format(urlencode({'id': torrent_id, 'passkey': self.passkey}))

            if not all([title, download_url]):
                continue
            seeders = row.get('seeders', 1)
            leechers = row.get('leechers', 0)

            # Filter unseeded torrent
            if seeders < min(self.minseed, 1):
                log.debug('Discarding torrent because it doesn\'t meet the minimum seeders: {0}. Seeders: {1}', title, seeders)
                continue

            size = row.get('size') or -1
            pubdate = row.get('added', '')

            item = {
                'title': title,
                'link': download_url,
                'size': size,
                'seeders': seeders,
                'leechers': leechers,
                'pubdate': pubdate,
            }
            log.debug('Found result: {title} with {x} seeders and {y} leechers', {'title': title}, {'x': seeders}, {'y': leechers})

            items.append(item)

        return items

    def _check_auth(self):

        if not self.username or not self.passkey:
            log.warning('Your authentication credentials for {provider} are missing, check your config.', {'provider': self.name})
            return False
        return True

    def _check_auth_from_data(self, parsed_json):

        if 'status' in parsed_json and 'message' in parsed_json:
            if parsed_json.get('status') == 5:
                log.warning('Invalid username or password. Check your settings')
                return False
        return True

provider = HDBitsProvider()

