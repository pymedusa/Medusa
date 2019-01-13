# coding=utf-8

from __future__ import unicode_literals

import logging
import os
import posixpath
import re

from medusa import helpers
from medusa.cache import recommended_series_cache
from medusa.imdb import Imdb
from medusa.indexers.indexer_config import INDEXER_TVDBV2, EXTERNAL_IMDB
from medusa.logger.adapters.style import BraceAdapter
from medusa.session.core import MedusaSession
from medusa.show.recommendations.recommended import (
    BasePopular,
    RecommendedShow,
    cached_get_imdb_series_details,
    create_key_from_series,
)

from requests import RequestException

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class ImdbPopular(BasePopular):
    """Gets a list of most popular TV series from imdb."""

    TITLE = 'IMDB Popular'
    CACHE_SUBFOLDER = __name__.split('.')[-1] if '.' in __name__ else __name__
    BASE_URL = 'https://anidb.net/perl-bin/animedb.pl?show=anime&aid={aid}'

    def __init__(self):
        """Initialize class."""
        super(ImdbPopular, self).__init__()
        self.cache_subfolder = ImdbPopular.CACHE_SUBFOLDER
        self.imdb_api = Imdb(session=self.session)
        self.recommender = ImdbPopular.TITLE
        self.source = EXTERNAL_IMDB

    @recommended_series_cache.cache_on_arguments(namespace='imdb', function_key_generator=create_key_from_series)
    def _create_recommended_show(self, storage_key, series):
        """Create the RecommendedShow object from the returned showobj."""
        tvdb_id = helpers.get_tvdb_from_id(series.get('imdb_tt'), 'IMDB')

        if not tvdb_id:
            return None

        rec_show = RecommendedShow(
            self,
            series.get('imdb_tt'),
            series.get('name'),
            **{
                'rating': series.get('rating'),
                'votes': series.get('votes'),
                'image_href': series.get('imdb_url'),
                'ids': {'tvdb_id': int(tvdb_id)}
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

            if imdb_id:
                try:
                    show_details = cached_get_imdb_series_details(imdb_id)
                except RequestException as error:
                    log.warning('Could not get show details for {imdb_id} with error: {error!r}',
                                {'imdb_id': imdb_id, 'error': error})

                if show_details:
                    try:
                        series['year'] = imdb_show.get('year')
                        series['name'] = imdb_show['title']
                        series['image_url_large'] = imdb_show['image']['url']
                        series['image_path'] = posixpath.join('images', 'imdb_popular',
                                                              os.path.basename(series['image_url_large']))
                        series['image_url'] = '{0}{1}'.format(imdb_show['image']['url'].split('V1')[0], '_SY600_AL_.jpg')
                        series['imdb_url'] = 'http://www.imdb.com{imdb_id}'.format(imdb_id=imdb_show['id'])
                        series['votes'] = show_details['ratings'].get('ratingCount', 0)
                        series['outline'] = show_details['plot'].get('outline', {}).get('text')
                        series['rating'] = show_details['ratings'].get('rating', 0)
                    except Exception as error:
                        log.warning('Could not parse show {imdb_id} with error: {error!r}',
                                    {'imdb_id': imdb_id, 'error': error})
                else:
                    continue

            if all([series['year'], series['name'], series['imdb_tt']]):
                try:
                    recommended_show = self._create_recommended_show(storage_key=series['imdb_tt'],
                                                                     series=series)
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
