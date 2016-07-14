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

from __future__ import unicode_literals

import traceback
import validators

from requests.compat import urljoin
from sickbeard.bs4_parser import BS4Parser

import sickbeard
from sickbeard import logger, tvcache

from sickrage.helper.common import convert_size, try_int
from sickrage.providers.torrent.TorrentProvider import TorrentProvider


class KatProvider(TorrentProvider):  # pylint: disable=too-many-instance-attributes
    """KAT Torrent provider"""
    def __init__(self):

        # Provider Init
        TorrentProvider.__init__(self, 'KickAssTorrents')

        # Credentials
        self.public = True

        # URLs
        self.url = 'https://kat.cr'
        self.urls = {
            'search': urljoin(self.url, '%s/'),
        }
        self.custom_url = None

        # Proper Strings

        # Miscellaneous Options
        self.confirmed = True

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tvcache.TVCache(self, search_params={'RSS': ['tv', 'anime']})

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-branches, too-many-locals, too-many-statements
        results = []

        anime = (self.show and self.show.anime) or (ep_obj and ep_obj.show and ep_obj.show.anime) or False
        search_params = {
            'q': '',
            'field': 'seeders',
            'sorder': 'desc',
            'rss': 1,
            'category': ('tv', 'anime')[anime]
        }

        for mode in search_strings:
            items = []
            logger.log('Search mode: {0}'.format(mode), logger.DEBUG)

            for search_string in search_strings[mode]:

                search_params['q'] = search_string if mode != 'RSS' else ''
                search_params['field'] = 'seeders' if mode != 'RSS' else 'time_add'

                if mode != 'RSS':
                    logger.log('Search string: {0}'.format(search_string),
                               logger.DEBUG)

                search_url = self.urls['search'] % ('usearch' if mode != 'RSS' else search_string)
                if self.custom_url:
                    if not validators.url(self.custom_url):
                        logger.log('Invalid custom url: {0}'.format(self.custom_url), logger.WARNING)
                        return results
                    search_url = urljoin(self.custom_url, search_url.split(self.url)[1])

                data = self.get_url(search_url, params=search_params, returns='text')
                if not data:
                    logger.log('URL did not return data, maybe try a custom url, or a different one', logger.DEBUG)
                    continue

                if not data.startswith('<?xml'):
                    logger.log('Expected xml but got something else, is your mirror failing?', logger.INFO)
                    continue

                with BS4Parser(data, 'html5lib') as html:
                    for item in html('item'):
                        try:
                            title = item.title.get_text(strip=True)
                            # Use the torcache link kat provides,
                            # unless it is not torcache or we are not using blackhole
                            # because we want to use magnets if connecting direct to client
                            # so that proxies work.
                            download_url = item.enclosure['url']
                            if sickbeard.TORRENT_METHOD != 'blackhole' or 'torcache' not in download_url:
                                download_url = item.find('torrent:magneturi').next.replace('CDATA', '').strip('[!]') + self._custom_trackers

                            if not (title and download_url):
                                continue

                            seeders = try_int(item.find('torrent:seeds').get_text(strip=True))
                            leechers = try_int(item.find('torrent:peers').get_text(strip=True))

                            # Filter unseeded torrent
                            if seeders < min(self.minseed, 1):
                                if mode != 'RSS':
                                    logger.log("Discarding torrent because it doesn't meet the "
                                               "minimum seeders: {0}. Seeders: {1}".format
                                               (title, seeders), logger.DEBUG)
                                continue

                            verified = bool(try_int(item.find('torrent:verified').get_text(strip=True)))
                            if self.confirmed and not verified:
                                if mode != 'RSS':
                                    logger.log("Found result {0} but that doesn't seem like a verified"
                                               " result so I'm ignoring it".format(title), logger.DEBUG)
                                continue

                            torrent_size = item.find('torrent:contentlength').get_text(strip=True)
                            size = convert_size(torrent_size) or -1
                            info_hash = item.find('torrent:infohash').get_text(strip=True)

                            item = {
                                'title': title,
                                'link': download_url,
                                'size': size,
                                'seeders': seeders,
                                'leechers': leechers,
                                'pubdate': None,
                                'hash': info_hash,
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


provider = KatProvider()
