# coding=utf-8

"""Provider code for Animetorrents."""

from __future__ import unicode_literals

import logging
import re

from medusa import (
    scene_exceptions,
    tv,
)
from medusa.bs4_parser import BS4Parser
from medusa.helper.common import convert_size
from medusa.helper.exceptions import AuthException
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.compat import urljoin
from requests.utils import dict_from_cookiejar

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class AnimeTorrentsProvider(TorrentProvider):
    """AnimeTorrent Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(AnimeTorrentsProvider, self).__init__('AnimeTorrents')

        # Credentials
        self.username = None
        self.password = None

        # URLs
        self.url = 'http://animetorrents.me'
        self.urls = {
            'login': urljoin(self.url, 'login.php'),
            'search_ajax': urljoin(self.url, 'ajax/torrents_data.php'),
        }

        # Miscellaneous Options
        self.supports_absolute_numbering = True
        self.anime_only = True
        self.categories = {
            2: 'Anime Series',
            7: 'Anime Series HD',
        }

        # Proper Strings
        self.proper_strings = []

        # Cache
        self.cache = tv.Cache(self, min_time=20)

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
            'search': '',
            'SearchSubmit': '',
            'page': 1,
            'total': 2,  # Setting this to 2, will make sure we are getting a paged result.
            'searchin': 'filedisc',
            'cat': '',
        }

        headers_paged = dict(self.headers)  # Create copy
        headers_paged.update({
            'X-Requested-With': 'XMLHttpRequest'
        })

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    search_params['search'] = search_string
                    search_params['total'] = 1  # Setting this to 1, makes sure we get 1 big result set.
                    log.debug('Search string: {search}',
                              {'search': search_string})

                self.headers = headers_paged
                for cat in self.categories:
                    search_params['cat'] = cat
                    response = self.session.get(self.urls['search_ajax'], params=search_params)

                    if not response or not response.text or 'Access Denied!' in response.text:
                        log.debug('No data returned from provider')
                        break

                    # Get the rows with results
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

        with BS4Parser(data, 'html5lib') as html:
            torrent_rows = html('tr')

            if not torrent_rows or not len(torrent_rows) > 1:
                log.debug('Data returned from provider does not contain any torrents')
                return items

            # Cat., Active, Filename, Dl, Wl, Added, Size, Uploader, S, L, C
            labels = [label.a.get_text(strip=True) if label.a else label.get_text(strip=True) for label in
                      torrent_rows[0]('th')]

            # Skip column headers
            for row in torrent_rows[1:]:
                try:
                    cells = row.find_all('td', recursive=False)[:len(labels)]
                    if len(cells) < len(labels):
                        continue

                    torrent_name = cells[labels.index('Torrent name')].a
                    title = torrent_name.get_text(strip=True) if torrent_name else None
                    download_url = torrent_name.get('href') if torrent_name else None
                    if not all([title, download_url]):
                        continue

                    slc = cells[labels.index('S')].get_text()
                    seeders, leechers, _ = [int(value.strip()) for value in slc.split('/')] if slc else (0, 0, 0)

                    # Filter unseeded torrent
                    if seeders < self.minseed:
                        if mode != 'RSS':
                            log.debug("Discarding torrent because it doesn't meet the"
                                      ' minimum seeders: {0}. Seeders: {1}',
                                      title, seeders)
                        continue

                    torrent_size = cells[labels.index('Size')].get_text()
                    size = convert_size(torrent_size) or -1

                    pubdate_raw = cells[labels.index('Added')].get_text()
                    pubdate = self.parse_pubdate(pubdate_raw)

                    item = {
                        'title': title,
                        'link': download_url,
                        'size': size,
                        'seeders': seeders,
                        'leechers': leechers,
                        'pubdate': pubdate,
                    }
                    if mode != 'RSS':
                        log.debug('Found result: {0} with {1} seeders and {2} leechers',
                                  title, seeders, leechers)

                    items.append(item)
                except (AttributeError, TypeError, KeyError, ValueError, IndexError):
                    log.exception('Failed parsing provider.')

        return items

    def login(self):
        """Login method used for logging in before doing search and torrent downloads."""
        cookies = dict_from_cookiejar(self.session.cookies)
        if any(cookies.values()) and all([cookies.get('XTZ_USERNAME'), cookies.get('XTZ_PASSWORD'),
                                          cookies.get('XTZUID')]):
            return True

        login_params = {
            'username': self.username,
            'password': self.password,
            'form': 'login',
            'rememberme[]': 1,
        }

        request = self.session.get(self.urls['login'])
        if not hasattr(request, 'cookies'):
            log.warning('Unable to retrieve the required cookies')
            return False

        response = self.session.post(self.urls['login'], data=login_params, cookies=request.cookies)

        if not response or not response.text:
            log.warning('Unable to connect to provider')
            return False

        if re.search(' Login', response.text):
            log.warning('Invalid username or password. Check your settings')
            return False

        return True

    def _check_auth(self):

        if not self.username or not self.password:
            raise AuthException('Your authentication credentials for {0} are missing,'
                                ' check your config.'.format(self.name))

        return True

    def _get_episode_search_strings(self, episode, add_string=''):
        """Get episode search strings."""
        if not episode:
            return []

        search_string = {
            'Episode': []
        }

        season_scene_names = scene_exceptions.get_scene_exceptions(
            episode.series, episode.scene_season
        )

        for show_name in episode.series.get_all_possible_names(season=episode.scene_season):
            if show_name in season_scene_names:
                episode_season = int(episode.scene_episode)
            else:
                episode_season = int(episode.absolute_number)
            episode_string = '{name}%{episode}'.format(
                name=show_name, episode=episode_season
            )

            if add_string:
                episode_string += '%{string}'.format(string=add_string)

            search_string['Episode'].append(episode_string.strip())

        return [search_string]

    def _get_season_search_strings(self, episode):
        """Create season search string."""
        search_string = {
            'Season': []
        }

        for show_name in episode.series.get_all_possible_names(season=episode.season):
            search_string['Season'].append(show_name)

        return [search_string]


provider = AnimeTorrentsProvider()
