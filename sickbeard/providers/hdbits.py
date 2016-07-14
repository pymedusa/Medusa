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

from __future__ import unicode_literals

import datetime
import json

from requests.compat import urlencode, urljoin

from sickbeard import classes, logger, tvcache

from sickrage.helper.exceptions import AuthException
from sickrage.providers.torrent.TorrentProvider import TorrentProvider


class HDBitsProvider(TorrentProvider):
    """HDBits Torrent provider"""
    def __init__(self):

        # Provider Init
        TorrentProvider.__init__(self, 'HDBits')

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

        # FIXME
        results = []

        logger.log('Search string: {0}'.format(search_strings), logger.DEBUG)

        self._check_auth()

        parsed_json = self.get_url(self.urls['search'], post_data=search_strings, returns='json')
        if not parsed_json:
            return []

        if self._check_auth_from_data(parsed_json):
            if parsed_json and 'data' in parsed_json:
                items = parsed_json['data']
            else:
                logger.log("Resulting JSON from provider isn't correct, not parsing it", logger.ERROR)
                items = []

            for item in items:
                results.append(item)
        # FIXME SORTING
        return results

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

    def find_propers(self, search_date=None):
        results = []

        search_terms = [' proper ', ' repack ']

        for term in search_terms:
            for item in self.search(self._make_post_data_json(search_term=term)):
                if item['utadded']:
                    try:
                        result_date = datetime.datetime.fromtimestamp(int(item['utadded']))
                    except Exception:
                        result_date = None

                    if result_date:
                        if not search_date or result_date > search_date:
                            title, url = self._get_title_and_url(item)
                            results.append(classes.Proper(title, url, result_date, self.show))

        return results

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
                    'episode': '%i' % int(episode.scene_absolute_number)
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
                    'season': '%d' % season.scene_absolute_number,
                }
            else:
                post_data['tvdb'] = {
                    'id': show.indexerid,
                    'season': season.scene_season,
                }

        if search_term:
            post_data['search'] = search_term

        return json.dumps(post_data)


class HDBitsCache(tvcache.TVCache):
    def _getRSSData(self):
        self.search_params = None  # HDBits cache does not use search_params so set it to None
        results = []

        try:
            parsed_json = self.provider.getURL(self.provider.urls['rss'], post_data=self.provider._make_post_data_json(), returns='json')

            if self.provider._check_auth_from_data(parsed_json):
                results = parsed_json['data']
        except Exception:
            pass

        return {'entries': results}


provider = HDBitsProvider()
