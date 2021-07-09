# coding=utf-8

"""TVDB2 api module."""
from __future__ import unicode_literals

import logging
from collections import OrderedDict

from medusa import app
from medusa.app import TVDB_API_KEY
from medusa.helper.metadata import needs_metadata
from medusa.indexers.base import (Actor, Actors, BaseIndexer)
from medusa.indexers.exceptions import (
    IndexerAuthFailed, IndexerError, IndexerShowNotFound,
    IndexerShowNotFoundInLanguage, IndexerUnavailable
)
from medusa.indexers.tvdbv2.fallback import PlexFallback
from medusa.logger.adapters.style import BraceAdapter
from medusa.show.show import Show

from requests.compat import urljoin

from six import string_types, text_type, viewitems

from tvdbapiv2 import ApiClient, EpisodesApi, SearchApi, SeriesApi, UpdatesApi
from tvdbapiv2.exceptions import ApiException

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())

API_BASE_TVDB = 'https://api.thetvdb.com'


class TVDBv2(BaseIndexer):
    """Create easy-to-use interface to name of season/episode name.

    >>> indexer_api = tvdbv2()
    >>> indexer_api['Scrubs'][1][24]['episodename']
    u'My Last Day'
    """

    def __init__(self, *args, **kwargs):  # pylint: disable=too-many-locals,too-many-arguments
        """Init object."""
        super(TVDBv2, self).__init__(*args, **kwargs)

        self.config['api_base_url'] = API_BASE_TVDB

        # Configure artwork prefix url
        self.config['artwork_prefix'] = '{base_url}/banners/{{image}}'.format(base_url='https://www.thetvdb.com')

        # client_id = ''  # (optional! Only required for the /user routes)
        # client_secret = ''  # (optional! Only required for the /user routes)

        if not hasattr(self.config['session'], 'api_client'):
            tvdb_client = ApiClient(self.config['api_base_url'], session=self.config['session'], api_key=TVDB_API_KEY)
            self.config['session'].api_client = tvdb_client
            self.config['session'].search_api = SearchApi(tvdb_client)
            self.config['session'].series_api = SeriesApi(tvdb_client)
            self.config['session'].episodes_api = EpisodesApi(tvdb_client)
            self.config['session'].updates_api = UpdatesApi(tvdb_client)

        # An api to indexer series/episode object mapping
        self.series_map = {
            'id': 'id',
            'series_name': 'seriesname',
            'summary': 'overview',
            'first_aired': 'firstaired',
            'banner': 'banner',
            'url': 'show_url',
            'epnum': 'absolute_number',
            'episode_name': 'episodename',
            'aired_episode_number': 'episodenumber',
            'aired_season': 'seasonnumber',
            'dvd_episode_number': 'dvd_episodenumber',
            'airs_day_of_week': 'airs_dayofweek',
            'last_updated': 'lastupdated',
            'network_id': 'networkid',
            'rating': 'contentrating',
            'imdbId': 'imdb_id',
            'site_rating': 'rating'
        }

    def _map_results(self, tvdb_response, key_mapping=None, list_separator='|'):
        parsed_response = []

        tvdb_response = getattr(tvdb_response, 'data', tvdb_response)

        if not isinstance(tvdb_response, list):
            tvdb_response = [tvdb_response]

        for parse_object in tvdb_response:
            return_dict = {}
            if parse_object.attribute_map:
                for attribute in parse_object.attribute_map:
                    try:
                        value = getattr(parse_object, attribute, None)
                        if value is None or value == []:
                            continue

                        if isinstance(value, list):
                            if list_separator and all(isinstance(x, string_types) for x in value):
                                value = list_separator.join(value)
                            else:
                                value = [self._map_results(x, key_mapping) for x in value]

                        if key_mapping and key_mapping.get(attribute):
                            if isinstance(value, dict) and isinstance(key_mapping[attribute], dict):
                                # Let's map the children, i'm only going 1 deep, because usecases that I need it for,
                                # I don't need to go any further
                                for k, v in viewitems(value):
                                    if key_mapping.get(attribute)[k]:
                                        return_dict[key_mapping[attribute][k]] = v

                            else:
                                if key_mapping.get(attribute):
                                    return_dict[key_mapping[attribute]] = value
                        else:
                            return_dict[attribute] = value

                    except Exception as error:
                        log.warning('Exception trying to parse attribute: {0}, with exception: {1!r}', attribute, error)
                parsed_response.append(return_dict)
            else:
                log.debug('Missing attribute map, cant parse to dict')

        return parsed_response if len(parsed_response) != 1 else parsed_response[0]

    def _show_search(self, show, request_language='en'):
        """Use the pytvdbv2 API to search for a show.

        @param show: The show name that's searched for as a string
        @return: A list of Show objects.
        """
        try:
            results = self.config['session'].search_api.search_series_get(name=show, accept_language=request_language)
        except ApiException as error:
            if error.status == 401:
                raise IndexerAuthFailed(
                    'Authentication failed, possible bad API key. Reason: {reason} ({status})'
                    .format(reason=error.reason, status=error.status)
                )
            if error.status == 404:
                raise IndexerShowNotFound(
                    'Show search failed in getting a result with reason: {reason} ({status})'
                    .format(reason=error.reason, status=error.status)
                )
            raise IndexerUnavailable(error.reason)

        return results

    @PlexFallback
    def search(self, series):
        """Search tvdbv2.com for the series name.

        :param series: the query for the series name
        :return: An ordered dict with the show searched for. In the format of OrderedDict{"series": [list of shows]}
        """
        log.debug('Searching for show: {0}', series)

        results = self._show_search(series, request_language=self.config['language'])
        if not results:
            return

        mapped_results = self._map_results(results, self.series_map, '|')
        mapped_results = [mapped_results] if not isinstance(mapped_results, list) else mapped_results

        # Remove results with an empty series_name.
        # Skip shows when they do not have a series_name in the searched language. example: '24 h berlin' in 'en'
        cleaned_results = [show for show in mapped_results if show.get('seriesname')]

        return OrderedDict({'series': cleaned_results})['series']

    @PlexFallback
    def _get_show_by_id(self, tvdbv2_id, request_language='en'):  # pylint: disable=unused-argument
        """Retrieve tvdbv2 show information by tvdbv2 id, or if no tvdbv2 id provided by passed external id.

        :param tvdbv2_id: The shows tvdbv2 id
        :return: An ordered dict with the show searched for.
        """
        results = None
        if tvdbv2_id:
            log.debug('Getting all show data for {0}', tvdbv2_id)
            try:
                results = self.config['session'].series_api.series_id_get(tvdbv2_id, accept_language=request_language)
            except ApiException as error:
                if error.status == 401:
                    raise IndexerAuthFailed(
                        'Authentication failed, possible bad API key. Reason: {reason} ({status})'
                        .format(reason=error.reason, status=error.status)
                    )
                if error.status == 404:
                    raise IndexerShowNotFound(
                        'Show search failed in getting a result with reason: {reason} ({status})'
                        .format(reason=error.reason, status=error.status)
                    )
                raise IndexerUnavailable(error.reason)

        if not results:
            return

        if not getattr(results.data, 'series_name', None):
            raise IndexerShowNotFoundInLanguage('Missing attribute series_name, cant index in language: {0}'
                                                .format(request_language), request_language)

        mapped_results = self._map_results(results, self.series_map, '|')
        return OrderedDict({'series': mapped_results})

    def _get_episodes(self, tvdb_id, specials=False, aired_season=None):
        """Get all the episodes for a show by tvdbv id.

        :param tvdb_id: tvdb series id.
        :return: An ordered dict with the show searched for. In the format of OrderedDict{"episode": [list of episodes]}
        """
        episodes = self._query_series(tvdb_id, specials=specials, aired_season=aired_season, full_info=True)

        return self._parse_episodes(tvdb_id, episodes)

    def _get_episodes_info(self, tvdb_id, episodes, season=None):
        """Add full episode information for existing episodes."""
        series = Show.find_by_id(app.showList, 1, tvdb_id)
        if not series:
            return episodes

        existing_episodes = series.get_all_episodes(season=season, has_location=True)
        if not existing_episodes:
            return episodes

        for i, ep in enumerate(episodes):
            # Try to be as conservative as possible. Only query if the episode
            # exists on disk and it needs episode metadata.
            if any(ep_obj.indexerid == ep.id and needs_metadata(ep_obj)
                   for ep_obj in existing_episodes):
                episode = self.config['session'].episodes_api.episodes_id_get(
                    ep.id, accept_language=self.config['language']
                )
                episodes[i] = episode.data

        return episodes

    @PlexFallback
    def _query_series(self, tvdb_id, specials=False, aired_season=None, full_info=False):
        """Query against episodes for the given series.

        :param tvdb_id: tvdb series id.
        :param specials: enable/disable download of specials. Currently not used.
        :param aired_season: the episodes returned for a specific aired season.
        :param full_info: add full information to the episodes
        :return: An ordered dict of {'episode': [list of episode dicts]}
        """
        results = []
        if aired_season:
            aired_season = [aired_season] if not isinstance(aired_season, list) else aired_season

        # Parse episode data
        log.debug('Getting all episodes of {0}', tvdb_id)

        # get paginated pages
        page = 1
        last = 1
        try:
            if aired_season:
                for season in aired_season:
                    page = 1
                    last = 1
                    while page <= last:
                        paged_episodes = self.config['session'].series_api.series_id_episodes_query_get(
                            tvdb_id, page=page, aired_season=season, accept_language=self.config['language']
                        )
                        if paged_episodes.data:
                            results += paged_episodes.data
                            last = paged_episodes.links.last
                            page += 1
            else:
                while page <= last:
                    paged_episodes = self.config['session'].series_api.series_id_episodes_query_get(
                        tvdb_id, page=page, accept_language=self.config['language']
                    )
                    if paged_episodes.data:
                        results += paged_episodes.data
                        last = paged_episodes.links.last
                        page += 1

            if results and full_info:
                results = self._get_episodes_info(tvdb_id, results, season=aired_season)

        except ApiException as error:
            log.debug('Error trying to index the episodes')
            if error.status == 401:
                raise IndexerAuthFailed(
                    'Authentication failed, possible bad API key. Reason: {reason} ({status})'
                    .format(reason=error.reason, status=error.status)
                )

            if error.status == 404:
                show_data = self.shows.get(tvdb_id)
                if show_data and not show_data['firstaired']:
                    log.info('Show {name} does not have any episodes yet.',
                             {'name': self.shows[tvdb_id]['seriesname']})

            else:
                raise IndexerUnavailable(
                    'Error connecting to TVDB API. Reason: {reason}'.format(
                        reason=error.reason
                    )
                )

        mapped_episodes = self._map_results(results, self.series_map, '|')
        return OrderedDict({'episode': mapped_episodes if isinstance(mapped_episodes, list) else [mapped_episodes]})

    def _parse_episodes(self, tvdb_id, episode_data):
        """Parse retreived episodes."""
        if 'episode' not in episode_data:
            return False

        episodes = episode_data['episode']
        if not isinstance(episodes, list):
            episodes = [episodes]

        for cur_ep in episodes:
            flag_dvd_numbering = False
            dvd_seas_no = dvd_ep_no = None

            seas_no, ep_no = cur_ep.get('seasonnumber'), cur_ep.get('episodenumber')

            if self.config['dvdorder']:
                dvd_seas_no, dvd_ep_no = cur_ep.get('dvd_season'), cur_ep.get('dvd_episodenumber')

                log.debug(
                    'Using DVD ordering for dvd season: {0} and dvd episode: {1}, '
                    'with regular season {2} and episode {3}',
                    dvd_seas_no, dvd_ep_no, seas_no, ep_no
                )
                flag_dvd_numbering = dvd_seas_no is not None and dvd_ep_no is not None

                # We didn't get a season number but did get a dvd order episode number. Mark it as special.
                if dvd_ep_no is not None and dvd_seas_no is None:
                    dvd_seas_no = 0
                    flag_dvd_numbering = True

            if self.config['dvdorder'] and not flag_dvd_numbering:
                log.warning(
                    'No DVD order available for episode (season: {0}, episode: {1}). Skipping this episode. '
                    'If you want to have this episode visible, please change it on the TheTVDB site, '
                    'or consider disabling DVD order for the show: {2}({3})',
                    dvd_seas_no or seas_no, dvd_ep_no or ep_no,
                    self.shows[tvdb_id]['seriesname'], tvdb_id
                )
                if not app.TVDB_DVD_ORDER_EP_IGNORE:
                    dvd_seas_no = 0  # Add as special.
                    # Use the epno (dvd order) and if not exist fall back to the regular episode number.
                    dvd_ep_no = dvd_ep_no or ep_no
                    flag_dvd_numbering = True
                else:
                    # If TVDB_DVD_ORDER_EP_IGNORE is enabled, we wil not add any episode as a special, when there is not
                    # a dvd ordered episode number.
                    continue

            if flag_dvd_numbering:
                seas_no = dvd_seas_no
                ep_no = dvd_ep_no

            if seas_no is None or ep_no in (None, 0):
                log.warning('Invalid episode numbering (series: {0}({1}), season: {2!r}, episode: {3!r}) '
                            'Contact TVDB forums to have it fixed',
                            self.shows[tvdb_id]['seriesname'], tvdb_id, seas_no, ep_no)
                continue  # Skip to next episode

            # float() is because https://github.com/dbr/tvnamer/issues/95 - should probably be fixed in TVDB data
            seas_no = int(float(seas_no))
            ep_no = int(float(ep_no))

            for k, v in viewitems(cur_ep):
                k = k.lower()

                if v and k == 'filename':
                    v = urljoin(self.config['artwork_prefix'], v)

                self._set_item(tvdb_id, seas_no, ep_no, k, v)

    @PlexFallback
    def _parse_images(self, sid):
        """Parse images XML.

        From http://thetvdb.com/api/[APIKEY]/series/[SERIES ID]/banners.xml
        images are retrieved using t['show name]['_banners'], for example:

        >>> indexer_api = Tvdb(images = True)
        >>> indexer_api['scrubs']['_banners'].keys()
        ['fanart', 'poster', 'series', 'season', 'seasonwide']
        For a Poster
        >>> t['scrubs']['_banners']['poster']['680x1000']['35308']['_bannerpath']
        u'http://thetvdb.com/banners/posters/76156-2.jpg'
        For a season poster or season banner (seasonwide)
        >>> t['scrubs']['_banners']['seasonwide'][4]['680x1000']['35308']['_bannerpath']
        u'http://thetvdb.com/banners/posters/76156-4-2.jpg'
        >>>

        Any key starting with an underscore has been processed (not the raw
        data from the XML)

        This interface will be improved in future versions.
        """
        key_mapping = {'file_name': 'bannerpath', 'language_id': 'language', 'key_type': 'bannertype',
                       'resolution': 'bannertype2', 'ratings_info': {'count': 'ratingcount', 'average': 'rating'},
                       'thumbnail': 'thumbnailpath', 'sub_key': 'sub_key', 'id': 'id'}

        search_for_image_type = self.config['image_type']

        log.debug('Getting show banners for {0}', sid)
        _images = {}

        # Let's get the different types of images available for this series
        try:
            series_images_count = self.config['session'].series_api.series_id_images_get(
                sid, accept_language=self.config['language']
            )
        except ApiException as error:
            log.info('Could not get image count for show ID: {0} with reason: {1}', sid, error.reason)
            return

        for image_type, image_count in viewitems(self._map_results(series_images_count)):
            if not image_count:
                continue

            if search_for_image_type and search_for_image_type != image_type:
                # We want to use the 'poster' image also for the 'poster_thumb' type
                if image_type != 'poster' or image_type == 'poster' and search_for_image_type != 'poster_thumb':
                    continue

            try:
                images = self.config['session'].series_api.series_id_images_query_get(
                    sid, key_type=image_type, accept_language=self.config['language']
                )
            except ApiException as error:
                log.debug(
                    'Could not parse {image} for show ID: {sid}, with exception: {reason}',
                    {'image': image_type, 'sid': sid, 'reason': error.reason}
                )
                continue

            if image_type not in _images:
                _images[image_type] = {}

            for image in images.data:
                # Store the images for each resolution available
                # Always provide a resolution or 'original'.
                resolution = image.resolution or 'original'
                if resolution not in _images[image_type]:
                    _images[image_type][resolution] = {}

                # _images[image_type][resolution][image.id] = image_dict
                image_attributes = self._map_results(image, key_mapping)

                bid = image_attributes.pop('id')

                if image_type in ['season', 'seasonwide']:
                    sub_key = int(image.sub_key)
                    if sub_key not in _images[image_type][resolution]:
                        _images[image_type][resolution][sub_key] = {}
                    if bid not in _images[image_type][resolution][sub_key]:
                        _images[image_type][resolution][sub_key][bid] = {}
                    base_path = _images[image_type][resolution][sub_key][bid]
                else:
                    if bid not in _images[image_type][resolution]:
                        _images[image_type][resolution][bid] = {}
                    base_path = _images[image_type][resolution][bid]

                for k, v in viewitems(image_attributes):
                    if k is None or v is None:
                        continue

                    if k.endswith('path'):
                        k = '_{0}'.format(k)
                        log.debug('Adding base url for image: {0}', v)
                        v = self.config['artwork_prefix'].format(image=v)

                    base_path[k] = v

        self._save_images(sid, _images)
        self._set_show_data(sid, '_banners', _images)

    @PlexFallback
    def _parse_actors(self, sid):
        """Parser actors XML.

        From http://thetvdb.com/api/[APIKEY]/series/[SERIES ID]/actors.xml
        Actors are retrieved using t['show name]['_actors'], for example:

        >>> indexer_api = Tvdb(actors = True)
        >>> actors = indexer_api['scrubs']['_actors']
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
        log.debug('Getting actors for {0}', sid)

        try:
            actors = self.config['session'].series_api.series_id_actors_get(sid)
        except ApiException as error:
            log.info('Could not get actors for show ID: {0} with reason: {1}', sid, error.reason)
            return

        if not actors or not actors.data:
            log.debug('Actors result returned zero')
            return

        cur_actors = Actors()
        for cur_actor in actors.data if isinstance(actors.data, list) else [actors.data]:
            new_actor = Actor()
            new_actor['id'] = cur_actor.id
            new_actor['image'] = self.config['artwork_prefix'].format(image=cur_actor.image)
            new_actor['name'] = cur_actor.name
            new_actor['role'] = cur_actor.role
            new_actor['sortorder'] = 0
            cur_actors.append(new_actor)
        self._set_show_data(sid, '_actors', cur_actors)

    def _get_show_data(self, sid, language):
        """Parse TheTVDB json response.

        Takes a series ID, gets the epInfo URL and parses the TheTVDB json response
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
                self.config['language'], language,
            )
            get_show_in_language = self.config['language']

        # Parse show information
        log.debug('Getting all series data for {0}', sid)

        # Parse show information
        series_info = self._get_show_by_id(sid, request_language=get_show_in_language)

        if not series_info:
            log.debug('Series result returned zero')
            raise IndexerError('Series result returned zero')

        # get series data / add the base_url to the image urls
        for k, v in viewitems(series_info['series']):
            if v is not None:
                if v and k in ['banner', 'fanart', 'poster']:
                    v = self.config['artwork_prefix'].format(image=v)
            self._set_show_data(sid, k, v)

        # Create the externals structure
        self._set_show_data(sid, 'externals', {'imdb_id': text_type(getattr(self[sid], 'imdb_id', ''))})

        # get episode data
        if self.config['episodes_enabled']:
            self._get_episodes(sid, specials=False, aired_season=None)

        # Parse banners
        if self.config['banners_enabled']:
            self._parse_images(sid)

        # Parse actors
        if self.config['actors_enabled']:
            self._parse_actors(sid)

        return True

    # Public methods, usable separate from the default api's interface api['show_id']
    @PlexFallback
    def get_last_updated_series(self, from_time, weeks=1, filter_show_list=None):
        """Retrieve a list with updated shows.

        :param from_time: epoch timestamp, with the start date/time as int
        :param weeks: number of weeks to get updates for.
        :param filter_show_list: Optional list of show objects, to use for filtering the returned list.
        :returns: A list of show_id's.
        """
        total_updates = []
        updates = True

        count = 0
        try:
            while updates and count < weeks:
                updates = self.config['session'].updates_api.updated_query_get(from_time).data
                if updates:
                    last_update_ts = max(x.last_updated for x in updates)
                    if last_update_ts == from_time:
                        break

                    from_time = last_update_ts
                    total_updates += [int(_.id) for _ in updates]
                count += 1
        except ApiException as error:
            if error.status == 401:
                raise IndexerAuthFailed(
                    'Authentication failed, possible bad API key. Reason: {reason} ({status})'
                    .format(reason=error.reason, status=error.status)
                )
            raise IndexerUnavailable('Error connecting to TVDB API. Reason: {0}'.format(error.reason))

        if total_updates and filter_show_list:
            new_list = []
            for show in filter_show_list:
                if show.indexerid in total_updates:
                    new_list.append(show.indexerid)
            total_updates = new_list

        return total_updates

    # Public methods, usable separate from the default api's interface api['show_id']
    def get_last_updated_seasons(self, show_list, from_time, weeks=1):
        """Return updated seasons for shows passed, using the from_time.

        :param show_list[int]: The list of shows, where seasons updates are retrieved for.
        :param from_time[int]: epoch timestamp, with the start date/time
        :param weeks: number of weeks to get updates for.
        """
        show_season_updates = {}

        for show_id in show_list:
            total_updates = []
            # Get the shows episodes using the GET /series/{id}/episodes route, and use the lastUpdated attribute
            # to check if the episodes season should be updated.
            log.debug('Getting episodes for {0}', show_id)
            episodes = self._query_series(show_id)

            for episode in episodes['episode']:
                seasnum = episode.get('seasonnumber')
                epno = episode.get('episodenumber')
                if seasnum is None or epno is None:
                    log.warning('Invalid episode numbering (series: {0}, season: {1!r}, episode: {2!r}) '
                                'Contact TVDB forums to have it fixed', show_id, seasnum, epno)
                    continue

                if int(episode['lastupdated']) > from_time:
                    total_updates.append(int(seasnum))

            show_season_updates[show_id] = list(set(total_updates))

        return show_season_updates
