# coding=utf-8

from __future__ import unicode_literals

import logging
import traceback

from medusa import app, helpers
from medusa.indexers.indexer_config import INDEXER_TVDBV2
from medusa.logger.adapters.style import BraceAdapter
from medusa.show.recommendations.recommended import (MissingTvdbMapping, RecommendedShow)
from medusa.session.core import MedusaSession

from simpleanidb import (Anidb, REQUEST_HOT)
from simpleanidb.exceptions import GeneralError


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
        self.anidb = Anidb(cache_dir=app.CACHE_DIR)

    def _create_recommended_show(self, show_obj):
        """Create the RecommendedShow object from the returned showobj."""
        try:
            tvdb_id = self.anidb.aid_to_tvdb_id(show_obj.aid)
        except Exception:
            log.warning("Couldn't map AniDB id {0} to a TVDB id", show_obj.aid)
            return None

        # If the anime can't be mapped to a tvdb_id, return none, and move on to the next.
        if not tvdb_id:
            return tvdb_id

        rec_show = RecommendedShow(self,
                                   show_obj.aid,
                                   show_obj.title,
                                   INDEXER_TVDBV2,
                                   tvdb_id,
                                   **{'rating': show_obj.rating_permanent,
                                      'votes': show_obj.count_permanent,
                                      'image_href': self.base_url.format(aid=show_obj.aid),
                                      'ids': {'tvdb': tvdb_id,
                                              'aid': show_obj.aid
                                              }
                                      }
                                   )

        # Check cache or get and save image
        use_default = self.default_img_src if not show_obj.picture.url else None
        rec_show.cache_image(show_obj.picture.url, default=use_default)

        # By default pre-configure the show option anime = True
        rec_show.is_anime = True

        return rec_show

    def fetch_popular_shows(self, list_type=REQUEST_HOT):
        """Get popular show information from IMDB"""
        shows = []
        result = []

        try:
            shows = self.anidb.get_list(list_type)
        except GeneralError as error:
            log.warning('Could not connect to AniDB service: {0}', error)

        for show in shows:
            try:
                recommended_show = self._create_recommended_show(show)
                if recommended_show:
                    result.append(recommended_show)
            except MissingTvdbMapping:
                log.info('Could not parse AniDB show {0}, missing tvdb mapping', show.title)
            except Exception:
                log.warning('Could not parse AniDB show, with exception: {0}', traceback.format_exc())

        return result
