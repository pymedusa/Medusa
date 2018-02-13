# coding=utf-8

from __future__ import unicode_literals

import logging
import os
import posixpath
import re
from datetime import date
from imdbpie import imdbpie
from medusa import app, helpers
from medusa.cache import recommended_series_cache
from medusa.indexers.indexer_config import INDEXER_TVDBV2
from medusa.logger.adapters.style import BraceAdapter
from medusa.session.core import MedusaSession
from medusa.show.recommendations.recommended import RecommendedShow

from requests import RequestException
from simpleanidb import Anidb

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())

imdb_api = imdbpie.Imdb()


class ImdbPopular(object):
    """Gets a list of most popular TV series from imdb."""

    def __init__(self):
        """Initialize class."""
        self.cache_subfolder = __name__.split('.')[-1] if '.' in __name__ else __name__
        self.session = MedusaSession()
        self.recommender = 'IMDB Popular'
        self.default_img_src = 'poster.png'
        self.anidb = Anidb(cache_dir=app.CACHE_DIR)

        # Use akas.imdb.com, just like the imdb lib.
        self.url = 'http://akas.imdb.com/search/title'

        self.params = {
            'at': 0,
            'sort': 'moviemeter',
            'title_type': 'tv_series',
            'year': '%s,%s' % (date.today().year - 1, date.today().year + 1),
        }

    @recommended_series_cache.cache_on_arguments()
    def _create_recommended_show(self, show_obj):
        """Create the RecommendedShow object from the returned showobj."""
        tvdb_id = helpers.get_tvdb_from_id(show_obj.get('imdb_tt'), 'IMDB')

        if not tvdb_id:
            return None

        rec_show = RecommendedShow(self,
                                   show_obj.get('imdb_tt'),
                                   show_obj.get('name'),
                                   INDEXER_TVDBV2,
                                   int(tvdb_id),
                                   **{'rating': show_obj.get('rating'),
                                      'votes': show_obj.get('votes'),
                                      'image_href': show_obj.get('imdb_url')}
                                   )

        if show_obj.get('image_url'):
            rec_show.cache_image(show_obj.get('image_url'))

        return rec_show

    @staticmethod
    @recommended_series_cache.cache_on_arguments()
    def _get_imdb_series_details(imdb_id):
        return imdb_api.get_title(imdb_id)

    def fetch_popular_shows(self):
        """Get popular show information from IMDB."""
        popular_shows = []

        imdb_result = imdb_api.get_popular_shows()

        for imdb_show in imdb_result['ranks']:
            show = dict()
            imdb_id = show['imdb_tt'] = imdb_show['id'].strip('/').split('/')[-1]

            if imdb_id:
                show_details = self._get_imdb_series_details(imdb_id)
                if show_details:
                    try:
                        show['year'] = imdb_show['year']
                        show['name'] = imdb_show['title']
                        show['image_url_large'] = imdb_show['image']['url']
                        show['image_path'] = posixpath.join('images', 'imdb_popular',
                                                            os.path.basename(show['image_url_large']))
                        show['image_url'] = '{0}{1}'.format(imdb_show['image']['url'].split('V1')[0], '_SY600_AL_.jpg')
                        show['imdb_url'] = 'http://www.imdb.com{imdb_id}'.format(imdb_id=imdb_show['id'])
                        show['votes'] = show_details['ratings'].get('ratingCount', 0)
                        show['outline'] = show_details['plot'].get('outline', {}).get('text')
                        show['rating'] = show_details['ratings'].get('rating', 0)
                    except Exception as error:
                        log.warning('Could not parse show {imdb_id} with error: {error}',
                                    {'imdb_id': imdb_id, 'error': error})
                else:
                    continue

            if all([show['year'], show['name'], show['imdb_tt']]):
                popular_shows.append(show)

        result = []
        for show in popular_shows:
            try:
                recommended_show = self._create_recommended_show(show)
                if recommended_show:
                    result.append(recommended_show)
            except RequestException:
                log.warning(
                    u'Could not connect to indexers to check if you already have'
                    u' this show in your library: {show} ({year})',
                    {'show': show['name'], 'year': show['name']}
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
