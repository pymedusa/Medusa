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

import logging
from collections import OrderedDict
from time import time

from pytvmaze import TVMaze
from pytvmaze.exceptions import CastNotFound, IDNotFound, ShowIndexError, ShowNotFound, UpdateNotFound

from ..indexer_base import (Actor, Actors, BaseIndexer)
from ..indexer_exceptions import IndexerError, IndexerException, IndexerShowNotFound


def log():
    return logging.getLogger('tvmaze')


class TVmaze(BaseIndexer):
    """Create easy-to-use interface to name of season/episode name
    >>> t = tvmaze()
    >>> t['Scrubs'][1][24]['episodename']
    u'My Last Day'
    """

    def __init__(self, *args, **kwargs):  # pylint: disable=too-many-locals,too-many-arguments
        super(TVmaze, self).__init__(*args, **kwargs)

        # List of language from http://thetvmaze.com/api/0629B785CE550C8D/languages.xml
        # Hard-coded here as it is realtively static, and saves another HTTP request, as
        # recommended on http://thetvmaze.com/wiki/index.php/API:languages.xml
        self.config['valid_languages'] = [
            'da', 'fi', 'nl', 'de', 'it', 'es', 'fr', 'pl', 'hu', 'el', 'tr',
            'ru', 'he', 'ja', 'pt', 'zh', 'cs', 'sl', 'hr', 'ko', 'en', 'sv', 'no'
        ]

        # thetvdb.com should be based around numeric language codes,
        # but to link to a series like http://thetvdb.com/?tab=series&id=79349&lid=16
        # requires the language ID, thus this mapping is required (mainly
        # for usage in tvdb_ui - internally tvdb_api will use the language abbreviations)
        self.config['langabbv_to_id'] = {'el': 20, 'en': 7, 'zh': 27,
                                         'it': 15, 'cs': 28, 'es': 16, 'ru': 22, 'nl': 13, 'pt': 26, 'no': 9,
                                         'tr': 21, 'pl': 18, 'fr': 17, 'hr': 31, 'de': 14, 'da': 10, 'fi': 11,
                                         'hu': 19, 'ja': 25, 'he': 24, 'ko': 32, 'sv': 8, 'sl': 30}

        # Initiate the pytvmaze API
        self.tvmaze_api = TVMaze(session=self.config['session'])

        self.config['artwork_prefix'] = '{base_url}{image_size}{file_path}'

        # An api to indexer series/episode object mapping
        self.series_map = {
            'id': 'id',
            'maze_id': 'id',
            'name': 'seriesname',
            'summary': 'overview',
            'premiered': 'firstaired',
            'image': 'fanart',
            'url': 'show_url',
            'genres': 'genre',
            'epnum': 'absolute_number',
            'title': 'episodename',
            'airdate': 'firstaired',
            'screencap': 'filename',
            'episode_number': 'episodenumber',
            'season_number': 'seasonnumber',
            'rating': 'contentrating',
        }

    def _map_results(self, tvmaze_response, key_mappings=None, list_separator='|'):
        """
        Map results to a a key_mapping dict.

        :param tvmaze_response: tvmaze response obect, or a list of response objects.
        :type tvmaze_response: list(object)
        :param key_mappings: Dict of tvmaze attributes, that are mapped to normalized keys.
        :type key_mappings: dictionary
        :param list_separator: A list separator used to transform lists to a character separator string.
        :type list_separator: string.
        """
        parsed_response = []

        if not isinstance(tvmaze_response, list):
            tvmaze_response = [tvmaze_response]

        # TVmaze does not number their special episodes. It does map it to a season. And that's something, medusa
        # Doesn't support. So for now, we increment based on the order, we process the specials. And map it to
        # season 0. We start with episode 1.
        index_special_episodes = 1

        for item in tvmaze_response:
            return_dict = {}
            try:
                for key, value in item.__dict__.iteritems():
                    if value is None or value == []:
                        continue

                    # These keys have more complex dictionaries, let's map these manually
                    if key in ['schedule', 'network', 'image', 'externals', 'rating']:
                        if key == 'schedule':
                            return_dict['airs_time'] = value.get('time') or '0:00AM'
                            return_dict['airs_dayofweek'] = value.get('days')[0] if value.get('days') else None
                        if key == 'network':
                            return_dict['network'] = value.name
                            return_dict['code'] = value.code
                            return_dict['timezone'] = value.timezone
                        if key == 'image':
                            if value.get('medium'):
                                return_dict['image_medium'] = value.get('medium')
                                return_dict['image_original'] = value.get('original')
                                return_dict['poster'] = value.get('original')
                        if key == 'externals':
                            return_dict['tvrage_id'] = value.get('tvrage')
                            return_dict['tvdb_id'] = value.get('thetvdb')
                            return_dict['imdb_id'] = value.get('imdb')
                        if key == 'rating':
                            return_dict['contentrating'] = str(value.get('average'))\
                                if isinstance(value, dict) else str(value)
                    else:
                        # Do some value sanitizing
                        if isinstance(value, list):
                            if all(isinstance(x, (str, unicode, int)) for x in value):
                                value = list_separator.join(str(v) for v in value)

                        # Try to map the key
                        if key in key_mappings:
                            key = key_mappings[key]

                        # Set value to key
                        return_dict[key] = str(value) if isinstance(value, (float, int)) else value

                # For episodes
                if hasattr(item, 'season_number') and getattr(item, 'episode_number') is None:
                    return_dict['episodenumber'] = str(index_special_episodes)
                    return_dict['seasonnumber'] = 0
                    index_special_episodes += 1

                # If there is a web_channel available, let's use that in stead of the network field.
                network = getattr(item, 'web_channel', None)
                if network and getattr(network, 'name', None):
                    return_dict['network'] = network.name

            except Exception as e:
                log().warning('Exception trying to parse attribute: %s, with exception: %r', key, e)

            parsed_response.append(return_dict)

        return parsed_response if len(parsed_response) != 1 else parsed_response[0]

    def _show_search(self, show, request_language='en'):
        """
        Uses the TVMaze API to search for a show
        :param show: The show name that's searched for as a string
        :param request_language: Language in two letter code. TVMaze fallsback to en itself.
        :return: A list of Show objects.
        """
        try:
            results = self.tvmaze_api.get_show_list(show)
        except ShowNotFound as e:
            raise IndexerShowNotFound(
                'Show search failed in getting a result with reason: %s' % e
            )
        except Exception as e:
            raise IndexerException('Show search failed in getting a result with error: %r' % e)

        if results:
            return results
        else:
            return None

    # Tvdb implementation
    def search(self, series):
        """This searches tvmaze.com for the series name

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

    def _get_show_by_id(self, tvmaze_id, request_language='en'):  # pylint: disable=unused-argument
        """
        Retrieve tvmaze show information by tvmaze id, or if no tvmaze id provided by passed external id.

        :param tvmaze_id: The shows tvmaze id
        :return: An ordered dict with the show searched for.
        """
        results = None
        if tvmaze_id:
            log().debug('Getting all show data for %s', [tvmaze_id])
            results = self.tvmaze_api.get_show(maze_id=tvmaze_id)

        if not results:
            return

        mapped_results = self._map_results(results, self.series_map)

        return OrderedDict({'series': mapped_results})

    def _get_episodes(self, tvmaze_id, specials=False, aired_season=None):  # pylint: disable=unused-argument
        """
        Get all the episodes for a show by tvmaze id

        :param tvmaze_id: Series tvmaze id.
        :return: An ordered dict with the show searched for. In the format of OrderedDict{"episode": [list of episodes]}
        """
        # Parse episode data
        log().debug('Getting all episodes of %s', [tvmaze_id])
        try:
            results = self.tvmaze_api.episode_list(tvmaze_id, specials=specials)
        except IDNotFound:
            log().debug('Episode search did not return any results.')
            return False

        episodes = self._map_results(results, self.series_map)

        if not episodes:
            return False

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

            for k, v in cur_ep.items():
                k = k.lower()

                if v is not None:
                    if k == 'image_original':
                        self._set_item(tvmaze_id, seas_no, ep_no, 'filename', v)
                self._set_item(tvmaze_id, seas_no, ep_no, k, v)

    def _parse_images(self, tvmaze_id):
        """Parse Show and Season posters.

        images are retrieved using t['show name]['_banners'], for example:

        >>> t = TVMaze(images = True)
        >>> t['scrubs']['_banners'].keys()
        ['fanart', 'poster', 'series', 'season']
        >>> t['scrubs']['_banners']['poster']['680x1000']['35308']['_bannerpath']
        u'http://theTMDB.com/banners/posters/76156-2.jpg'
        >>>

        Any key starting with an underscore has been processed (not the raw
        data from the XML)

        This interface will be improved in future versions.
        """
        log().debug('Getting show banners for %s', [tvmaze_id])

        try:
            image_original = self.shows[tvmaze_id]['image_original']
        except Exception:
            log().debug('Could not parse Poster for showid: %s', [tvmaze_id])
            return False

        # Set the poster (using the original uploaded poster for now, as the medium formated is 210x195
        _images = {u'poster': {u'1014x1500': {u'1': {u'rating': 1,
                                                     u'language': u'en',
                                                     u'ratingcount': 1,
                                                     u'bannerpath': image_original.split('/')[-1],
                                                     u'bannertype': u'poster',
                                                     u'bannertype2': u'210x195',
                                                     u'_bannerpath': image_original,
                                                     u'id': u'1035106'}}}}

        season_images = self._parse_season_images(tvmaze_id)
        if season_images:
            _images.update(season_images)

        self._save_images(tvmaze_id, _images)
        self._set_show_data(tvmaze_id, '_banners', _images)

    def _parse_season_images(self, tvmaze_id):
        """Parse Show and Season posters."""
        seasons = {}
        if tvmaze_id:
            log().debug('Getting all show data for %s', [tvmaze_id])
            seasons = self.tvmaze_api.show_seasons(maze_id=tvmaze_id)

        _images = {'season': {'original': {}}}
        # Get the season posters
        for season in seasons.keys():
            if not getattr(seasons[season], 'image', None):
                continue
            if season not in _images['season']['original']:
                _images['season']['original'][season] = {seasons[season].id: {}}
            _images['season']['original'][season][seasons[season].id]['_bannerpath'] = seasons[season].image['original']
            _images['season']['original'][season][seasons[season].id]['rating'] = 1

        return _images

    def _parse_actors(self, tvmaze_id):
        """Parsers actors XML, from
        http://theTMDB.com/api/[APIKEY]/series/[SERIES ID]/actors.xml

        Actors are retrieved using t['show name]['_actors'], for example:

        >>> t = TVMaze(actors = True)
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
        data from the indexer)
        """
        log().debug('Getting actors for %s', [tvmaze_id])
        try:
            actors = self.tvmaze_api.show_cast(tvmaze_id)
        except CastNotFound:
            log().debug('Actors result returned zero')
            return

        cur_actors = Actors()
        for order, cur_actor in enumerate(actors.people):
            save_actor = Actor()
            save_actor['id'] = cur_actor.id
            save_actor['image'] = cur_actor.image.get('original')
            save_actor['name'] = cur_actor.name
            save_actor['role'] = cur_actor.character.name
            save_actor['sortorder'] = order
            cur_actors.append(save_actor)
        self._set_show_data(tvmaze_id, '_actors', cur_actors)

    def _get_show_data(self, tvmaze_id, language='en'):  # pylint: disable=too-many-branches,too-many-statements,too-many-locals
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
        log().debug('Getting all series data for %s' % tvmaze_id)

        # Parse show information
        series_info = self._get_show_by_id(tvmaze_id, request_language=get_show_in_language)

        if not series_info:
            log().debug('Series result returned zero')
            raise IndexerError('Series result returned zero')

        # save all retrieved show information to Show object.
        for k, v in series_info['series'].items():
            if v is not None:
                self._set_show_data(tvmaze_id, k, v)

        # Get external ids.
        # As the external id's are not part of the shows default response, we need to make an additional call for it.
        # Im checking for the external value. to make sure only externals with a value get in.
        self._set_show_data(tvmaze_id, 'externals', {external_id: str(getattr(self.shows[tvmaze_id], external_id, None))
                                                     for external_id in ['tvdb_id', 'imdb_id', 'tvrage_id']
                                                     if getattr(self.shows[tvmaze_id], external_id, None)})

        # get episode data
        if self.config['episodes_enabled']:
            self._get_episodes(tvmaze_id, specials=False, aired_season=None)

        # Parse banners
        if self.config['banners_enabled']:
            self._parse_images(tvmaze_id)

        # Parse actors
        if self.config['actors_enabled']:
            self._parse_actors(tvmaze_id)

        return True

    def _get_all_updates(self, tvmaze_id=None, start_date=None, end_date=None):
        """Retrieve all updates (show,season,episode) from TVMaze"""
        results = []
        try:
            updates = self.tvmaze_api.show_updates()
        except (ShowIndexError, UpdateNotFound):
            return False

        if getattr(updates, 'updates', None):
            for show_id, update_ts in updates.updates.iteritems():
                if start_date < update_ts < (end_date or time()):
                    results.append(int(show_id))

        return results

    # Public methods, usable separate from the default api's interface api['show_id']
    def get_last_updated_series(self, from_time, weeks=1, filter_show_list=None):
        """Retrieve a list with updated shows

        :param from_time: epoch timestamp, with the start date/time
        :param weeks: number of weeks to get updates for.
        :param filter_show_list: Optional list of show objects, to use for filtering the returned list.
        """
        total_updates = []
        updates = self._get_all_updates(from_time, from_time + (weeks * 604800))  # + seconds in a week

        if updates and filter_show_list:
            new_list = []
            for show in filter_show_list:
                if show.indexerid in total_updates:
                    new_list.append(show.indexerid)
            updates = new_list

        return updates

    def get_id_by_external(self, **kwargs):
        """Search tvmaze for a show, using an external id.

        Accepts as kwargs, so you'l need to add the externals as key/values.
        :param tvrage: The tvrage id.
        :param thetvdb: The tvdb id.
        :param imdb: An imdb id (inc. tt).
        :returns: A dict with externals, including the tvmaze id.
        """
        mapping = {'thetvdb': 'tvdb_id', 'tvrage': 'tvrage_id', 'imdb': 'imdb_id'}
        externals = {}
        for external_id in ['tvdb_id', 'imdb_id', 'tvrage_id']:
            if kwargs.get(external_id):
                try:
                    result = self.tvmaze_api.get_show(**{external_id: kwargs.get(external_id)})
                    if result:
                        externals = result.externals
                        externals[external_id] = result.id
                        return {mapping[external_id]: external_value
                                for external_id, external_value
                                in externals.items()
                                if external_value and mapping.get(external_id)}
                except ShowNotFound:
                    log().debug('Could not get tvmaze externals using external key %s and id %s',
                                external_id, kwargs.get(external_id))
                    continue
        return externals
