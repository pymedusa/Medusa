# coding=utf-8
import os
import posixpath
import re

from datetime import date

from bs4 import BeautifulSoup

import sickbeard
from sickbeard import helpers

from sickrage.helper.encoding import ek


class imdbPopular(object):
    def __init__(self):
        """Get a list of most popular TV series from imdb."""
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

        data = helpers.getURL(self.url, session=self.session, params=self.params,
                              headers={'Referer': 'http://akas.imdb.com/'}, returns='text')
        if not data:
            return None

        soup = BeautifulSoup(data, 'html5lib')
        results = soup.find('div', class_='lister-list')
        rows = results.find_all('div', class_='lister-item mode-advanced')

        for row in rows:
            show = {}

            image_div = row.find('div', class_='lister-item-image float-left')
            if image_div:
                image = image_div.find('img')
                show['image_url_large'] = image['loadlate'].replace('67_CR0,0,67,98', '186_CR0,0,186,273')
                show['image_path'] = ek(posixpath.join, 'images', 'imdb_popular', ek(os.path.basename,
                                                                                     show['image_url_large']))
                self.cache_image(show['image_url_large'])

            content_div = row.find('div', class_='lister-item-content')
            if content_div:
                show_info = content_div.find('a')
                show['name'] = show_info.get_text()
                show['imdb_url'] = 'http://www.imdb.com' + show_info['href']
                show['imdb_tt'] = show['imdb_url'][-25:][0:9]
                show['year'] = content_div.find('span', class_='lister-item-year text-muted unbold').get_text()[1:5]

                rating_div = content_div.find('div', class_='ratings-bar')
                if rating_div:
                    show['rating'] = rating_div.find('strong').get_text()

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
        match = re.search("^(.*)V1._(.{2})(.*?)_(.{2})(.*?),(.*?),(.*?),(.*?)_.jpg$", image_url)

        if match:
            matches = match.groups()
            ek(os.path.basename, image_url)
            matches = list(matches)
            matches[2] = int(matches[2]) * factor
            matches[4] = int(matches[4]) * factor
            matches[5] = int(matches[5]) * factor
            matches[6] = int(matches[6]) * factor
            matches[7] = int(matches[7]) * factor

            return "%sV1._%s%s_%s%s,%s,%s,%s_.jpg" % (matches[0], matches[1], matches[2], matches[3], matches[4],
                                                      matches[5], matches[6], matches[7])
        else:
            return image_url

    def cache_image(self, image_url):
        """
        Store cache of image in cache dir.

        :param image_url: Source URL
        """
        path = ek(os.path.abspath, ek(os.path.join, sickbeard.CACHE_DIR, 'images', 'imdb_popular'))

        if not ek(os.path.exists, path):
            ek(os.makedirs, path)

        full_path = ek(os.path.join, path, ek(os.path.basename, image_url))

        if not ek(os.path.isfile, full_path):
            helpers.download_file(image_url, full_path, session=self.session)

imdb_popular = imdbPopular()
