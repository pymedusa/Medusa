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

import validators
import traceback

from sickbeard import logger, tvcache
from sickbeard.common import USER_AGENT

from sickrage.helper.common import convert_size, try_int
from sickrage.providers.torrent.TorrentProvider import TorrentProvider


class TorrentProjectProvider(TorrentProvider):  # pylint: disable=too-many-instance-attributes

    def __init__(self):

        # Provider Init
        TorrentProvider.__init__(self, 'TorrentProject')

        # Credentials
        self.public = True

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # URLs
        self.url = 'https://torrentproject.se/'

        self.custom_url = None
        self.headers.update({'User-Agent': USER_AGENT})

        # Proper Strings

        # Cache
        self.cache = tvcache.TVCache(self, search_params={'RSS': ['0day']})

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-locals, too-many-branches, too-many-statements
        results = []

        search_params = {
            'out': 'json',
            'filter': 2101,
            'showmagnets': 'on',
            'num': 150
        }

        for mode in search_strings:  # Mode = RSS, Season, Episode
            items = []
            logger.log('Search Mode: {0}'.format(mode), logger.DEBUG)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    logger.log('Search string: {0}'.format(search_string.decode('utf-8')),
                               logger.DEBUG)

                search_params['s'] = search_string

                if self.custom_url:
                    if not validators.url(self.custom_url):
                        logger.log('Invalid custom url set, please check your settings', logger.WARNING)
                        return results
                    search_url = self.custom_url
                else:
                    search_url = self.url

                torrents = self.get_url(search_url, params=search_params, returns='json')
                if not (torrents and int(torrents.pop('total_found', 0)) > 0):
                    logger.log('Data returned from provider does not contain any torrents', logger.DEBUG)
                    continue

                for result in torrents:
                    try:
                        title = torrents[result].get('title')
                        download_url = torrents[result].get('magnet')
                        if not all([title, download_url]):
                            continue

                        download_url += self._custom_trackers
                        seeders = try_int(torrents[result].get('seeds'), 1)
                        leechers = try_int(torrents[result].get('leechs'), 0)

                        # Filter unseeded torrent
                        if seeders < min(self.minseed, 1):
                            if mode != 'RSS':
                                logger.log("Discarding torrent because it doesn't meet the"
                                           ' minimum seeders: {0}. Seeders: {1}'.format
                                           (title, seeders), logger.DEBUG)
                            continue

                        torrent_hash = torrents[result].get('torrent_hash')
                        torrent_size = torrents[result].get('torrent_size')
                        size = convert_size(torrent_size) or -1

                        item = {
                            'title': title,
                            'link': download_url,
                            'size': size,
                            'seeders': seeders,
                            'leechers': leechers,
                            'pubdate': None,
                            'hash': torrent_hash
                        }
                        if mode != 'RSS':
                            logger.log('Found result: {0} with {1} seeders and {2} leechers'.format
                                       (title, seeders, leechers), logger.DEBUG)

                        items.append(item)
                    except (AttributeError, TypeError, KeyError, ValueError, IndexError):
                        logger.log('Failed parsing provider. Traceback: {0!r}'.format
                                   (traceback.format_exc()), logger.ERROR)
                        continue

            # For each search mode sort all the items by seeders if available
            items.sort(key=lambda d: try_int(d.get('seeders', 0)), reverse=True)
            results += items

        return results


provider = TorrentProjectProvider()
