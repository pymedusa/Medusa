"""Trakt recommendations module."""
# coding=utf-8

from __future__ import unicode_literals

import logging
import os

from medusa import app
from medusa.cache import recommended_series_cache
from medusa.helper.common import try_int
from medusa.helper.exceptions import MultipleShowObjectsException
from medusa.helpers.trakt import get_trakt_show_collection, get_trakt_user
from medusa.indexers.api import indexerApi
from medusa.indexers.config import EXTERNAL_TRAKT, INDEXER_TVDBV2, TRAKT_INDEXERS
from medusa.logger.adapters.style import BraceAdapter
from medusa.show.recommendations import ExpiringList
from medusa.show.recommendations.recommended import (
    BasePopular,
    RecommendedShow,
)

from six import iteritems

from trakt import sync
from trakt.errors import ForbiddenException

from tvdbapiv2.exceptions import ApiException


log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


missing_posters = ExpiringList(cache_timeout=3600 * 24 * 3)  # Cache 3 days


def create_key_from_trakt_series(namespace, fn, **kw):
    """Create a key made of indexer name and show ID."""
    def generate_key(*args, **kw):
        show_id = args[1].trakt
        show_key = f'{namespace}_{show_id}'
        return show_key
    return generate_key


class TraktPopular(BasePopular):
    """This class retrieves a speficed recommended show list from Trakt.

    The list of returned shows is mapped to a RecommendedShow object
    """

    TITLE = 'Trakt Popular'
    CACHE_SUBFOLDER = __name__.split('.')[-1] if '.' in __name__ else __name__
    CATEGORIES = [
        'trending', 'popular', 'anticipated', 'collected',
        'watched', 'played', 'recommendations', 'newshow', 'newseason'
    ]

    def __init__(self):
        """Initialize the trakt recommended list object."""
        super(TraktPopular, self).__init__()
        self.cache_subfolder = TraktPopular.CACHE_SUBFOLDER
        self.source = EXTERNAL_TRAKT
        self.recommender = TraktPopular.TITLE
        self.default_img_src = 'trakt-default.png'
        self.tvdb_api_v2 = indexerApi(INDEXER_TVDBV2).indexer()

    @recommended_series_cache.cache_on_arguments(namespace='trakt', function_key_generator=create_key_from_trakt_series)
    def _create_recommended_show(self, show, subcat=None):
        """Create the RecommendedShow object from the returned showobj."""
        rec_show = RecommendedShow(
            self,
            show.trakt,
            show.title,
            **{'rating': show.ratings['rating'],
                'votes': try_int(show.ratings['votes'], '0'),
                'image_href': 'http://www.trakt.tv/shows/{0}'.format(show.ids['ids']['slug']),
                # Adds like: {'tmdb': 62126, 'tvdb': 304219, 'trakt': 79382, 'imdb': 'tt3322314',
                # 'tvrage': None, 'slug': 'marvel-s-luke-cage'}
                'ids': {f'{k}_id': v for k, v in iteritems(show.ids['ids']) if TRAKT_INDEXERS.get(k)},
                'subcat': subcat,
                'genres': [genre.lower() for genre in show.genres],
                'plot': show.overview
               }
        )

        use_default = None
        image = None
        try:
            if not missing_posters.has(show.tvdb):
                image = self.check_cache_for_poster(show.tvdb) or \
                    self.tvdb_api_v2.config['session'].series_api.series_id_images_query_get(
                        show.tvdb, key_type='poster').data[0].file_name
            else:
                log.info('CACHE: Missing poster on TVDB for show {0}', show.title)
                use_default = self.default_img_src
        except ApiException as error:
            use_default = self.default_img_src
            if getattr(error, 'status', None) == 404:
                log.info('Missing poster on TheTVDB for show {0}', show.title)
                missing_posters.append(show.tvdb)
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
        if 'jp' in [show.country, show.language]:
            rec_show.flag_as_anime(show.tvdb)

        return rec_show

    def get_removed_from_medusa(self):
        """
        Return an array of shows (tvdb id's) that are still located in the trakt `watched` and `show collection` collections.

        But that are not in medusa's library.
        Library is compared based on the tvdb id's.
        """
        library_shows = sync.get_watched('shows', extended='noseasons') + sync.get_collection('shows', extended='full')
        medusa_shows = [show.externals.get('tvdb_id', show.series_id) for show in app.showList if show.series_id]
        return [lshow.tvdb for lshow in library_shows if lshow.tvdb not in medusa_shows]

    def fetch_popular_shows(self, trakt_list=None):
        """Get a list of popular shows from different Trakt lists based on a provided trakt_list.

        :param page_url: the page url opened to the base api url, for retreiving a specific list
        :param trakt_list: a description of the trakt list
        :return: A list of RecommendedShow objects, an empty list of none returned
        :throw: ``Exception`` if an Exception is thrown not handled by the libtrats exceptions
        """
        recommended_shows = []

        try:
            not_liked_show = ''

            removed_from_medusa = self.get_removed_from_medusa()

            if app.TRAKT_BLACKLIST_NAME:
                trakt_user = get_trakt_user()
                not_liked_show = trakt_user.get_list(app.TRAKT_BLACKLIST_NAME) or []
            else:
                log.debug('Trakt blacklist name is empty')

            limit = None
            if trakt_list not in ['recommended', 'newshow', 'newseason']:
                limit = 100 + len(not_liked_show)

            # Get the trakt list
            shows = get_trakt_show_collection(trakt_list, limit)

            # Trigger a cache cleanup
            missing_posters.clean()

            for show in shows:
                try:
                    # If there isn't a tvdb id available skip it. We can't add it anyway.
                    if show.tvdb is None:
                        continue

                    if (not_liked_show and show.tvdb
                            in (s.tvdb for s in not_liked_show if s.media_type == 'shows')):
                        continue

                    recommended_show = self._create_recommended_show(show, subcat=trakt_list)
                    if recommended_show:
                        recommended_show.save_to_db()
                        recommended_shows.append(recommended_show)

                except MultipleShowObjectsException:
                    continue

            # # Update the dogpile index. This will allow us to retrieve all stored dogpile shows from the dbm.
            # update_recommended_series_cache_index('trakt', [binary_type(s.series_id) for s in trending_shows])
            blacklist = app.TRAKT_BLACKLIST_NAME not in ''
        except ForbiddenException as error:
            log.warning(
                'Trying to connect to trakt.tv but it seems you are not authenticated. error: {error}',
                {'error': error}
            )
            raise
        except Exception as error:
            log.exception('Could not connect to Trakt service: {0}', error)

        return blacklist, recommended_shows, removed_from_medusa

    def check_cache_for_poster(self, tvdb_id):
        """Verify if we already have a poster downloaded for this show."""
        if not os.path.exists(os.path.join(app.CACHE_DIR, 'images', self.cache_subfolder)):
            os.makedirs(os.path.join(app.CACHE_DIR, 'images', self.cache_subfolder))

        for image_file_name in os.listdir(os.path.abspath(os.path.join(app.CACHE_DIR, 'images', self.cache_subfolder))):
            if os.path.isfile(os.path.abspath(os.path.join(app.CACHE_DIR, 'images', self.cache_subfolder, image_file_name))):
                if str(tvdb_id) == image_file_name.split('-')[0]:
                    return image_file_name
        return False
