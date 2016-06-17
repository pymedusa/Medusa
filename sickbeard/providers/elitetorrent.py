# coding=utf-8
# Author: CristianBB
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

from sickrage.helper.common import try_int
from sickrage.providers.torrent.TorrentProvider import TorrentProvider


class elitetorrentProvider(TorrentProvider):
    """EliteTorrent Torrent provider"""
    def __init__(self):

        # Provider Init
        TorrentProvider.__init__(self, 'EliteTorrent')

        # Credentials

        # URLs
        self.url = 'http://www.elitetorrent.net'
        self.urls = {
            'base_url': self.url,
            'search': urljoin(self.url, 'torrents.php')
        }

        # Proper Strings

        # Miscellaneous Options
        self.onlyspasearch = None

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tvcache.TVCache(self)  # Only poll EliteTorrent every 20 minutes max

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-locals, too-many-branches
        """
        EliteTorrent search and parsing

        :param search_string: A dict with mode (key) and the search value (value)
        :param age: Not used
        :param ep_obj: Not used
        :returns: A list of search results (structure)
        """
        results = []
        lang_info = '' if not ep_obj or not ep_obj.show else ep_obj.show.lang

        # Search query:
        # http://www.elitetorrent.net/torrents.php?cat=4&modo=listado&orden=fecha&pag=1&buscar=fringe
        # Search Params
        search_params = {
            'cat': 4,  # Shows
            'modo': 'listado',  # display results mode
            'orden': 'fecha',  # date order
            'pag': 1,  # page number
            'buscar': '',  # Search show
        }

        for mode in search_strings:
            items = []
            logger.log('Search mode: {0}'.format(mode), logger.DEBUG)

            # Only search if user conditions are true
            if self.onlyspasearch and lang_info != 'es' and mode != 'RSS':
                logger.log('Show info is not spanish, skipping provider search', logger.DEBUG)
                continue

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    logger.log('Search string: {search}'.format
                               (search=search_string), logger.DEBUG)

                search_string = re.sub(r'S0*(\d*)E(\d*)', r'\1x\2', search_string)
                search_params['buscar'] = search_string.strip() if mode != 'RSS' else ''
                data = self.get_url(self.urls['search'], params=search_params, returns='text')
                if not data:
                    logger.log('No data returned from provider', logger.DEBUG)
                    continue

                with BS4Parser(data, 'html5lib') as html:
                    torrent_table = html.find('table', class_='fichas-listado')
                    torrent_rows = torrent_table('tr') if torrent_table else []

                    # Continue only if at least one release is found
                    if len(torrent_rows) < 2:
                        logger.log('Data returned from provider does not contain any torrents', logger.DEBUG)
                        continue

                    # Skip column headers
                    for row in torrent_rows[1:]:
                        try:
                            title = self._process_title(row.find('a', class_='nombre')['title'])
                            download_url = self.urls['base_url'] + row.find('a')['href']
                            if not all([title, download_url]):
                                continue

                            seeders = try_int(row.find('td', class_='semillas').get_text(strip=True))
                            leechers = try_int(row.find('td', class_='clientes').get_text(strip=True))

                            # Filter unseeded torrent
                            if seeders < min(self.minseed, 1):
                                if mode != 'RSS':
                                    logger.log("Discarding torrent because it doesn't meet the "
                                               "minimum seeders: {0}. Seeders: {1}".format
                                               (title, seeders), logger.DEBUG)
                                continue

                            size = -1  # Provider does not provide size

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

    @staticmethod
    def _process_title(title):

        # Quality, if no literal is defined it's HDTV
        if 'calidad' not in title:
            title += ' HDTV x264'

        title = title.replace('(calidad baja)', 'HDTV x264')
        title = title.replace('(Buena calidad)', '720p HDTV x264')
        title = title.replace('(Alta calidad)', '720p HDTV x264')
        title = title.replace('(calidad regular)', 'DVDrip x264')
        title = title.replace('(calidad media)', 'DVDrip x264')

        # Language, all results from this provider have spanish audio, we append it to title (to avoid downloading undesired torrents)
        title += ' SPANISH AUDIO'
        title += '-ELITETORRENT'

        return title.strip()


provider = elitetorrentProvider()
