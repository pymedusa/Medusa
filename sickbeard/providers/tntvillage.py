# coding=utf-8
# Original author: Giovanni Borri
# Modified by gborri, https://github.com/gborri for TNTVillage
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

from six.moves.urllib_parse import parse_qs

from requests.utils import dict_from_cookiejar
from requests.compat import urljoin

from sickbeard import logger, tvcache
from sickbeard.bs4_parser import BS4Parser

from sickrage.helper.common import convert_size, try_int
from sickrage.helper.exceptions import AuthException
from sickrage.providers.torrent.TorrentProvider import TorrentProvider


class TNTVillageProvider(TorrentProvider):  # pylint: disable=too-many-instance-attributes
    """TNTVillage Torrent provider"""
    def __init__(self):

        # Provider Init
        TorrentProvider.__init__(self, 'TNTVillage')

        # Credentials
        self.username = None
        self.password = None
        self._uid = None
        self._hash = None

        # URLs
        self.url = 'http://forum.tntvillage.scambioetico.org/'
        self.urls = {
            'login': urljoin(self.url, 'index.php?act=Login&CODE=01'),
            'download': urljoin(self.url, 'index.php?act=Attach&type=post&id={0}'),
        }

        # Proper Strings
        self.proper_strings = ['PROPER', 'REPACK']

        # Miscellaneous Options
        self.engrelease = None
        self.subtitle = None

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tvcache.TVCache(self, min_time=30)  # only poll TNTVillage every 30 minutes max

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-locals, too-many-branches
        """
        TNTVillage search and parsing

        :param search_string: A dict with mode (key) and the search value (value)
        :param age: Not used
        :param ep_obj: Not used
        :returns: A list of search results (structure)
        """
        results = []
        if not self.login():
            return results

        search_params = {
            'act': 'allreleases',
            'filter': 'eng ' if self.engrelease else '',
            'cat': 29,
        }

        for mode in search_strings:
            items = []
            logger.log('Search mode: {0}'.format(mode), logger.DEBUG)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    logger.log('Search string: {search}'.format
                               (search=search_string), logger.DEBUG)
                    search_params['filter'] += search_string
                    search_params['cat'] = None

                response = self.get_url(self.url, params=search_params, returns='response')
                if not response or not response.text:
                    logger.log('No data returned from provider', logger.DEBUG)
                    continue

                with BS4Parser(response.text, 'html5lib') as html:
                    torrent_table = html.find('table', class_='copyright')
                    torrent_rows = torrent_table('tr') if torrent_table else []

                    # Continue only if at least one release is found
                    if len(torrent_rows) < 3:
                        logger.log('Data returned from provider does not contain any torrents', logger.DEBUG)
                        continue

                    # Skip column headers
                    for result in torrent_table('tr')[1:]:
                        try:
                            cells = result('td')
                            if not cells:
                                continue

                            last_cell_anchor = cells[-1].find('a')
                            if not last_cell_anchor:
                                continue
                            params = parse_qs(last_cell_anchor.get('href', ''))
                            download_url = self.urls['download'].format(params['pid'][0]) if \
                                params.get('pid') else None
                            title = self._process_title(cells[0], cells[1], mode)
                            if not all([title, download_url]):
                                continue

                            info_cell = cells[3].find_all('td')
                            leechers = info_cell[0].find('span').get_text(strip=True)
                            leechers = try_int(leechers)
                            seeders = info_cell[1].find('span').get_text()
                            seeders = try_int(seeders, 1)

                            # Filter unseeded torrent
                            if seeders < min(self.minseed, 1):
                                if mode != 'RSS':
                                    logger.log("Discarding torrent because it doesn't meet the "
                                               "minimum seeders: {0}. Seeders: {1}".format
                                               (title, seeders), logger.DEBUG)
                                continue

                            if self._has_only_subs(title) and not self.subtitle:
                                logger.log('Torrent is only subtitled, skipping: {0}'.format
                                           (title), logger.DEBUG)
                                continue

                            torrent_size = info_cell[3].find('span').get_text() + ' GB'
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
        if len(self.session.cookies) > 1:
            cookies_dict = dict_from_cookiejar(self.session.cookies)
            if cookies_dict['pass_hash'] != '0' and cookies_dict['member_id'] != '0':
                return True

        login_params = {
            'UserName': self.username,
            'PassWord': self.password,
            'CookieDate': 1,
            'submit': 'Connettiti al Forum',
        }

        response = self.get_url(self.urls['login'], post_data=login_params, returns='text')
        if not response:
            logger.log('Unable to connect to provider', logger.WARNING)
            return False

        if re.search('Sono stati riscontrati i seguenti errori', response) or \
                re.search('<title>Connettiti</title>', response):
            logger.log('Invalid username or password. Check your settings', logger.WARNING)
            return False

        return True

    def _check_auth(self):

        if not self.username or not self.password:
            raise AuthException('Your authentication credentials for {0} are missing,'
                                ' check your config.'.format(self.name))

        return True

    @staticmethod
    def _process_title(title, info, mode):

        result_title = title.find('a').get_text()
        result_info = info.find('span')

        if not result_info:
            return None

        bad_words = ['[cura]', 'hot', 'season', 'stagione', 'series', 'premiere', 'finale', 'fine',
                     'full', 'Completa', 'supereroi', 'commedia', 'drammatico', 'poliziesco', 'azione',
                     'giallo', 'politico', 'sitcom', 'funzionante']

        formatted_info = ''
        for info_part in result_info:
            if mode == 'RSS':
                try:
                    info_part = info_part.get('src')
                    info_part = info_part.replace('style_images/mkportal-636/', '')
                    info_part = info_part.replace('.gif', '').replace('.png', '')
                    if info_part == 'dolby':
                        info_part = 'Ac3'
                    elif info_part == 'fullHd':
                        info_part = '1080p'
                except AttributeError:
                    info_part = info_part.replace('·', '').replace(',', '')
                    info_part = info_part.replace('by', '-').strip()
                formatted_info += ' ' + info_part
            else:
                formatted_info = info_part

        allowed_words = [word for word in formatted_info.split() if word.lower() not in bad_words]
        final_title = '{0} '.format(result_title) + ' '.join(allowed_words).strip('-').strip()

        return final_title

    @staticmethod
    def _has_only_subs(title):

        title = title.lower()

        if 'sub' in title:
            title = title.split()
            counter = 0
            for word in title:
                if 'ita' in word:
                    counter += 1
            if counter < 2:
                return True


provider = TNTVillageProvider()
