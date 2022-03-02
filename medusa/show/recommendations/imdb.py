# coding=utf-8
"""Anidb recommended show class."""
from __future__ import unicode_literals

import logging
import os
import posixpath
import re

from medusa.cache import recommended_series_cache
from medusa.imdb import Imdb
from medusa.indexers.api import indexerApi
from medusa.indexers.config import EXTERNAL_IMDB, INDEXER_TMDB
from medusa.indexers.imdb.api import ImdbIdentifier
from medusa.logger.adapters.style import BraceAdapter
from medusa.show.recommendations.recommended import (
    BasePopular,
    RecommendedShow,
    cached_get_imdb_series_details,
    cached_get_imdb_series_genres,
    create_key_from_series,
)

from requests import RequestException

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class ImdbPopular(BasePopular):
    """Gets a list of most popular TV series from imdb."""

    TITLE = 'IMDB Popular'
    CACHE_SUBFOLDER = __name__.split('.')[-1] if '.' in __name__ else __name__

    def __init__(self):
        """Initialize class."""
        super(ImdbPopular, self).__init__()
        self.cache_subfolder = ImdbPopular.CACHE_SUBFOLDER
        self.imdb_api = Imdb(session=self.session)
        self.recommender = ImdbPopular.TITLE
        self.source = EXTERNAL_IMDB

    @recommended_series_cache.cache_on_arguments(namespace='imdb', function_key_generator=create_key_from_series)
    def _create_recommended_show(self, series):
        """Create the RecommendedShow object from the returned showobj."""
        externals = {'imdb_id': ImdbIdentifier(series.get('imdb_tt')).series_id}

        # Get tmdb id using a call to tmdb api.
        t = indexerApi(INDEXER_TMDB).indexer(**indexerApi(INDEXER_TMDB).api_params.copy())
        externals.update(t.get_id_by_external(**externals))

        rec_show = RecommendedShow(
            self,
            ImdbIdentifier(series.get('imdb_tt')).series_id,
            series.get('name'),
            **{
                'rating': series.get('rating'),
                'votes': series.get('votes'),
                'image_href': series.get('imdb_url'),
                'ids': externals,
                'subcat': 'popular',
                'genres': [genre.lower() for genre in series.get('genres')],
                'plot': series.get('outline')
            }
        )

        if series.get('image_url'):
            rec_show.cache_image(series.get('image_url'))

        return rec_show

    def fetch_popular_shows(self):
        """Get popular show information from IMDB."""
        imdb_result = self.imdb_api.get_popular_shows()
        result = []
        for imdb_show in imdb_result['ranks']:
            series = {}
            show_details = None
            imdb_id = series['imdb_tt'] = imdb_show['id'].strip('/').split('/')[-1]

            if not imdb_id:
                continue

            series['year'] = imdb_show.get('year')
            series['name'] = imdb_show['title']
            series['image_url_large'] = imdb_show['image']['url']
            series['image_path'] = posixpath.join(
                'images', 'imdb_popular', os.path.basename(series['image_url_large'])
            )
            series['image_url'] = '{0}{1}'.format(imdb_show['image']['url'].split('V1')[0], '_SY600_AL_.jpg')
            series['imdb_url'] = 'http://www.imdb.com{imdb_id}'.format(imdb_id=imdb_show['id'])

            show_details = {}
            show_genres = {}
            try:
                show_details = cached_get_imdb_series_details(imdb_id)
                show_genres = cached_get_imdb_series_genres(imdb_id)
            except Exception as error:
                log.warning('Could not get show details for {imdb_id} with error: {error}',
                            {'imdb_id': imdb_id, 'error': error})

            if not show_details:
                continue

            # Get details.
            try:
                series['votes'] = show_details.get('ratings', {}).get('ratingCount', 0)
                series['outline'] = show_details.get('plot', {}).get('outline', {}).get('text')
                series['rating'] = show_details.get('ratings', {}).get('rating', 0)
            except Exception as error:
                log.warning('Could not parse show {imdb_id} with error: {error!r}',
                            {'imdb_id': imdb_id, 'error': error})

            series['genres'] = show_genres.get('genres', [])

            if all([series['year'], series['name'], series['imdb_tt']]):
                try:
                    recommended_show = self._create_recommended_show(series)
                    if recommended_show:
                        recommended_show.save_to_db()
                        result.append(recommended_show)
                except RequestException:
                    log.warning(
                        u'Could not connect to indexers to check if you already have'
                        u' this show in your library: {show} ({year})',
                        {'show': series['name'], 'year': series['name']}
                    )

        return result

    @staticmethod
    def change_size(image_url, factor=3):
        """Change the size of the image we get from IMDB.

        :param: image_url: Image source URL
        :param: factor: Multiplier for the image size
        """
        match = re.search(r'(.+[X|Y])(\d+)(_CR\d+,\d+,)(\d+),(\d+)', image_url)

        if match:
            matches = list(match.groups())
            matches[1] = int(matches[1]) * factor
            matches[3] = int(matches[3]) * factor
            matches[4] = int(matches[4]) * factor

            return '{0}{1}{2}{3},{4}_AL_.jpg'.format(matches[0], matches[1], matches[2],
                                                     matches[3], matches[4])
        else:
            return image_url
