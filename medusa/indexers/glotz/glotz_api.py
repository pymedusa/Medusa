# coding=utf-8

"""Glotz api module."""
from __future__ import unicode_literals

import logging
from collections import OrderedDict
from time import time

from medusa import app
from medusa.app import GLOTZ_API_KEY
from medusa.indexers.indexer_base import (Actor, Actors, BaseIndexer)
from medusa.indexers.indexer_exceptions import (IndexerError, IndexerException, IndexerShowNotFound)
from medusa.logger.adapters.style import BraceAdapter

from pyglotz import Glotz
from pyglotz.exceptions import (ActorNotFound, BaseError, IDNotFound, ShowIndexError, ShowNotFound, UpdateNotFound)

from requests.compat import urljoin

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class GLOTZ(BaseIndexer):
    """Create easy-to-use interface to name of season/episode name.

    >>> indexer_api = Glotz()
    >>> indexer_api['Scrubs'][1][24]['episodename']
    u'My Last Day'
    """

    def __init__(self, *args, **kwargs):  # pylint: disable=too-many-locals,too-many-arguments
        super(GLOTZ, self).__init__(*args, **kwargs)

        # Initiate the Glotz API
        self.glotz_api = Glotz(api_key=GLOTZ_API_KEY, session=self.config['session'])
        # TODO check if better linked directly to TVDB
        self.config['artwork_prefix'] = '{base_url}/banners/{{image}}'.format(base_url='https://www.glotz.info')

        # An api to indexer series/episode object mapping
        self.series_map = {
            # series stuff
            'id': 'id',
            'actors': 'actors',
            'airs_day_of_week': 'airs_dayofweek',
            'airs_time': 'airs_time',
            'content_rating': 'contentrating',
            'first_aired': 'firstaired',
            'genre': 'genre',
            'imdb_id': 'imdb_id',
            'language': 'language',
            'network': 'network',
            'network_id': 'networkid',
            'overview': 'overview',
            'rating': 'rating',
            'rating_count': 'rating_count',
            'runtime': 'runtime',
            'series_id': 'series_id',
            'series_name': 'seriesname',
            'status': 'status',
            'added': 'added',
            'added_by': 'added_by',
            'banner': 'banner',
            'fan_art': 'fanart',
            'last_updated': 'last_updated',
            'poster': 'poster',
            'zap2it_id': 'zap2it_id',
            'slug': 'slug',
            'tvrage_id': 'tvrage_id',
            'year': 'year',
            'aliases': 'aliases',
            'url': 'show_url',
            # additional episode stuff
            # 'combined_episodenumber': 'episodenumber',
            'combined_season': 'seasonnumber',
            'cvd_chapter': 'cvd_chapter',
            'dvd_discid': 'dvd_discid',
            'dvd_episodenumber': 'dvd_episodenumber',
            'dvd_season': 'dvd_season',
            'director': 'director',
            # 'ep_img_flag': 'ep_img_flag',
            'episode_name': 'episodename',
            'episode_number': 'episodenumber',
            'guest_stars': 'guest_stars',
            'production_code': 'production_code',
            'season_number': 'seasonnumber',
            'writer': 'writers',
            'absolute_number': 'absolute_number',
            'filename': 'filename',
            'season_id': 'seasonid',
            'thumb_added': 'thumb_added',
            'thumb_height': 'thumb_height',
            'thumb_width': 'thumb_width',
        }

    def _map_results(self, glotz_response, key_mappings=None, list_separator='|'):
        """
        Map results to a a key_mapping dict.

        :param glotz_response: glotz response object, or a list of response objects.
        :type glotz_response: list(object)
        :param key_mappings: Dict of glotz attributes, that are mapped to normalized keys.
        :type key_mappings: dictionary
        :param list_separator: A list separator used to transform lists to a character separator string.
        :type list_separator: string.
        """
        parsed_response = []

        if not isinstance(glotz_response, list):
            glotz_response = [glotz_response]

        for item in glotz_response:
            return_dict = {}
            try:
                for key, value in iter(item.__dict__.items()):
                    if value is None or value == []:
                        continue

                    if isinstance(value, list) and value != 'episodes':
                        if all(isinstance(x, (str, int)) for x in value):
                            value = list_separator.join(str(v) for v in value)

                    # Try to map the key
                    if key in key_mappings:
                        key = key_mappings[key]

                    # Set value to key
                    return_dict[key] = str(value) if isinstance(value, (float, int)) else value

            except Exception as error:
                log.warning('Exception trying to parse attribute: {0}, with exception: {1!r}', key, error)

            parsed_response.append(return_dict)

        return parsed_response if len(parsed_response) != 1 else parsed_response[0]

    # get show by name
    def _show_search(self, show, request_language='de'):
        """
        Use the Glotz API to search for a show.

        :param show: The show name that's searched for as a string.
        :param request_language: Language in two letter code. As Glotz is primarily a German indexer, default is German
        :return: A list of Show objects.
        """
        try:
            results = self.glotz_api.get_show_list(show, request_language)
        except ShowNotFound as error:
            # Use error.value because Glotz API exceptions may be utf-8 encoded when using __str__
            raise IndexerShowNotFound(
                'Show search failed in getting a result with reason: {0}'.format(error.value)
            )
        except BaseError as error:
            raise IndexerException('Show search failed in getting a result with error: {0!r}'.format(error))

        if results:
            return results
        else:
            return None

    # Tvdb implementation
    def search(self, series):
        """Search glotz.info for the series name.

        :param series: the query for the series name
        :return: An ordered dict with the show searched for. In the format of OrderedDict{"series": [list of shows]}
        """
        log.debug('Searching for show {0}', series)

        results = self._show_search(series, request_language=self.config['language'])

        if not results:
            return

        mapped_results = self._map_results(results, self.series_map, '|')

        return OrderedDict({'series': mapped_results})['series']

    def _get_show_by_id(self, tvdb_id, request_language='de'):  # pylint: disable=unused-argument
        """Retrieve Glotz show information by tvdb id.

        :param tvdb_id: The shows tvdb id
        :return: An ordered dict with the show searched for.
        """
        results = None
        if tvdb_id:
            log.debug('Getting all show data for {0}', tvdb_id)
            results = self.glotz_api.get_show(tvdb_id=tvdb_id, language=request_language)

        if results:
            log.debug('Getting aliases for show {0}', tvdb_id)
            results.aliases = self.glotz_api.get_show_aliases(tvdb_id)
        if not results:
            log.debug('Getting show data for {0} on Glotz failed', tvdb_id)
            return

        mapped_results = self._map_results(results, self.series_map)

        return OrderedDict({'series': mapped_results})

    def _get_episodes(self, tvdb_id, specials=False, aired_season=None):  # pylint: disable=unused-argument
        """
        Get all the episodes for a show by tvdb id.

        :param tvdb_id: Series tvdb id.
        :return: An ordered dict with the show searched for. In the format of OrderedDict{"episode": [list of episodes]}
        """
        # Parse episode data
        log.debug('Getting all episodes of {0}', tvdb_id)
        try:
            results = self.glotz_api.get_show(tvdb_id)
        except IDNotFound:
            log.debug('Episode search did not return any results.')
            return False
        except BaseError as e:
            raise IndexerException('Show episodes search failed in getting a result with error: {0!r}'.format(e))

        episodes = self._map_results(results.episodes, self.series_map)

        return self._parse_episodes(tvdb_id, episodes)

    def _parse_episodes(self, tvdb_id, episodes):
        """Parse retreived episodes."""
        if not episodes:
            return False

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

            if seas_no is None or ep_no is None:
                log.warning('Invalid episode numbering (series: {0}({1}), season: {2!r}, episode: {3!r}) '
                            'Contact TVDB forums to have it fixed',
                            self.shows[tvdb_id]['seriesname'], tvdb_id, seas_no, ep_no)
                continue  # Skip to next episode

            # float() is because https://github.com/dbr/tvnamer/issues/95 - should probably be fixed in TVDB data
            seas_no = int(float(seas_no))
            ep_no = int(float(ep_no))

            for k, v in dict.items(cur_ep):
                k = k.lower()

                if v and k == 'filename':
                    v = urljoin(self.config['artwork_prefix'], v)

                self._set_item(tvdb_id, seas_no, ep_no, k, v)

    def _get_show_data(self, sid, language):
        """Fetches available information about a show."""
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
        for k, v in dict.items(series_info['series']):
            if v is not None:
                if v and k in ['banner', 'fanart', 'poster']:
                    v = self.config['artwork_prefix'].format(image=v)
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

    def _parse_images(self, sid):
        """Get image information from Glotz and parse them."""
        key_mapping = {'id': 'id', 'banner_path': 'bannerpath', 'banner_type': 'bannertype',
                       'banner_type2': 'bannertype2', 'colors': 'colors', 'series_name': 'seriesname',
                       'thumbnail_path': 'thumbnailpath', 'vignette_path': 'vignettepath', 'language': 'language',
                       'season': 'season', 'rating': 'rating', 'rating_count': 'ratingcount'}

        log.debug('Getting show banners for {0}', sid)
        _images = {}

        # Let's get the different types of images available for this series
        try:
            series_images = self.glotz_api.get_banners(sid)
        except IndexerError as error:
            log.info('Could not get images for show ID: {0} with reason: {1}', sid, error)
            return

        results = self._map_results(series_images, key_mappings=key_mapping)

        img_types = ['poster', 'fanart', 'season', 'series', 'seasonwide']

        for img in results:
            # don't process all languages
            if img.get('language') == 'en' or self.config['language']:
                _img_type = img.get('bannertype')

                # filter unknown image types
                if (_img_type not in _images) and (_img_type in img_types):

                    # Glotz returns seasonwides as bannertype2
                    if img.get('bannertype2') == 'seasonwide':
                        _img_type = 'seasonwide'

                    _images[_img_type] = {}

                # set resolution to 'original' if not a number
                if img.get('bannertype2')[0].isdigit():
                    _resolution = img.get('bannertype2')
                else:
                    _resolution = 'original'

                if _resolution not in _images[_img_type]:
                    _images[_img_type][_resolution] = {}

                _img_id = img.pop('id')

                if _img_type in ['season', 'seasonwide']:
                    if img.get('season').isdigit():
                        _sub_key = int(img.get('season'))
                    else:
                        _sub_key = 1
                    if _sub_key not in _images[_img_type][_resolution]:
                        _images[_img_type][_resolution][_sub_key] = {}
                    if _img_id not in _images[_img_type][_resolution][_sub_key]:
                        _images[_img_type][_resolution][_sub_key][_img_id] = {}
                    base_path = _images[_img_type][_resolution][_sub_key][_img_id]
                else:
                    if _img_id not in _images[_img_type][_resolution]:
                        _images[_img_type][_resolution][_img_id] = {}
                    base_path = _images[_img_type][_resolution][_img_id]

                for k, v in dict.items(img):
                    if k is None or v is None:
                        continue

                    if k.endswith('path'):
                        k = '_{0}'.format(k)
                        log.debug('Adding base url for image: {0}', v)
                        v = self.config['artwork_prefix'].format(image=v)

                    base_path[k] = v

                if 'rating' not in base_path:
                    base_path['rating'] = 1
                else:
                    base_path['rating'] = float(base_path['rating'])

                if 'ratingcount' not in base_path:
                    base_path['ratingcount'] = 1
                else:
                    base_path['ratingcount'] = int(float(base_path['ratingcount']))

        self._save_images(sid, _images)
        self._set_show_data(sid, '_banners', _images)

    def _parse_actors(self, sid):
        """Parser actors JSON.

        From http://www.glotz.info/api/[APIKEY]/series/[SERIES ID]/actors.json
        Actors are retrieved using t['show name]['_actors'].
        """
        log.debug('Getting actors for {0}', sid)

        try:
            _actors = self.glotz_api.get_actors_list(sid)
        except ActorNotFound:
            log.debug('Actors result returned zero')
            return
        except IndexerError as error:
            log.info('Could not get actors for show ID: {0} with reason: {1}', sid, error)
            return

        cur_actors = Actors()
        for cur_actor in _actors if isinstance(_actors, list) else [_actors]:
            new_actor = Actor()
            new_actor['id'] = cur_actor.id
            new_actor['image'] = self.config['artwork_prefix'].format(image=cur_actor.image)
            new_actor['name'] = cur_actor.name
            new_actor['role'] = cur_actor.role
            new_actor['sortorder'] = cur_actor.sort_order
            cur_actors.append(new_actor)
        self._set_show_data(sid, '_actors', cur_actors)

    def _get_updates(self, start_date=int(time()) - 604800):
        """Retrieve all shows that have been updated from Glotz."""
        results = []
        try:
            updates = self.glotz_api.get_show_updates(start_date)
        except (ShowIndexError, UpdateNotFound):
            return results
        except BaseError as e:
            log.warning('Getting show updates failed. Cause: {0}', e)
            return results

        if updates:
            for item in updates:
                if start_date < int(item.get('last_update')) < (int(time())):
                    results.append(int(item.get('tvdb_id')))

        return results

    def get_last_updated_series(self, from_time, weeks=1, filter_show_list=None):
        """Retrieve a list with updated shows.

        :param from_time: epoch timestamp, with the start date/time
        :param weeks: number of weeks to get updates for.
        :param filter_show_list: Optional list of show objects, to use for filtering the returned list.
        :returns: A list of show_id's.
        """
        updates = self._get_updates(from_time)
        if updates and filter_show_list:
            new_list = []
            for show in filter_show_list:
                if show.indexerid in updates:
                    new_list.append(show.indexerid)
            updates = new_list

        return updates
