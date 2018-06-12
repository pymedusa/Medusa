# coding=utf-8

from __future__ import unicode_literals

import logging
import traceback
from builtins import object

from medusa import app
from medusa.cache import recommended_show_cache
from medusa.indexers.indexer_config import INDEXER_TVDBV2
from medusa.logger.adapters.style import BraceAdapter
from medusa.session.core import MedusaSession
from medusa.show.recommendations.recommended import (
    MissingTvdbMapping, RecommendedShow, cached_aid_to_tvdb, create_key_from_show,
    update_recommended_show_cache_index
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

    @recommended_show_cache.cache_on_arguments(namespace='anidb', function_key_generator=create_key_from_show)
    def _create_recommended_show(self, show, storage_key=None):
        """Create the RecommendedShow object from the returned showobj."""
        try:
            tvdb_id = cached_aid_to_tvdb(show.aid)
        except Exception:
            log.warning("Couldn't map AniDB id {0} to a TVDB id", show.aids)
            return None

        # If the anime can't be mapped to a tvdb_id, return none, and move on to the next.
        if not tvdb_id:
            return tvdb_id

        rec_show = RecommendedShow(
            self,
            show.aid,
            show.title,
            INDEXER_TVDBV2,
            tvdb_id,
            **{'rating': show.rating_permanent,
                'votes': show.count_permanent,
                'image_href': self.base_url.format(aid=show.aid),
                'ids': {'tvdb': tvdb_id,
                        'aid': show.aid
                        }
               }
        )

        # Check cache or get and save image
        use_default = self.default_img_src if not show.picture.url else None
        rec_show.cache_image(show.picture.url, default=use_default)

        # By default pre-configure the show option anime = True
        rec_show.is_anime = True

        return rec_show

    def fetch_popular_shows(self, list_type=REQUEST_HOT):
        """Get popular show information from IMDB."""
        show = []
        result = []

        try:
            show = Anidb(cache_dir=app.CACHE_DIR).get_list(list_type)
        except GeneralError as error:
            log.warning('Could not connect to AniDB service: {0}', error)

        for show in show:
            try:
                recommended_show = self._create_recommended_show(show, storage_key=b'anidb_{0}'.format(show.aid))
                if recommended_show:
                    result.append(recommended_show)
            except MissingTvdbMapping:
                log.info('Could not parse AniDB show {0}, missing tvdb mapping', show.title)
            except Exception:
                log.warning('Could not parse AniDB show, with exception: {0}', traceback.format_exc())

        # Update the dogpile index. This will allow us to retrieve all stored dogpile shows from the dbm.
        update_recommended_show_cache_index('anidb', [binary_type(s.show_id) for s in result])

        return result
