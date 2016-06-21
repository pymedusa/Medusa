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
from sickbeard.show_name_helpers import allPossibleShowNames


SEASON_PACK = 1
SINGLE_EP = 2
MULTI_EP = 3
MULTI_SEASON = 4
COMPLETE = 5
OTHER = 6


class AnimeBytes(TorrentProvider):  # pylint: disable=too-many-instance-attributes
    """AnimeBytes Torrent provider"""
    def __init__(self):

        # Provider Init
        TorrentProvider.__init__(self, 'AnimeBytes')

        # Credentials
        self.username = None
        self.password = None

        # URLs
        self.url = 'https://animebytes.tv/'
        self.urls = {
            'login': urljoin(self.url, '/user/login'),
            'search': urljoin(self.url, 'torrents.php'),
            'download': urljoin(self.url, '/torrent/{torrent_id}/download/{passkey}'),
        }

        # Proper Strings
        self.proper_strings = []

        # Miscellaneous Options

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tvcache.TVCache(self, min_time=30)

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-locals, too-many-branches
        """
        AnimeBytes search and parsing
        :param search_string: A dict with mode (key) and the search value (value)
        :param age: Not used
        :param ep_obj: Not used
        :returns: A list of search results (structure)
        """
        _ = age
        _ = ep_obj
        results = []

        if self.show and not self.show.is_anime:
            return results

        if not self.login():
            return results

        episode = None
        season = None

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
                                show_name = row.find('span', class_='group_title').find_next('a').get_text()
                                show_table = row.find('table', class_='torrent_group')
                                show_info = show_table.find_all('td')

                                # A type of release used to determine how to parse the release
                                # For example a SINGLE_EP should be parsed like: show_name.episode.12.[source].[codec].[release_group]
                                # A multi ep release shoiuld look like: show_name.episode.1-12.[source]..
                                release_type = OTHER

                                rows_to_skip = 0

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
                                        properties_string = hrefs[1].get_text().rstrip(' |').replace('|', '.').replace(' ', '')
                                        properties_string = properties_string.replace('h26410-bit', 'h264.hi10p')  # Hack for the h264 10bit stuff
                                        properties = properties_string.split('.')
                                        download_url = self.urls['download'].format(torrent_id=params['id'][0],
                                                                                    passkey=params['torrent_pass'][0])
                                        if not all([params, properties]):
                                            continue

                                        tags = '{torrent_source}.{torrent_container}.{torrent_codec}.{torrent_res}.' \
                                               '{torrent_audio}'.format(torrent_source=properties[0],
                                                                        torrent_container=properties[1],
                                                                        torrent_codec=properties[2],
                                                                        torrent_res=properties[3],
                                                                        torrent_audio=properties[4])

                                        last_field = re.match(r'(.*)\((.*)\)', properties[-1])
                                        # subs = last_field.group(1) if last_field else ''  # We're not doing anything with this for now
                                        release_group = '-{0}'.format(last_field.group(2)) if last_field else ''

                                        # Construct title based on the release type

                                        if release_type == SINGLE_EP:
                                            # Create the single episode release_name
                                            # Single.Episode.TV.Show.SXXEXX[Episode.Part].[Episode.Title].TAGS.[LANGUAGE].720p.FORMAT.x264-GROUP
                                            title = '{title}.{season}{episode}.{tags}' \
                                                    '{release_group}'.format(title=show_name,
                                                                             season='S{0}'.format(season) if season else 'S01',
                                                                             episode='E{0}'.format(episode),
                                                                             tags=tags,
                                                                             release_group=release_group)
                                        if release_type == MULTI_EP:
                                            # Create the multi-episode release_name
                                            # Multiple.Episode.TV.Show.SXXEXX-EXX[Episode.Part].[Episode.Title].TAGS.[LANGUAGE].720p.FORMAT.x264-GROUP
                                            title = '{title}.{season}{multi_episode}.{tags}' \
                                                    '{release_group}'.format(title=show_name,
                                                                             season='S{0}'.format(season) if season else 'S01',
                                                                             multi_episode='E01-E{0}'.format(episode),
                                                                             tags=tags,
                                                                             release_group=release_group)
                                        if release_type == SEASON_PACK:
                                            # Create the season pack release_name
                                            title = '{title}.{season}.{tags}' \
                                                    '{release_group}'.format(title=show_name,
                                                                             season='S{0}'.format(season) if season else 'S01',
                                                                             tags=tags,
                                                                             release_group=release_group)

                                        if release_type == MULTI_SEASON:
                                            # Create the multi season pack release_name
                                            # Multiple.Episode.TV.Show.EXX-EXX[Episode.Part].[Episode.Title].TAGS.[LANGUAGE].720p.FORMAT.x264-GROUP
                                                title = '{title}.{episode}.{tags}' \
                                                        '{release_group}'.format(title=show_name,
                                                                                 episode=episode,
                                                                                 tags=tags,
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

                                    # Determine episode, season and type
                                    if info.startswith('Episode'):
                                        # show_name = '{0}.{1}'.format(show_title, info)
                                        episode = re.match('^Episode.([0-9]+)', info).group(1)
                                        release_type = SINGLE_EP
                                    elif info.startswith('Season'):
                                        # Test for MultiSeason pack
                                        if re.match('Season.[0-9]+-[0-9]+.\([0-9-]+\)', info):
                                            # We can read the season AND the episodes, but we can only process multiep.
                                            # So i've chosen to use it like 12-23 or 1-12.
                                            match = re.match('Season.([0-9]+)-([0-9]+).\(([0-9-]+)\)', info)
                                            episode = match.group(3).upper()
                                            season = '{0}-{1}'.format(match.group(1), match.group(2))
                                            release_type = MULTI_SEASON
                                        else:
                                            season = re.match('Season.([0-9]+)', info).group(1)
                                            # show_name = '{0}.{1}'.format(show_title, info)
                                            release_type = SEASON_PACK
                                    elif re.match('([0-9]+).episodes.*', info):
                                        # This is a season pack, but, let's use it as a multi ep for now
                                        # 13 episodes -> SXXEXX-EXX
                                        episode = re.match('^([0-9]+).episodes.*', info).group(1)
                                        release_type = MULTI_EP
                                    else:
                                        # Row is useless, skip it (eg. only animation studio)
                                        continue

                            except (AttributeError, TypeError, KeyError, ValueError, IndexError):
                                logger.log('Failed parsing provider. Traceback: {0!r}'.format
                                           (traceback.format_exc()), logger.ERROR)
                                continue

            results += items

        return results

    def login(self):
        """Login to AnimeBytes, check of the session cookie"""
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

    def _get_episode_search_strings(self, episode, add_string=''):
        """Method override because AnimeBytes doesnt support searching showname + episode number"""
        if not episode:
            return []

        search_string = {
            'Episode': []
        }

        for show_name in allPossibleShowNames(episode.show, season=episode.scene_season):
            search_string['Episode'].append(show_name.strip())

        return [search_string]

    def _get_season_search_strings(self, episode):
        """Method override because AnimeBytes doesnt support searching showname + season number"""
        search_string = {
            'Season': []
        }

        for show_name in allPossibleShowNames(episode.show, season=episode.scene_season):
            search_string['Season'].append(show_name.strip())

        return [search_string]


provider = AnimeBytes()
