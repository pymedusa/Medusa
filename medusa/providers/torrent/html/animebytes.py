# coding=utf-8

"""Provider code for AnimeBytes."""

from __future__ import unicode_literals

import logging
import re

from medusa import tv
from medusa.bs4_parser import BS4Parser
from medusa.helper.common import convert_size
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.compat import urljoin
from requests.utils import dict_from_cookiejar


log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())

SEASON_PACK = 1
SINGLE_EP = 2
MULTI_EP = 3
MULTI_SEASON = 4
COMPLETE = 5
OTHER = 6


class AnimeBytes(TorrentProvider):
    """AnimeBytes Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(AnimeBytes, self).__init__('AnimeBytes')

        # Credentials
        self.username = None
        self.password = None

        # URLs
        self.url = 'https://animebytes.tv'
        self.urls = {
            'login': urljoin(self.url, 'user/login'),
            'search': urljoin(self.url, 'torrents.php'),
        }

        # Proper Strings
        self.proper_strings = []

        # Miscellaneous Options
        self.anime_only = True

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tv.Cache(self, min_time=30)

    def search(self, search_strings, age=0, ep_obj=None, **kwargs):
        """
        Search a provider and parse the results.

        :param search_strings: A dict with mode (key) and the search value (value)
        :param age: Not used
        :param ep_obj: Not used
        :returns: A list of search results (structure)
        """
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
            log.debug('Search Mode: {0}', mode)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {search}',
                              {'search': search_string})
                    search_params['searchstr'] = search_string

                response = self.session.get(self.urls['search'], params=search_params)
                if not response or not response.text:
                    log.debug('No data returned from provider')
                    continue

                results += self.parse(response.text, mode)

        return results

    def parse(self, data, mode):
        """
        Parse search results for items.

        :param data: The raw response from a search
        :param mode: The current mode used to search, e.g. RSS

        :return: A list of items found
        """
        items = []

        episode = None
        season = None

        with BS4Parser(data, 'html5lib') as html:
            torrent_div = html.find('div', class_='thin')
            torrent_group = torrent_div('div', class_='group_cont box anime')

            # Continue only if at least one release is found
            if not torrent_group:
                log.debug('Data returned from provider does not contain any torrents')
                return items

            for group in torrent_group:
                torrent_rows = group('div', class_='group_main')

                for row in torrent_rows:
                    try:
                        show_name = row.find('span', class_='group_title').find_next('a').get_text()
                        show_table = row.find('table', class_='torrent_group')
                        show_info = show_table.find_all('td')

                        # A type of release used to determine how to parse the release
                        # For example a SINGLE_EP should be parsed like:
                        # show_name.episode.12.[source].[codec].[release_group]
                        # A multi ep release should look like: show_name.episode.1-12.[source]..
                        release_type = OTHER

                        rows_to_skip = 0

                        for index, info in enumerate(show_info):

                            if rows_to_skip:
                                rows_to_skip -= 1
                                continue

                            info = info.get_text(strip=True)

                            if show_name and info.startswith('[DL]'):
                                # Set skip next 4 rows, as they are useless
                                rows_to_skip = 4

                                hrefs = show_info[index].find_all('a')
                                download_url = hrefs[0].get('href')
                                properties_string = hrefs[1].get_text().rstrip(' |').replace('|', '.').replace(' ', '')
                                # Hack for the h264 10bit stuff
                                properties_string = properties_string.replace('h26410-bit', 'h264.hi10p')
                                properties = properties_string.split('.')
                                if not all([download_url, properties]):
                                    continue

                                tags = '{torrent_source}.{torrent_container}.{torrent_codec}.{torrent_res}.' \
                                       '{torrent_audio}'.format(torrent_source=properties[0],
                                                                torrent_container=properties[1],
                                                                torrent_codec=properties[2],
                                                                torrent_res=properties[3],
                                                                torrent_audio=properties[4])

                                last_field = re.match(r'(.*)\((.*)\)', properties[-1])
                                # subs = last_field.group(1) if last_field else ''
                                # We're not doing anything with this for now
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
                                        log.debug("Discarding torrent because it doesn't meet the"
                                                  " minimum seeders: {0}. Seeders: {1}",
                                                  title, seeders)
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
                                }
                                if mode != 'RSS':
                                    log.debug('Found result: {0} with {1} seeders and {2} leechers',
                                              title, seeders, leechers)

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
                        log.exception('Failed parsing provider.')

        return items

    def login(self):
        """Login method used for logging in before doing search and torrent downloads."""
        if any(dict_from_cookiejar(self.session.cookies).values()) and \
                dict_from_cookiejar(self.session.cookies).get('session'):
            return True

        # Get csrf_index and csrf_token
        csrf_response = self.session.get(self.urls['login'])
        if not csrf_response or not csrf_response.text:
            log.warning('Unable to connect to provider')
            return False

        with BS4Parser(csrf_response.text, 'html5lib') as html:
            csrf_index = html.find('input', {'name': '_CSRF_INDEX'}).get('value')
            csrf_token = html.find('input', {'name': '_CSRF_TOKEN'}).get('value')

        if not all([csrf_index, csrf_token]):
            log.warning("Unable to get csrf_index and csrf_token, can't login")
            return False

        login_params = {
            '_CSRF_INDEX': csrf_index,
            '_CSRF_TOKEN': csrf_token,
            'username': self.username,
            'password': self.password,
            'keeplogged': 'on',
            'login': 'Log In!',
        }

        response = self.session.post(self.urls['login'], data=login_params)
        if not response or not response.text:
            log.warning('Unable to connect to provider')
            return False

        if re.search('You will be banned for 6 hours after your login attempts run out.', response.text):
            log.warning('Invalid username or password. Check your settings')
            self.session.cookies.clear()
            return False

        return True

    def _get_episode_search_strings(self, episode, add_string=''):
        """Override method because AnimeBytes doesn't support searching showname + episode number."""
        if not episode:
            return []

        search_string = {
            'Episode': []
        }

        for show_name in episode.series.get_all_possible_names(season=episode.scene_season):
            search_string['Episode'].append(show_name.strip())

        return [search_string]

    def _get_season_search_strings(self, episode):
        """Override method because AnimeBytes doesn't support searching showname + season number."""
        search_string = {
            'Season': []
        }

        for show_name in episode.series.get_all_possible_names(season=episode.scene_season):
            search_string['Season'].append(show_name.strip())

        return [search_string]


provider = AnimeBytes()
