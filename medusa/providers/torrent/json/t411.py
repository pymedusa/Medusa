# coding=utf-8

"""Torrent Provider T411."""


from __future__ import unicode_literals

import logging
import time
import traceback
from collections import namedtuple
from operator import itemgetter

from contextlib2 import suppress

from medusa import (
    config,
    tv,
)
from medusa.common import USER_AGENT
from medusa.helper.common import (
    convert_size,
    try_int,
)
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.torrent.torrent_provider import TorrentProvider
from medusa.scene_exceptions import get_scene_exceptions

from requests.auth import AuthBase
from requests.compat import quote, urljoin

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())

# Map episode number to the T411 search term for that episode
EPISODE_MAP = {
    0: 936, 1: 937, 2: 938, 3: 939, 4: 940, 5: 941, 6: 942, 7: 943, 8: 944, 9: 946, 10: 947, 11: 948, 12: 949, 13: 950,
    14: 951, 15: 952, 16: 954, 17: 953, 18: 955, 19: 956, 20: 957, 21: 958, 22: 959, 23: 960, 24: 961, 25: 962, 26: 963,
    27: 964, 28: 965, 29: 966, 30: 967, 31: 1088, 32: 1089, 33: 1090, 34: 1091, 35: 1092, 36: 1093, 37: 1094, 38: 1095,
    39: 1096, 40: 1097, 41: 1098, 42: 1099, 43: 1100, 44: 1101, 45: 1102, 46: 1103, 47: 1104, 48: 1105, 49: 1106,
    50: 1107, 51: 1108, 52: 1109, 53: 1110, 54: 1111, 55: 1112, 56: 1113, 57: 1114, 58: 1115, 59: 1116, 60: 1117,
}

# Map season number to the T411 search term for that season
SEASON_MAP = {
    1: 968, 2: 969, 3: 970, 4: 971, 5: 972, 6: 973, 7: 974, 8: 975, 9: 976, 10: 977, 11: 978, 12: 979, 13: 980, 14: 981,
    15: 982, 16: 983, 17: 984, 18: 985, 19: 986, 20: 987, 21: 988, 22: 989, 23: 990, 24: 991, 25: 994, 26: 992, 27: 993,
    28: 995, 29: 996, 30: 997,
}


