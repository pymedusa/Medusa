# coding=utf-8
# Author: p0psicles
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

import medusa as app
from collections import OrderedDict
import logging
from requests.compat import urljoin

from tmdb_api import TMDB

from ..indexer_ui import BaseUI, ConsoleUI
from ..indexer_base import (BaseIndexer, Actors, Actor)
from ..indexer_exceptions import (IndexerError, IndexerException, IndexerShowIncomplete, IndexerShowNotFound)


def log():
    return logging.getLogger('tmdb')


class Tmdb(BaseIndexer):
    """Create easy-to-use interface to name of season/episode name
    >>> t = tmdb()
    >>> t['Scrubs'][1][24]['episodename']
    u'My Last Day'
    """

    def __init__(self, *args, **kwargs):  # pylint: disable=too-many-locals,too-many-arguments
        super(Tmdb, self).__init__(*args, **kwargs)

        self.config['base_url'] = 'http://themoviedb.'

        # Old: self.config['url_artworkPrefix'] = self.config['artwork_prefix']

        self.tmdb = TMDB(app.TMDB_API_KEY)
        self.tmdb_configuration = self.tmdb.Configuration()
        self.response = self.tmdb_configuration.info()

        self.config['artwork_prefix'] = '{base_url}{image_size}{file_path}'

        # An api to indexer series/episode object mapping
        self.series_map = {
            'id': 'id',
            'name': 'seriesname',
            'overview': 'overview',
            'air_date': 'firstaired',
            'first_air_date': 'firstaired',
            'backdrop_path': 'banner',
            'url': 'show_url',
            'epnum': 'absolute_number',
            'episode_name': 'episodename',
            'aired_episode_number': 'episodenumber',
            'season_number': 'seasonnumber',
            'dvd_episode_number': 'dvd_episodenumber',
            'airs_day_of_week': 'airs_dayofweek',
            'last_updated': 'lastupdated',
            'network_id': 'networkid',
            'vote_average': 'contentrating',
            'poster_path': 'poster',
            'episode_run_time': 'runtime',
            'episode_number': 'episodenumber',
            'genres': 'genre',
            'type': 'classification',
            'networks': 'network'
        }

    def _map_results(self, tmdb_response, key_mappings=None, list_separator='|'):
        """
        Map results to a a key_mapping dict.

        :type tmdb_response: object
        """
        parsed_response = []

        if not isinstance(tmdb_response, list):
            tmdb_response = [tmdb_response]

        for item in tmdb_response:
            return_dict = {}
            try:
                for key, value in item.items():
                    if value is None or value == []:
                        continue

                    # Do some value sanitizing
                    if isinstance(value, list):
                        if all(isinstance(x, (str, unicode, int)) for x in value):
                            value = list_separator.join(str(v) for v in value)

                    # Process genres
                    if key == 'genres':
                        value = list_separator.join(item['name'] for item in value)

                    if key == 'networks':
                        value = list_separator.join(item['name'] for item in value)

                    # Try to map the key
                    if key in key_mappings:
                        key = key_mappings[key]

                    # Set value to key
                    return_dict[key] = value

            except Exception as e:
                log().warning('Exception trying to parse attribute: %s, with exception: %r', key, e)

            parsed_response.append(return_dict)

        return parsed_response if len(parsed_response) != 1 else parsed_response[0]

    def _show_search(self, show, request_language='en'):
        """
        Uses the TMDB API to search for a show
        @param show: The show name that's searched for as a string
        @return: A list of Show objects.
        """
        try:
            results = self.tmdb.Search().tv({'query': show, 'language': 'en-US'})
        except Exception as e:
            raise IndexerException('Show search failed in getting a result with error: %r', e)

        if results:
            return results
        else:
            return OrderedDict({'data': None})

    # Tvdb implementation
    def search(self, series):
        """This searches tmdb.com for the series name

        :param series: the query for the series name
        :return: An ordered dict with the show searched for. In the format of OrderedDict{"series": [list of shows]}
        """
        series = series.encode('utf-8')
        log().debug('Searching for show %s', [series])

        results = self._show_search(series, request_language=self.config['language'])

        if not results and not results.get('results', None):
            return

        mapped_results = self._map_results(results.get('results'), self.series_map, '|')

        return OrderedDict({'series': mapped_results})['series']

    def _get_show_by_id(self, tmdb_id, request_language='en'):  # pylint: disable=unused-argument
        """
        Retrieve tmdb show information by tmdb id, or if no tmdb id provided by passed external id.

        :param tmdb_id: The shows tmdb id
        :return: An ordered dict with the show searched for.
        """

        if tmdb_id:
            log().debug('Getting all show data for %s', [tmdb_id])
            results = self.tmdb.TV(tmdb_id).info()

        if not results:
            return

        mapped_results = self._map_results(results, self.series_map, '|')

        return OrderedDict({'series': mapped_results})

    def _get_episodes(self, tmdb_id, specials=False, aired_season=None):  # pylint: disable=unused-argument
        """
        Get all the episodes for a show by tmdb id

        :param tmdb_id: Series tmdb id.
        :return: An ordered dict with the show searched for. In the format of OrderedDict{"episode": [list of episodes]}
        """
        results = []
        if aired_season:
            aired_season = [aired_season] if not isinstance(aired_season, list) else aired_season
        else:
            if tmdb_id not in self.shows:
                self._get_show_by_id(tmdb_id)
            aired_season = [season['season_number'] for season in self.shows[tmdb_id].data.get('seasons')]

        # Parse episode data
        log().debug('Getting all episodes of %s', [tmdb_id])

        # get episodes for each season
        for season in aired_season:
            season_info = self.tmdb.TV_Seasons(tmdb_id, season).info()
            results += season_info['episodes']

        if not results:
            log().debug('Series results incomplete')
            raise IndexerShowIncomplete('Show search returned incomplete results (cannot find complete show on TheTVDB)')

        mapped_episodes = self._map_results(results, self.series_map, '|')
        episode_data = OrderedDict({'episode': mapped_episodes})

        if 'episode' not in episode_data:
            return False

        episodes = episode_data['episode']
        if not isinstance(episodes, list):
            episodes = [episodes]

        for cur_ep in episodes:
            if self.config['dvdorder']:
                log().debug('Using DVD ordering.')
                use_dvd = cur_ep['dvd_season'] != None and cur_ep['dvd_episodenumber'] != None
            else:
                use_dvd = False

            if use_dvd:
                seasnum, epno = cur_ep.get('dvd_season'), cur_ep.get('dvd_episodenumber')
            else:
                seasnum, epno = cur_ep.get('seasonnumber'), cur_ep.get('episodenumber')

            if seasnum is None or epno is None:
                log().warning('An episode has incomplete season/episode number (season: %r, episode: %r)', seasnum, epno)
                continue  # Skip to next episode

            # float() is because https://github.com/dbr/tvnamer/issues/95 - should probably be fixed in TVDB data
            seas_no = int(float(seasnum))
            ep_no = int(float(epno))

            for k, v in cur_ep.items():
                k = k.lower()

                if v is not None:
                    if k == 'still_path':
                        # I'm using the default 'original' quality. But you could also check tmdb_configuration,
                        # for the available image sizes.
                        v = self.config['artwork_prefix'].format(base_url=self.tmdb_configuration.images['base_url'],
                                                                 image_size='original',
                                                                 file_path=v)

                self._set_item(tmdb_id, seas_no, ep_no, k, v)

    def _get_series(self, series):
        """This searches themoviedb.org for the series name,
        If a custom_ui UI is configured, it uses this to select the correct
        series. If not, and interactive == True, ConsoleUI is used, if not
        BaseUI is used to select the first result.

        :param series: the query for the series name
        :return: A list of series mapped to a UI (for example: a BaseUi or CustomUI).
        """

        allSeries = self.search(series)
        if not allSeries:
            log().debug('Series result returned zero')
            IndexerShowNotFound('Show search returned zero results (cannot find show on TVDB)')

        if not isinstance(allSeries, list):
            allSeries = [allSeries]

        if self.config['custom_ui'] is not None:
            log().debug('Using custom UI %s', [repr(self.config['custom_ui'])])
            CustomUI = self.config['custom_ui']
            ui = CustomUI(config=self.config)
        else:
            if not self.config['interactive']:
                log().debug('Auto-selecting first search result using BaseUI')
                ui = BaseUI(config=self.config)
            else:
                log().debug('Interactively selecting show using ConsoleUI')
                ui = ConsoleUI(config=self.config)  # pylint: disable=redefined-variable-type

        return ui.select_series(allSeries)

    def _parse_images(self, sid):
        """Parses images XML, from
        http://thetvdb.com/api/[APIKEY]/series/[SERIES ID]/banners.xml

        images are retrieved using t['show name]['_banners'], for example:

        >>> t = Tvdb(images = True)
        >>> t['scrubs']['_banners'].keys()
        ['fanart', 'poster', 'series', 'season']
        >>> t['scrubs']['_banners']['poster']['680x1000']['35308']['_bannerpath']
        u'http://thetvdb.com/banners/posters/76156-2.jpg'
        >>>

        Any key starting with an underscore has been processed (not the raw
        data from the XML)

        This interface will be improved in future versions.
        """
        key_mapping = {'file_name': 'bannerpath', 'language_id': 'language', 'key_type': 'bannertype', 'resolution': 'bannertype2',
                       'ratings_info': {'count': 'ratingcount', 'average': 'rating'}, 'thumbnail': 'thumbnailpath', 'sub_key': 'sub_key', 'id': 'id'}

        search_for_image_type = self.config['image_type']

        log().debug('Getting show banners for %s', sid)
        _images = {}

        # Let's fget the different type of images available for this series

        try:
            series_images_count = self.series_api.series_id_images_get(sid, accept_language=self.config['language'])
        except Exception as e:
            log().debug('Could not get image count for showid: %s, with exception: %r', sid, e)
            return False

        for image_type, image_count in self._map_results(series_images_count).iteritems():
            try:

                if search_for_image_type and search_for_image_type != image_type:
                    continue

                if not image_count:
                    continue

                if image_type not in _images:
                    _images[image_type] = {}

                images = self.series_api.series_id_images_query_get(sid, key_type=image_type)
                for image in images.data:
                    # Store the images for each resolution available
                    if image.resolution not in _images[image_type]:
                        _images[image_type][image.resolution] = {}

                    # _images[image_type][image.resolution][image.id] = image_dict
                    image_attributes = self._map_results(image, key_mapping)
                    bid = image_attributes.pop('id')
                    _images[image_type][image.resolution][bid] = {}

                    for k, v in image_attributes.items():
                        if k is None or v is None:
                            continue

                        k, v = k.lower(), v.lower()
                        _images[image_type][image.resolution][bid][k] = v

                    for k, v in _images[image_type][image.resolution][bid].items():
                        if k.endswith('path'):
                            new_key = '_%s' % (k)
                            log().debug('Adding base url for image: %s', v)
                            new_url = self.config['artwork_prefix'] % (v)
                            _images[image_type][image.resolution][bid][new_key] = new_url

            except Exception as e:
                log().warning('Could not parse Poster for showid: %s, with exception: %r', sid, e)
                return False

        self._save_images(sid, _images)
        self._set_show_data(sid, '_banners', _images)

    def _parse_actors(self, sid):
        """Parsers actors XML, from
        http://thetvdb.com/api/[APIKEY]/series/[SERIES ID]/actors.xml

        Actors are retrieved using t['show name]['_actors'], for example:

        >>> t = Tvdb(actors = True)
        >>> actors = t['scrubs']['_actors']
        >>> type(actors)
        <class 'tvdb_api.Actors'>
        >>> type(actors[0])
        <class 'tvdb_api.Actor'>
        >>> actors[0]
        <Actor "Zach Braff">
        >>> sorted(actors[0].keys())
        ['id', 'image', 'name', 'role', 'sortorder']
        >>> actors[0]['name']
        u'Zach Braff'
        >>> actors[0]['image']
        u'http://thetvdb.com/banners/actors/43640.jpg'

        Any key starting with an underscore has been processed (not the raw
        data from the XML)
        """
        log().debug('Getting actors for %s', sid)

        actors = self.series_api.series_id_actors_get(sid)

        if not actors or not actors.data:
            log().debug('Actors result returned zero')
            return

        cur_actors = Actors()
        for cur_actor in actors.data if isinstance(actors.data, list) else [actors.data]:
            new_actor = Actor()
            new_actor['id'] = cur_actor.id
            new_actor['image'] = cur_actor.image
            new_actor['name'] = cur_actor.name
            new_actor['role'] = cur_actor.role
            new_actor['sortorder'] = 0
            cur_actors.append(new_actor)
        self._set_show_data(sid, '_actors', cur_actors)

    def _get_show_data(self, sid, language, get_ep_info=False):  # pylint: disable=too-many-branches,too-many-statements,too-many-locals
        """Takes a series ID, gets the epInfo URL and parses the TheTVDB json response
        into the shows dict in layout:
        shows[series_id][season_number][episode_number]
        """
        if self.config['language'] is None:
            log().debug('Config language is none, using show language')
            if language is None:
                raise IndexerError("config['language'] was None, this should not happen")
            get_show_in_language = language
        else:
            log().debug(
                'Configured language %s override show language of %s' % (
                    self.config['language'],
                    language
                )
            )
            get_show_in_language = self.config['language']

        # Parse show information
        log().debug('Getting all series data for %s' % (sid))

        # Parse show information
        series_info = self._get_show_by_id(sid, request_language=get_show_in_language)

        if not series_info:
            log().debug('Series result returned zero')
            raise IndexerError('Series result returned zero')

        # get series data / add the base_url to the image urls
        for k, v in series_info['series'].items():
            if v is not None:
                if k in ['banner', 'fanart', 'poster']:
                    v = self.config['artwork_prefix'].format(base_url=self.tmdb_configuration.images['base_url'],
                                                             image_size='original',
                                                             file_path=v)

            self._set_show_data(sid, k, v)

        # get episode data
        if get_ep_info:
            self._get_episodes(sid, specials=False, aired_season=None)

        # Parse banners
        if self.config['banners_enabled']:
            self._parse_images(sid)

        # Parse actors
        if self.config['actors_enabled']:
            self._parse_actors(sid)

        return True

    # Public methods, usable separate from the default api's interface api['show_id']
    def get_last_updated_series(self, from_time, weeks=1):
        """Retrieve a list with updated shows

        @param from_time: epoch timestamp, with the start date/time
        @param until_time: epoch timestamp, with the end date/time (not mandatory)"""
        total_updates = []
        updates = True

        count = 0
        while updates and count < weeks:
            updates = self.updates_api.updated_query_get(from_time).data
            last_update_ts = max(x.last_updated for x in updates)
            from_time = last_update_ts
            total_updates += updates
            count += 1

        return total_updates

    def get_episodes_for_season(self, show_id, *args, **kwargs):
        self._get_episodes(show_id, *args, **kwargs)
        return self.shows[show_id]
