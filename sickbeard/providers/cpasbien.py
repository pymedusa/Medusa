# coding=utf-8
# Author: Guillaume Serre <guillaume.serre@gmail.com>
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

from sickbeard import logger, tvcache
from sickbeard.bs4_parser import BS4Parser

from sickrage.helper.common import convert_size, try_int
from sickrage.providers.torrent.TorrentProvider import TorrentProvider


class CpasbienProvider(TorrentProvider):
    """Cpasbien Torrent provider"""
    def __init__(self):

        # Provider Init
        TorrentProvider.__init__(self, 'Cpasbien')

        # Credentials
        self.public = True

        # URLs
        self.url = 'http://www.cpasbien.cm'

        # Proper Strings
        self.proper_strings = ['PROPER', 'REPACK']

        # Miscellaneous Options

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tvcache.TVCache(self)

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-locals
        results = []

        # Units
        units = ['o', 'Ko', 'Mo', 'Go', 'To', 'Po']

        for mode in search_strings:
            items = []
            logger.log('Search Mode: {0}'.format(mode), logger.DEBUG)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    logger.log('Search string: {search}'.format
                               (search=search_string), logger.DEBUG)
                    search_url = self.url + '/recherche/' + search_string.replace('.', '-').replace(' ', '-') + '.html,trie-seeds-d'
                else:
                    search_url = self.url + '/view_cat.php?categorie=series&trie=date-d'

                data = self.get_url(search_url, returns='text')
                if not data:
                    continue

                with BS4Parser(data, 'html5lib') as html:
                    torrent_rows = html(class_=re.compile('ligne[01]'))
                    for result in torrent_rows:
                        try:
                            title = result.find(class_='titre').get_text(strip=True).replace('HDTV', 'HDTV x264-CPasBien')
                            title = re.sub(r' Saison', ' Season', title, flags=re.IGNORECASE)
                            tmp = result.find('a')['href'].split('/')[-1].replace('.html', '.torrent').strip()
                            download_url = (self.url + '/telechargement/%s' % tmp)
                            if not all([title, download_url]):
                                continue

                            seeders = try_int(result.find(class_='up').get_text(strip=True))
                            leechers = try_int(result.find(class_='down').get_text(strip=True))

                            # Filter unseeded torrent
                            if seeders < min(self.minseed, 1):
                                if mode != 'RSS':
                                    logger.log("Discarding torrent because it doesn't meet the "
                                               "minimum seeders: {0}. Seeders: {1}".format
                                               (title, seeders), logger.DEBUG)
                                continue

                            torrent_size = result.find(class_='poid').get_text(strip=True)
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


provider = CpasbienProvider()
