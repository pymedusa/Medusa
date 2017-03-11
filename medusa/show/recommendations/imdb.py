# coding=utf-8
from __future__ import unicode_literals

import os
import posixpath
import re
import traceback
from datetime import date

from bs4 import BeautifulSoup
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

        response = helpers.get_url(self.url, session=self.session, params=self.params,
                                   headers={'Referer': 'http://akas.imdb.com/'}, returns='response')
        if not response or not response.text:
            return None

        soup = BeautifulSoup(response.text, 'html5lib')
        results = soup.find('div', class_='lister-list')
        rows = results.find_all('div', class_='lister-item mode-advanced')

        for row in rows:
            show = {}

            image_div = row.find('div', class_='lister-item-image float-left')
            if image_div:
                image = image_div.find('img')
                show['image_url_large'] = self.change_size(image['loadlate'])
                show['image_path'] = posixpath.join('images', 'imdb_popular',
                                                    os.path.basename(show['image_url_large']))
                # self.cache_image(show['image_url_large'])

            content_div = row.find('div', class_='lister-item-content')
            if content_div:
                show_info = content_div.find('a')
                show['name'] = show_info.get_text()
                show['imdb_url'] = 'http://www.imdb.com' + show_info['href']
                show['imdb_tt'] = row.find('div', class_='ribbonize')['data-tconst']
                show['year'] = content_div.find('span', class_='lister-item-year text-muted unbold').get_text()[1:5]

                rating_div = content_div.find('div', class_='ratings-bar')
                if rating_div:
                    rating_strong = rating_div.find('strong')
                    if rating_strong:
                        show['rating'] = rating_strong.get_text()

                votes_p = content_div.find('p', class_='sort-num_votes-visible')
                if votes_p:
                    show['votes'] = votes_p.find('span', {'name': 'nv'}).get_text().replace(',', '')

                text_p = content_div.find('p', class_='text-muted')
                if text_p:
                    show['outline'] = text_p.get_text(strip=True)

                popular_shows.append(show)

        result = []
        for show in popular_shows:
            try:
                recommended_show = self._create_recommended_show(show)
                if recommended_show:
                    result.append(recommended_show)
            except Exception:
                logger.log(u'Could not parse IMDB show, with exception: {0!r}'.format
                           (traceback.format_exc()), logger.WARNING)

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
