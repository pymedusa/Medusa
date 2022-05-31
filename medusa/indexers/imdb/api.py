# coding=utf-8
"""Imdb indexer api module."""

from __future__ import unicode_literals

import locale
import logging
from collections import OrderedDict, namedtuple
from datetime import datetime
from itertools import chain
from time import time

from imdbpie import imdbpie

from medusa import app
from medusa.bs4_parser import BS4Parser
from medusa.indexers.base import (Actor, Actors, BaseIndexer)
from medusa.indexers.exceptions import (
    IndexerError, IndexerShowIncomplete, IndexerShowNotFound, IndexerUnavailable
)
from medusa.logger.adapters.style import BraceAdapter
from medusa.show.show import Show

from requests.exceptions import RequestException

from six import string_types, text_type


log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class ImdbIdentifier(object):
    """Imdb identifier class."""

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
        """Return series id."""
        return self._series_id

    @series_id.setter
    def series_id(self, value):
        """Set series id."""
        self._series_id = value

    @property
    def imdb_id(self):
        """Return imdb id."""
        return self._imdb_id

    @imdb_id.setter
    def imdb_id(self, value):
        """Set imdb id."""
        if value is None or value == '':
            self._imdb_id = self.series_id = None
            return

        if isinstance(value, string_types) and 'tt' in value:
            self._imdb_id = self._clean(value)
            self.series_id = int(self._imdb_id.split('tt')[-1])
        else:
            self._imdb_id = 'tt{0}'.format(text_type(value).zfill(7))
            try:
                self.series_id = int(value)
            except (TypeError, ValueError):
                self.series_id = None


