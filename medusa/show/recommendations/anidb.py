# coding=utf-8

from __future__ import unicode_literals

import logging
import traceback

from medusa import app
from medusa.cache import recommended_series_cache
from medusa.indexers.indexer_config import INDEXER_TVDBV2
from medusa.logger.adapters.style import BraceAdapter
from medusa.session.core import MedusaSession
from medusa.show.recommendations.recommended import (
    MissingTvdbMapping, RecommendedShow, cached_aid_to_tvdb, create_key_from_series,
    update_recommended_series_cache_index
)

from simpleanidb import Anidb, REQUEST_HOT
from simpleanidb.exceptions import GeneralError

from six import binary_type


log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class AnidbPopular(object):  # pylint: disable=too-few-public-methods
    def __init__(self):
        """Class retrieves a specified recommended show list from Trakt.

        List of returned shows is mapped to a RecommendedShow object
        """
        self.cache_subfolder = __name__.split('.')[-1] if '.' in __name__ else __name__
        self.session = MedusaSession()
        self.recommender = "Anidb Popular"
        self.base_url = 'https://anidb.net/perl-bin/animedb.pl?show=anime&aid={aid}'
        self.default_img_src = 'poster.png'

    @recommended_series_cache.cache_on_arguments(namespace='anidb', function_key_generator=create_key_from_series)
    def _create_recommended_show(self, series, storage_key=None):
        """Create the RecommendedShow object from the returned showobj."""
        try:
            tvdb_id = cached_aid_to_tvdb(series.aid)
        except Exception:
            log.warning("Couldn't map AniDB id {0} to a TVDB id", series.aids)
            return None

        # If the anime can't be mapped to a tvdb_id, return none, and move on to the next.
        if not tvdb_id:
            return tvdb_id

        rec_show = RecommendedShow(
            self,
            series.aid,
            series.title,
            INDEXER_TVDBV2,
            tvdb_id,
            **{'rating': series.rating_permanent,
                'votes': series.count_permanent,
                'image_href': self.base_url.format(aid=series.aid),
                'ids': {'tvdb': tvdb_id,
                        'aid': series.aid
                        }
               }
        )

        # Check cache or get and save image
        use_default = self.default_img_src if not series.picture.url else None
        rec_show.cache_image(series.picture.url, default=use_default)

        # By default pre-configure the show option anime = True
        rec_show.is_anime = True

        return rec_show

    def fetch_popular_shows(self, list_type=REQUEST_HOT):
        """Get popular show information from IMDB."""
        series = []
        result = []

        try:
            series = Anidb(cache_dir=app.CACHE_DIR).get_list(list_type)
        except GeneralError as error:
            log.warning('Could not connect to AniDB service: {0}', error)

        for show in series:
            try:
                recommended_show = self._create_recommended_show(show, storage_key=b'anidb_{0}'.format(show.aid))
                if recommended_show:
                    result.append(recommended_show)
            except MissingTvdbMapping:
                log.info('Could not parse AniDB show {0}, missing tvdb mapping', show.title)
            except Exception:
                log.warning('Could not parse AniDB show, with exception: {0}', traceback.format_exc())

        # Update the dogpile index. This will allow us to retrieve all stored dogpile shows from the dbm.
        update_recommended_series_cache_index('anidb', [binary_type(s.series_id) for s in result])

        return result