class T411Provider(TorrentProvider):
    """T411 Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(T411Provider, self).__init__("T411")

        # Credentials
        self.username = None
        self.password = None
        self.token = None
        self.tokenLastUpdate = None

        # URLs
        self.url = 'https://api.t411.al'
        self.urls = {
            'search': urljoin(self.url, 'torrents/search/{search}'),
            'rss': urljoin(self.url, 'torrents/top/today'),
            'login_page': urljoin(self.url, 'auth'),
            'download': urljoin(self.url, 'torrents/download/{id}'),
        }

        # Proper Strings

        # Miscellaneous Options
        self.headers.update({'User-Agent': USER_AGENT})
        self.subcategories = (
            # 402,  # Video Clips (Vid�o-clips)
            433,  # TV Series (S�rie TV)
            455,  # Animation
            # 631,  # Film
            # 633,  # Concert
            # 634,  # Documentary (Documentaire)
            # 635,  # Show (Spectacle)
            636,  # Sport
            637,  # Animations (Animation S�rie)
            639,  # TV Programs (Emission TV)
        )

        self.confirmed = False

        # Torrent Stats
        self.minseed = 0
        self.minleech = 0

        # Cache
        self.cache = tv.Cache(self, min_time=10)  # Only poll T411 every 10 minutes max

    def _get_season_search_strings(self, episode):
        """Get season search strings."""
        if not episode:
            return []

        search_string = {
            'Season': []
        }

        for series in episode.show.get_all_possible_names(season=episode.scene_season):
            episode_string = series + ' '

            if episode.show.air_by_date or episode.show.sports:
                episode_string += str(episode.airdate).split('-')[0]
            elif episode.show.anime:
                episode_string += 'Season'
            elif episode.scene_season > max(SEASON_MAP):
                # Check if season and episode are within the mapped values. Otherwise use normal search.
                episode_string += 'S{season:0>2}'.format(season=episode.scene_season)

            search_string['Season'].append(episode_string.strip())
        return [search_string]

    def _get_episode_search_strings(self, episode, add_string=''):
        """Get episode search strings."""
        if not episode:
            return []

        search_string = {
            'Episode': []
        }

        for series in episode.show.get_all_possible_names(season=episode.scene_season):
            episode_string = series + self.search_separator

            if episode.show.air_by_date:
                episode_string += str(episode.airdate).replace('-', ' ')
            elif episode.show.sports:
                episode_string += str(episode.airdate).replace('-', ' ')
                episode_string += ('|', ' ')[len(self.proper_strings) > 1]
                episode_string += episode.airdate.strftime('%b')
            elif episode.show.anime:
                # If the series is a season scene exception, we want to use the indexer episode number.
                if (episode.scene_season > 1 and
                    series in get_scene_exceptions(episode.show.indexerid,
                                                   episode.show.indexer,
                                                   episode.scene_season)):
                    # This is apparently a season exception, let's use the scene_episode instead of absolute
                    ep = episode.scene_episode
                else:
                    ep = episode.scene_absolute_number
                episode_string += '{episode:0>2}'.format(episode=ep)
            elif episode.scene_season > max(SEASON_MAP) or episode.scene_episode > max(EPISODE_MAP):
                # Check if season and episode are not within the mapped values.
                # In that case we are not going to search using season and episode parameters. And we need
                # contruct a search term.
                episode_string += config.naming_ep_type[2] % {
                    'seasonnumber': episode.scene_season,
                    'episodenumber': episode.scene_episode,
                }

            search_string['Episode'].append(episode_string.strip())

        return [search_string]

    def search(self, search_strings, age=0, ep_obj=None):
        """
        Search T411 and parse the results.

        T411 has custom parameters for searching by term

        To add a term to a search you add the param term[id] where id is the number
        of the desired term, and the value is the categories desired for that term.
        Commonly used term IDs are 45 (season) and 46 (episode).

        For normal season and episode searches it will use the term parameters
        season and episode term parameters for categories that support them.
        For example:
            # search for an entire season (term id for season 1 is 968)
            requests.get(search_url, params={'term[45][]': 968})

            # search for an episode (term id for season 1 is 968, for episode 1 is 936)
            requests.get(search_url, params={'term[45][]':968, 'term[46][]': 936})

        A normal string search, without terms, will be used in some cases. Searching
        without terms returns lot of bad results, but is sometimes the only option.
        Some examples of when a normal string search will be used is for air-by-date
        series, season or episodes without a corresponding term id, or when searching
        categories that do not support the specific term (e.g. the sports category
        which does not support season and episode).

        :param search_strings: A dict with mode (key) and the search value (value).
        :param age: Not used
        :param ep_obj: Not used
        :returns: A list of search results (structure)
        """
        results = []
        if not self.login():
            return results

        # Search Params
        search_params = {}

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            for search_string in search_strings[mode]:
                if mode != 'RSS':

                    if self.confirmed:
                        log.debug('Searching only confirmed torrents')

                    # use string formatting to safely coerce the search term
                    # to unicode then utf-8 encode the unicode string
                    term = '{term}'.format(term=search_string).encode('utf-8')
                    # build the search URL
                    search_url = self.urls['search'].format(
                        search=quote(term)  # URL encode the search term
                    )
                    categories = self.subcategories
                    search_params.update({'limit': 100})

                    # Search using season and episode specific params only for normal episodes
                    if all(
                        [not ep_obj.show.air_by_date,
                         not ep_obj.show.sports,
                         not ep_obj.show.anime,
                         ep_obj.scene_season <= max(SEASON_MAP) and ep_obj.scene_episode <= max(EPISODE_MAP)]
                    ):
                        if mode == 'Season':
                            search_params.update({'term[46][]': EPISODE_MAP.get(0)})
                        else:
                            search_params.update({'term[46][]': EPISODE_MAP.get(ep_obj.scene_episode)})
                        search_params.update({'term[45][]': SEASON_MAP.get(ep_obj.scene_season)})
                        log.debug('Search params: Name: {series}. Season: {season} Episode: {episode}',
                                  {'series': search_string, 'season': ep_obj.scene_season, 'episode': ep_obj.scene_episode})
                    else:
                        log.debug('Search string: {search}', {'search': search_string})

                else:
                    search_url = self.urls['rss']
                    # Using None as a category removes it as a search param
                    categories = [None]  # Must be a list for iteration

                for category in categories:
                    search_params.update({'cid': category})
                    response = self.get_url(
                        search_url, params=search_params, returns='response'
                    )

                    if not response or not response.content:
                        log.debug('No data returned from provider')
                        continue

                    try:
                        jdata = response.json()
                    except ValueError:
                        log.debug('No data returned from provider')
                        continue

                    results += self.parse(jdata, mode)

        return results

    def parse(self, data, mode):
        """
        Parse search results for items.

        :param data: The raw response from a search
        :param mode: The current mode used to search, e.g. RSS

        :return: A list of items found
        """
        items = []

        unsorted_torrent_rows = data.get('torrents') if mode != 'RSS' else data

        if not unsorted_torrent_rows:
            log.debug(
                'Data returned from provider does not contain any {torrents}',
                {'torrents': 'confirmed torrents' if self.confirmed else 'torrents'}
            )
            return items

        torrent_rows = sorted(unsorted_torrent_rows, key=itemgetter('added'), reverse=True)

        for row in torrent_rows:
            if not isinstance(row, dict):
                log.warning('Invalid data returned from provider')
                continue

            if mode == 'RSS' and 'category' in row and try_int(row['category'], 0) not in self.subcategories:
                continue

            try:
                title = row['name']
                torrent_id = row['id']
                download_url = self.urls['download'].format(id=torrent_id)
                if not all([title, download_url]):
                    continue

                seeders = try_int(row['seeders'])
                leechers = try_int(row['leechers'])
                verified = bool(row['isVerified'])

                # Filter unseeded torrent
                if seeders < min(self.minseed, 1):
                    if mode != 'RSS':
                        log.debug("Discarding torrent because it doesn't meet the"
                                  " minimum seeders: {0}. Seeders: {1}",
                                  title, seeders)
                    continue

                if self.confirmed and not verified and mode != 'RSS':
                    log.debug("Found result {0} but that doesn't seem like a verified"
                              " result so I'm ignoring it", title)
                    continue

                torrent_size = row['size']
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
            except (AttributeError, TypeError, KeyError, ValueError, IndexError):
                log.error('Failed parsing provider. Traceback: {0!r}',
                          traceback.format_exc())

        return items

    def login(self):
        """Log into provider."""
        if self.token is not None:
            if time.time() < (self.tokenLastUpdate + 30 * 60):
                return True

        login_params = {
            'username': self.username,
            'password': self.password,
        }

        response = self.get_url(self.urls['login_page'], post_data=login_params, returns='json')
        if not response:
            log.warning('Unable to connect to provider')
            return False

        if response and 'token' in response:
            self.token = response['token']
            self.tokenLastUpdate = time.time()
            # self.uid = response['uid'].encode('ascii', 'ignore')
            self.session.auth = T411Auth(self.token)
            return True
        else:
            log.warning('Token not found in authentication response')
            return False


class T411Auth(AuthBase):
    """Attach HTTP Authentication to the given Request object."""

    def __init__(self, token):
        """Init object."""
        self.token = token

    def __call__(self, r):
        """Add token to request header."""
        r.headers['Authorization'] = self.token
        return r


provider = T411Provider()
