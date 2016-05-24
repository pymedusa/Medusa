# coding=utf-8
import re
import os
from bs4 import BeautifulSoup
from datetime import date

import sickbeard
from sickbeard import helpers
from sickrage.helper.encoding import ek
from sickbeard import logger
from sickrage.helper.exceptions import ex
from .recommended import RecommendedShow


class ImdbPopular(object):
    def __init__(self):
        """Gets a list of most popular TV series from imdb"""

        self.cache_subfolder = __name__.split('.')[-1] if '.' in __name__ else __name__
        self.session = helpers.make_session()
        self.recommender = 'IMDB Popular'
        self.default_img_src = ''

        # Use akas.imdb.com, just like the imdb lib.
        self.url = 'http://akas.imdb.com/search/title'
        self.params = {
            'at': 0,
            'sort': 'moviemeter',
            'title_type': 'tv_series',
            'year': '%s,%s' % (date.today().year - 1, date.today().year + 1)
        }

    def _create_recommended_show(self, show_obj):
        """creates the RecommendedShow object from the returned showobj"""

        tvdb_id = helpers.getTVDBFromID(show_obj.get('imdb_tt'), 'IMDB')
        if not tvdb_id:
            return None

        rec_show = RecommendedShow(self,
                                   show_obj.get('imdb_tt'),
                                   show_obj.get('name'),
                                   1,
                                   tvdb_id,
                                   **{'rating': show_obj.get('rating'),
                                      'votes': show_obj.get('votes'),
                                      'image_href': show_obj.get('imdb_url')}
                                   )

        if show_obj.get('image_url_large'):
            rec_show.cache_image(show_obj.get('image_url_large'))

        return rec_show

    def fetch_popular_shows(self):
        """Get popular show information from IMDB"""

        popular_shows = []

        data = helpers.getURL(self.url, session=self.session, params=self.params,
                              headers={'Referer': 'http://akas.imdb.com/'}, returns='text')
        if not data:
            return None

        soup = BeautifulSoup(data, 'html5lib')
        results = soup.find('table', {'class': 'results'})
        rows = results.find_all('tr')

        for row in rows:
            show = {}
            image_td = row.find('td', {'class': 'image'})

            if image_td:
                image = image_td.find('img')
                show['image_url_large'] = self.change_size(image['src'], 3)

            td = row.find('td', {'class': 'title'})

            if td:
                show['name'] = td.find('a').contents[0]
                show['imdb_url'] = 'http://akas.imdb.com{0}'.format(td.find('a')['href'])
                show['imdb_tt'] = show['imdb_url'][-10:][0:9]
                show['year'] = td.find('span', {'class': 'year_type'}).contents[0].split(' ')[0][1:]

                rating_all = td.find('div', {'class': 'user_rating'})
                if rating_all:
                    rating_string = rating_all.find('div', {'class': 'rating rating-list'})
                    if rating_string:
                        rating_string = rating_string['title']

                        match = re.search(r'.* (.*)\/10.*\((.*)\).*', rating_string)
                        if match:
                            matches = match.groups()
                            show['rating'] = matches[0]
                            show['votes'] = matches[1]
                        else:
                            show['rating'] = None
                            show['votes'] = None
                else:
                    show['rating'] = None
                    show['votes'] = None

                outline = td.find('span', {'class': 'outline'})
                if outline:
                    show['outline'] = outline.contents[0]
                else:
                    show['outline'] = u''

                popular_shows.append(show)

        result = []
        for show in popular_shows:
            try:
                result.append(self._create_recommended_show(show))
            except Exception, e:
                logger.log(u'Could not parse IMDB show, with exception: %s' % ex(e), logger.WARNING)

        return result

    @staticmethod
    def change_size(image_url, factor=3):
        match = re.search(r'^(.*)V1._(.{2})(.*?)_(.{2})(.*?),(.*?),(.*?),(.*?)_.jpg$', image_url)

        if match:
            matches = match.groups()
            ek(os.path.basename, image_url)
            matches = list(matches)
            matches[2] = int(matches[2]) * factor
            matches[4] = int(matches[4]) * factor
            matches[5] = int(matches[5]) * factor
            matches[6] = int(matches[6]) * factor
            matches[7] = int(matches[7]) * factor

            return '%sV1._%s%s_%s%s,%s,%s,%s_.jpg' % (matches[0], matches[1], matches[2], matches[3], matches[4],
                                                      matches[5], matches[6], matches[7])
        else:
            return image_url

    def cache_image(self, image_url):
        """
        Store cache of image in cache dir
        :param image_url: Source URL
        """
        path = ek(os.path.abspath, ek(os.path.join, sickbeard.CACHE_DIR, 'images', 'imdb_popular'))

        if not ek(os.path.exists, path):
            ek(os.makedirs, path)

        full_path = ek(os.path.join, path, ek(os.path.basename, image_url))

        if not ek(os.path.isfile, full_path):
            helpers.download_file(image_url, full_path, session=self.session)

        return full_path
