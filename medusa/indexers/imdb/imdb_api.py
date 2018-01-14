# coding=utf-8

from __future__ import unicode_literals
from itertools import chain
import logging
from collections import OrderedDict
from imdbpie import imdbpie
from time import time
from six import text_type

from medusa.indexers.indexer_base import (Actor, Actors, BaseIndexer)
from medusa.indexers.indexer_exceptions import (
    IndexerError,
)
from medusa.logger.adapters.style import BraceAdapter


log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class ImdbIdentifier(object):
    def __init__(self, imdb_id):
        """Initialize an identifier object. Can be used to get the full textual id e.a. 'tt3986523'.
        Or the series_id: 3986523
        """
        self._imdb_id = None
        self._series_id = None
        self.imdb_id = imdb_id

    @property
    def series_id(self):
        return self._series_id

    @series_id.setter
    def series_id(self, value):
        self._series_id = value

    @property
    def imdb_id(self):
        return self._imdb_id

    @imdb_id.setter
    def imdb_id(self, value):
        if isinstance(value, text_type) and 'tt' in value:
            self._imdb_id = value
            self.series_id = int(value.split('tt')[-1])
        else:
            self._imdb_id = 'tt{0}'.format(text_type(value).zfill(7))
            self.series_id = int(value)


class Imdb(BaseIndexer):
    """Create easy-to-use interface to name of season/episode name
    >>> indexer_api = imdb()
    >>> indexer_api['Scrubs'][1][24]['episodename']
    u'My Last Day'
    """

    def __init__(self, *args, **kwargs):  # pylint: disable=too-many-locals,too-many-arguments
        super(Imdb, self).__init__(*args, **kwargs)

        self.indexer = 10

        # List of language from http://theimdb.com/api/0629B785CE550C8D/languages.xml
        # Hard-coded here as it is realtively static, and saves another HTTP request, as
        # recommended on http://theimdb.com/wiki/index.php/API:languages.xml
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

        # Initiate the imdbpie API
        self.imdb_api = imdbpie.Imdb(session=self.config['session'])

        self.config['artwork_prefix'] = '{base_url}{image_size}{file_path}'

        # An api to indexer series/episode object mapping
        self.series_map = [
            ('id', 'imdb_id'),
            ('id', 'base.id'),
            ('seriesname', 'title'),
            ('seriesname', 'base.title'),
            ('summary', 'plot.summaries[0].text'),
            ('firstaired', 'year'),
            ('fanart', 'base.image.url'),
            ('show_url', 'base.id'),
            ('firstaired', 'base.seriesStartYear'),
            ('contentrating', 'ratings.rating'),
        ]

        self.episode_map = [
            ('id', 'id'),
            ('episodename', 'title'),
            ('firstaired', 'year'),
        ]

    def _map_results(self, imdb_response, key_mappings=None, list_separator='|'):
        """
        Map results to a a key_mapping dict.

        :param imdb_response: imdb response obect, or a list of response objects.
        :type imdb_response: list(object)
        :param key_mappings: Dict of imdb attributes, that are mapped to normalized keys.
        :type key_mappings: dictionary
        :param list_separator: A list separator used to transform lists to a character separator string.
        :type list_separator: string.
        """
        parsed_response = []

        if not isinstance(imdb_response, list):
            imdb_response = [imdb_response]

        # TVmaze does not number their special episodes. It does map it to a season. And that's something, medusa
        # Doesn't support. So for now, we increment based on the order, we process the specials. And map it to
        # season 0. We start with episode 1.
        index_special_episodes = 1

        for item in imdb_response:
            return_dict = {}
            try:
                if item.get('type') in ('feature', 'video game', 'TV short'):
                    continue

                # return_dict['id'] = ImdbIdentifier(item.pop('imdb_id')).series_id
                for key, config in self.series_map:
                    value = self.get_nested_value(item, config)
                    if key == 'id' and value:
                        value = ImdbIdentifier(value.rstrip('/')).series_id
                    if key == 'contentrating':
                        value = text_type(value)
                    if value is not None:
                        return_dict[key] = value

                # Check if the show is continuing
                return_dict['status'] = 'Continuing' if item.get('base', {}).get('nextEpisode') else 'Ended'

            except Exception as error:
                log.warning('Exception trying to parse attribute: {0}, with exception: {1!r}', item, error)

            parsed_response.append(return_dict)

        return parsed_response if len(parsed_response) != 1 else parsed_response[0]

    def _show_search(self, series, request_language='en'):
        """
        Uses the TVMaze API to search for a show
        :param show: The show name that's searched for as a string
        :param request_language: Language in two letter code. TVMaze fallsback to en itself.
        :return: A list of Show objects.
        """

        results = self.imdb_api.search_for_title(series)

        if results:
            return results
        else:
            return None

    # Tvdb implementation
    def search(self, series):
        """This searches imdb.com for the series name

        :param series: the query for the series name
        :return: An ordered dict with the show searched for. In the format of OrderedDict{"series": [list of shows]}
        """
        series = series.encode('utf-8')
        log.debug('Searching for show {0}', series)

        results = self._show_search(series, request_language=self.config['language'])

        if not results:
            return

        mapped_results = self._map_results(results, self.series_map, '|')

        return OrderedDict({'series': mapped_results})['series']

    def _get_show_by_id(self, imdb_id, request_language='en'):  # pylint: disable=unused-argument
        """
        Retrieve imdb show information by imdb id, or if no imdb id provided by passed external id.

        :param imdb_id: The shows imdb id
        :return: An ordered dict with the show searched for.
        """
        results = None
        imdb_id = ImdbIdentifier(imdb_id).imdb_id
        if imdb_id:
            log.debug('Getting all show data for {0}', imdb_id)
            results = self.imdb_api.get_title(imdb_id)

        if not results:
            return

        mapped_results = self._map_results(results, self.series_map)

        # Get firstaired
        releases = self.imdb_api.get_title_releases(imdb_id)
        if releases.get('releases'):
            first_released = sorted([r['date'] for r in releases['releases']])[0]
            mapped_results['firstaired'] = first_released
        return OrderedDict({'series': mapped_results})

    def _get_episodes(self, imdb_id, specials=False, aired_season=None):  # pylint: disable=unused-argument
        """
        Get all the episodes for a show by imdb id

        :param imdb_id: Series imdb id.
        :return: An ordered dict with the show searched for. In the format of OrderedDict{"episode": [list of episodes]}
        """
        # Parse episode data
        log.debug('Getting all episodes of {0}', imdb_id)

        series_id = imdb_id
        imdb_id = 'tt{0}'.format(text_type(imdb_id).zfill(7))
        results = self.imdb_api.get_title_episodes(imdb_id)

        if not results or not results.get('seasons'):
            return False

        for season in results.get('seasons'):
            for episode in season['episodes']:
                season_no, episode_no = episode.get('season'), episode.get('episode')

                if season_no is None or episode_no is None:
                    log.warning('An episode has incomplete season/episode number (season: {0!r}, episode: {1!r})', seasnum, epno)
                    continue  # Skip to next episode

                for k, config in self.episode_map:
                    v = self.get_nested_value(episode, config)
                    if v is not None:
                        if k == 'id':
                            v = ImdbIdentifier(v.rstrip('/')).series_id
                        if k == 'firstaired':
                            v = '{year}-01-01'.format(year=v)

                        self._set_item(series_id, season_no, episode_no, k, v)

    def _parse_images(self, imdb_id):
        """Parse Show and Season posters.

        Any key starting with an underscore has been processed (not the raw
        data from the XML)

        This interface will be improved in future versions.
        """
        log.debug('Getting show banners for {0}', imdb_id)

        images = self.imdb_api.get_title_images(ImdbIdentifier(imdb_id).imdb_id)

        _images = {}
        try:
            for image in images.get('images', []):
                if image.get('type') not in ('poster',):
                    continue

                image_type = image.get('type')
                if image_type not in _images:
                    _images[image_type] = {}

                # Store the images for each resolution available
                # Always provide a resolution or 'original'.
                resolution = '{0}x{1}'.format(image['width'], image['height'])
                if resolution not in _images[image_type]:
                    _images[image_type][resolution] = {}

                bid = image['id'].split('/')[-1]

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

                base_path['bannertype'] = image_type
                base_path['bannertype2'] = resolution
                base_path['_bannerpath'] = image.get('url')
                base_path['bannerpath'] = image.get('url').split('/')[-1]
                base_path['id'] = bid

        except Exception as error:
            log.warning('Could not parse Poster for show id: {0}, with exception: {1!r}', imdb_id, error)
            return

        self._save_images(imdb_id, _images)
        self._set_show_data(imdb_id, '_banners', _images)

    def _save_images(self, series_id, images):
        """
        Save the highest rated images for the show.

        :param series_id: The series ID
        :param images: A nested mapping of image info
            images[type][res][id] = image_info_mapping
                type: image type such as `banner`, `poster`, etc
                res: resolution such as `1024x768`, `original`, etc
                id: the image id
        """
        # Get desired image types from images
        image_types = 'banner', 'fanart', 'poster'

        def get_resolution(image):
            w, h = image['bannertype2'].split('x')
            return int(w) * int(h)

        # Iterate through desired image types
        for img_type in image_types:

            try:
                image_type = images[img_type]
            except KeyError:
                log.debug(
                    u'No {image}s found for {series}', {
                        'image': img_type,
                        'series': series_id,
                    }
                )
                continue

            # Flatten image_type[res][id].values() into list of values
            merged_images = chain.from_iterable(
                resolution.values()
                for resolution in image_type.values()
            )

            # Sort by resolution
            sort_images = sorted(
                merged_images,
                key=get_resolution,
                reverse=True,
            )

            if not sort_images:
                continue

            # Get the highest rated image
            highest_rated = sort_images[0]
            img_url = highest_rated['_bannerpath']
            log.debug(
                u'Selecting highest rated {image} (rating={img[rating]}):'
                u' {img[_bannerpath]}', {
                    'image': img_type,
                    'img': highest_rated,
                }
            )
            log.debug(
                u'{image} details: {img}', {
                    'image': img_type.capitalize(),
                    'img': highest_rated,
                }
            )

            # Save the image
            self._set_show_data(series_id, img_type, img_url)

    def _parse_season_images(self, imdb_id):
        """Parse Show and Season posters."""
        seasons = {}
        if imdb_id:
            log.debug('Getting all show data for {0}', imdb_id)
            try:
                seasons = self.imdb_api.show_seasons(maze_id=imdb_id)
            except BaseError as e:
                log.warning('Getting show seasons for the season images failed. Cause: {0}', e)

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

    def _parse_actors(self, imdb_id):
        """Parsers actors XML, from
        http://theimdb.com/api/[APIKEY]/series/[SERIES ID]/actors.xml

        Actors are retrieved using t['show name]['_actors'], for example:

        >>> indexer_api = TVMaze(actors = True)
        >>> actors = indexer_api['scrubs']['_actors']
        >>> type(actors)
        <class 'imdb_api.Actors'>
        >>> type(actors[0])
        <class 'imdb_api.Actor'>
        >>> actors[0]
        <Actor "Zach Braff">
        >>> sorted(actors[0].keys())
        ['id', 'image', 'name', 'role', 'sortorder']
        >>> actors[0]['name']
        u'Zach Braff'
        >>> actors[0]['image']
        u'http://theimdb.com/banners/actors/43640.jpg'

        Any key starting with an underscore has been processed (not the raw
        data from the indexer)
        """
        log.debug('Getting actors for {0}', imdb_id)
        return
        # FIXME: implement cast
        actors = self.imdb_api.show_cast(imdb_id)

        cur_actors = Actors()
        for order, cur_actor in enumerate(actors.people):
            save_actor = Actor()
            save_actor['id'] = cur_actor.id
            save_actor['image'] = cur_actor.image.get('original') if cur_actor.image else ''
            save_actor['name'] = cur_actor.name
            save_actor['role'] = cur_actor.character.name
            save_actor['sortorder'] = order
            cur_actors.append(save_actor)
        self._set_show_data(imdb_id, '_actors', cur_actors)

    def _get_show_data(self, imdb_id, language='en'):  # pylint: disable=too-many-branches,too-many-statements,too-many-locals
        """Takes a series ID, gets the epInfo URL and parses the imdb json response
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
                'Configured language {0} override show language of {1}', (
                    self.config['language'],
                    language
                )
            )
            get_show_in_language = self.config['language']

        # Parse show information
        log.debug('Getting all series data for {0}', imdb_id)

        # Parse show information
        series_info = self._get_show_by_id(imdb_id, request_language=get_show_in_language)

        if not series_info:
            log.debug('Series result returned zero')
            raise IndexerError('Series result returned zero')

        # save all retrieved show information to Show object.
        for k, v in series_info['series'].items():
            if v is not None:
                self._set_show_data(imdb_id, k, v)

        # Get external ids.
        # As the external id's are not part of the shows default response, we need to make an additional call for it.
        # Im checking for the external value. to make sure only externals with a value get in.
        self._set_show_data(imdb_id, 'externals', {external_id: text_type(getattr(self.shows[imdb_id], external_id, None))
                                                   for external_id in ['tvdb_id', 'imdb_id', 'tvrage_id']
                                                   if getattr(self.shows[imdb_id], external_id, None)})

        # get episode data
        if self.config['episodes_enabled']:
            self._get_episodes(imdb_id, specials=False, aired_season=None)

        # Parse banners
        if self.config['banners_enabled']:
            self._parse_images(imdb_id)

        # Parse actors
        if self.config['actors_enabled']:
            self._parse_actors(imdb_id)

        return True

    def _get_all_updates(self, start_date=None, end_date=None):
        """Retrieve all updates (show,season,episode) from TVMaze."""
        results = []
        try:
            updates = self.imdb_api.show_updates()
        except (ShowIndexError, UpdateNotFound):
            return results
        except BaseError as e:
            log.warning('Getting show updates failed. Cause: {0}', e)
            return results

        if getattr(updates, 'updates', None):
            for show_id, update_ts in updates.updates.items():
                if start_date < update_ts.seconds_since_epoch < (end_date or int(time())):
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
        """Search imdb for a show, using an external id.

        Accepts as kwargs, so you'l need to add the externals as key/values.
        :param tvrage: The tvrage id.
        :param thetvdb: The tvdb id.
        :param imdb: An imdb id (inc. tt).
        :returns: A dict with externals, including the imdb id.
        """
        mapping = {'thetvdb': 'tvdb_id', 'tvrage': 'tvrage_id', 'imdb': 'imdb_id'}
        for external_id in mapping.values():
            if kwargs.get(external_id):
                try:
                    result = self.imdb_api.get_show(**{external_id: kwargs.get(external_id)})
                    if result:
                        externals = {mapping[imdb_external_id]: external_value
                                     for imdb_external_id, external_value
                                     in result.externals.items()
                                     if external_value and mapping.get(imdb_external_id)}
                        externals['imdb_id'] = result.maze_id
                        return externals
                except ShowNotFound:
                    log.debug('Could not get imdb externals using external key {0} and id {1}',
                              external_id, kwargs.get(external_id))
                    continue
                except BaseError as e:
                    log.warning('Could not get imdb externals. Cause: {0}', e)
                    continue
        return {}
