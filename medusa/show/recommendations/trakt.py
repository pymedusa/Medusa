# coding=utf-8
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
from __future__ import unicode_literals

import requests
import time
from simpleanidb import Anidb
from traktor import (TokenExpiredException, TraktApi, TraktException)
from tvdbapiv2.rest import ApiException
from .recommended import RecommendedShow
from ... import app, logger
from ...helper.common import try_int
from ...helper.exceptions import MultipleShowObjectsException, ex
from ...indexers.indexer_api import indexerApi
from ...indexers.indexer_config import INDEXER_TVDBV2


class MissingPosterList(list):
    """Smart custom list, with a cache expiration.

    A list used to store the trakt shows that do not have a poster on tvdb. This will prevent searches for posters
    that have recently been searched using the tvdb's api, and resulted in a 404.
    """

    def __init__(self, items=None, cache_timeout=3600, implicit_clean=False):
        """Initialize the MissingPosterList.

        :param items: Provide the initial list.
        :param cache_timeout: Timeout after which the item expires.
        :param implicit_clean: If enabled, run the clean() method, to check for expired items. Else you'll have to run
        this periodically.
        """
        list.__init__(self, items or [])
        self.cache_timeout = cache_timeout
        self.implicit_clean = implicit_clean

    def append(self, item):
        """Add new items to the list."""
        if self.implicit_clean:
            self.clean()
        super(MissingPosterList, self).append((int(time.time()), item))

    def clean(self):
        """Use the cache_timeout to remove expired items."""
        new_list = [_ for _ in self if _[0] + self.cache_timeout > int(time.time())]
        self.__init__(new_list, self.cache_timeout, self.implicit_clean)

    def has(self, value):
        """Check if the value is in the list.

        We need a smarter method to check if an item is already in the list. This will return a list with items that
        match the value.
        :param value: The value to check for.
        :return: A list of tuples with matches. For example: (141234234, '12342').
        """
        if self.implicit_clean:
            self.clean()
        return [_ for _ in self if _[1] == value]


missing_posters = MissingPosterList(cache_timeout=3600 * 24 * 3)  # Cache 3 days


class TraktPopular(object):
    """This class retrieves a speficed recommended show list from Trakt.

    The list of returned shows is mapped to a RecommendedShow object
    """

    def __init__(self):
        """Initialize the trakt recommended list object."""
        self.cache_subfolder = __name__.split('.')[-1] if '.' in __name__ else __name__
        self.session = requests.Session()
        self.recommender = "Trakt Popular"
        self.default_img_src = 'trakt-default.png'
        self.anidb = Anidb(cache_dir=app.CACHE_DIR)
        self.tvdb_api_v2 = indexerApi(INDEXER_TVDBV2).indexer()

    def _create_recommended_show(self, show_obj):
        """Create the RecommendedShow object from the returned showobj."""
        rec_show = RecommendedShow(self,
                                   show_obj['show']['ids'], show_obj['show']['title'],
                                   INDEXER_TVDBV2,  # indexer
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
                        self.tvdb_api_v2.series_api.series_id_images_query_get(
                            show_obj['show']['ids']['tvdb'], key_type='poster'
                        ).data[0].file_name
            else:
                logger.log('CACHE: Missing poster on TheTVDB for show %s' % (show_obj['show']['title']), logger.INFO)
                use_default = self.default_img_src
        except ApiException as e:
            use_default = self.default_img_src
            if getattr(e, 'status', None) == 404:
                logger.log('Missing poster on TheTVDB for show %s' % (show_obj['show']['title']), logger.INFO)
                missing_posters.append(show_obj['show']['ids']['tvdb'])
        except Exception as e:
            use_default = self.default_img_src
            logger.log('Missing poster on TheTVDB, cause: %r' % e, logger.DEBUG)

        rec_show.cache_image('http://thetvdb.com/banners/{0}'.format(image), default=use_default)
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
                    logger.log('Trakt blacklist name is empty', logger.DEBUG)

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

        except TraktException as e:
            logger.log('Could not connect to Trakt service: %s' % ex(e), logger.WARNING)
            raise

        return blacklist, trending_shows, removed_from_medusa

    def check_cache_for_poster(self, tvdb_id):
        """Verify if we already have a poster downloaded for this show."""
        import os
        for image_file_name in os.listdir(os.path.abspath(os.path.join(app.CACHE_DIR, 'images', self.cache_subfolder))):
            if os.path.isfile(os.path.abspath(os.path.join(app.CACHE_DIR, 'images', self.cache_subfolder, image_file_name))):
                if str(tvdb_id) == image_file_name.split('-')[0]:
                    return image_file_name
        return False
