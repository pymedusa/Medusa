# coding=utf-8

from __future__ import unicode_literals

import logging
import traceback

from os.path import join

from medusa import app
from medusa.cache import recommended_series_cache
from medusa.indexers.config import EXTERNAL_ANIDB, EXTERNAL_MYANIMELIST
from medusa.logger.adapters.style import BraceAdapter
from medusa.show.recommendations.recommended import (
    BasePopular,
    RecommendedShow,
    cached_aid_to_tvdb,
    create_key_from_series,
)
from medusa.session.core import MedusaSession
from requests import RequestException


log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class MyAnimeListPopular(BasePopular):  # pylint: disable=too-few-public-methods

    BASE_URL = 'https://myanimelist.net/anime'
    TITLE = 'MyAnimelist'
    CACHE_SUBFOLDER = __name__.split('.')[-1] if '.' in __name__ else __name__

    def __init__(self):
        """Class retrieves a specified recommended show list from Trakt.

        List of returned shows is mapped to a RecommendedShow object
        """
        super(MyAnimeListPopular, self).__init__()
        self.cache_subfolder = MyAnimeListPopular.CACHE_SUBFOLDER
        self.recommender = MyAnimeListPopular.TITLE
        self.source = EXTERNAL_MYANIMELIST
        self.base_url = MyAnimeListPopular.BASE_URL
        self.session = MedusaSession()

    @recommended_series_cache.cache_on_arguments(namespace='myanimelist', function_key_generator=create_key_from_series)
    def _create_recommended_show(self, show):
        """Create the RecommendedShow object from the returned showobj."""

        rec_show = RecommendedShow(
            self,
            show['mal_id'],
            show['title'],
            **{
                'rating': show['score'],
                'votes': show['scored_by'],
                'image_href': show['images']['jpg']['image_url'],
                'ids': {
                    'myanimelist_id': show['mal_id']
                },
                'is_anime': True,
                'subcat': f"{show['year']}_{show['season']}"
            }
        )

        # Check cache or get and save image
        use_default = self.default_img_src if not show['images']['jpg']['image_url'] else None
        rec_show.cache_image(show['images']['jpg']['image_url'], default=use_default)

        return rec_show

    def fetch_popular_shows(self, year, season):
        """Get popular show information from IMDB."""
        shows = []
        result = []

        try:
            response = self.session.get(f'https://api.jikan.moe/v4/seasons/{year}/{season}')
            shows = response.json()['data']
        except Exception as error:
            log.warning('Unable to get MyAnimelist shows: {0!r}', error)
            return []

        for show in shows:
            try:
                recommended_show = self._create_recommended_show(show)
                if recommended_show:
                    recommended_show.save_to_db()
                    result.append(recommended_show)
            except Exception:
                log.warning('Could not parse AniDB show, with exception: {0}', traceback.format_exc())

        return result
