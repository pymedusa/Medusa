# coding=utf-8

from __future__ import unicode_literals

import logging
import os

from medusa import app
from medusa.helper.common import try_int
from medusa.helper.exceptions import MultipleShowObjectsException
from medusa.indexers.api import indexerApi
from medusa.indexers.config import INDEXER_TVDB
from medusa.logger.adapters.style import BraceAdapter
from medusa.show.recommendations import ExpiringList
from medusa.show.recommendations.recommended import RecommendedShow

from simpleanidb import Anidb
from traktor import (TokenExpiredException, TraktApi, TraktException)
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
        self.recommender = "Trakt Popular"
        self.default_img_src = 'trakt-default.png'
        self.anidb = Anidb(cache_dir=app.CACHE_DIR)
        self.tvdb_api_v2 = indexerApi(INDEXER_TVDB).indexer()

    def _create_recommended_show(self, show_obj):
        """Create the RecommendedShow object from the returned showobj."""
        rec_show = RecommendedShow(self,
                                   show_obj['show']['ids'], show_obj['show']['title'],
                                   INDEXER_TVDB,  # indexer
                                   show_obj['show']['ids']['tvdb'],
                                   **{'rating': show_obj['show']['rating'],
                                      'votes': try_int(show_obj['show']['votes'], '0'),
                                      'image_href': 'http://www.trakt.tv/shows/{0}'.format(show_obj['show']['ids']['slug']),
                                      # Adds like: {'tmdb': 62126, 'tvdb': 304219, 'trakt': 79382, 'imdb': 'tt3322314',
                                      # 'tvrage': None, 'slug': 'marvel-s-luke-cage'}
                                      'ids': show_obj['show']['ids']
                                      }
                                   )

        use_default = None
        image = None
        try:
            if not missing_posters.has(show_obj['show']['ids']['tvdb']):
                image = self.check_cache_for_poster(show_obj['show']['ids']['tvdb']) or \
                    self.tvdb_api_v2.config['session'].series_api.series_id_images_query_get(show_obj['show']['ids']['tvdb'],
                                                                                             key_type='poster').data[0].file_name
            else:
                log.info('CACHE: Missing poster on TVDB for show {0}', show_obj['show']['title'])
                use_default = self.default_img_src
        except ApiException as error:
            use_default = self.default_img_src
            if getattr(error, 'status', None) == 404:
                log.info('Missing poster on TheTVDB for show {0}', show_obj['show']['title'])
                missing_posters.append(show_obj['show']['ids']['tvdb'])
        except Exception as error:
            use_default = self.default_img_src
            log.debug('Missing poster on TheTVDB, cause: {0!r}', error)

        if image:
            rec_show.cache_image('http://thetvdb.com/banners/{0}'.format(image), default=use_default)
        else:
            rec_show.cache_image('', default=use_default)

        # As the method below requires allot of resources, i've only enabled it when
        # the shows language or country is 'jp' (japanese). Looks a litle bit akward,
        # but alternative is allot of resource used
        if 'jp' in [show_obj['show']['country'], show_obj['show']['language']]:
            rec_show.check_if_anime(self.anidb, show_obj['show']['ids']['tvdb'])

        return rec_show

    @staticmethod
    def fetch_and_refresh_token(trakt_api, path):
        """Fetch shows from trakt and store the refresh token when needed."""
        try:
            library_shows = trakt_api.request(path) or []
            if trakt_api.access_token_refreshed:
                app.TRAKT_ACCESS_TOKEN = trakt_api.access_token
                app.TRAKT_REFRESH_TOKEN = trakt_api.refresh_token
                app.instance.save_config()
        except TokenExpiredException:
            app.TRAKT_ACCESS_TOKEN = ''
            raise

        return library_shows

    def fetch_popular_shows(self, page_url=None, trakt_list=None):  # pylint: disable=too-many-nested-blocks,too-many-branches
        """Get a list of popular shows from different Trakt lists based on a provided trakt_list.

        :param page_url: the page url opened to the base api url, for retreiving a specific list
        :param trakt_list: a description of the trakt list
        :return: A list of RecommendedShow objects, an empty list of none returned
        :throw: ``Exception`` if an Exception is thrown not handled by the libtrats exceptions
        """
        trending_shows = []
        removed_from_medusa = []

        # Create a trakt settings dict
        trakt_settings = {'trakt_api_secret': app.TRAKT_API_SECRET,
                          'trakt_api_key': app.TRAKT_API_KEY,
                          'trakt_access_token': app.TRAKT_ACCESS_TOKEN,
                          'trakt_refresh_token': app.TRAKT_REFRESH_TOKEN}

        trakt_api = TraktApi(timeout=app.TRAKT_TIMEOUT, ssl_verify=app.SSL_VERIFY, **trakt_settings)

        try:  # pylint: disable=too-many-nested-blocks
            not_liked_show = ''
            if app.TRAKT_ACCESS_TOKEN != '':
                library_shows = self.fetch_and_refresh_token(trakt_api, 'sync/watched/shows?extended=noseasons') + \
                    self.fetch_and_refresh_token(trakt_api, 'sync/collection/shows?extended=full')

                medusa_shows = [show.indexerid for show in app.showList if show.indexerid]
                removed_from_medusa = [lshow['show']['ids']['tvdb'] for lshow in library_shows if lshow['show']['ids']['tvdb'] not in medusa_shows]

                if app.TRAKT_BLACKLIST_NAME is not None and app.TRAKT_BLACKLIST_NAME:
                    not_liked_show = trakt_api.request('users/' + app.TRAKT_USERNAME + '/lists/' +
                                                       app.TRAKT_BLACKLIST_NAME + '/items') or []
                else:
                    log.debug('Trakt blacklist name is empty')

            if trakt_list not in ['recommended', 'newshow', 'newseason']:
                limit_show = '?limit=' + str(100 + len(not_liked_show)) + '&'
            else:
                limit_show = '?'

            shows = self.fetch_and_refresh_token(trakt_api, page_url + limit_show + 'extended=full,images') or []

            # Let's trigger a cache cleanup.
            missing_posters.clean()

            for show in shows:
                try:
                    if 'show' not in show:
                        show['show'] = show

                    if not_liked_show:
                        if show['show']['ids']['tvdb'] not in (show['show']['ids']['tvdb']
                                                               for show in not_liked_show if show['type'] == 'show'):
                            trending_shows.append(self._create_recommended_show(show))
                    else:
                        trending_shows.append(self._create_recommended_show(show))

                except MultipleShowObjectsException:
                    continue

            blacklist = app.TRAKT_BLACKLIST_NAME not in ''

        except TraktException as error:
            log.warning('Could not connect to Trakt service: {0}', error)
            raise

        return blacklist, trending_shows, removed_from_medusa

    def check_cache_for_poster(self, tvdb_id):
        """Verify if we already have a poster downloaded for this show."""
        if not os.path.exists(os.path.join(app.CACHE_DIR, 'images', self.cache_subfolder)):
            os.makedirs(os.path.join(app.CACHE_DIR, 'images', self.cache_subfolder))

        for image_file_name in os.listdir(os.path.abspath(os.path.join(app.CACHE_DIR, 'images', self.cache_subfolder))):
            if os.path.isfile(os.path.abspath(os.path.join(app.CACHE_DIR, 'images', self.cache_subfolder, image_file_name))):
                if str(tvdb_id) == image_file_name.split('-')[0]:
                    return image_file_name
        return False
