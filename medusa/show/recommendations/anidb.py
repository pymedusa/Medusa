# coding=utf-8

from __future__ import unicode_literals

import logging
import traceback
from os.path import join

from medusa import app
from medusa.cache import recommended_series_cache
from medusa.indexers.config import EXTERNAL_ANIDB
from medusa.logger.adapters.style import BraceAdapter
from medusa.show.recommendations.recommended import (
    BasePopular,
    MissingTvdbMapping,
    RecommendedShow,
    cached_aid_to_tvdb,
)

from simpleanidb import Anidb, REQUEST_HOT
from simpleanidb.exceptions import GeneralError


log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


def create_key_from_anidb_series(namespace, fn, **kw):
    """Create a key made of indexer name and show ID."""
    def generate_key(*args, **kw):
        show_id = args[1].aid
        show_key = f'{namespace}_{show_id}'
        return show_key
    return generate_key


class AnidbPopular(BasePopular):  # pylint: disable=too-few-public-methods

    TITLE = 'Anidb Popular'
    CACHE_SUBFOLDER = __name__.split('.')[-1] if '.' in __name__ else __name__

    def __init__(self):
        """Class retrieves a specified recommended show list from Trakt.

        List of returned shows is mapped to a RecommendedShow object
        """
        super(AnidbPopular, self).__init__()
        self.cache_subfolder = AnidbPopular.CACHE_SUBFOLDER
        self.recommender = AnidbPopular.TITLE
        self.source = EXTERNAL_ANIDB
        self.base_url = 'https://anidb.net/perl-bin/animedb.pl?show=anime&aid={aid}'

    @recommended_series_cache.cache_on_arguments(namespace='anidb', function_key_generator=create_key_from_anidb_series)
    def _create_recommended_show(self, series):
        """Create the RecommendedShow object from the returned showobj."""
        try:
            tvdb_id = cached_aid_to_tvdb(series.aid)
        except Exception:
            log.warning("Couldn't map AniDB id {0} to a TVDB id", series.aids)
            return None

        rec_show = RecommendedShow(
            self,
            series.aid,
            str(series.title),
            **{'rating': series.rating_permanent,
                'votes': series.count_permanent,
                'image_href': self.base_url.format(aid=series.aid),
                'ids': {
                    'tvdb_id': tvdb_id,
                    'anidb_id': series.aid
                },
                'is_anime': True,
                'subcat': 'hot'}
        )

        # Check cache or get and save image
        use_default = self.default_img_src if not series.picture.url else None
        rec_show.cache_image(series.picture.url, default=use_default)

        return rec_show

    def fetch_popular_shows(self, list_type=REQUEST_HOT):
        """Get popular show information from IMDB."""
        series = []
        result = []

        try:
            series = Anidb(cache_dir=join(app.CACHE_DIR, 'simpleanidb')).get_list(list_type)
        except GeneralError as error:
            log.warning('Could not connect to AniDB service: {0}', error)

        for show in series:
            try:
                recommended_show = self._create_recommended_show(series=show)
                if recommended_show:
                    recommended_show.save_to_db()
                    result.append(recommended_show)
            except MissingTvdbMapping:
                log.info('Could not parse AniDB show {0}, missing tvdb mapping', show.title)
            except Exception:
                log.warning('Could not parse AniDB show, with exception: {0}', traceback.format_exc())

        return result
