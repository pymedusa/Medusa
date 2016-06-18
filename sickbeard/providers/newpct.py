# coding=utf-8
# Author: CristianBB
# Greetings to Mr. Pine-apple
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

from sickbeard import helpers
from sickbeard import logger, tvcache
from sickbeard.bs4_parser import BS4Parser

from sickrage.helper.common import convert_size
from sickrage.providers.torrent.TorrentProvider import TorrentProvider


class newpctProvider(TorrentProvider):
    """Newpct Torrent provider"""
    def __init__(self):

        # Provider Init
        TorrentProvider.__init__(self, 'Newpct')

        # Credentials

        # URLs
        self.url = 'http://www.newpct.com'
        self.urls = {
            'search': urljoin(self.url, 'index.php'),
        }

        # Proper Strings

        # Miscellaneous Options
        self.onlyspasearch = None

        # Torrent Stats

        # Cache
        self.cache = tvcache.TVCache(self, min_time=20)

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-locals, too-many-branches
        """
        Newpct search and parsing

        :param search_string: A dict with mode (key) and the search value (value)
        :param age: Not used
        :param ep_obj: Not used
        :returns: A list of search results (structure)
        """

        results = []

        # Only search if user conditions are true
        lang_info = '' if not ep_obj or not ep_obj.show else ep_obj.show.lang

        # http://www.newpct.com/index.php?l=doSearch&q=fringe&category_=All&idioma_=1&bus_de_=All
        # Search Params
        search_params = {
            'l': 'doSearch',
            'q': '',  # Show name
            'category_': 'All',  # Category 'Shows' (767)
            'idioma_': 1,  # Language Spanish (1)
            'bus_de_': 'All'  # Date from (All, hoy)
        }

        for mode in search_strings:
            items = []
            logger.log('Search mode: {0}'.format(mode), logger.DEBUG)

            # Only search if user conditions are true
            if self.onlyspasearch and lang_info != 'es' and mode != 'RSS':
                logger.log('Show info is not spanish, skipping provider search', logger.DEBUG)
                continue

            search_params['bus_de_'] = 'All' if mode != 'RSS' else 'hoy'

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    logger.log('Search string: {search}'.format
                               (search=search_string), logger.DEBUG)

                search_params['q'] = search_string
                data = self.get_url(self.urls['search'], params=search_params, returns='text')
                if not data:
                    logger.log('No data returned from provider', logger.DEBUG)
                    continue

                with BS4Parser(data, 'html5lib') as html:
                    torrent_table = html.find('table', id='categoryTable')
                    torrent_rows = torrent_table('tr') if torrent_table else []

                    # Continue only if at least one release is found
                    if len(torrent_rows) < 3:  # Headers + 1 Torrent + Pagination
                        logger.log('Data returned from provider does not contain any torrents', logger.DEBUG)
                        continue

                    # 'Fecha', 'Título', 'Tamaño', ''
                    # Date,    Title,     Size
                    labels = [label.get_text(strip=True) for label in torrent_rows[0]('th')]

                    # Skip column headers
                    for row in torrent_rows[1:-1]:
                        cells = row('td')
                        if len(cells) < len(labels):
                            continue

                        try:
                            torrent_row = row.find('a')
                            title = self._process_title(torrent_row.get('title', ''))
                            download_url = torrent_row.get('href', '')
                            if not all([title, download_url]):
                                continue

                            seeders = 1  # Provider does not provide seeders
                            leechers = 0  # Provider does not provide leechers
                            torrent_size = cells[labels.index('Tamaño')].get_text(strip=True)
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

    @staticmethod
    def _process_title(title):
        # Remove 'Mas informacion sobre ' literal from title
        title = title[22:]

        # Quality - Use re module to avoid case sensitive problems with replace
        title = re.sub(r'\[HDTV 1080p[^\[]*]', '1080p HDTV x264', title, flags=re.IGNORECASE)
        title = re.sub(r'\[HDTV 720p[^\[]*]', '720p HDTV x264', title, flags=re.IGNORECASE)
        title = re.sub(r'\[ALTA DEFINICION 720p[^\[]*]', '720p HDTV x264', title, flags=re.IGNORECASE)
        title = re.sub(r'\[HDTV]', 'HDTV x264', title, flags=re.IGNORECASE)
        title = re.sub(r'\[DVD[^\[]*]', 'DVDrip x264', title, flags=re.IGNORECASE)
        title = re.sub(r'\[BluRay 1080p[^\[]*]', '1080p BlueRay x264', title, flags=re.IGNORECASE)
        title = re.sub(r'\[BluRay MicroHD[^\[]*]', '1080p BlueRay x264', title, flags=re.IGNORECASE)
        title = re.sub(r'\[MicroHD 1080p[^\[]*]', '1080p BlueRay x264', title, flags=re.IGNORECASE)
        title = re.sub(r'\[BLuRay[^\[]*]', '720p BlueRay x264', title, flags=re.IGNORECASE)
        title = re.sub(r'\[BRrip[^\[]*]', '720p BlueRay x264', title, flags=re.IGNORECASE)
        title = re.sub(r'\[BDrip[^\[]*]', '720p BlueRay x264', title, flags=re.IGNORECASE)

        # Language
        title = re.sub(r'\[Spanish[^\[]*]', 'SPANISH AUDIO', title, flags=re.IGNORECASE)
        title = re.sub(r'\[Castellano[^\[]*]', 'SPANISH AUDIO', title, flags=re.IGNORECASE)
        title = re.sub(r'\[Español[^\[]*]', 'SPANISH AUDIO', title, flags=re.IGNORECASE)
        title = re.sub(r'\[AC3 5\.1 Español[^\[]*]', 'SPANISH AUDIO', title, flags=re.IGNORECASE)

        title += '-NEWPCT'

        return title.strip()

    def get_url(self, url, post_data=None, params=None, timeout=30, **kwargs):  # pylint: disable=too-many-arguments
        """
        returns='content' when trying access to torrent info (For calling torrent client). Previously we must parse
        the URL to get torrent file
        """
        trickery = kwargs.pop('returns', '')
        if trickery == 'content':
            kwargs['returns'] = 'text'
            data = super(newpctProvider, self).get_url(url, post_data=post_data, params=params, timeout=timeout, **kwargs)
            url = re.search(r'http://tumejorserie.com/descargar/.+\.torrent', data, re.DOTALL).group()

        kwargs['returns'] = trickery
        return super(newpctProvider, self).get_url(url, post_data=post_data, params=params,
                                                   timeout=timeout, **kwargs)

    def download_result(self, result):
        """
        Save the result to disk.
        """

        # check for auth
        if not self.login():
            return False

        urls, filename = self._make_url(result)

        for url in urls:
            # Search results don't return torrent files directly, it returns show sheets so we must parse showSheet to access torrent.
            data = self.get_url(url, returns='text')
            url_torrent = re.search(r'http://tumejorserie.com/descargar/.+\.torrent', data, re.DOTALL).group()

            if url_torrent.startswith('http'):
                self.headers.update({'Referer': '/'.join(url_torrent.split('/')[:3]) + '/'})

            logger.log('Downloading a result from {0}'.format(url))

            if helpers.download_file(url_torrent, filename, session=self.session, headers=self.headers):
                if self._verify_download(filename):
                    logger.log('Saved result to {0}'.format(filename), logger.INFO)
                    return True
                else:
                    logger.log('Could not download {0}'.format(url), logger.WARNING)
                    helpers.remove_file_failed(filename)

        if urls:
            logger.log('Failed to download any results', logger.WARNING)

        return False


provider = newpctProvider()
