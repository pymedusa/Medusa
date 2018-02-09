# coding=utf-8

from __future__ import unicode_literals

from datetime import datetime
from itertools import chain
import logging
from collections import OrderedDict
from imdbpie import imdbpie
import locale
from six import string_types, text_type
from medusa.bs4_parser import BS4Parser
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

    def _clean(self, imdb_id):
        if isinstance(imdb_id, string_types):
            return imdb_id.strip('/').split('/')[-1]

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
        if isinstance(value, string_types) and 'tt' in value:
            self._imdb_id = self._clean(value)
            self.series_id = int(self._imdb_id.split('tt')[-1])
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
            ('poster', 'base.image.url'),
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
        :type key_mappings: list
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
                title_type = item.get('type') or item.get('base',{}).get('titleType')
                if title_type in ('feature', 'video game', 'TV short', None):
                    continue

                # return_dict['id'] = ImdbIdentifier(item.pop('imdb_id')).series_id
                for key, config in self.series_map:
                    value = self.get_nested_value(item, config)
                    if not value:
                        continue
                    if key == 'id' and value:
                        value = ImdbIdentifier(value.rstrip('/')).series_id
                    if key == 'contentrating':
                        value = text_type(value)
                    if key == 'poster':
                        return_dict['poster_thumb'] = value.split('V1')[0] + 'V1_SY{0}_AL_.jpg'.format('1000').split('/')[-1]
                    if value is not None:
                        return_dict[key] = value

                # Check if the show is continuing
                return_dict['status'] = 'Continuing' if item.get('base', {}).get('nextEpisode') else 'Ended'

                # Add static value for airs time.
                return_dict['airs_time'] = '0:00AM'

            except Exception as error:
                log.warning('Exception trying to parse attribute: {0}, with exception: {1!r}', item, error)

            parsed_response.append(return_dict)

        return parsed_response if len(parsed_response) != 1 else parsed_response[0]

    def _show_search(self, series, request_language='en'):
        """
        Uses the TVMaze API to search for a show
        :param series: The series name that's searched for as a string
        :param request_language: Language in two letter code. TVMaze fallsback to en itself.
        :return: A list of Show objects.
        """

        results = self.imdb_api.search_for_title(series)

        if results:
            return results
        else:
            return None

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

        if not mapped_results:
            return

        # Get firstaired
        releases = self.imdb_api.get_title_releases(imdb_id)
        if releases.get('releases'):
            first_released = sorted([r for r in releases['releases']])[0]
            mapped_results['firstaired'] = first_released['date']

        companies = self.imdb_api.get_title_companies(imdb_id)
        origins = self.imdb_api.get_title_versions(imdb_id)['origins'][0]
        first_release = sorted([dist for dist in companies['distribution'] if origins in dist['regions']], key=lambda x: x['startYear'])

        if first_release:
            mapped_results['network'] = first_release[0]['company']['name']

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
        imdb_id = ImdbIdentifier(imdb_id).imdb_id
        results = self.imdb_api.get_title_episodes(imdb_id)

        if not results or not results.get('seasons'):
            return False

        for season in results.get('seasons'):
            for episode in season['episodes']:
                season_no, episode_no = episode.get('season'), episode.get('episode')

                if season_no is None or episode_no is None:
                    log.warning('An episode has incomplete season/episode number (season: {0!r}, episode: {1!r})',
                                season_no, episode_no)
                    continue  # Skip to next episode

                for k, config in self.episode_map:
                    v = self.get_nested_value(episode, config)
                    if v is not None:
                        if k == 'id':
                            v = ImdbIdentifier(v).series_id
                        if k == 'firstaired':
                            v = '{year}-01-01'.format(year=v)

                        self._set_item(series_id, season_no, episode_no, k, v)

            if season.get('season'):
                # Enrich episode for the current season.
                self._enrich_episodes(imdb_id, season['season'])

    def _enrich_episodes(self, imdb_id, season):
        """Enrich the episodes with additional information for a specific season."""
        episodes_url = 'http://www.imdb.com/title/{imdb_id}/episodes?season={season}'
        series_id = ImdbIdentifier(imdb_id).series_id
        try:
            response = self.config['session'].get(episodes_url.format(imdb_id=ImdbIdentifier(imdb_id).imdb_id, season=season))
            with BS4Parser(response.text, 'html5lib') as html:
                for episode in html.find_all('div', class_='list_item'):
                    try:
                        episode_no = int(episode.find('meta')['content'])
                    except AttributeError:
                        pass
                    try:
                        first_aired_raw = episode.find('div', class_='airdate').get_text(strip=True)
                    except AttributeError:
                        pass

                    lc = locale.setlocale(locale.LC_TIME)
                    try:
                        locale.setlocale(locale.LC_ALL, 'C')
                        first_aired = datetime.strptime(first_aired_raw.replace('.', ''), '%d %b %Y').strftime('%Y-%m-%d')
                    except (AttributeError, ValueError):
                        first_aired = None
                    finally:
                        locale.setlocale(locale.LC_TIME, lc)

                    try:
                        episode_rating = float(episode.find('span', class_='ipl-rating-star__rating').get_text(strip=True))
                    except AttributeError:
                        episode_rating = None

                    try:
                        episode_votes = int(episode.find('span', class_='ipl-rating-star__total-votes').get_text(strip=True).strip('()').replace(',', ''))
                    except AttributeError:
                        episode_votes = None

                    try:
                        synopsis = episode.find('div', class_='item_description').get_text(strip=True)
                        if 'Know what this is about?' in synopsis:
                            synopsis = ''
                    except AttributeError:
                        synopsis = ''

                    self._set_item(series_id, season, episode_no, 'firstaired', first_aired)
                    self._set_item(series_id, season, episode_no, 'rating', episode_rating)
                    self._set_item(series_id, season, episode_no, 'votes', episode_votes)
                    self._set_item(series_id, season, episode_no, 'overview', synopsis)

        except Exception as error:
            log.exception('Error while trying to enrich imdb series {0}, {1}', series_id, error)

    def _parse_images(self, imdb_id):
        """Parse Show and Season posters.

        Any key starting with an underscore has been processed (not the raw
        data from the XML)

        This interface will be improved in future versions.
        """
        log.debug('Getting show banners for {0}', imdb_id)

        images = self.imdb_api.get_title_images(ImdbIdentifier(imdb_id).imdb_id)
        thumb_height = 640

        _images = {}
        try:
            for image in images.get('images', []):
                if image.get('type') not in ('poster',):
                    continue

                image_type = image.get('type')
                image_type_thumb = image_type + '_thumb'
                if image_type not in _images:
                    _images[image_type] = {}
                    _images[image_type + '_thumb'] = {}

                # Store the images for each resolution available
                # Always provide a resolution or 'original'.
                resolution = '{0}x{1}'.format(image['width'], image['height'])
                thumb_width = int((float(image['width']) / image['height']) * thumb_height)
                resolution_thumb = '{0}x{1}'.format(thumb_width, thumb_height)

                if resolution not in _images[image_type]:
                    _images[image_type][resolution] = {}
                    _images[image_type_thumb][resolution_thumb] = {}

                bid = image['id'].split('/')[-1]

                if image_type in ['season', 'seasonwide']:
                    if int(image.sub_key) not in _images[image_type][resolution]:
                        _images[image_type][resolution][int(image.sub_key)] = {}
                    if bid not in _images[image_type][resolution][int(image.sub_key)]:
                        _images[image_type][resolution][int(image.sub_key)][bid] = {}
                    base_path = _images[image_type_thumb][resolution][int(image.sub_key)][bid]
                else:
                    if bid not in _images[image_type][resolution]:
                        _images[image_type][resolution][bid] = {}
                        _images[image_type_thumb][resolution_thumb][bid] = {}
                    base_path = _images[image_type][resolution][bid]
                    base_path_thumb = _images[image_type_thumb][resolution_thumb][bid]

                base_path['bannertype'] = image_type
                base_path['bannertype2'] = resolution
                base_path['_bannerpath'] = image.get('url')
                base_path['bannerpath'] = image.get('url').split('/')[-1]
                base_path['id'] = bid

                base_path_thumb['bannertype'] = image_type_thumb
                base_path_thumb['bannertype2'] = resolution_thumb
                base_path_thumb['_bannerpath'] = image['url'].split('V1')[0] + 'V1_SY{0}_AL_.jpg'.format(thumb_height)
                base_path_thumb['bannerpath'] = image['url'].split('V1')[0] + 'V1_SY{0}_AL_.jpg'.format(thumb_height).split('/')[-1]
                base_path_thumb['id'] = bid

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
                u'Selecting image with the highest resolution {image} (resolution={resolution}):', {
                    'image': img_type,
                    'resolution': highest_rated['bannertype2'],
                }
            )

            # Save the image
            self._set_show_data(series_id, img_type, img_url)

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
                'Configured language {0} override show language of {1}',
                self.config['language'],
                language
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
