# coding=utf-8
# Author: Gonçalo M. (aka duramato/supergonkas) <supergonkas@gmail.com>
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

import traceback

from requests.compat import urljoin

from sickbeard import logger, tvcache

from sickrage.helper.common import convert_size, try_int
from sickrage.providers.torrent.TorrentProvider import TorrentProvider


class HD4FreeProvider(TorrentProvider):  # pylint: disable=too-many-instance-attributes
    """HD4Free Torrent provider"""
    def __init__(self):

        # Provider Init
        TorrentProvider.__init__(self, 'HD4Free')

        # Credentials
        self.username = None
        self.api_key = None

        # URLs
        self.url = 'https://hd4free.xyz'
        self.urls = {
            'search': urljoin(self.url, '/searchapi.php'),
        }

        # Proper Strings

        # Miscellaneous Options
        self.freeleech = None

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tvcache.TVCache(self, min_time=10)  # Only poll HD4Free every 10 minutes max

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-locals, too-many-branches
        """
        HD4Free search and parsing

        :param search_string: A dict with mode (key) and the search value (value)
        :param age: Not used
        :param ep_obj: Not used
        :returns: A list of search results (structure)
        """
        results = []
        if not self._check_auth:
            return results

        # Search Params
        search_params = {
            'tv': 'true',
            'username': self.username,
            'apikey': self.api_key,
            'fl': 'true' if self.freeleech else None
        }

        for mode in search_strings:
            items = []
            logger.log('Search mode: {0}'.format(mode), logger.DEBUG)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    logger.log('Search string: {search}'.format
                               (search=search_string), logger.DEBUG)
                    search_params['search'] = search_string
                else:
                    search_params['search'] = None

                try:
                    jdata = self.get_url(self.urls['search'], params=search_params, returns='json')
                except ValueError:
                    logger.log('No data returned from provider', logger.DEBUG)
                    continue

                # Continue only if at least one release is found
                if not jdata:
                    logger.log('Data returned from provider does not contain any torrents', logger.DEBUG)
                    continue

                error = jdata.get('error')
                if error:
                    logger.log('{0}'.format(error), logger.DEBUG)
                    return results

                try:
                    if jdata['0']['total_results'] == 0:
                        logger.log('Provider has no results for this search', logger.DEBUG)
                        continue
                except KeyError:
                    continue

                for i in jdata:
                    try:
                        title = jdata[i]['release_name']
                        download_url = jdata[i]['download_url']
                        if not all([title, download_url]):
                            continue

                        seeders = jdata[i]['seeders']
                        leechers = jdata[i]['leechers']

                        # Filter unseeded torrent
                        if seeders < min(self.minseed, 1):
                            if mode != 'RSS':
                                logger.log("Discarding torrent because it doesn't meet the "
                                           "minimum seeders: {0}. Seeders: {1}".format
                                           (title, seeders), logger.DEBUG)
                            continue

                        torrent_size = str(jdata[i]['size']) + ' MB'
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

    def _check_auth(self):
        if self.username and self.api_key:
            return True

        logger.log('Your authentication credentials for {provider} are missing, check your config.'.format
                   (provider=self.name), logger.WARNING)
        return False

provider = HD4FreeProvider()
