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

import re
import traceback
import validators

from requests.compat import urljoin

from sickbeard import logger, tvcache
from sickbeard.bs4_parser import BS4Parser

from sickrage.helper.common import convert_size, try_int
from sickrage.providers.torrent.TorrentProvider import TorrentProvider


class ThePirateBayProvider(TorrentProvider):  # pylint: disable=too-many-instance-attributes
    """ThePirateBay Torrent provider"""
    def __init__(self):

        # Provider Init
        TorrentProvider.__init__(self, 'ThePirateBay')

        # Credentials
        self.public = True

        # URLs
        self.url = 'https://thepiratebay.org'
        self.urls = {
            'rss': urljoin(self.url, 'tv/latest'),
            'search': urljoin(self.url, 's/'),  # Needs trailing /
        }
        self.custom_url = None

        # Proper Strings

        # Miscellaneous Options
        self.confirmed = True

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tvcache.TVCache(self, min_time=20)  # only poll ThePirateBay every 20 minutes max

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-locals, too-many-branches, too-many-statements
        results = []
        """
        205 = SD, 208 = HD, 200 = All Videos
        https://pirateproxy.pl/s/?q=Game of Thrones&type=search&orderby=7&page=0&category=200
        """
        search_params = {
            'q': '',
            'type': 'search',
            'orderby': 7,
            'page': 0,
            'category': 200
        }

        # Units
        units = ['B', 'KIB', 'MIB', 'GIB', 'TIB', 'PIB']

        def process_column_header(th):
            result = ''
            if th.a:
                result = th.a.get_text(strip=True)
            if not result:
                result = th.get_text(strip=True)
            return result

        for mode in search_strings:
            items = []
            logger.log('Search mode: {0}'.format(mode), logger.DEBUG)

            for search_string in search_strings[mode]:

                search_url = self.urls['search'] if mode != 'RSS' else self.urls['rss']
                if self.custom_url:
                    if not validators.url(self.custom_url):
                        logger.log('Invalid custom url: {0}'.format(self.custom_url), logger.WARNING)
                        return results
                    search_url = urljoin(self.custom_url, search_url.split(self.url)[1])

                if mode != 'RSS':
                    search_params['q'] = search_string
                    logger.log('Search string: {search}'.format
                               (search=search_string), logger.DEBUG)

                    data = self.get_url(search_url, params=search_params, returns='text')
                else:
                    data = self.get_url(search_url, returns='text')

                if not data:
                    logger.log('No data returned from provider', logger.DEBUG)
                    continue

                with BS4Parser(data, 'html5lib') as html:
                    torrent_table = html.find('table', id='searchResult')
                    torrent_rows = torrent_table('tr') if torrent_table else []

                    # Continue only if at least one release is found
                    if len(torrent_rows) < 2:
                        logger.log('Data returned from provider does not contain any torrents', logger.DEBUG)
                        continue

                    labels = [process_column_header(label) for label in torrent_rows[0]('th')]

                    # Skip column headers
                    for result in torrent_rows[1:]:
                        try:
                            cells = result('td')

                            title = result.find(class_='detName')
                            title = title.get_text(strip=True) if title else None
                            download_url = result.find(title='Download this torrent using magnet')
                            download_url = download_url['href'] + self._custom_trackers if download_url else None
                            if download_url and 'magnet:?' not in download_url:
                                logger.log('Invalid ThePirateBay proxy please try another one', logger.DEBUG)
                                continue
                            if not all([title, download_url]):
                                continue

                            seeders = try_int(cells[labels.index('SE')].get_text(strip=True))
                            leechers = try_int(cells[labels.index('LE')].get_text(strip=True))

                            # Filter unseeded torrent
                            if seeders < min(self.minseed, 1):
                                if mode != 'RSS':
                                    logger.log("Discarding torrent because it doesn't meet the "
                                               "minimum seeders: {0}. Seeders: {1}".format
                                               (title, seeders), logger.DEBUG)
                                continue

                            # Accept Torrent only from Good People for every Episode Search
                            if self.confirmed and not result.find(alt=re.compile(r'VIP|Trusted')):
                                if mode != 'RSS':
                                    logger.log("Found result {0} but that doesn't seem like a trusted"
                                               " result so I'm ignoring it".format(title), logger.DEBUG)
                                continue

                            # Convert size after all possible skip scenarios
                            torrent_size = cells[labels.index('Name')].find(class_='detDesc').get_text(strip=True).split(', ')[1]
                            torrent_size = re.sub(r'Size ([\d.]+).+([KMGT]iB)', r'\1 \2', torrent_size)
                            size = convert_size(torrent_size, units=units) or -1

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


provider = ThePirateBayProvider()
