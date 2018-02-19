# coding=utf-8

from __future__ import unicode_literals

from datetime import datetime
from itertools import chain
import logging
from collections import namedtuple, OrderedDict
from imdbpie import imdbpie
import locale
from six import string_types, text_type
from medusa.bs4_parser import BS4Parser
from medusa.indexers.base import (Actor, Actors, BaseIndexer)
from medusa.indexers.exceptions import (
    IndexerError, IndexerShowIncomplete
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
            ('nextepisode', 'base.nextEpisode'),
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

        for item in imdb_response:
            return_dict = {}
            try:
                title_type = item.get('type') or item.get('base', {}).get('titleType')
                if title_type in ('feature', 'video game', 'TV short', None):
                    continue

                return_dict['status'] = 'Ended'

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
                    if key == 'nextepisode' and value:
                        return_dict['status'] = 'Continuing'

                    return_dict[key] = value

                # Add static value for airs time.
                return_dict['airs_time'] = '0:00AM'

            except Exception as error:
                log.warning('Exception trying to parse attribute: {0}, with exception: {1!r}', item, error)

            parsed_response.append(return_dict)

        return parsed_response if len(parsed_response) != 1 else parsed_response[0]

    def _show_search(self, series):
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

        results = self._show_search(series)

        if not results:
            return

        mapped_results = self._map_results(results, self.series_map, '|')

        return OrderedDict({'series': mapped_results})['series']

    def _get_show_by_id(self, imdb_id):  # pylint: disable=unused-argument
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

        # If there was a release check if it was distributed.
        if companies.get('distribution'):
            origins = self.imdb_api.get_title_versions(imdb_id)['origins'][0]
            released_in_regions = [
                dist for dist in companies['distribution'] if dist.get('regions') and origins in dist['regions']
            ]
            # Used item.get('startYear') because a startYear is not always available.
            first_release = sorted(released_in_regions, key=lambda x: x.get('startYear'))

            if first_release:
                mapped_results['network'] = first_release[0]['company']['name']

        return OrderedDict({'series': mapped_results})

    def _get_episodes(self, imdb_id, *args):  # pylint: disable=unused-argument
        """
        Get all the episodes for a show by imdb id

        :param imdb_id: Series imdb id.
        :return: An ordered dict with the show searched for. In the format of OrderedDict{"episode": [list of episodes]}
        """
        # Parse episode data
        log.debug('Getting all episodes of {0}', imdb_id)

        series_id = imdb_id
        imdb_id = ImdbIdentifier(imdb_id).imdb_id
        try:
            results = self.imdb_api.get_title_episodes(imdb_id)
        except LookupError as error:
            raise IndexerShowIncomplete(
                'Show episode search exception, '
                'could not get any episodes. Exception: {e!r}'.format(
                    e=error
                )
            )

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
        """
        Enrich the episodes with additional information for a specific season.

        For this we're making use of html scraping using beautiful soup.
        :param imdb_id: imdb id including the `tt`.
        :param season: season passed as integer.
        """
        def parse_date_with_local(date, template, use_locale, method='strptime'):
            lc = locale.setlocale(locale.LC_TIME)
            locale.setlocale(locale.LC_ALL, use_locale)
            try:
                if method == 'strptime':
                    return datetime.strptime(date, template)
                else:
                    return date.strftime(template)
            except (AttributeError, ValueError):
                raise
            finally:
                locale.setlocale(locale.LC_TIME, lc)

        episodes_url = 'http://www.imdb.com/title/{imdb_id}/episodes?season={season}'
        series_id = ImdbIdentifier(imdb_id).series_id
        series_status = 'Ended'
        episodes = []

        try:
            response = self.config['session'].get(episodes_url.format(imdb_id=ImdbIdentifier(imdb_id).imdb_id, season=season))
            if not response or not response.text:
                log.warning('Problem requesting episode information for show {0}, and season {1}.', imdb_id, season)
                return

            Episode = namedtuple('Episode', ['episode_number', 'season_number', 'first_aired', 'episode_rating', 'episode_votes', 'synopsis', 'thumbnail'])
            with BS4Parser(response.text, 'html5lib') as html:
                for episode in html.find_all('div', class_='list_item'):
                    try:
                        episode_number = int(episode.find('meta')['content'])
                    except AttributeError:
                        pass

                    try:
                        first_aired_raw = episode.find('div', class_='airdate').get_text(strip=True)
                    except AttributeError:
                        pass

                    try:
                        first_aired = parse_date_with_local(first_aired_raw.replace('.', ''), '%d %b %Y', 'C').strftime('%Y-%m-%d')
                    except (AttributeError, ValueError):
                        try:
                            first_aired = parse_date_with_local(first_aired_raw.replace('.', ''), '%b %Y', 'C').strftime('%Y-%m-01')
                            series_status = 'Continuing'
                        except (AttributeError, ValueError):
                            try:
                                parse_date_with_local(first_aired_raw.replace('.', ''), '%Y', 'C').strftime('%Y')
                                first_aired = None
                                series_status = 'Continuing'
                            except (AttributeError, ValueError):
                                first_aired = None

                    try:
                        episode_rating = float(episode.find('span', class_='ipl-rating-star__rating').get_text(strip=True))
                    except AttributeError:
                        episode_rating = None

                    try:
                        episode_votes = int(episode.find('span', class_='ipl-rating-star__total-votes').get_text(
                            strip=True
                        ).strip('()').replace(',', ''))
                    except AttributeError:
                        episode_votes = None

                    try:
                        synopsis = episode.find('div', class_='item_description').get_text(strip=True)
                        if 'Know what this is about?' in synopsis:
                            synopsis = ''
                    except AttributeError:
                        synopsis = ''

                    try:
                        episode_thumbnail = episode.find('img', class_='zero-z-index')['src']
                    except:
                        episode_thumbnail = None

                    episodes.append(Episode(episode_number=episode_number, season_number=season, first_aired=first_aired,
                                            episode_rating=episode_rating, episode_votes=episode_votes,
                                            synopsis=synopsis, thumbnail=episode_thumbnail))
                    self._set_show_data(series_id, 'status', series_status)

        except Exception as error:
            log.exception('Error while trying to enrich imdb series {0}, {1}', series_id, error)

        for episode in episodes:
            self._set_item(series_id, episode.season_number, episode.episode_number, 'firstaired', episode.first_aired)
            self._set_item(series_id, episode.season_number, episode.episode_number, 'rating', episode.episode_rating)
            self._set_item(series_id, episode.season_number, episode.episode_number, 'votes', episode.episode_votes)
            self._set_item(series_id, episode.season_number, episode.episode_number, 'overview', episode.synopsis)
            self._set_item(series_id, episode.season_number, episode.episode_number, 'filename', episode.thumbnail)

        # Get the last (max 10 airdates) and try to calculate an airday + time.
        last_airdates = sorted(episodes, key=lambda x: x.first_aired, reverse=True)[:10]
        weekdays = {}
        for aired in last_airdates:
            if aired.first_aired:
                day = parse_date_with_local(datetime.strptime(aired.first_aired, '%Y-%m-%d'), '%A', 'C', method='strftime')
                weekdays[day] = 1 if day not in weekdays else weekdays[day] + 1

        airs_day_of_week = sorted(weekdays.keys(), key=lambda x: weekdays[x], reverse=True)[0] if weekdays else None
        self._set_show_data(series_id, 'airs_dayofweek', airs_day_of_week)

    def _parse_images(self, imdb_id):
        """Parse Show and Season posters.

        Any key starting with an underscore has been processed (not the raw
        data from the XML)

        This interface will be improved in future versions.
        Available sources: amazon, custom, getty, paidcustomer, presskit, userupload.
        Available types: behind_the_scenes, event, poster, product, production_art, publicity, still_frame
        """
        log.debug('Getting show banners for {0}', imdb_id)

        images = self.imdb_api.get_title_images(ImdbIdentifier(imdb_id).imdb_id)
        image_mapping = {'poster': 'poster', 'production_art': 'fanart'}  # Removed 'still_frame': 'fanart',
        thumb_height = 640

        _images = {}
        try:
            for image in images.get('images', []):
                image_type = image_mapping.get(image.get('type'))
                if image_type not in ('poster', 'fanart'):
                    continue
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

            # Save the image, but not for the poster, as we're using the poster that comes with the series data.
            if img_type != 'poster':
                self._set_show_data(series_id, img_type, img_url)

    def _parse_actors(self, imdb_id):
        """Get and parse actors using the get_title_credits route.

        Actors are retrieved using t['show name]['_actors'].

        Any key starting with an underscore has been processed (not the raw
        data from the indexer)
        """
        log.debug('Getting actors for {0}', imdb_id)

        actors = self.imdb_api.get_title_credits(ImdbIdentifier(imdb_id).imdb_id)

        cur_actors = Actors()
        for order, cur_actor in enumerate(actors['credits']['cast'][:25]):
            save_actor = Actor()
            save_actor['id'] = cur_actor['id'].split('/')[-2]
            save_actor['image'] = cur_actor.get('image', {}).get('url', None)
            save_actor['name'] = cur_actor['name']
            save_actor['role'] = cur_actor['characters'][0]
            save_actor['sortorder'] = order
            cur_actors.append(save_actor)
        self._set_show_data(imdb_id, '_actors', cur_actors)

    def _get_show_data(self, imdb_id, language='en'):  # pylint: disable=too-many-branches,too-many-statements,too-many-locals
        """Takes a series ID, gets the epInfo URL and parses the imdb json response
        into the shows dict in layout:
        shows[series_id][season_number][episode_number]
        """

        # Parse show information
        log.debug('Getting all series data for {0}', imdb_id)

        # Parse show information
        series_info = self._get_show_by_id(imdb_id)

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
            self._get_episodes(imdb_id)

        # Parse banners
        if self.config['banners_enabled']:
            self._parse_images(imdb_id)

        # Parse actors
        if self.config['actors_enabled']:
            self._parse_actors(imdb_id)

        return True
