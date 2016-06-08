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

from requests.compat import urljoin
from requests.utils import dict_from_cookiejar

from sickbeard import logger, tvcache
from sickbeard.bs4_parser import BS4Parser

from sickrage.helper.common import convert_size
from sickrage.providers.torrent.TorrentProvider import TorrentProvider
from sickbeard.show_name_helpers import allPossibleShowNames


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

        # Login
        response = self.get_url(self.urls['login'], post_data=login_params, returns='text')
        if not response:
            logger.log('Unable to connect to provider', logger.WARNING)
            return False

        if not re.search('torrents.php', response):
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
                    search_params["searchstr"] = search_string

                data = self.get_url(self.urls['search'], params=search_params, returns='text')
                if not data:
                    continue

                with BS4Parser(data, 'html5lib') as html:
                    group_cont = html.find_all(True, {'class': 'group_cont'})

                    for group in group_cont:
                        results += self.parse(group, search_string)

        return results

    def parse(self, html, search_string):
        """Parse the result"""
        items = []

        # Get genaral box info
        group_title = html.find('span', class_='group_title')
        show_title = group_title.find_all('a')[0].get_text()
        category = group_title.find_all('a')[1].get_text()

        if category != 'TV Series':
            return items

        get_rows = html.find_all('tr', {'class': ['edition_info', 'torrent']})
        start_parsing_season = False
        for row in get_rows:
            if 'Season' in row.get_text():
                season = row.get_text().split(' ')[1]
                start_parsing_season = True

            if start_parsing_season:
                if 'torrent' in row['class']:
                    torrent_url = urljoin(self.url, row.find('a')['href'])
                    properties = row.find_all('a')[-1].get_text().split(' | ')
                    torrent_source = properties[0]
                    torrent_container = properties[1]
                    torrent_codec = properties[2]
                    torrent_res = properties[3]
                    torrent_audio = properties[4]
                    if len(properties[5].split(' ')) == 2:
                        subs = properties[5].split(' ')[0]
                        release_group = properties[5].split(' ')[1].strip('()')
                    torrent_size = row.find('td', class_='torrent_size').get_text()
                    size = convert_size(torrent_size) or -1
                    torrent_seeders = row.find('td', class_='torrent_seeders').get_text()
                    torrent_leechers = row.find('td', class_='torrent_leechers').get_text()
                    # lets wrap up and create this release
                    release_name = '{title}.Season.{season}.{torrent_res}.{torrent_source}.' \
                                   '{torrent_codec}.-{release_group}'.format(title=search_string, season=season.lstrip('0'), torrent_res=torrent_res,
                                                                             torrent_source=torrent_source, torrent_codec=torrent_codec,
                                                                             release_group=release_group)
                    item = {'title': release_name, 'link': torrent_url, 'size': size,
                            'seeders': torrent_seeders, 'leechers': torrent_leechers, 'pubdate': None, 'hash': None}
                    items.append(item)
        return items

    def _get_episode_search_strings(self, episode, add_string=''):
        return []

    def _get_season_search_strings(self, episode):
        search_string = {
            'Season': []
        }

        for show_name in allPossibleShowNames(episode.show, season=episode.scene_season):
            search_string['Season'].append(show_name)

        return [search_string]

provider = AnimeBytes()