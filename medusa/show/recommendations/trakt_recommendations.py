# coding=utf-8

from __future__ import unicode_literals

import logging
import os
from builtins import object

from medusa import app
from medusa.cache import recommended_series_cache
from medusa.helper.common import try_int
from medusa.helper.exceptions import MultipleShowObjectsException
from medusa.indexers.indexer_api import indexerApi
from medusa.indexers.indexer_config import INDEXER_TVDBV2
from medusa.logger.adapters.style import BraceAdapter
from medusa.show.recommendations import ExpiringList
from medusa.show.recommendations.recommended import (
    RecommendedShow, create_key_from_series, update_recommended_series_cache_index
)

from six import binary_type, text_type

import trakt
from trakt import tv

from tvdbapiv2.exceptions import ApiException


log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


missing_posters = ExpiringList(cache_timeout=3600 * 24 * 3)  # Cache 3 days


class TraktPopular(object):
    """This class retrieves a speficed recommended show list from Trakt.

    The list of returned shows is mapped to a RecommendedShow object
    """

    def __init__(self):
        """Initialize the trakt recommended list object."""
        self.cache_subfolder = __name__.split('.')[-1] if '.' in __name__ else __name__
        self.recommender = 'Trakt Popular'
        self.default_img_src = 'trakt-default.png'
        self.tvdb_api_v2 = indexerApi(INDEXER_TVDBV2).indexer()
        trakt.CONFIG_PATH = os.path.join(app.CACHE_DIR, '.pytrakt.json')

    @recommended_series_cache.cache_on_arguments(namespace='trakt', function_key_generator=create_key_from_series)
    def _create_recommended_show(self, series, storage_key=None):
        """Create the RecommendedShow object from the returned showobj."""
        rec_show = RecommendedShow(
            self,
            series['show']['ids'], series['show']['title'],
            INDEXER_TVDBV2,  # indexer
            series['show']['ids']['tvdb'],
            **{'rating': series['show']['rating'],
                'votes': try_int(series['show']['votes'], '0'),
                'image_href': 'http://www.trakt.tv/shows/{0}'.format(series['show']['ids']['slug']),
                # Adds like: {'tmdb': 62126, 'tvdb': 304219, 'trakt': 79382, 'imdb': 'tt3322314',
                # 'tvrage': None, 'slug': 'marvel-s-luke-cage'}
                'ids': series['show']['ids']
               }
        )

        use_default = None
        image = None
        try:
            if not missing_posters.has(series['show']['ids']['tvdb']):
                image = self.check_cache_for_poster(series['show']['ids']['tvdb']) or \
                        self.tvdb_api_v2.config['session'].series_api.series_id_images_query_get(
                            series['show']['ids']['tvdb'], key_type='poster').data[0].file_name
            else:
                log.info('CACHE: Missing poster on TVDB for show {0}', series['show']['title'])
                use_default = self.default_img_src
        except ApiException as error:
            use_default = self.default_img_src
            if getattr(error, 'status', None) == 404:
                log.info('Missing poster on TheTVDB for show {0}', series['show']['title'])
                missing_posters.append(series['show']['ids']['tvdb'])
        except Exception as error:
            use_default = self.default_img_src
            log.debug('Missing poster on TheTVDB, cause: {0!r}', error)

        image_url = ''
        if image:
            image_url = self.tvdb_api_v2.config['artwork_prefix'].format(image=image)

        rec_show.cache_image(image_url, default=use_default)

        # As the method below requires a lot of resources, i've only enabled it when
        # the shows language or country is 'jp' (japanese). Looks a litle bit akward,
        # but alternative is a lot of resource used
        if 'jp' in [series['show']['country'], series['show']['language']]:
            rec_show.flag_as_anime(series['show']['ids']['tvdb'])

        return rec_show

    # @staticmethod
    # def fetch_and_refresh_token(trakt_api, path):
    #     """Fetch shows from trakt and store the refresh token when needed."""
    #     try:
    #         library_shows = trakt_api.request(path) or []
    #         if trakt_api.access_token_refreshed:
    #             app.TRAKT_ACCESS_TOKEN = trakt_api.access_token
    #             app.TRAKT_REFRESH_TOKEN = trakt_api.refresh_token
    #             app.instance.save_config()
    #     except TokenExpiredException:
    #         app.TRAKT_ACCESS_TOKEN = ''
    #         raise
    #
    #     return library_shows

    def fetch_popular_shows(self, page_url=None, trakt_list=None):
        """Get a list of popular shows from different Trakt lists based on a provided trakt_list.

        :param page_url: the page url opened to the base api url, for retreiving a specific list
        :param trakt_list: a description of the trakt list
        :return: A list of RecommendedShow objects, an empty list of none returned
        :throw: ``Exception`` if an Exception is thrown not handled by the libtrats exceptions
        """
        my_trending_shows = []
        removed_from_medusa = []

        # Create a trakt settings dict
        # trakt_settings = {'trakt_api_secret': app.TRAKT_API_SECRET,
        #                   'trakt_api_key': app.TRAKT_API_KEY,
        #                   'trakt_access_token': app.TRAKT_ACCESS_TOKEN,
        #                   'trakt_refresh_token': app.TRAKT_REFRESH_TOKEN}

        # import trakt.core as core

        try:
            not_liked_show = ''
            if app.TRAKT_ACCESS_TOKEN != '':

                # Shows from the users library
                library_shows = trakt.sync.get_watched('shows', extended=True) + \
                    trakt.sync.get_collection('shows', extended=True)

                medusa_shows = [show.indexerid for show in app.showList if show.indexerid]
                removed_from_medusa = [lshow['show']['ids']['tvdb'] for lshow in library_shows if lshow['show']['ids']['tvdb'] not in medusa_shows]

                if app.TRAKT_BLACKLIST_NAME is not None and app.TRAKT_BLACKLIST_NAME:
                    trakt_user = trakt.users.User(app.TRAKT_USERNAME)
                    not_liked_show = trakt_user.get_list(app.TRAKT_BLACKLIST_NAME) or []
                else:
                    log.debug('Trakt blacklist name is empty')

            if trakt_list not in ['recommended', 'newshow', 'newseason']:
                limit_show = '?limit=' + text_type(100 + len(not_liked_show)) + '&'
            else:
                limit_show = '?'

            # series = self.fetch_and_refresh_token(trakt_api, page_url + limit_show + 'extended=full,images') or []
            map_to_trakt_api_method = {
                'shows/trending': trakt.tv.trending_shows,
                'shows/popular': trakt.tv.popular_shows,
                'shows/anticipated': trakt.tv.anticipated_shows,
                'shows/collected': trakt.tv.collected_shows,
                'shows/watched': trakt.tv.watched_shows,
                'shows/played': trakt.tv.played_shows,
                'recommendations/shows': trakt.tv.get_recommended_shows
            }

            shows = map_to_trakt_api_method.get(page_url)()

            # Let's trigger a cache cleanup.
            missing_posters.clean()

            for show in shows:
                try:
                    if 'show' not in show:
                        show['show'] = show

                    if not_liked_show:
                        if show['show']['ids']['tvdb'] in (s['show']['ids']['tvdb']
                                                           for s in not_liked_show if s['type'] == 'show'):
                            continue
                    else:
                        my_trending_shows.append(self._create_recommended_show(
                            show, storage_key='trakt_{0}'.format(show['show']['ids']['trakt'])
                        ))

                except MultipleShowObjectsException:
                    continue

            # Update the dogpile index. This will allow us to retrieve all stored dogpile shows from the dbm.
            update_recommended_series_cache_index('trakt', [binary_type(s.series_id) for s in my_trending_shows])
            blacklist = app.TRAKT_BLACKLIST_NAME not in ''

        # TODO: Replace with normal exception
        except Exception as error:
            log.warning('Could not connect to Trakt service: {0}', error)
            raise

        return blacklist, my_trending_shows, removed_from_medusa

    def check_cache_for_poster(self, tvdb_id):
        """Verify if we already have a poster downloaded for this show."""
        if not os.path.exists(os.path.join(app.CACHE_DIR, 'images', self.cache_subfolder)):
            os.makedirs(os.path.join(app.CACHE_DIR, 'images', self.cache_subfolder))

        for image_file_name in os.listdir(os.path.abspath(os.path.join(app.CACHE_DIR, 'images', self.cache_subfolder))):
            if os.path.isfile(os.path.abspath(os.path.join(app.CACHE_DIR, 'images', self.cache_subfolder, image_file_name))):
                if text_type(tvdb_id) == image_file_name.split('-')[0]:
                    return image_file_name
        return False
