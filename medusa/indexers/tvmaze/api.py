# coding=utf-8

from __future__ import unicode_literals

import logging
from collections import OrderedDict
from time import time

from medusa.indexers.base import (Actor, Actors, BaseIndexer)
from medusa.indexers.exceptions import (
    IndexerError,
    IndexerException,
    IndexerShowNotFound,
    IndexerUnavailable
)
from medusa.logger.adapters.style import BraceAdapter

from pytvmaze import TVMaze
from pytvmaze.exceptions import BaseError, CastNotFound, IDNotFound, ShowIndexError, ShowNotFound, UpdateNotFound

from six import integer_types, itervalues, string_types, text_type, viewitems

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class TVmaze(BaseIndexer):
    """Create easy-to-use interface to name of season/episode name.

    >>> indexer_api = tvmaze()
    >>> indexer_api['Scrubs'][1][24]['episodename']
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

        # for usage in the indexer UI - the api will use the language abbreviations)
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
                for key, value in viewitems(item.__dict__):
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
                                return_dict['poster'] = value.get('medium')
                        if key == 'externals':
                            return_dict['tvrage_id'] = value.get('tvrage')
                            return_dict['tvdb_id'] = value.get('thetvdb')
                            return_dict['imdb_id'] = value.get('imdb')
                        if key == 'rating':
                            return_dict['rating'] = value.get('average') \
                                if isinstance(value, dict) else value
                    else:
                        # Do some value sanitizing
                        if isinstance(value, list):
                            if all(isinstance(x, (string_types, integer_types)) for x in value):
                                value = list_separator.join(text_type(v) for v in value)

                        # Try to map the key
                        if key in key_mappings:
                            key = key_mappings[key]

                        # Set value to key
                        return_dict[key] = text_type(value) if isinstance(value, (float, integer_types)) else value

                # For episodes
                if hasattr(item, 'season_number') and getattr(item, 'episode_number') is None:
                    return_dict['episodenumber'] = text_type(index_special_episodes)
                    return_dict['seasonnumber'] = 0
                    index_special_episodes += 1

                # If there is a web_channel available, let's use that in stead of the network field.
                network = getattr(item, 'web_channel', None)
                if network and getattr(network, 'name', None):
                    return_dict['network'] = network.name

            except Exception as error:
                log.warning('Exception trying to parse attribute: {0}, with exception: {1!r}', key, error)

            parsed_response.append(return_dict)

        return parsed_response if len(parsed_response) != 1 else parsed_response[0]

    def _show_search(self, show, request_language='en'):
        """
        Use the TVMaze API to search for a show.

        :param show: The show name that's searched for as a string
        :param request_language: Language in two letter code. TVMaze fallsback to en itself.
        :return: A list of Show objects.
        """
        try:
            results = self.tvmaze_api.get_show_list(show)
        except ShowNotFound as error:
            # Use error.value because TVMaze API exceptions may be utf-8 encoded when using __str__
            raise IndexerShowNotFound(
                'Show search failed in getting a result with reason: {0}'.format(error.value)
            )
        except BaseError as error:
            raise IndexerUnavailable('Show search failed in getting a result with error: {0!r}'.format(error))

        return results

    def search(self, series):
        """Search tvmaze.com for the series name.

        :param series: the query for the series name
        :return: An ordered dict with the show searched for. In the format of OrderedDict{"series": [list of shows]}
        """
        log.debug('Searching for show {0}', series)

        results = None
        # If search term is digit's only, store it and attempt to search by id.
        show_by_id = None

        try:
            if series.isdigit():
                show_by_id = self._get_show_by_id(series, request_language=self.config['language'])
            results = self._show_search(series, request_language=self.config['language'])
        except IndexerShowNotFound:
            pass

        if not results and not show_by_id:
            raise IndexerShowNotFound(
                'Tvmaze show search failed in getting a result for search term {search}'.format(search=series)
            )

        mapped_results = []
        if results:
            mapped_results = self._map_results(results, self.series_map, '|')

        # The search by id result, is already mapped. We can just add it to the array with results.
        if show_by_id:
            mapped_results.append(show_by_id['series'])

        return OrderedDict({'series': mapped_results})['series']

    def _get_show_by_id(self, tvmaze_id, request_language='en'):  # pylint: disable=unused-argument
        """
        Retrieve tvmaze show information by tvmaze id, or if no tvmaze id provided by passed external id.

        :param tvmaze_id: The shows tvmaze id
        :return: An ordered dict with the show searched for.
        """
        results = None
        if tvmaze_id:
            log.debug('Getting all show data for {0}', tvmaze_id)

            try:
                results = self.tvmaze_api.get_show(maze_id=tvmaze_id)
            except ShowNotFound as error:
                # Use error.value because TVMaze API exceptions may be utf-8 encoded when using __str__
                raise IndexerShowNotFound(
                    'Show search failed in getting a result with reason: {0}'.format(error.value)
                )
            except BaseError as error:
                raise IndexerUnavailable('Show search failed in getting a result with error: {0!r}'.format(error))

        if not results:
            return

        mapped_results = self._map_results(results, self.series_map)
        return OrderedDict({'series': mapped_results})

    def _get_episodes(self, tvmaze_id, specials=False, aired_season=None):  # pylint: disable=unused-argument
        """
        Get all the episodes for a show by tvmaze id.

        :param tvmaze_id: Series tvmaze id.
        :return: An ordered dict with the show searched for. In the format of OrderedDict{"episode": [list of episodes]}
        """
        # Parse episode data
        log.debug('Getting all episodes of {0}', tvmaze_id)
        try:
            results = self.tvmaze_api.episode_list(tvmaze_id, specials=specials)
        except IDNotFound:
            log.debug('Episode search did not return any results.')
            return False
        except BaseError as e:
            raise IndexerException('Show episodes search failed in getting a result with error: {0!r}'.format(e))

        episodes = self._map_results(results, self.series_map)

        if not episodes:
            return False

        if not isinstance(episodes, list):
            episodes = [episodes]

        for cur_ep in episodes:
            if self.config['dvdorder']:
                log.debug('Using DVD ordering.')
                use_dvd = cur_ep.get('dvd_season') is not None and cur_ep.get('dvd_episodenumber') is not None
            else:
                use_dvd = False

            if use_dvd:
                seasnum, epno = cur_ep.get('dvd_season'), cur_ep.get('dvd_episodenumber')
            else:
                seasnum, epno = cur_ep.get('seasonnumber'), cur_ep.get('episodenumber')
                if self.config['dvdorder']:
                    log.warning('No DVD order for episode (season: {0}, episode: {1}). '
                                'Falling back to non-DVD order. '
                                'Please consider disabling DVD order for the show with TVmaze ID: {2}',
                                seasnum, epno, tvmaze_id)

            if seasnum is None or epno in (None, 0):
                log.warning('An episode has incomplete season/episode number (season: {0!r}, episode: {1!r})', seasnum, epno)
                continue  # Skip to next episode

            seas_no = int(seasnum)
            ep_no = int(epno)

            for k, v in viewitems(cur_ep):
                k = k.lower()

                if v is not None:
                    if k == 'image_medium':
                        self._set_item(tvmaze_id, seas_no, ep_no, 'filename', v)
                self._set_item(tvmaze_id, seas_no, ep_no, k, v)

    def _parse_images(self, tvmaze_id):
        """Parse Show and Season posters.

        images are retrieved using t['show name]['_banners'], for example:

        >>> indexer_api = TVMaze(images = True)
        >>> indexer_api['scrubs']['_banners'].keys()
        ['fanart', 'poster', 'series', 'season']
        >>> t['scrubs']['_banners']['poster']['680x1000']['35308']['_bannerpath']
        u'http://thetvmaze.com/banners/posters/76156-2.jpg'
        >>>

        Any key starting with an underscore has been processed (not the raw
        data from the XML)

        This interface will be improved in future versions.
        """
        log.debug('Getting show banners for {0}', tvmaze_id)

        try:
            image_medium = self.shows[tvmaze_id]['image_medium']
        except Exception:
            log.debug('Could not parse Poster for showid: {0}', tvmaze_id)
            return False

        # Set the poster (using the original uploaded poster for now, as the medium formated is 210x195
        _images = {u'poster': {u'1014x1500': {u'1': {u'rating': 1,
                                                     u'language': u'en',
                                                     u'ratingcount': 1,
                                                     u'bannerpath': image_medium.split('/')[-1],
                                                     u'bannertype': u'poster',
                                                     u'bannertype2': u'210x195',
                                                     u'_bannerpath': image_medium,
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
            log.debug('Getting all show data for {0}', tvmaze_id)
            try:
                seasons = self.tvmaze_api.show_seasons(maze_id=tvmaze_id)
            except BaseError as e:
                log.warning('Getting show seasons for the season images failed. Cause: {0}', e)

        _images = {'season': {'original': {}}}
        # Get the season posters
        for season in seasons:
            if not getattr(seasons[season], 'image', None):
                continue
            if season not in _images['season']['original']:
                _images['season']['original'][season] = {seasons[season].id: {}}
            _images['season']['original'][season][seasons[season].id]['_bannerpath'] = seasons[season].image['original']
            _images['season']['original'][season][seasons[season].id]['rating'] = 1

        return _images

    def _parse_actors(self, tvmaze_id):
        """Parsers actors XML, from
        http://thetvmaze.com/api/[APIKEY]/series/[SERIES ID]/actors.xml

        Actors are retrieved using t['show name]['_actors'], for example:

        >>> indexer_api = TVMaze(actors = True)
        >>> actors = indexer_api['scrubs']['_actors']
        >>> type(actors)
        <class 'tvmaze_api.Actors'>
        >>> type(actors[0])
        <class 'tvmaze_api.Actor'>
        >>> actors[0]
        <Actor "Zach Braff">
        >>> sorted(actors[0].keys())
        ['id', 'image', 'name', 'role', 'sortorder']
        >>> actors[0]['name']
        u'Zach Braff'
        >>> actors[0]['image']
        u'http://thetvmaze.com/banners/actors/43640.jpg'

        Any key starting with an underscore has been processed (not the raw
        data from the indexer)
        """
        log.debug('Getting actors for {0}', tvmaze_id)
        try:
            actors = self.tvmaze_api.show_cast(tvmaze_id)
        except CastNotFound:
            log.debug('Actors result returned zero')
            return
        except BaseError as e:
            log.warning('Getting actors failed. Cause: {0}', e)
            return

        cur_actors = Actors()
        for order, cur_actor in enumerate(actors.people):
            save_actor = Actor()
            save_actor['id'] = cur_actor.id
            save_actor['image'] = cur_actor.image.get('original') if cur_actor.image else ''
            save_actor['name'] = cur_actor.name
            save_actor['role'] = cur_actor.character.name
            save_actor['sortorder'] = order
            cur_actors.append(save_actor)
        self._set_show_data(tvmaze_id, '_actors', cur_actors)

    def _get_show_data(self, tvmaze_id, language='en'):
        """Take a series ID, gets the epInfo URL and parses the tvmaze json response.

        into the shows dict in layout:
        shows[series_id][season_number][episode_number]
        """
        if self.config['language'] is None:
            log.debug('Config language is none, using show language')
            if language is None:
                raise IndexerError("config['language'] was None, this should not happen")
            get_show_in_language = language
        else:
            log.debug(
                'Configured language {0} override show language of {1}',
                self.config['language'],
                language
            )
            get_show_in_language = self.config['language']

        # Parse show information
        log.debug('Getting all series data for {0}', tvmaze_id)

        # Parse show information
        series_info = self._get_show_by_id(tvmaze_id, request_language=get_show_in_language)

        if not series_info:
            log.debug('Series result returned zero')
            raise IndexerError('Series result returned zero')

        # save all retrieved show information to Show object.
        for k, v in viewitems(series_info['series']):
            if v is not None:
                self._set_show_data(tvmaze_id, k, v)

        # Get external ids.
        # As the external id's are not part of the shows default response, we need to make an additional call for it.
        # Im checking for the external value. to make sure only externals with a value get in.
        self._set_show_data(tvmaze_id, 'externals', {external_id: text_type(getattr(self.shows[tvmaze_id], external_id, None))
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

    def _get_all_updates(self, start_date=None, end_date=None):
        """Retrieve all updates (show,season,episode) from TVMaze."""
        results = []
        try:
            updates = self.tvmaze_api.show_updates()
        except (ShowIndexError, UpdateNotFound):
            return results
        except BaseError as e:
            log.warning('Getting show updates failed. Cause: {0}', e)
            return results

        if getattr(updates, 'updates', None):
            for show_id, update_ts in viewitems(updates.updates):
                if start_date < update_ts.seconds_since_epoch < (end_date or int(time())):
                    results.append(int(show_id))

        return results

    # Public methods, usable separate from the default api's interface api['show_id']
    def get_last_updated_series(self, from_time, weeks=1, filter_show_list=None):
        """Retrieve a list with updated shows.

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
        for external_id in itervalues(mapping):
            if kwargs.get(external_id):
                try:
                    result = self.tvmaze_api.get_show(**{external_id: kwargs.get(external_id)})
                    if result:
                        externals = {mapping[tvmaze_external_id]: external_value
                                     for tvmaze_external_id, external_value
                                     in viewitems(result.externals)
                                     if external_value and mapping.get(tvmaze_external_id)}
                        externals['tvmaze_id'] = result.maze_id
                        return externals
                except ShowNotFound:
                    log.debug('Could not get tvmaze externals using external key {0} and id {1}',
                              external_id, kwargs.get(external_id))
                    continue
                except BaseError as e:
                    log.warning('Could not get tvmaze externals. Cause: {0}', e)
                    continue
        return {}
