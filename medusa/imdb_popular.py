# coding=utf-8
import os
import posixpath
import re
from datetime import date

from bs4 import BeautifulSoup
from . import app, helpers


class ImdbPopular(object):
    """This class contains everything for the IMDB popular page."""

    def __init__(self):
        """Constructor for ImdbPopular."""
        # Use akas.imdb.com, just like the imdb lib.
        self.url = 'http://akas.imdb.com/search/title'

        self.params = {
            'at': 0,
            'sort': 'moviemeter',
            'title_type': 'tv_series',
            'year': '%s,%s' % (date.today().year - 1, date.today().year + 1),
        }

        self.session = helpers.make_session()

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
                show['image_path'] = posixpath.join('images', 'imdb_popular', os.path.basename(show['image_url_large']))
                self.cache_image(show['image_url_large'])

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

        return popular_shows

    @staticmethod
    def change_size(image_url, factor=3):
        """
        Change the size of the image we get from IMDB.

        :param: image_url: Image source URL
        :param: factor: Multiplier for the image size
        """
        match = re.search('(.+[X|Y])(\d+)(_CR\d+,\d+,)(\d+),(\d+)', image_url)

        if match:
            matches = list(match.groups())
            matches[1] = int(matches[1]) * factor
            matches[3] = int(matches[3]) * factor
            matches[4] = int(matches[4]) * factor

            return '{0}{1}{2}{3},{4}_AL_.jpg'.format(matches[0], matches[1], matches[2],
                                                     matches[3], matches[4])
        else:
            return image_url

    def cache_image(self, image_url):
        """
        Store cache of image in cache dir.

        :param image_url: Image source URL
        """
        path = os.path.abspath(os.path.join(app.CACHE_DIR, 'images', 'imdb_popular'))

        if not os.path.exists(path):
            os.makedirs(path)

        full_path = os.path.join(path, os.path.basename(image_url))

        if not os.path.isfile(full_path):
            helpers.download_file(image_url, full_path, session=self.session)


imdb_popular = ImdbPopular()
