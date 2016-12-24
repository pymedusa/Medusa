# coding=utf-8
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
"""Provider code for Animetorrents."""
from __future__ import unicode_literals

import re
import traceback

from dateutil import parser

from requests.compat import urljoin
from requests.utils import dict_from_cookiejar

from ..torrent_provider import TorrentProvider
from .... import logger, scene_exceptions, tv_cache
from ....bs4_parser import BS4Parser
from ....helper.common import convert_size
from ....helper.exceptions import AuthException
from ....show_name_helpers import allPossibleShowNames


class AnimeTorrentsProvider(TorrentProvider):
    """AnimeTorrent Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(self.__class__, self).__init__('AnimeTorrents')

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

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tv_cache.TVCache(self, min_time=20)

    def search(self, search_strings, age=0, ep_obj=None):
        """
        Search a provider and parse the results.

        :param search_strings: A dict with mode (key) and the search value (value)
        :param age: Not used
        :param ep_obj: Not used
        :returns: A list of search results (structure)
        """
        results = []

        if self.show and not self.show.is_anime:
            return results

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
            logger.log('Search mode: {0}'.format(mode), logger.DEBUG)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    search_params['search'] = search_string
                    search_params['total'] = 1  # Setting this to 1, makes sure we get 1 big result set.
                    logger.log('Search string: {search}'.format
                               (search=search_string), logger.DEBUG)

                self.headers = headers_paged
                for cat in self.categories:
                    search_params['cat'] = cat
                    response = self.get_url(self.urls['search_ajax'], params=search_params, returns='response')

                    if not response or not response.text or 'Access Denied!' in response.text:
                        logger.log('No data returned from provider', logger.DEBUG)
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
                logger.log('Data returned from provider does not contain any torrents', logger.DEBUG)
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
                    if seeders < min(self.minseed, 1):
                        if mode != 'RSS':
                            logger.log("Discarding torrent because it doesn't meet the "
                                       "minimum seeders: {0}. Seeders: {1}".format
                                       (title, seeders), logger.DEBUG)
                        continue

                    torrent_size = cells[labels.index('Size')].get_text()
                    size = convert_size(torrent_size) or -1

                    pubdate_raw = cells[labels.index('Added')].get_text() if cells[labels.index('Added')] else None
                    pubdate = parser.parse(pubdate_raw) if pubdate_raw else None

                    item = {
                        'title': title,
                        'link': download_url,
                        'size': size,
                        'seeders': seeders,
                        'leechers': leechers,
                        'pubdate': pubdate,
                    }
                    if mode != 'RSS':
                        logger.log('Found result: {0} with {1} seeders and {2} leechers'.format
                                   (title, seeders, leechers), logger.DEBUG)

                    items.append(item)
                except (AttributeError, TypeError, KeyError, ValueError, IndexError):
                    logger.log('Failed parsing provider. Traceback: {0!r}'.format
                               (traceback.format_exc()), logger.ERROR)

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

        request = self.get_url(self.urls['login'], returns='response')
        if not hasattr(request, 'cookies'):
            logger.log('Unable to retrieve the required cookies', logger.WARNING)
            return False

        response = self.get_url(self.urls['login'], post_data=login_params, cookies=request.cookies,
                                returns='response')

        if not response or not response.text:
            logger.log('Unable to connect to provider', logger.WARNING)
            return False

        if re.search(' Login', response.text):
            logger.log('Invalid username or password. Check your settings', logger.WARNING)
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

        season_scene_names = scene_exceptions.get_scene_exceptions(episode.show.indexerid, season=episode.scene_season)

        for show_name in allPossibleShowNames(episode.show, season=episode.scene_season):
            episode_string = '{name}%'.format(name=show_name)

            if season_scene_names and show_name in season_scene_names:
                episode_season = int(episode.scene_episode)
            else:
                episode_season = int(episode.absolute_number)
            episode_string += '{episode}'.format(episode=episode_season)

            if add_string:
                episode_string += '%{string}'.format(string=add_string)

            search_string['Episode'].append(episode_string.strip())

        return [search_string]

    def _get_season_search_strings(self, episode):
        """Create season search string."""
        search_string = {
            'Season': []
        }

        for show_name in allPossibleShowNames(episode.show, season=episode.season):
            search_string['Season'].append(show_name)

        return [search_string]


provider = AnimeTorrentsProvider()
