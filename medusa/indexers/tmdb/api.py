# coding=utf-8

"""TMDB module."""
from __future__ import division
from __future__ import unicode_literals

import logging
from builtins import range
from collections import OrderedDict
from datetime import datetime, timedelta

from dateutil import parser

from medusa.app import TMDB_API_KEY
from medusa.indexers.base import (Actor, Actors, BaseIndexer)
from medusa.indexers.exceptions import (
    IndexerError, IndexerException,
    IndexerShowNotFound, IndexerUnavailable
)
from medusa.logger.adapters.style import BraceAdapter

from requests.exceptions import RequestException

from six import integer_types, string_types, text_type, viewitems

import tmdbsimple as tmdb

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class Tmdb(BaseIndexer):
    """Create easy-to-use interface to name of season/episode name.

    indexer_api = tmdb()
    indexer_api['Scrubs'][1][24]['episodename']
    u'My Last Day'
    """

    def __init__(self, *args, **kwargs):  # pylint: disable=too-many-locals,too-many-arguments
        """Tmdb api constructor."""
        super(Tmdb, self).__init__(*args, **kwargs)

        self.tmdb = tmdb
        self.tmdb.API_KEY = TMDB_API_KEY
        self.tmdb.REQUESTS_SESSION = self.config['session']
        self.tmdb_configuration = self.tmdb.Configuration()
        try:
            self.response = self.tmdb_configuration.info()
        except RequestException as e:
            raise IndexerUnavailable('Indexer TMDB is unavailable at this time. Cause: {cause}'.format(cause=e))

        self.config['artwork_prefix'] = '{base_url}{image_size}{file_path}'

        # An api to indexer series/episode object mapping
        self.series_map = {
            'id': 'id',
            'name': 'seriesname',
            'original_name': 'aliases',
            'overview': 'overview',
            'air_date': 'firstaired',
            'first_air_date': 'firstaired',
            'backdrop_path': 'fanart',
            'url': 'show_url',
            'episode_number': 'episodenumber',
            'season_number': 'seasonnumber',
            'dvd_episode_number': 'dvd_episodenumber',
            'last_air_date': 'airs_dayofweek',
            'last_updated': 'lastupdated',
            'network_id': 'networkid',
            'vote_average': 'rating',
            'poster_path': 'poster',
            'genres': 'genre',
            'type': 'classification',
            'networks': 'network',
            'episode_run_time': 'runtime'
        }

        self.episodes_map = {
            'id': 'id',
            'name': 'episodename',
            'overview': 'overview',
            'air_date': 'firstaired',
            'episode_run_time': 'runtime',
            'episode_number': 'episodenumber',
            'season_number': 'seasonnumber',
            'vote_average': 'rating',
            'still_path': 'filename'
        }

    @staticmethod
    def _map_results(tmdb_response, key_mappings=None, list_separator='|'):
        """Map results to a a key_mapping dict.

        :type tmdb_response: object
        """
        def week_day(input_date):
            days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            week_day_number = parser.parse(input_date).weekday()
            return days[week_day_number]

        parsed_response = []

        if not isinstance(tmdb_response, list):
            tmdb_response = [tmdb_response]

        for item in tmdb_response:
            return_dict = {}
            try:
                for key, value in viewitems(item):
                    if value is None or value == []:
                        continue

                    # Do some value sanitizing
                    if isinstance(value, list) and key not in ['episode_run_time']:
                        if all(isinstance(x, (string_types, integer_types)) for x in value):
                            value = list_separator.join(text_type(v) for v in value)

                    # Process genres
                    if key == 'genres':
                        value = list_separator.join(item['name'] for item in value)

                    if key == 'networks':
                        value = value[0].get('name') if value else ''

                    if key == 'last_air_date':
                        value = week_day(value)

                    if key == 'episode_run_time':
                        # Using the longest episode runtime if there are multiple.
                        value = max(value) if isinstance(value, list) else ''

                    # Try to map the key
                    if key in key_mappings:
                        key = key_mappings[key]

                    # Set value to key
                    return_dict[key] = value

                # Add static values
                return_dict['airs_time'] = '0:00AM'

            except Exception as error:
                log.warning('Exception trying to parse attribute: {0}, with exception: {1!r}', key, error)

            parsed_response.append(return_dict)

        return parsed_response if len(parsed_response) != 1 else parsed_response[0]

    def _show_search(self, show, request_language='en'):
        """Use TMDB API to search for a show.

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
                search_result = self.tmdb.Search().tv(query=show,
                                                      language=request_language,
                                                      page=page)
                last = search_result.get('total_pages', 0)
                results += search_result.get('results')
                page += 1
        except RequestException as error:
            raise IndexerUnavailable('Show search failed using indexer TMDB. Cause: {cause}'.format(cause=error))

        if not results:
            raise IndexerShowNotFound('Show search failed in getting a result with reason: Not found')

        return results

    def search(self, series):
        """Search TMDB (themoviedb.org) for the series name.

        :param series: The query for the series name
        :return: An ordered dict with the show searched for. In the format of OrderedDict{"series": [list of shows]}
        """
        log.debug('Searching for show: {0}', series)

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
            return

        mapped_results = []
        if results:
            mapped_results = self._map_results(results, self.series_map, '|')

        # The search by id result, is already mapped. We can just add it to the array with results.
        if show_by_id:
            mapped_results.append(show_by_id['series'])

        return OrderedDict({'series': mapped_results})['series']

    def get_show_country_codes(self, tmdb_id):
        """Retrieve show's 2 letter country codes from TMDB.

        :param tmdb_id: The show's tmdb id
        :return: A list with the show's country codes
        """
        show_info = self._get_show_by_id(tmdb_id)['series']

        if show_info and show_info.get('origin_country'):
            return show_info['origin_country'].split('|')

    def _get_show_by_id(self, tmdb_id, request_language='en', extra_info=None):
        """Retrieve tmdb show information by tmdb id.

        :param tmdb_id: The show's tmdb id
        :param request_language: Language to get the show in
        :type request_language: string or unicode
        :extra_info: Extra details of the show to get (e.g. ['content_ratings', 'external_ids'])
        :type extra_info: list, tuple or None
        :return: An ordered dict with the show searched for.
        """
        if extra_info and isinstance(extra_info, (list, tuple)):
            extra_info = ','.join(extra_info)

        log.debug('Getting all show data for {0}', tmdb_id)
        try:
            results = self.tmdb.TV(tmdb_id).info(
                language='{0},null'.format(request_language),
                append_to_response=extra_info
            )
        except RequestException as error:
            raise IndexerUnavailable('Show info retrieval failed using indexer TMDB. Cause: {cause!r}'.format(
                cause=error
            ))

        if not results:
            return

        mapped_results = self._map_results(results, self.series_map, '|')
        return OrderedDict({'series': mapped_results})

    def _get_episodes(self, tmdb_id, specials=False, aired_season=None):  # pylint: disable=unused-argument
        """Get all the episodes for a show by TMDB id.

        :param tmdb_id: Series tmdb id.
        :return: An ordered dict with the show searched for. In the format of OrderedDict{"episode": [list of episodes]}
        """
        results = []
        if aired_season:
            aired_season = [aired_season] if not isinstance(aired_season, list) else aired_season
        else:
            if tmdb_id not in self.shows or not self.shows[tmdb_id].data.get('seasons'):
                self.config['episodes_enabled'] = False  # Don't want to get episodes, as where already doing that.
                self._get_show_data(tmdb_id)  # Get show data, with the list of seasons
            aired_season = [season['season_number'] for season in self.shows[tmdb_id].data.get('seasons', [])]

        if not aired_season:
            log.debug('Series does not have any seasons added on indexer TMDB.')
            return

        # Parse episode data
        log.debug('Getting all episodes of {0}', tmdb_id)

        # get episodes for each season
        for season in aired_season:
            try:
                season_info = self.tmdb.TV_Seasons(tmdb_id, season).info(language=self.config['language'])
                results += season_info['episodes']
            except RequestException as error:
                raise IndexerException(
                    'Could not get episodes for series {series} using indexer TMDB. Cause: {cause}'.format(
                        series=tmdb_id, cause=error
                    )
                )

        if not results:
            log.debug('Series does not have any episodes added on indexer TMDB.')
            return

        mapped_episodes = self._map_results(results, self.episodes_map, '|')
        episode_data = OrderedDict({'episode': mapped_episodes})

        if 'episode' not in episode_data:
            return False

        episodes = episode_data['episode']
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
                    log.warning(
                        'No DVD order available for episode (season: {0}, episode: {1}). '
                        'Falling back to non-DVD order. '
                        'Please consider disabling DVD order for the show with TMDB ID: {2}',
                        seasnum, epno, tmdb_id
                    )

            if seasnum is None or epno in (None, 0):
                log.warning('Invalid episode numbering (season: {0!r}, episode: {1!r})', seasnum, epno)
                continue  # Skip to next episode

            seas_no = int(seasnum)
            ep_no = int(epno)

            image_width = {'fanart': 'w1280', 'poster': 'w780', 'filename': 'w300'}
            for k, v in viewitems(cur_ep):
                k = k.lower()

                if v is not None:
                    if k in ['filename', 'poster', 'fanart']:
                        # I'm using the default 'original' quality. But you could also check tmdb_configuration,
                        # for the available image sizes.
                        v = self.config['artwork_prefix'].format(base_url=self.tmdb_configuration.images['base_url'],
                                                                 image_size=image_width[k],
                                                                 file_path=v)
                self._set_item(tmdb_id, seas_no, ep_no, k, v)

    def _parse_images(self, tmdb_id):
        """Parse images.

        This interface will be improved in future versions.
        """
        key_mapping = {'file_path': 'bannerpath', 'vote_count': 'ratingcount', 'vote_average': 'rating', 'id': 'id'}
        image_sizes = {'fanart': 'backdrop_sizes', 'poster': 'poster_sizes'}
        typecasts = {'rating': float, 'ratingcount': int}

        log.debug('Getting show banners for {series}', series=tmdb_id)
        _images = {}

        # Let's get the different type of images available for this series
        params = {'include_image_language': '{search_language},null'.format(search_language=self.config['language'])}

        try:
            images = self.tmdb.TV(tmdb_id).images(params=params)
        except RequestException as error:
            raise IndexerUnavailable('Error trying to get images. Cause: {cause}'.format(cause=error))

        bid = images['id']
        for image_type, images in viewitems({'poster': images['posters'], 'fanart': images['backdrops']}):
            try:
                if images and image_type not in _images:
                    _images[image_type] = {}

                for image in images:
                    bid += 1
                    image_mapped = self._map_results(image, key_mappings=key_mapping)

                    for size in self.tmdb_configuration.images.get(image_sizes[image_type]):
                        if size == 'original':
                            width = image_mapped['width']
                            height = image_mapped['height']
                        else:
                            width = int(size[1:])
                            height = int(round(width / float(image_mapped['aspect_ratio'])))
                        resolution = '{0}x{1}'.format(width, height)

                        if resolution not in _images[image_type]:
                            _images[image_type][resolution] = {}

                        if bid not in _images[image_type][resolution]:
                            _images[image_type][resolution][bid] = {}

                        for k, v in viewitems(image_mapped):
                            if k is None or v is None:
                                continue

                            try:
                                typecast = typecasts[k]
                            except KeyError:
                                pass
                            else:
                                v = typecast(v)

                            _images[image_type][resolution][bid][k] = v
                            if k.endswith('path'):
                                new_key = '_{0}'.format(k)
                                log.debug('Adding base url for image: {0}', v)
                                _images[image_type][resolution][bid][new_key] = self.config['artwork_prefix'].format(
                                    base_url=self.tmdb_configuration.images['base_url'],
                                    image_size=size,
                                    file_path=v)

                        if size != 'original':
                            _images[image_type][resolution][bid]['rating'] = 0

            except Exception as error:
                log.warning('Could not parse Poster for show id: {0}, with exception: {1!r}', tmdb_id, error)
                return False

        season_images = self._parse_season_images(tmdb_id)
        if season_images:
            _images.update(season_images)

        self._save_images(tmdb_id, _images)
        self._set_show_data(tmdb_id, '_banners', _images)

    def _parse_season_images(self, tmdb_id):
        """Get all season posters for a TMDB show."""
        # Let's fget the different type of images available for this series
        season_posters = getattr(self[tmdb_id], 'seasons', None)
        if not season_posters:
            return

        _images = {'season': {'original': {}}}
        for season in season_posters:
            # Store each season poster in the format
            if not season['season_number'] in _images['season']['original']:
                _images['season']['original'][season['season_number']] = {season['id']: {}}
            _images['season']['original'][season['season_number']][season['id']]['bannerpath'] = season['poster_path']
            _images['season']['original'][season['season_number']][season['id']]['_bannerpath'] = \
                self.config['artwork_prefix'].format(base_url=self.tmdb_configuration.images['base_url'],
                                                     image_size='w780',
                                                     file_path=season['poster_path'])

        return _images

    def _parse_actors(self, tmdb_id):
        """Parse actors XML."""
        log.debug('Getting actors for {0}', tmdb_id)

        # TMDB also support passing language here as a param.
        try:
            credits = self.tmdb.TV(tmdb_id).credits(language=self.config['language'])  # pylint: disable=W0622
        except RequestException as error:
            raise IndexerException('Could not get actors. Cause: {cause}'.format(cause=error))

        if not credits or not credits.get('cast'):
            log.debug('Actors result returned zero')
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
        self._set_show_data(tmdb_id, '_actors', cur_actors)

    def _get_show_data(self, tmdb_id, language='en'):
        """Take a series ID, gets the epInfo URL and parses the TMDB json response.

        into the shows dict in layout:
        shows[series_id][season_number][episode_number]
        """
        if self.config['language'] is None:
            log.debug('Config language is none, using show language')
            if language is None:
                raise IndexerError("config['language'] was None, this should not happen")
            get_show_in_language = language
        else:
            log.debug('Configured language {0} override show language of {1}',
                      self.config['language'], language)
            get_show_in_language = self.config['language']

        # Parse show information
        log.debug('Getting all series data for {0}', tmdb_id)

        # Parse show information
        extra_series_info = ('content_ratings', 'external_ids')
        series_info = self._get_show_by_id(
            tmdb_id,
            request_language=get_show_in_language,
            extra_info=extra_series_info
        )

        if not series_info:
            log.debug('Series result returned zero')
            raise IndexerError('Series result returned zero')

        # Get MPAA rating if available
        content_ratings = series_info['series'].get('content_ratings', {}).get('results')
        if content_ratings:
            mpaa_rating = next((r['rating'] for r in content_ratings
                                if r['iso_3166_1'].upper() == 'US'), None)
            if mpaa_rating:
                self._set_show_data(tmdb_id, 'contentrating', mpaa_rating)

        # get series data / add the base_url to the image urls
        # Create a key/value dict, to map the image type to a default image width.
        # possitlbe widths can also be retrieved from self.configuration.images['poster_sizes'] and
        # self.configuration.images['still_sizes']
        image_width = {'fanart': 'w1280', 'poster': 'w500'}

        for k, v in viewitems(series_info['series']):
            if v is not None:
                if k in ['fanart', 'banner', 'poster']:
                    v = self.config['artwork_prefix'].format(base_url=self.tmdb_configuration.images['base_url'],
                                                             image_size=image_width[k],
                                                             file_path=v)

            self._set_show_data(tmdb_id, k, v)

        # Get external ids.
        external_ids = series_info['series'].get('external_ids', {})
        self._set_show_data(tmdb_id, 'externals', external_ids)

        # get episode data
        if self.config['episodes_enabled']:
            self._get_episodes(tmdb_id, specials=False, aired_season=None)

        # Parse banners
        if self.config['banners_enabled']:
            self._parse_images(tmdb_id)

        # Parse actors
        if self.config['actors_enabled']:
            self._parse_actors(tmdb_id)

        return True

    def _get_series_season_updates(self, tmdb_id, start_date=None, end_date=None):
        """
        Retrieve all updates (show,season,episode) from TMDB.

        :return: A list of updated seasons for a show id.
        """
        results = []
        page = 1
        total_pages = 1

        try:
            while page <= total_pages:
                # Requesting for the changes on a specific showid, will result in json with changes per season.
                updates = self.tmdb.TV_Changes(tmdb_id).series(start_date=start_date, end_date=end_date)
                if updates and updates.get('changes'):
                    for items in [update['items'] for update in updates['changes'] if update['key'] == 'season']:
                        for season in items:
                            results += [season['value']['season_number']]
                    total_pages = updates.get('total_pages', 0)
                page += 1
        except RequestException as error:
            raise IndexerException('Could not get latest series season updates for series {series}. Cause: {cause}'.format(
                series=tmdb_id, cause=error
            ))

        return set(results)

    def _get_all_updates(self, start_date=None, end_date=None):
        """Retrieve all updates (show,season,episode) from TMDB."""
        results = []
        page = 1
        total_pages = 1

        try:
            while page <= total_pages:
                updates = self.tmdb.Changes().tv(start_date=start_date, end_date=end_date, page=page)
                if not updates or not updates.get('results'):
                    break
                results += [_.get('id') for _ in updates.get('results')]
                total_pages = updates.get('total_pages')
                page += 1
        except RequestException as error:
            raise IndexerException('Could not get latest updates. Cause: {cause}'.format(
                cause=error
            ))

        return set(results)

    # Public methods, usable separate from the default api's interface api['show_id']
    def get_last_updated_series(self, from_time, weeks=1, filter_show_list=None):
        """Retrieve a list with updated shows.

        :param from_time: epoch timestamp, with the start date/time
        :param weeks: number of weeks to get updates for.
        :param filter_show_list: Optional list of show objects, to use for filtering the returned list.
        """
        total_updates = []
        dt_start = datetime.fromtimestamp(float(from_time))
        search_max_weeks = 2

        for week in range(search_max_weeks, weeks + search_max_weeks, search_max_weeks):
            search_from = dt_start + timedelta(weeks=week - search_max_weeks)
            search_until = dt_start + timedelta(weeks=week)
            # No use searching in the future
            if search_from > datetime.today():
                break
            # Get the updates
            total_updates += self._get_all_updates(search_from.strftime('%Y-%m-%d'), search_until.strftime('%Y-%m-%d'))

        total_updates = set(total_updates)
        if total_updates and filter_show_list:
            new_list = []
            for show in filter_show_list:
                if show.indexerid in total_updates:
                    new_list.append(show.indexerid)
            total_updates = new_list

        return list(total_updates)

    # Public methods, usable separate from the default api's interface api['show_id']
    def get_last_updated_seasons(self, show_list, from_time, weeks=1):
        """Retrieve a list with updated shows.

        :param show_list: The list of shows, where seasons updates are retrieved for.
        :param from_time: epoch timestamp, with the start date/time
        :param weeks: number of weeks to get updates for.
        """
        show_season_updates = {}
        dt_start = datetime.fromtimestamp(float(from_time))
        search_max_weeks = 2

        for show in show_list:
            total_updates = []
            for week in range(search_max_weeks, weeks + search_max_weeks, search_max_weeks):
                search_from = dt_start + timedelta(weeks=week - search_max_weeks)
                search_until = dt_start + timedelta(weeks=week)
                # No use searching in the future
                if search_from > datetime.today():
                    break
                # Get the updates
                total_updates += self._get_series_season_updates(show, search_from.strftime('%Y-%m-%d'),
                                                                 search_until.strftime('%Y-%m-%d'))
            show_season_updates[show] = list(set(total_updates))

        return show_season_updates

    def get_id_by_external(self, **kwargs):
        """Search tmdb for a show, using an external id.

        Accepts as kwargs, so you'l need to add the externals as key/values.
        :param tvrage_id: The tvrage id.
        :param tvdb_id: The tvdb id.
        :param imdb_id: An imdb id (inc. tt).
        :returns: A dict with externals, including the tvmaze id.
        """
        try:
            wanted_externals = ['tvdb_id', 'imdb_id', 'tvrage_id']
            for external_id in wanted_externals:
                if kwargs.get(external_id):
                    result = self.tmdb.Find(kwargs.get(external_id)).info(**{'external_source': external_id})
                    if result.get('tv_results') and result['tv_results'][0]:
                        # Get the external id's for the passed shows id.
                        externals = self.tmdb.TV(result['tv_results'][0]['id']).external_ids()
                        externals = {tmdb_external_id: external_value
                                     for tmdb_external_id, external_value
                                     in viewitems(externals)
                                     if external_value and tmdb_external_id in wanted_externals}
                        externals['tmdb_id'] = result['tv_results'][0]['id']
                        return externals
            return {}
        except RequestException as error:
            raise IndexerException("Could not get external id's. Cause: {cause}".format(cause=error))
