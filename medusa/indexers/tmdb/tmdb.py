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

from tmdb_api import TMDB

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

        self.tmdb = TMDB(app.TMDB_API_KEY, session=self.config['session'])
        self.tmdb_configuration = self.tmdb.Configuration()
        self.response = self.tmdb_configuration.info()

        self.config['artwork_prefix'] = '{base_url}{image_size}{file_path}'

        # An api to indexer series/episode object mapping
        self.series_map = {
            'id': 'id',
            'name': 'seriesname',
            'original_name': 'aliasnames',
            'overview': 'overview',
            'air_date': 'firstaired',
            'first_air_date': 'firstaired',
            'backdrop_path': 'fanart',
            'url': 'show_url',
            'episode_number': 'episodenumber',
            'season_number': 'seasonnumber',
            'dvd_episode_number': 'dvd_episodenumber',
            'airs_day_of_week': 'airs_dayofweek',
            'last_updated': 'lastupdated',
            'network_id': 'networkid',
            'vote_average': 'contentrating',
            'poster_path': 'poster',
            'genres': 'genre',
            'type': 'classification',
            'networks': 'network'
        }

        self.episodes_map = {
            'id': 'id',
            'name': 'episodename',
            'overview': 'overview',
            'air_date': 'firstaired',
            'episode_run_time': 'runtime',
            'episode_number': 'episodenumber',
            'season_number': 'seasonnumber',
            'still_path': 'poster',
            'vote_average': 'contentrating',
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
        :param show: The show name that's searched for as a string
        :param request_language: Language in two letter code. TMDB fallsback to en itself.
        :return: A list of Show objects.
        """
        try:
            # get paginated pages
            page = 1
            last = 1
            results = []
            while page <= last:
                search_result = self.tmdb.Search().tv({'query': show,
                                                       'language': request_language,
                                                       'page': page})
                last = search_result.get('total_pages', 0)
                results += search_result.get('results')
                page += 1
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

        if not results:
            return

        mapped_results = self._map_results(results, self.series_map, '|')

        return OrderedDict({'series': mapped_results})['series']

    def _get_show_by_id(self, tmdb_id, request_language='en'):  # pylint: disable=unused-argument
        """
        Retrieve tmdb show information by tmdb id, or if no tmdb id provided by passed external id.

        :param tmdb_id: The shows tmdb id
        :return: An ordered dict with the show searched for.
        """

        if tmdb_id:
            log().debug('Getting all show data for %s', [tmdb_id])
            results = self.tmdb.TV(tmdb_id).info({'language': '{0},null'.format(request_language)})

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
            season_info = self.tmdb.TV_Seasons(tmdb_id, season).info({'language': self.config['language']})
            results += season_info['episodes']

        if not results:
            log().debug('Series results incomplete')
            raise IndexerShowIncomplete('Show search returned incomplete results '
                                        '(cannot find complete show on TheMovieDb)')

        mapped_episodes = self._map_results(results, self.episodes_map, '|')
        episode_data = OrderedDict({'episode': mapped_episodes})

        if 'episode' not in episode_data:
            return False

        episodes = episode_data['episode']
        if not isinstance(episodes, list):
            episodes = [episodes]

        for cur_ep in episodes:
            if self.config['dvdorder']:
                log().debug('Using DVD ordering.')
                use_dvd = cur_ep['dvd_season'] is not None and cur_ep['dvd_episodenumber'] is not None
            else:
                use_dvd = False

            if use_dvd:
                seasnum, epno = cur_ep.get('dvd_season'), cur_ep.get('dvd_episodenumber')
            else:
                seasnum, epno = cur_ep.get('seasonnumber'), cur_ep.get('episodenumber')

            if seasnum is None or epno is None:
                log().warning('An episode has incomplete season/episode number (season: %r, episode: %r)', seasnum, epno)
                continue  # Skip to next episode

            seas_no = int(seasnum)
            ep_no = int(epno)

            image_width = {'fanart': 'w1280', 'poster': 'w780'}
            for k, v in cur_ep.items():
                k = k.lower()

                if v is not None:
                    if k in ['fanart', 'poster']:
                        # I'm using the default 'original' quality. But you could also check tmdb_configuration,
                        # for the available image sizes.
                        v = self.config['artwork_prefix'].format(base_url=self.tmdb_configuration.images['base_url'],
                                                                 image_size=image_width[k],
                                                                 file_path=v)

                self._set_item(tmdb_id, seas_no, ep_no, k, v)

    def _parse_images(self, sid):
        """Parses images XML, from
        http://theTMDB.com/api/[APIKEY]/series/[SERIES ID]/banners.xml

        images are retrieved using t['show name]['_banners'], for example:

        >>> t = TMDB(images = True)
        >>> t['scrubs']['_banners'].keys()
        ['fanart', 'poster', 'series', 'season']
        >>> t['scrubs']['_banners']['poster']['680x1000']['35308']['_bannerpath']
        u'http://theTMDB.com/banners/posters/76156-2.jpg'
        >>>

        Any key starting with an underscore has been processed (not the raw
        data from the XML)

        This interface will be improved in future versions.
        """
        key_mapping = {'file_path': 'bannerpath', 'vote_count': 'ratingcount', 'vote_average': 'rating', 'id': 'id'}
        image_sizes = {'fanart': 'backdrop_sizes', 'poster': 'poster_sizes'}

        search_for_image_type = self.config['image_type']

        log().debug('Getting show banners for %s', sid)
        _images = {}

        # Let's fget the different type of images available for this series
        params = {'include_image_language': '{search_language},null'.format(search_language=self.config['language'])}

        images = self.tmdb.TV(sid).images(params=params)
        bid = images['id']
        for image_type, images in {'poster': images['posters'], 'fanart': images['backdrops']}.iteritems():
            try:
                if image_type not in _images:
                    _images[image_type] = {}

                for image in images:
                    image_mapped = self._map_results(image, key_mappings=key_mapping)

                    for size in self.tmdb_configuration.images.get(image_sizes[image_type]):
                        if size == 'original':
                            width = image_mapped['width']
                            height = image_mapped['height']
                        else:
                            width = int(size[1:])
                            height = int(round(width / image_mapped['aspect_ratio']))
                        resolution = '{0}x{1}'.format(width, height)

                        if resolution not in _images[image_type]:
                            _images[image_type][resolution] = {}

                        if bid not in _images[image_type][resolution]:
                            _images[image_type][resolution][bid] = {}

                        for k, v in image_mapped.items():
                            if k is None or v is None:
                                continue

                            _images[image_type][resolution][bid][k] = v

                        for k, v in _images[image_type][resolution][bid].items():
                            if k.endswith('path'):
                                new_key = '_%s' % k
                                log().debug('Adding base url for image: %s', v)
                                _images[image_type][resolution][bid][new_key] = self.config['artwork_prefix'].format(
                                    base_url=self.tmdb_configuration.images['base_url'],
                                    image_size=size,
                                    file_path=v)

            except Exception as e:
                log().warning('Could not parse Poster for showid: %s, with exception: %r', sid, e)
                return False

        self._save_images(sid, _images)
        self._set_show_data(sid, '_banners', _images)

    def _parse_actors(self, sid):
        """Parsers actors XML, from
        http://theTMDB.com/api/[APIKEY]/series/[SERIES ID]/actors.xml

        Actors are retrieved using t['show name]['_actors'], for example:

        >>> t = TMDB(actors = True)
        >>> actors = t['scrubs']['_actors']
        >>> type(actors)
        <class 'TMDB_api.Actors'>
        >>> type(actors[0])
        <class 'TMDB_api.Actor'>
        >>> actors[0]
        <Actor "Zach Braff">
        >>> sorted(actors[0].keys())
        ['id', 'image', 'name', 'role', 'sortorder']
        >>> actors[0]['name']
        u'Zach Braff'
        >>> actors[0]['image']
        u'http://theTMDB.com/banners/actors/43640.jpg'

        Any key starting with an underscore has been processed (not the raw
        data from the XML)
        """
        log().debug('Getting actors for %s', sid)

        # TMDB also support passing language here as a param.
        credits = self.tmdb.TV(38472).credits({'language': self.config['language']})

        if not credits or not credits.get('cast'):
            log().debug('Actors result returned zero')
            return

        cur_actors = Actors()
        for cur_actor in credits.get('cast'):
            new_actor = Actor()
            new_actor['id'] = cur_actor['credit_id']
            new_actor['image'] = \
                '{base_url}{image_size}{profile_path}'.format(base_url=self.tmdb_configuration.images['base_url'],
                                                              image_size='original',
                                                              profile_path=cur_actor['profile_path'])
            new_actor['name'] = cur_actor['name']
            new_actor['role'] = cur_actor['character']
            new_actor['sortorder'] = cur_actor['order']
            cur_actors.append(new_actor)
        self._set_show_data(sid, '_actors', cur_actors)

    def _get_show_data(self, sid, language, get_ep_info=False):  # pylint: disable=too-many-branches,too-many-statements,too-many-locals
        """Takes a series ID, gets the epInfo URL and parses the TheTMDB json response
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
        # Create a key/value dict, to map the image type to a default image width.
        # possitlbe widths can also be retrieved from self.configuration.images['poster_sizes'] and
        # self.configuration.images['still_sizes']
        image_width = {'fanart': 'w1280', 'poster': 'w500'}

        for k, v in series_info['series'].items():
            if v is not None:
                if k in ['fanart', 'banner', 'poster']:
                    v = self.config['artwork_prefix'].format(base_url=self.tmdb_configuration.images['base_url'],
                                                             image_size=image_width[k],
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