class Imdb(BaseIndexer):
    """Create easy-to-use interface to name of season/episode name.

    >>> indexer_api = imdb()
    >>> indexer_api['Scrubs'][1][24]['episodename']
    u'My Last Day'
    """

    def __init__(self, *args, **kwargs):  # pylint: disable=too-many-locals,too-many-arguments
        """Imdb constructor."""
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
            ('summary', 'plot.outline.text'),
            ('firstaired', 'year'),
            ('poster', 'base.image.url'),
            ('show_url', 'base.id'),
            ('firstaired', 'base.seriesStartYear'),
            ('rating', 'ratings.rating'),
            ('votes', 'ratings.ratingCount'),
            ('nextepisode', 'base.nextEpisode'),
            ('lastaired', 'base.seriesEndYear'),
            # Could not find contentrating in api.
        ]

        self.episode_map = [
            ('id', 'id'),
            ('episodename', 'title'),
            ('firstaired', 'year'),
            ('absolute_number', 'absolute_number'),
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
                if title_type in ('feature', 'video game', 'TV short', 'TV movie', None):
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
                        return_dict['poster_thumb'] = value.split('V1')[0] + 'V1_SY{0}_AL_.jpg'.format('640').split('/')[-1]
                    if key == 'nextepisode' and value:
                        return_dict['status'] = 'Continuing'

                    return_dict[key] = value

                # Add static value for airs time.
                return_dict['airs_time'] = '0:00AM'

                if return_dict.get('firstaired'):
                    return_dict['status'] = 'Ended' if return_dict.get('lastaired') else 'Continuing'

            except Exception as error:
                log.warning('Exception trying to parse attribute: {0}, with exception: {1!r}', item, error)

            parsed_response.append(return_dict)

        return parsed_response if len(parsed_response) != 1 else parsed_response[0]

    def _show_search(self, series):
        """
        Use the Imdb API to search for a show.

        :param series: The series name that's searched for as a string
        :return: A list of Show objects.series_map
        """
        try:
            results = self.imdb_api.search_for_title(series)
        except LookupError as error:
            raise IndexerShowNotFound('Could not get any results searching for {series} using indexer Imdb. Cause: {cause!r}'.format(
                series=series, cause=error
            ))
        except (AttributeError, RequestException) as error:
            raise IndexerUnavailable('Could not get any results searching for {series} using indexer Imdb. Cause: {cause!r}'.format(
                series=series, cause=error
            ))

        if results:
            return results
        else:
            return None

    def search(self, series):
        """Search imdb.com for the series name.

        :param series: the query for the series name
        :return: An ordered dict with the show searched for. In the format of OrderedDict{"series": [list of shows]}
        """
        # series = series.encode('utf-8')
        log.debug('Searching for show {0}', series)
        mapped_results = []
        try:
            if series.startswith('tt'):
                show_by_id = self._get_show_by_id(series)
                # The search by id result, is already mapped. We can just add it to the array with results.
                mapped_results.append(show_by_id['series'])
                return OrderedDict({'series': mapped_results})['series']
            results = self._show_search(series)
        except IndexerShowNotFound:
            results = None

        if not results:
            return

        mapped_results = self._map_results(results, self.series_map, '|')

        return OrderedDict({'series': mapped_results})['series']

    def _get_show_by_id(self, imdb_id):  # pylint: disable=unused-argument
        """Retrieve imdb show information by imdb id, or if no imdb id provided by passed external id.

        :param imdb_id: The shows imdb id
        :return: An ordered dict with the show searched for.
        """
        results = None
        log.debug('Getting all show data for {0}', imdb_id)
        try:
            results = self.imdb_api.get_title(ImdbIdentifier(imdb_id).imdb_id)
        except LookupError as error:
            raise IndexerShowNotFound('Could not find show {imdb_id} using indexer Imdb. Cause: {cause!r}'.format(
                imdb_id=imdb_id, cause=error
            ))
        except (AttributeError, RequestException) as error:
            raise IndexerUnavailable('Could not find show {imdb_id} using indexer Imdb. Cause: {cause!r}'.format(
                imdb_id=imdb_id, cause=error
            ))

        if not results:
            return

        mapped_results = self._map_results(results, self.series_map)

        if not mapped_results:
            return

        try:
            # Get firstaired
            releases = self.imdb_api.get_title_releases(ImdbIdentifier(imdb_id).imdb_id)
        except LookupError as error:
            raise IndexerShowNotFound('Could not find show {imdb_id} using indexer Imdb. Cause: {cause!r}'.format(
                imdb_id=imdb_id, cause=error
            ))
        except (AttributeError, RequestException) as error:
            raise IndexerUnavailable('Could not get title releases for show {imdb_id} using indexer Imdb. Cause: {cause!r}'.format(
                imdb_id=imdb_id, cause=error
            ))

        if releases.get('releases'):
            first_released = sorted([r['date'] for r in releases['releases']])[0]
            mapped_results['firstaired'] = first_released

        try:
            companies = self.imdb_api.get_title_companies(ImdbIdentifier(imdb_id).imdb_id)
            # If there was a release check if it was distributed.
            if companies.get('distribution'):
                origins = self.imdb_api.get_title_versions(ImdbIdentifier(imdb_id).imdb_id)['origins'][0]
                released_in_regions = [
                    dist for dist in companies['distribution']
                    if dist.get('regions') and origins in dist['regions'] and dist['isOriginalAiring'] and dist['startYear']
                ]

                if released_in_regions:
                    # Used item.get('startYear') because a startYear is not always available.
                    first_release = sorted(released_in_regions, key=lambda x: x.get('startYear'))

                    if first_release:
                        mapped_results['network'] = first_release[0]['company']['name']
        except (AttributeError, LookupError, RequestException):
            log.info('No company data available for {0}, cant get a network', imdb_id)

        return OrderedDict({'series': mapped_results})

    def _get_episodes(self, imdb_id, detailed=True, aired_season=None, *args, **kwargs):  # pylint: disable=unused-argument
        """Get all the episodes for a show by imdb id.

        :param imdb_id: Series imdb id.
        :return: An ordered dict with the show searched for. In the format of OrderedDict{"episode": [list of episodes]}
        """
        # Parse episode data
        log.debug('Getting all episodes of {0}', imdb_id)

        if aired_season:
            aired_season = [aired_season] if not isinstance(aired_season, list) else aired_season

        series_id = imdb_id
        imdb_id = ImdbIdentifier(imdb_id).imdb_id

        try:
            # results = self.imdb_api.get_title_episodes(imdb_id)
            results = self.imdb_api.get_title_episodes(ImdbIdentifier(imdb_id).imdb_id)
        except LookupError as error:
            raise IndexerShowIncomplete(
                'Show episode search exception, '
                'could not get any episodes. Exception: {e!r}'.format(
                    e=error
                )
            )
        except (AttributeError, RequestException) as error:
            raise IndexerUnavailable('Error connecting to Imdb api. Caused by: {0!r}'.format(error))

        if not results or not results.get('seasons'):
            return False

        absolute_number_counter = 1
        for season in results.get('seasons'):
            if aired_season and season.get('season') not in aired_season:
                continue

            for episode in season['episodes']:
                season_no, episode_no = episode.get('season'), episode.get('episode')

                if season_no is None or episode_no is None:
                    log.debug('{0}: Found incomplete episode with season: {1!r} and episode: {2!r})',
                              imdb_id, season_no, episode_no)
                    continue  # Skip to next episode

                if season_no > 0:
                    episode['absolute_number'] = absolute_number_counter
                    absolute_number_counter += 1

                for k, config in self.episode_map:
                    v = self.get_nested_value(episode, config)
                    if v is not None:
                        if k == 'id':
                            v = ImdbIdentifier(v).series_id
                        if k == 'firstaired':
                            v = '{year}-01-01'.format(year=v)

                        self._set_item(series_id, season_no, episode_no, k, v)

            if detailed and season.get('season'):
                # Enrich episode for the current season.
                self._get_episodes_detailed(imdb_id, season['season'])

                # Scrape the synopsys and the episode thumbnail.
                self._enrich_episodes(imdb_id, season['season'])

        # Try to calculate the airs day of week
        self._calc_airs_day_of_week(imdb_id)

    def _calc_airs_day_of_week(self, imdb_id):
        series_id = ImdbIdentifier(imdb_id).series_id

        if self[series_id]:
            all_episodes = []

            for season in self[series_id]:
                all_episodes.extend([
                    self[series_id][season][ep]
                    for ep in self[series_id][season]
                    if self[series_id][season][ep].get('firstaired')
                ])

            # Get the last (max 10 airdates) and try to calculate an airday + time.
            last_airdates = sorted(all_episodes, key=lambda x: x['firstaired'], reverse=True)[:10]
            weekdays = {}
            for episode in last_airdates:
                if episode['firstaired']:
                    day = self._parse_date_with_local(datetime.strptime(episode['firstaired'], '%Y-%m-%d'), '%A', 'C', method='strftime')
                    weekdays[day] = 1 if day not in weekdays else weekdays[day] + 1

            airs_day_of_week = sorted(weekdays.keys(), key=lambda x: weekdays[x], reverse=True)[0] if weekdays else None
            self._set_show_data(series_id, 'airs_dayofweek', airs_day_of_week)

    @staticmethod
    def _parse_date_with_local(date, template, locale_format='C', method='strptime'):
        lc = locale.setlocale(locale.LC_TIME)
        locale.setlocale(locale.LC_ALL, locale_format)
        try:
            if method == 'strptime':
                return datetime.strptime(date, template)
            else:
                return date.strftime(template)
        except (AttributeError, ValueError):
            raise
        finally:
            locale.setlocale(locale.LC_TIME, lc)

    def _get_episodes_detailed(self, imdb_id, season):
        """Enrich the episodes with additional information for a specific season.

        :param imdb_id: imdb id including the `tt`.
        :param season: season passed as integer.
        """
        try:
            results = self.imdb_api.get_title_episodes_detailed(imdb_id=ImdbIdentifier(imdb_id).imdb_id, season=season)
        except (AttributeError, LookupError, RequestException) as error:
            raise IndexerShowIncomplete(
                'Show episode search exception, '
                'could not get any episodes. Exception: {e!r}'.format(
                    e=error
                )
            )

        if not results.get('episodes'):
            return

        series_id = ImdbIdentifier(imdb_id).series_id
        for episode in results.get('episodes'):
            try:
                if episode['releaseDate']['first']['date']:
                    first_aired = self._parse_date_with_local(
                        datetime.strptime(
                            episode['releaseDate']['first']['date'], '%Y-%m-%d'
                        ), '%Y-%m-%d', 'C', method='strftime'
                    )
                    self._set_item(series_id, season, episode['episodeNumber'], 'firstaired', first_aired)
            except ValueError:
                pass

            self._set_item(series_id, season, episode['episodeNumber'], 'rating', episode['rating'])
            self._set_item(series_id, season, episode['episodeNumber'], 'votes', episode['ratingCount'])

    def _enrich_episodes(self, imdb_id, season):
        """Enrich the episodes with additional information for a specific season.

        For this we're making use of html scraping using beautiful soup.
        :param imdb_id: imdb id including the `tt`.
        :param season: season passed as integer.
        """
        episodes_url = 'http://www.imdb.com/title/{imdb_id}/episodes?season={season}'
        episodes = []

        try:
            response = self.config['session'].get(episodes_url.format(
                imdb_id=ImdbIdentifier(imdb_id).imdb_id, season=season)
            )
            if not response or not response.text:
                log.warning('Problem requesting episode information for show {0}, and season {1}.', imdb_id, season)
                return

            Episode = namedtuple('Episode', ['episode_number', 'season_number', 'synopsis', 'thumbnail'])
            with BS4Parser(response.text, 'html5lib') as html:
                for episode in html.find_all('div', class_='list_item'):
                    try:
                        episode_number = int(episode.find('meta')['content'])
                    except AttributeError:
                        pass

                    try:
                        synopsis = episode.find('div', class_='item_description').get_text(strip=True)
                        if 'Know what this is about?' in synopsis:
                            synopsis = ''
                    except AttributeError:
                        synopsis = ''

                    try:
                        episode_thumbnail = episode.find('img', class_='zero-z-index')['src']
                    except (AttributeError, TypeError):
                        episode_thumbnail = None

                    episodes.append(Episode(episode_number=episode_number, season_number=season,
                                            synopsis=synopsis, thumbnail=episode_thumbnail))

        except Exception as error:
            log.exception('Error while trying to enrich imdb series {0}, {1}', ImdbIdentifier(imdb_id).imdb_id, error)

        for episode in episodes:
            self._set_item(imdb_id, episode.season_number, episode.episode_number, 'overview', episode.synopsis)
            self._set_item(imdb_id, episode.season_number, episode.episode_number, 'filename', episode.thumbnail)

    def _parse_images(self, imdb_id, language='en'):
        """Parse Show and Season posters.

        Any key starting with an underscore has been processed (not the raw
        data from the XML)

        This interface will be improved in future versions.
        Available sources: amazon, custom, getty, paidcustomer, presskit, userupload.
        Available types: behind_the_scenes, event, poster, product, production_art, publicity, still_frame
        """
        log.debug('Getting show banners for {0}', imdb_id)

        try:
            images = self.imdb_api.get_title_images(ImdbIdentifier(imdb_id).imdb_id)
        except LookupError as error:
            raise IndexerShowNotFound('Could not find show {imdb_id} using indexer Imdb. Cause: {cause!r}'.format(
                imdb_id=imdb_id, cause=error
            ))
        except (AttributeError, RequestException) as error:
            raise IndexerUnavailable('Could not get images for show {imdb_id} using indexer Imdb. Cause: {cause!r}'.format(
                imdb_id=imdb_id, cause=error
            ))

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
                base_path['languages'] = image.get('languages')
                base_path['source'] = image.get('source')
                base_path['id'] = bid

                base_path_thumb['bannertype'] = image_type_thumb
                base_path_thumb['bannertype2'] = resolution_thumb
                base_path_thumb['_bannerpath'] = image['url'].split('V1')[0] + 'V1_SY{0}_AL_.jpg'.format(thumb_height)
                base_path_thumb['bannerpath'] = image['url'].split('V1')[0] + 'V1_SY{0}_AL_.jpg'.format(thumb_height).split('/')[-1]
                base_path_thumb['id'] = bid

        except Exception as error:
            log.warning('Could not parse Poster for show id: {0}, with exception: {1!r}', imdb_id, error)
            return

        def _get_poster_thumb(thumbs):
            for bid in thumbs.values():
                for image in bid.values():
                    return image.get('bannerpath')

        if _images.get('poster_thumb'):
            self._set_show_data(imdb_id, 'poster_thumb', _get_poster_thumb(_images.get('poster_thumb')))

        self._save_images(imdb_id, _images, language=language)
        self._set_show_data(imdb_id, '_banners', _images)

    def _save_images(self, series_id, images, language='en'):
        """
        Save the highest rated images for the show.

        :param series_id: The series ID
        :param images: A nested mapping of image info
            images[type][res][id] = image_info_mapping
                type: image type such as `banner`, `poster`, etc
                res: resolution such as `1024x768`, `original`, etc
                id: the image id
        """
        def by_aspect_ratio(image):
            w, h = image['bannertype2'].split('x')
            return int(w) / int(h)

        # Parse Posters and Banners (by aspect ratio)
        if images.get('poster'):
            # Flatten image_type[res][id].values() into list of values
            merged_images = chain.from_iterable(
                resolution.values()
                for resolution in images['poster'].values()
            )

            # Sort by aspect ratio
            sort_images = sorted(
                merged_images,
                key=by_aspect_ratio
            )

            # Filter out the posters with an aspect ratio between 0.6 and 0.8
            posters = [
                image for image in sort_images if by_aspect_ratio(image) > 0.6 and by_aspect_ratio(image) < 0.8
                and image.get('languages')
                and image['languages'] == [language]
            ]
            banners = [image for image in sort_images if by_aspect_ratio(image) > 3]

            if len(posters):
                highest_rated = posters[0]
                img_url = highest_rated['_bannerpath']
                log.debug(
                    u'Selecting poster with the lowest aspect ratio (resolution={resolution})\n'
                    'aspect ratio of {aspect_ratio} ', {
                        'resolution': highest_rated['bannertype2'],
                        'aspect_ratio': by_aspect_ratio(highest_rated)
                    }
                )
                self._set_show_data(series_id, 'poster', img_url)

            if len(banners):
                highest_rated = banners[-1]
                img_url = highest_rated['_bannerpath']
                log.debug(
                    u'Selecting poster with the lowest aspect ratio (resolution={resolution})\n'
                    'aspect ratio of {aspect_ratio} ', {
                        'resolution': highest_rated['bannertype2'],
                        'aspect_ratio': by_aspect_ratio(highest_rated)
                    }
                )
                self._set_show_data(series_id, 'banner', img_url)

        if images.get('fanart'):
            # Flatten image_type[res][id].values() into list of values
            merged_images = chain.from_iterable(
                resolution.values()
                for resolution in images['fanart'].values()
            )

            # Sort by resolution
            sort_images = sorted(
                merged_images,
                key=by_aspect_ratio,
                reverse=True,
            )

            if len(sort_images):
                highest_rated = sort_images[0]
                img_url = highest_rated['_bannerpath']
                log.debug(
                    u'Selecting poster with the lowest aspect ratio (resolution={resolution})\n'
                    'aspect ratio of {aspect_ratio} ', {
                        'resolution': highest_rated['bannertype2'],
                        'aspect_ratio': by_aspect_ratio(highest_rated)
                    }
                )
                self._set_show_data(series_id, 'fanart', img_url)

    def _parse_actors(self, imdb_id):
        """Get and parse actors using the get_title_credits route.

        Actors are retrieved using t['show name]['_actors'].

        Any key starting with an underscore has been processed (not the raw
        data from the indexer)
        """
        log.debug('Getting actors for {0}', imdb_id)

        try:
            actors = self.imdb_api.get_title_credits(ImdbIdentifier(imdb_id).imdb_id)
        except LookupError as error:
            raise IndexerShowNotFound('Could not find show {imdb_id} using indexer Imdb. Cause: {cause!r}'.format(
                imdb_id=imdb_id, cause=error
            ))
        except (AttributeError, RequestException) as error:
            raise IndexerUnavailable('Could not get actors for show {imdb_id} using indexer Imdb. Cause: {cause!r}'.format(
                imdb_id=imdb_id, cause=error
            ))

        if not actors.get('credits') or not actors['credits'].get('cast'):
            return

        cur_actors = Actors()
        for order, cur_actor in enumerate(actors['credits']['cast'][:25]):
            save_actor = Actor()
            save_actor['id'] = cur_actor['id'].split('/')[-2]
            save_actor['image'] = cur_actor.get('image', {}).get('url', None)
            save_actor['name'] = cur_actor['name']
            save_actor['role'] = cur_actor['characters'][0] if cur_actor.get('characters') else ''
            save_actor['sortorder'] = order
            cur_actors.append(save_actor)
        self._set_show_data(imdb_id, '_actors', cur_actors)

    def _get_show_data(self, imdb_id, language='en'):  # pylint: disable=too-many-branches,too-many-statements,too-many-locals
        """Get show data by imdb id.

        Take a series ID, gets the epInfo URL and parses the imdb json response into the shows dict in a format:
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
            self._get_episodes(imdb_id, aired_season=self.config['limit_seasons'])

        # Parse banners
        if self.config['banners_enabled']:
            self._parse_images(imdb_id, language=language)

        # Parse actors
        if self.config['actors_enabled']:
            self._parse_actors(imdb_id)

        return True

    @staticmethod
    def _calc_update_interval(date_season_last, season_finished=True):

        minimum_interval = 2 * 24 * 3600  # 2 days

        # Season net yet finished, let's use the minimum update interval of 2 days.
        if not season_finished:
            return minimum_interval

        # season is finished, or show has ended. So let's calculate using the delta divided by 50.
        interval = int((datetime.combine(date_season_last, datetime.min.time()) - datetime.utcfromtimestamp(0)).total_seconds() / 50)

        return max(minimum_interval, interval)

    # Public methods, usable separate from the default api's interface api['show_id']
    def get_last_updated_seasons(self, show_list=None, cache=None, *args, **kwargs):
        """Return updated seasons for shows passed, using the from_time.

        :param show_list[int]: The list of shows, where seasons updates are retrieved for.
        :param from_time[int]: epoch timestamp, with the start date/time
        :param weeks: number of weeks to get updates for.
        """
        show_season_updates = {}

        # we don't have a single api call tha we can run to check if an update is required.
        # So we'll have to check what's there in the library, and decide based on the last episode's date, if a
        # season update is needed.

        for series_id in show_list:
            series_obj = Show.find_by_id(app.showList, self.indexer, series_id)
            all_episodes_local = series_obj.get_all_episodes()

            total_updates = []
            results = None
            # A small api call to get the amount of known seasons
            try:
                results = self.imdb_api.get_title_episodes(ImdbIdentifier(series_id).imdb_id)
            except LookupError as error:
                raise IndexerShowIncomplete(
                    'Show episode search exception, '
                    'could not get any episodes. Exception: {error!r}'.format(
                        error=error
                    )
                )
            except (AttributeError, RequestException) as error:
                raise IndexerUnavailable('Error connecting to Imdb api. Caused by: {0!r}'.format(error))

            if not results or not results.get('seasons'):
                continue

            # Get all the seasons

            # Loop through seasons
            for season in results['seasons']:
                season_number = season.get('season')

                # Imdb api gives back a season without the 'season' key. This season has special episodes.
                # Dont know what this is, but skipping it.
                if not season_number:
                    continue

                # Check if the season is already known in our local db.
                local_season_episodes = [ep for ep in all_episodes_local if ep.season == season_number]
                remote_season_episodes = season['episodes']
                if not local_season_episodes or len(remote_season_episodes) != len(local_season_episodes):
                    total_updates.append(season_number)
                    log.debug('{series}: Season {season} seems to be a new season. Adding it.',
                              {'series': series_obj.name, 'season': season_number})
                    continue

                # Per season, get latest episode airdate
                sorted_episodes = sorted(local_season_episodes, key=lambda x: x.airdate)
                # date_season_start = sorted_episodes[0].airdate
                date_season_last = sorted_episodes[-1].airdate

                # Get date for last updated, from the cache object.

                # Calculate update interval for the season
                update_interval = self._calc_update_interval(
                    # date_season_start,
                    date_season_last,
                    season_finished=bool([s for s in results['seasons'] if s.get('season') == season_number + 1])
                )

                last_update = cache.get_last_update_season(self.indexer, series_id, season_number)
                if last_update < time() - update_interval:
                    # This season should be updated.
                    total_updates.append(season_number)

                    # Update last_update for this season.
                    cache.set_last_update_season(self.indexer, series_id, season_number)
                else:
                    log.debug(
                        '{series}: Season {season} seems to have been recently updated. Not scheduling a new refresh',
                        {'series': series_obj.name, 'season': season_number}
                    )

            show_season_updates[series_id] = list(set(total_updates))

        return show_season_updates
