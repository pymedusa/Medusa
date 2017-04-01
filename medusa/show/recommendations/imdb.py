# coding=utf-8
from __future__ import unicode_literals

import os
import posixpath
import re

from datetime import date

from imdbpie import imdbpie

from requests import RequestException

from simpleanidb import Anidb

from .recommended import RecommendedShow
from ... import app, helpers, logger
from ...indexers.indexer_config import INDEXER_TVDBV2


class ImdbPopular(object):
    """Gets a list of most popular TV series from imdb."""

    def __init__(self):
        """Constructor for ImdbPopular."""
        self.cache_subfolder = __name__.split('.')[-1] if '.' in __name__ else __name__
        self.session = helpers.make_session()
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

        if show_obj.get('image_url_large'):
            rec_show.cache_image(show_obj.get('image_url_large'))

        return rec_show

    def fetch_popular_shows(self):
        """Get popular show information from IMDB."""
        popular_shows = []

        imdb_api = imdbpie.Imdb()
        imdb_result = imdb_api.popular_shows()

        for imdb_show in imdb_result:
            show = dict()
            imdb_tt = imdb_show['tconst']

            if imdb_tt:
                show['imdb_tt'] = imdb_show['tconst']
                show_details = imdb_api.get_title_by_id(imdb_tt)

                if show_details:
                    show['year'] = getattr(show_details, 'year')
                    show['name'] = getattr(show_details, 'title')
                    show['image_url_large'] = getattr(show_details, 'cover_url')
                    show['image_path'] = posixpath.join('images', 'imdb_popular',
                                                        os.path.basename(show['image_url_large']))
                    show['imdb_url'] = 'http://www.imdb.com/title/{imdb_tt}'.format(imdb_tt=imdb_tt)
                    show['votes'] = getattr(show_details, 'votes', 0)
                    show['outline'] = getattr(show_details, 'plot_outline', 'Not available')
                    show['rating'] = getattr(show_details, 'rating', 0)
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
                logger.log(u'Could not connect to indexers to check if you already have '
                           u'this show in your library: {show} ({year})'.format
                           (show=show['name'], year=show['name']), logger.WARNING)

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
