# coding=utf-8
# Author: xataz <xataz@mondedie.fr>
# Based on works of Dustyn Gibson <miigotu@gmail.com> for sickrage
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
"""Provider code for Xthor."""
from __future__ import unicode_literals

from medusa import (
    logger,
    tv,
)
from medusa.common import USER_AGENT
from medusa.helper.common import (
    try_int,
)
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.compat import quote, urljoin


class XthorProvider(TorrentProvider):
    """Xthor Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(self.__class__, self).__init__("Xthor")

        # Credentials
        self.passkey = None
        self.freeleech = None

        # URLs
        self.url = 'https://xthor.bz'
        self.urls = {
            'search': 'https://api.xthor.bz',
        }

        # Proper Strings


        # Miscellaneous Options
        self.headers.update({'User-Agent': USER_AGENT})
        self.subcategories = [433, 637, 455, 639]
        self.confirmed = False


        # Cache
        self.cache = tv.Cache(self, min_time=10)

    def search(self, search_strings, age=0, ep_obj=None):
        results = []
        if not self._check_auth:
            return results

        search_params = {
            'passkey': self.passkey
        }
        if self.freeleech:
            search_params['freeleech'] = 1

        for mode in search_strings:
            items = []
            logger.log('Search Mode: {0}'.format(mode), logger.DEBUG)
            for search_string in search_strings[mode]:
                if mode != 'RSS':
                    logger.log('Search string: ' + search_string.strip(), logger.DEBUG)
                    search_params['search'] = search_string
                else:
                    search_params.pop('search', '')

                jdata = self.get_url(self.urls['search'], params=search_params, returns='json')
                if not jdata:
                    logger.log('No data returned from provider', logger.DEBUG)
                    continue

                error_code = jdata.pop('error', {})
                if error_code.get('code'):
                    if error_code.get('code') != 2:
                        logger.log('{0}'.format(error_code.get('descr', 'Error code 2 - no description available')), logger.WARNING)
                        return results
                    continue

                account_ok = jdata.pop('user', {}).get('can_leech')
                if not account_ok:
                    logger.log('Sorry, your account is not allowed to download, check your ratio', logger.WARNING)
                    return results

                torrents = jdata.pop('torrents', None)
                if not torrents:
                    logger.log('Provider has no results for this search', logger.DEBUG)
                    continue

                for torrent in torrents:
                    try:
                        title = torrent.get('name')
                        download_url = torrent.get('download_link')
                        if not (title and download_url):
                            continue

                        seeders = torrent.get('seeders')
                        leechers = torrent.get('leechers')
                        if not seeders and mode != 'RSS':
                            logger.log('Discarding torrent because it doesn\'t meet the minimum seeders or leechers: {0} (S:{1} L:{2})'.format
                                       (title, seeders, leechers), logger.DEBUG)
                            continue

                        size = torrent.get('size') or -1
                        item = {'title': title, 'link': download_url, 'size': size, 'seeders': seeders, 'leechers': leechers, 'hash': ''}

                        if mode != 'RSS':
                            logger.log('Found result: {0} with {1} seeders and {2} leechers'.format(title, seeders, leechers), logger.DEBUG)

                        items.append(item)
                    except StandardError:
                        continue

            # For each search mode sort all the items by seeders if available
            items.sort(key=lambda d: try_int(d.get('seeders', 0)), reverse=True)

            results += items

        return results


provider = XthorProvider()
