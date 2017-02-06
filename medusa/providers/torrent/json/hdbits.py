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
"""Provider code for HDBits."""
from __future__ import unicode_literals

import json

from medusa import (
    logger,
    tv,
)
from medusa.helper.exceptions import AuthException
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.compat import urlencode, urljoin


class HDBitsProvider(TorrentProvider):
    """HDBits Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(self.__class__, self).__init__('HDBits')

        # Credentials
        self.username = None
        self.passkey = None

        # URLs
        self.url = 'https://hdbits.org'
        self.urls = {
            'search': urljoin(self.url, '/api/torrents'),
            'rss': urljoin(self.url, '/api/torrents'),
            'download': urljoin(self.url, '/download.php'),
        }

        # Proper Strings

        # Miscellaneous Options

        # Torrent Stats

        # Cache
        self.cache = HDBitsCache(self, min_time=15)  # only poll HDBits every 15 minutes max

    def search(self, search_strings, age=0, ep_obj=None):
        """
        Search a provider and parse the results.

        :param search_strings: A dict with mode (key) and the search value (value)
        :param age: Not used
        :param ep_obj: Not used
        :returns: A list of search results (structure)
        """
        # FIXME
        results = []

        logger.log('Search string: {0}'.format(search_strings), logger.DEBUG)

        self._check_auth()

        response = self.get_url(self.urls['search'], post_data=search_strings, returns='response')
        if not response or not response.content:
            logger.log('No data returned from provider', logger.DEBUG)
            return results

        if not self._check_auth_from_data(response):
            return results

        try:
            jdata = response.json()
        except ValueError:  # also catches JSONDecodeError if simplejson is installed
            logger.log('No data returned from provider', logger.DEBUG)
            return results

        results += self.parse(jdata, None)

        return results

    def parse(self, data, mode):
        """
        Parse search results for items.

        :param data: The raw response from a search
        :param mode: The current mode used to search, e.g. RSS

        :return: A list of items found
        """
        items = []

        torrent_rows = data.get('data')
        if not torrent_rows:
            logger.log("Resulting JSON from provider isn't correct, not parsing it", logger.ERROR)

        for row in torrent_rows:
            items.append(row)

        # FIXME SORTING
        return items

    def _check_auth(self):

        if not self.username or not self.passkey:
            raise AuthException('Your authentication credentials for ' + self.name + ' are missing, check your config.')

        return True

    def _check_auth_from_data(self, parsed_json):

        if 'status' in parsed_json and 'message' in parsed_json:
            if parsed_json.get('status') == 5:
                logger.log('Invalid username or password. Check your settings', logger.WARNING)

        return True

    def _get_title_and_url(self, item):
        title = item.get('name', '').replace(' ', '.')
        url = self.urls['download'] + '?' + urlencode({'id': item['id'], 'passkey': self.passkey})

        return title, url

    def _get_season_search_strings(self, ep_obj):
        season_search_string = [self._make_post_data_json(show=ep_obj.show, season=ep_obj)]
        return season_search_string

    def _get_episode_search_strings(self, ep_obj, add_string=''):
        episode_search_string = [self._make_post_data_json(show=ep_obj.show, episode=ep_obj)]
        return episode_search_string

    def _make_post_data_json(self, show=None, episode=None, season=None, search_term=None):
        post_data = {
            'username': self.username,
            'passkey': self.passkey,
            'category': [2],
            # TV Category
        }

        if episode:
            if show.air_by_date:
                post_data['tvdb'] = {
                    'id': show.indexerid,
                    'episode': str(episode.airdate).replace('-', '|')
                }
            elif show.sports:
                post_data['tvdb'] = {
                    'id': show.indexerid,
                    'episode': episode.airdate.strftime('%b')
                }
            elif show.anime:
                post_data['tvdb'] = {
                    'id': show.indexerid,
                    'episode': "{0}".format(episode.scene_absolute_number)
                }
            else:
                post_data['tvdb'] = {
                    'id': show.indexerid,
                    'season': episode.scene_season,
                    'episode': episode.scene_episode
                }

        if season:
            if show.air_by_date or show.sports:
                post_data['tvdb'] = {
                    'id': show.indexerid,
                    'season': str(season.airdate)[:7],
                }
            elif show.anime:
                post_data['tvdb'] = {
                    'id': show.indexerid,
                    'season': "{0}".format(season.scene_absolute_number),
                }
            else:
                post_data['tvdb'] = {
                    'id': show.indexerid,
                    'season': season.scene_season,
                }

        if search_term:
            post_data['search'] = search_term

        return json.dumps(post_data)


class HDBitsCache(tv.Cache):
    """Provider cache class."""

    def _get_rss_data(self):
        """Get RSS data."""
        self.search_params = None  # HDBits cache does not use search_params so set it to None
        results = []

        try:
            parsed_json = self.provider.get_url(self.provider.urls['rss'],
                                                post_data=self.provider._make_post_data_json(), returns='json')

            if self.provider._check_auth_from_data(parsed_json):
                results = parsed_json['data']
        except Exception:
            pass

        return {'entries': results}


provider = HDBitsProvider()
