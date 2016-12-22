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

import logging
from collections import OrderedDict

from requests.compat import urljoin
from requests.packages.urllib3.exceptions import MaxRetryError, RequestError

from tvdbapiv2 import (ApiClient, AuthenticationApi, SearchApi, SeriesApi, UpdatesApi)
from tvdbapiv2.rest import ApiException

from ..indexer_base import (Actor, Actors, BaseIndexer)
from ..indexer_exceptions import (IndexerError, IndexerException, IndexerShowIncomplete, IndexerShowNotFound,
                                  IndexerShowNotFoundInLanguage, IndexerUnavailable)
from ..indexer_ui import BaseUI, ConsoleUI


def log():
    """Return log."""
    return logging.getLogger('tvdbv2_api')


class TVDBv2(BaseIndexer):
    """Create easy-to-use interface to name of season/episode name.

    >>> t = tvdbv2()
    >>> t['Scrubs'][1][24]['episodename']
    u'My Last Day'
    """

    def __init__(self, *args, **kwargs):  # pylint: disable=too-many-locals,too-many-arguments
        """Init object."""
        super(TVDBv2, self).__init__(*args, **kwargs)

        self.config['base_url'] = 'http://thetvdb.com'

        # Configure artwork prefix url
        self.config['artwork_prefix'] = '%(base_url)s/banners/%%s' % self.config
        # Old: self.config['url_artworkPrefix'] = self.config['artwork_prefix']

        # Initiate the tvdb api v2
        api_base_url = 'https://api.thetvdb.com'

        # client_id = 'username'  # (optional! Only required for the /user routes)
        # client_secret = 'pass'  # (optional! Only required for the /user routes)
        apikey = '0629B785CE550C8D'

        authentication_string = {'apikey': apikey, 'username': '', 'userpass': ''}

        try:
            unauthenticated_client = ApiClient(api_base_url)
            auth_api = AuthenticationApi(unauthenticated_client)
            access_token = auth_api.login_post(authentication_string)
            auth_client = ApiClient(api_base_url, 'Authorization', 'Bearer ' + access_token.token)
        except ApiException as e:
            log().warning("could not authenticate to the indexer TheTvdb.com, with reason '%s',%s)", e.reason, e.status)
            raise IndexerUnavailable("Indexer unavailable with reason '%s' (%s)" % (e.reason, e.status))
        except (MaxRetryError, RequestError) as e:
            log().warning("could not authenticate to the indexer TheTvdb.com, with reason '%s'.", e.reason)
            raise IndexerUnavailable("Indexer unavailable with reason '%s'" % e.reason)

        self.search_api = SearchApi(auth_client)
        self.series_api = SeriesApi(auth_client)
        self.updates_api = UpdatesApi(auth_client)

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
            'imdbId': 'imdb_id'
        }

    def _object_to_dict(self, tvdb_response, key_mapping=None, list_separator='|'):
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
                            if list_separator and all(isinstance(x, (str, unicode)) for x in value):
                                value = list_separator.join(value)
                            else:
                                value = [self._object_to_dict(x, key_mapping) for x in value]

                        if key_mapping and key_mapping.get(attribute):
                            if isinstance(value, dict) and isinstance(key_mapping[attribute], dict):
                                # Let's map the children, i'm only going 1 deep, because usecases that I need it for,
                                # I don't need to go any further
                                for k, v in value.iteritems():
                                    if key_mapping.get(attribute)[k]:
                                        return_dict[key_mapping[attribute][k]] = v

                            else:
                                if key_mapping.get(attribute):
                                    return_dict[key_mapping[attribute]] = value
                        else:
                            return_dict[attribute] = value

                    except Exception as e:
                        log().warning('Exception trying to parse attribute: %s, with exception: %r', attribute, e)
                parsed_response.append(return_dict)
            else:
                log().debug('Missing attribute map, cant parse to dict')

        return parsed_response if len(parsed_response) != 1 else parsed_response[0]

    def _show_search(self, show, request_language='en'):
        """Use the pytvdbv2 API to search for a show.

        @param show: The show name that's searched for as a string
        @return: A list of Show objects.
        """
        try:
            results = self.search_api.search_series_get(name=show, accept_language=request_language)
        except ApiException as e:
            raise IndexerShowNotFound(
                'Show search failed in getting a result with reason: %s (%s)' % (e.reason, e.status)
            )
        except Exception as e:
            raise IndexerException('Show search failed in getting a result with error: %r' % e)

        if results:
            return results
        else:
            return OrderedDict({'data': None})

    # Tvdb implementation
    def search(self, series):
        """Search tvdbv2.com for the series name.

        :param series: the query for the series name
        :return: An ordered dict with the show searched for. In the format of OrderedDict{"series": [list of shows]}
        """
        series = series.encode('utf-8')
        log().debug('Searching for show %s', [series])

        results = self._show_search(series, request_language=self.config['language'])

        if not results:
            return

        mapped_results = self._object_to_dict(results, self.series_map, '|')
        mapped_results = [mapped_results] if not isinstance(mapped_results, list) else mapped_results

        # Remove results with an empty series_name.
        # Skip shows when they do not have a series_name in the searched language. example: '24 h berlin' in 'en'
        cleaned_results = [show for show in mapped_results if show.get('seriesname')]

        return OrderedDict({'series': cleaned_results})['series']

    def _get_show_by_id(self, tvdbv2_id, request_language='en'):  # pylint: disable=unused-argument
        """Retrieve tvdbv2 show information by tvdbv2 id, or if no tvdbv2 id provided by passed external id.

        :param tvdbv2_id: The shows tvdbv2 id
        :return: An ordered dict with the show searched for.
        """
        if tvdbv2_id:
            log().debug('Getting all show data for %s', [tvdbv2_id])
            results = self.series_api.series_id_get(tvdbv2_id, accept_language=request_language)

        if not results:
            return

        if not getattr(results.data, 'series_name', None):
            raise IndexerShowNotFoundInLanguage('Missing attribute series_name, cant index in language: {0}'
                                                .format(request_language), request_language)

        mapped_results = self._object_to_dict(results, self.series_map, '|')

        return OrderedDict({'series': mapped_results})

    def _get_episodes(self, tvdb_id, specials=False, aired_season=None):  # pylint: disable=unused-argument
        """Get all the episodes for a show by tvdbv2 id.

        :param tvdb_id: Series tvdbv2 id.
        :return: An ordered dict with the show searched for. In the format of OrderedDict{"episode": [list of episodes]}
        """
        results = []
        if aired_season:
            aired_season = [aired_season] if not isinstance(aired_season, list) else aired_season

        # Parse episode data
        log().debug('Getting all episodes of %s', [tvdb_id])

        # get paginated pages
        page = 1
        last = 1
        try:
            if aired_season:
                for season in aired_season:
                    page = 1
                    last = 1
                    while page <= last:
                        paged_episodes = self.series_api.series_id_episodes_query_get(tvdb_id, page=page, aired_season=season,
                                                                                      accept_language=self.config['language'])
                        results += paged_episodes.data
                        last = paged_episodes.links.last
                        page += 1
            else:
                while page <= last:
                    paged_episodes = self.series_api.series_id_episodes_query_get(tvdb_id, page=page,
                                                                                  accept_language=self.config['language'])
                    results += paged_episodes.data
                    last = paged_episodes.links.last
                    page += 1
        except ApiException as e:
            log().debug('Error trying to index the episodes')
            raise IndexerShowIncomplete(
                'Show episode search exception, '
                'could not get any episodes. Did a {search_type} search. Exception: {ex}'.
                format(search_type='full' if not aired_season else
                       'season {season}'.format(season=aired_season), ex=e)
            )

        if not results:
            log().debug('Series results incomplete')
            raise IndexerShowIncomplete(
                'Show episode search returned incomplete results, '
                'could not get any episodes. Did a {search_type} search.'.
                format(search_type='full' if not aired_season else
                       'season {season}'.format(season=aired_season))
            )

        mapped_episodes = self._object_to_dict(results, self.series_map, '|')
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

            # float() is because https://github.com/dbr/tvnamer/issues/95 - should probably be fixed in TVDB data
            seas_no = int(float(seasnum))
            ep_no = int(float(epno))

            for k, v in cur_ep.items():
                k = k.lower()

                if v is not None:
                    if k == 'filename':
                        v = urljoin(self.config['artwork_prefix'], v)
                    else:
                        v = self._clean_data(v)

                self._set_item(tvdb_id, seas_no, ep_no, k, v)

    def _get_series(self, series):
        """Search thetvdb.com for the series name.

        If a custom_ui UI is configured, it uses this to select the correct
        series. If not, and interactive == True, ConsoleUI is used, if not
        BaseUI is used to select the first result.

        :param series: the query for the series name
        :return: A list of series mapped to a UI (for example: a BaseUi or custom_ui).
        """
        all_series = self.search(series)
        if not all_series:
            log().debug('Series result returned zero')
            IndexerShowNotFound('Show search returned zero results (cannot find show on TVDB)')

        if not isinstance(all_series, list):
            all_series = [all_series]

        if self.config['custom_ui'] is not None:
            log().debug('Using custom UI %s', [repr(self.config['custom_ui'])])
            custom_ui = self.config['custom_ui']
            ui = custom_ui(config=self.config)
        else:
            if not self.config['interactive']:
                log().debug('Auto-selecting first search result using BaseUI')
                ui = BaseUI(config=self.config)
            else:
                log().debug('Interactively selecting show using ConsoleUI')
                ui = ConsoleUI(config=self.config)  # pylint: disable=redefined-variable-type

        return ui.select_series(all_series)

    def _parse_images(self, sid):
        """Parse images XML.

        From http://thetvdb.com/api/[APIKEY]/series/[SERIES ID]/banners.xml
        images are retrieved using t['show name]['_banners'], for example:

        >>> t = Tvdb(images = True)
        >>> t['scrubs']['_banners'].keys()
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

        log().debug('Getting show banners for %s', sid)
        _images = {}

        # Let's get the different types of images available for this series
        try:
            series_images_count = self.series_api.series_id_images_get(sid, accept_language=self.config['language'])
        except Exception as e:
            log().debug('Could not get image count for showid: %s, with exception: %r', sid, e)
            return False

        for image_type, image_count in self._object_to_dict(series_images_count).iteritems():
            try:
                if search_for_image_type and search_for_image_type != image_type:
                    # We want to use the 'poster' image also for the 'poster_thumb' type
                    if image_type != 'poster' or image_type == 'poster' and search_for_image_type != 'poster_thumb':
                        continue

                if not image_count:
                    continue

                if image_type not in _images:
                    _images[image_type] = {}

                images = self.series_api.series_id_images_query_get(sid, key_type=image_type,
                                                                    accept_language=self.config['language'])
                for image in images.data:
                    # Store the images for each resolution available
                    # Always provide a resolution or 'original'.
                    resolution = image.resolution or 'original'
                    if resolution not in _images[image_type]:
                        _images[image_type][resolution] = {}

                    # _images[image_type][resolution][image.id] = image_dict
                    image_attributes = self._object_to_dict(image, key_mapping)

                    bid = image_attributes.pop('id')

                    if image_type in ['season', 'seasonwide']:
                        if int(image.sub_key) not in _images[image_type][resolution]:
                            _images[image_type][resolution][int(image.sub_key)] = {}
                        if bid not in _images[image_type][resolution][int(image.sub_key)]:
                            _images[image_type][resolution][int(image.sub_key)][bid] = {}
                        base_path = _images[image_type][resolution][int(image.sub_key)][bid]
                    else:
                        if bid not in _images[image_type][resolution]:
                            _images[image_type][resolution][bid] = {}
                        base_path = _images[image_type][resolution][bid]

                    for k, v in image_attributes.items():
                        if k is None or v is None:
                            continue

                        if k.endswith('path'):
                            k = '_%s' % k
                            log().debug('Adding base url for image: %s', v)
                            v = self.config['artwork_prefix'] % v

                        base_path[k] = v

            except Exception as e:
                log().warning('Could not parse Poster for showid: %s, with exception: %r', sid, e)
                return False

        self._save_images(sid, _images)
        self._set_show_data(sid, '_banners', _images)

    def _parse_actors(self, sid):
        """Parser actors XML.

        From http://thetvdb.com/api/[APIKEY]/series/[SERIES ID]/actors.xml
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
            new_actor['image'] = self.config['artwork_prefix'] % cur_actor.image
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
        log().debug('Getting all series data for %s' % sid)

        # Parse show information
        series_info = self._get_show_by_id(sid, request_language=get_show_in_language)

        if not series_info:
            log().debug('Series result returned zero')
            raise IndexerError('Series result returned zero')

        # get series data / add the base_url to the image urls
        for k, v in series_info['series'].items():
            if v is not None:
                if k in ['banner', 'fanart', 'poster']:
                    v = self.config['artwork_prefix'] % v
            self._set_show_data(sid, k, v)

        # Create the externals structure
        self._set_show_data(sid, 'externals', {'imdb_id': str(getattr(self[sid], 'imdb_id', ''))})

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
    def get_last_updated_series(self, from_time, weeks=1, filter_show_list=None):
        """Retrieve a list with updated shows.

        :param from_time: epoch timestamp, with the start date/time
        :param weeks: number of weeks to get updates for.
        :param filter_show_list: Optional list of show objects, to use for filtering the returned list.
        :returns: A list of show_id's.
        """
        total_updates = []
        updates = True

        count = 0
        try:
            while updates and count < weeks:
                updates = self.updates_api.updated_query_get(from_time).data
                last_update_ts = max(x.last_updated for x in updates)
                from_time = last_update_ts
                total_updates += [int(_.id) for _ in updates]
                count += 1
        except RequestError as e:
            raise IndexerUnavailable('Error connecting to Tvdb api. Caused by: {0!r}'.format(e))

        if total_updates and filter_show_list:
            new_list = []
            for show in filter_show_list:
                if show.indexerid in total_updates:
                    new_list.append(show.indexerid)
            total_updates = new_list

        return total_updates
