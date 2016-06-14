# coding=utf-8
# Author: p0ps
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

from urlparse import parse_qs

from requests.compat import urljoin
from requests.utils import dict_from_cookiejar

from sickbeard import logger, tvcache
from sickbeard.bs4_parser import BS4Parser

from sickrage.helper.common import convert_size
from sickrage.providers.torrent.TorrentProvider import TorrentProvider


class AnimeBytes(TorrentProvider):  # pylint: disable=too-many-instance-attributes

    def __init__(self):

        # Provider Init
        TorrentProvider.__init__(self, 'AnimeBytes')

        # Credentials
        self.username = None
        self.password = None

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # URLs
        self.url = 'https://animebytes.tv/'
        self.urls = {
            'login': urljoin(self.url, '/user/login'),
            'search': urljoin(self.url, 'torrents.php'),
            'download': urljoin(self.url, '/torrent/{torrent_id}/download/{passkey}'),
        }

        # Proper Strings
        self.proper_strings = []

        # Cache
        self.cache = tvcache.TVCache(self, min_time=30)

    def login(self):
        if (any(dict_from_cookiejar(self.session.cookies).values()) and
                dict_from_cookiejar(self.session.cookies).get('session')):
                    return True

        # Get csrf_token
        data = self.get_url(self.urls['login'], returns='text')
        with BS4Parser(data, 'html5lib') as html:
            csrf_token = html.find('input', {'name': 'csrf_token'}).get('value')

        if not csrf_token:
            logger.log("Unable to get csrf_token, can't login", logger.WARNING)
            return False

        login_params = {
            'username': self.username,
            'password': self.password,
            'csrf_token': csrf_token,
            'login': 'Log In!',
            'keeplogged_sent': 'true',
        }

        response = self.get_url(self.urls['login'], post_data=login_params, returns='text')
        if not response:
            logger.log('Unable to connect to provider', logger.WARNING)
            return False

        if re.search('Login incorrect. Only perfect spellers may enter this system!', response):
            logger.log('Invalid username or password. Check your settings', logger.WARNING)
            self.session.cookies.clear()
            return False

        return True

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-locals, too-many-branches
        results = []
        if not self.login():
            return results

        # Search Params
        search_params = {
            'filter_cat[1]': '1',
            'filter_cat[5]': '1',
            'action': 'advanced',
            'search_type': 'title',
            'year': '',
            'year2': '',
            'tags': '',
            'tags_type': '0',
            'sort': 'time_added',
            'way': 'desc',
            'hentai': '2',
            'anime[tv_series]': '1',
            'anime[tv_special]': '1',
            'releasegroup': '',
            'epcount': '',
            'epcount2': '',
            'artbooktitle': '',
        }

        for mode in search_strings:
            items = []
            logger.log('Search Mode: {0}'.format(mode), logger.DEBUG)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    logger.log('Search string: {0}'.format(search_string),
                               logger.DEBUG)
                    search_params['searchstr'] = search_string

                data = self.get_url(self.urls['search'], params=search_params, returns='text')
                if not data:
                    logger.log('No data returned from provider', logger.DEBUG)
                    continue

                with BS4Parser(data, 'html5lib') as html:
                    torrent_div = html.find('div', class_='thin')
                    torrent_group = torrent_div.find_all('div', class_='group_cont box anime')

                    if not torrent_group:
                        logger.log('Data returned from provider does not contain any torrents', logger.DEBUG)
                        continue

                    for group in torrent_group:
                        torrent_main = group.find_all('div', class_='group_main')

                        for row in torrent_main:
                            try:
                                show_title = row.find('span', class_='group_title').find_next('a').get_text()
                                show_table = row.find('table', class_='torrent_group')
                                show_info = show_table.find_all('td')

                                show_name = None
                                rows_to_skip = 0

                                # Complete searies don't have a description td
                                if len(show_info) < 6:
                                    show_name = '{0}.{1}'.format(show_title, 'Complete Series')

                                for index, info in enumerate(show_info):

                                    if rows_to_skip:
                                        rows_to_skip = rows_to_skip - 1
                                        continue

                                    info = info.get_text(strip=True)

                                    if show_name and info.startswith('[DL]'):
                                        # Set skip next 4 rows, as they are useless
                                        rows_to_skip = 4

                                        hrefs = show_info[index].find_all('a')
                                        params = parse_qs(hrefs[0].get('href', ''))
                                        properties = hrefs[1].get_text().split(' | ')
                                        download_url = self.urls['download'].format(torrent_id=params['id'][0],
                                                                                    passkey=params['torrent_pass'][0])
                                        if not all([params, properties]):
                                            continue

                                        torrent_source = properties[0]
                                        torrent_container = properties[1]
                                        torrent_codec = properties[2]
                                        torrent_res = properties[3]
                                        torrent_audio = properties[4]
                                        if len(properties[5].split(' ')) == 2:
                                            subs = properties[5].split(' ')[0]
                                            release_group = properties[5].split(' ')[1].strip('()')

                                        # Construct title
                                        title = '{title}.{torrent_res}.{torrent_source}.{torrent_codec}' \
                                                '-{release_group}'.format(title=show_name,
                                                                          torrent_res=torrent_res,
                                                                          torrent_source=torrent_source,
                                                                          torrent_codec=torrent_codec,
                                                                          release_group=release_group)

                                        seeders = show_info[index + 3].get_text()
                                        leechers = show_info[index + 4].get_text()

                                        # Filter unseeded torrent
                                        if seeders < min(self.minseed, 1):
                                            if mode != 'RSS':
                                                logger.log("Discarding torrent because it doesn't meet the"
                                                           ' minimum seeders: {0}. Seeders: {1}'.format
                                                           (title, seeders), logger.DEBUG)
                                            continue

                                        torrent_size = show_info[index + 1].get_text()
                                        size = convert_size(torrent_size) or -1

                                        item = {
                                            'title': title,
                                            'link': download_url,
                                            'size': size,
                                            'seeders': seeders,
                                            'leechers': leechers,
                                            'pubdate': None,
                                            'hash': None
                                        }
                                        if mode != 'RSS':
                                            logger.log('Found result: {0} with {1} seeders and {2} leechers'.format
                                                       (title, seeders, leechers), logger.DEBUG)

                                        items.append(item)

                                    # Determine name and type
                                    if info.startswith('Episode'):
                                        show_name = '{0}.{1}'.format(show_title, info)
                                    elif info.startswith('Season'):
                                        info = info.split(' (', 1)[0]
                                        show_name = '{0}.{1}'.format(show_title, info)
                                    elif any(word in info for word in ['episodes', 'episode']):
                                        if show_info[index + 1].get_text(strip=True).startswith('Episode'):
                                            # It's not a pack, skip this row
                                            continue
                                        info = info.split('/', 1)[0].strip()
                                        show_name = '{0}.{1}'.format(show_title, info)
                                    else:
                                        # Row is useless, skip it (eg. only animation studio)
                                        continue

                            except (AttributeError, TypeError, KeyError, ValueError, IndexError):
                                logger.log('Failed parsing provider. Traceback: {0!r}'.format
                                           (traceback.format_exc()), logger.ERROR)
                                continue

                results += items

            return results


provider = AnimeBytes()
