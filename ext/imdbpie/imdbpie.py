from __future__ import absolute_import, unicode_literals

import re
import json
import time
import random
import logging
import datetime
import warnings

import requests
from cachecontrol import CacheControl
from cachecontrol.caches import FileCache
from six.moves import html_parser
from six.moves import http_client as httplib
from six.moves.urllib.parse import urlencode, quote, quote_plus

from imdbpie.objects import Image, Title, Person, Episode, Review
from imdbpie.constants import (
    BASE_URI, SHA1_KEY, USER_AGENTS, DEFAULT_PROXY_URI
)

logger = logging.getLogger(__name__)


class Imdb(object):

    def __init__(self, api_key=None, locale=None, anonymize=False,
                 exclude_episodes=False, user_agent=None, cache=None,
                 proxy_uri=None, verify_ssl=True, session=None):
        self.api_key = api_key or SHA1_KEY
        self.timestamp = time.mktime(datetime.date.today().timetuple())
        self.user_agent = user_agent or random.choice(USER_AGENTS)
        self.locale = locale or 'en_US'
        self.exclude_episodes = exclude_episodes
        self.caching_enabled = True if cache is True else False
        self.proxy_uri = proxy_uri or DEFAULT_PROXY_URI
        self.anonymize = anonymize
        self.verify_ssl = verify_ssl
        self.session = session or requests.Session()

        if self.caching_enabled:
            warnings.warn('caching will be removed in version 5.0.0 '
                          'due to not being thread safe')
            self.session = CacheControl(
                self.session, cache=FileCache('.imdbpie_cache')
            )

    def get_person_by_id(self, imdb_id):
        self.validate_imdb_id(imdb_id)
        url = self._build_url('/name/maindetails', {'nconst': imdb_id})
        response = self._get(url)

        if response is None or self._is_redirection_result(response):
            return None

        person = Person(response["data"])
        return person

    def get_title_by_id(self, imdb_id):
        self.validate_imdb_id(imdb_id)
        url = self._build_url('/title/maindetails', {'tconst': imdb_id})
        response = self._get(url)

        if response is None or self._is_redirection_result(response):
            return None

        # get the full cast information, add key if not present
        response['data']['credits'] = self._get_credits_data(imdb_id)
        response['data']['plots'] = self.get_title_plots(imdb_id)

        if (
            self.exclude_episodes is True and
            response['data'].get('type') == 'tv_episode'
        ):
            return None

        title = Title(data=response['data'])
        return title

    def get_title_plots(self, imdb_id):
        self.validate_imdb_id(imdb_id)
        url = self._build_url('/title/plot', {'tconst': imdb_id})
        response = self._get(url)

        if response['data']['tconst'] != imdb_id:  # pragma: no cover
            return []

        plots = response['data'].get('plots', [])
        return [plot.get('text') for plot in plots]

    def title_exists(self, imdb_id):
        self.validate_imdb_id(imdb_id)
        page_url = 'http://www.imdb.com/title/{0}/'.format(imdb_id)

        if self.anonymize is True:
            page_url = self.proxy_uri.format(quote(page_url))

        response = self.session.head(page_url)

        if response.status_code == httplib.OK:
            return True
        elif response.status_code == httplib.NOT_FOUND:
            return False
        elif response.status_code == httplib.MOVED_PERMANENTLY:
            # redirection result
            return False
        else:
            response.raise_for_status()

    def search_for_person(self, name):
        query = quote(name)
        url = 'https://v2.sg.media-imdb.com/suggests/{0}/{1}.json'.format(
            query[0].lower(), query
        )
        search_results = self._get(url)
        results = []
        for result in search_results.get('d', ()):
            if not result['id'].startswith('nm'):
                # ignore non-person results
                continue
            result_item = {
                'name': result['l'],
                'imdb_id': result['id'],
            }
            results.append(result_item)
        return results

    def search_for_title(self, title):
        query = quote(title)
        url = 'https://v2.sg.media-imdb.com/suggests/{0}/{1}.json'.format(
            query[0].lower(), query
        )
        search_results = self._get(url)
        results = []
        for result in search_results.get('d', ()):
            result_item = {
                'title': result['l'],
                'year': str(result.get('y')) if result.get('y') else None,
                'imdb_id': result['id'],
                'type': result.get('q'),
            }
            results.append(result_item)
        return results

    def top_250(self):
        url = self._build_url('/chart/top', {})
        response = self._get(url)
        return response['data']['list']['list']

    def popular_shows(self):
        url = self._build_url('/chart/tv', {})
        response = self._get(url)
        return response['data']['list']

    def popular_movies(self):
        url = self._build_url('/chart/moviemeter', {})
        response = self._get(url)
        return response['data']['list']

    def get_title_images(self, imdb_id):
        self.validate_imdb_id(imdb_id)
        url = self._build_url('/title/photos', {'tconst': imdb_id})
        response = self._get(url)
        return self._get_images(response)

    def get_title_reviews(self, imdb_id, max_results=None):
        """Retrieve reviews for a title ordered by 'Best' descending"""
        self.validate_imdb_id(imdb_id)
        user_comments = self._get_reviews_data(
            imdb_id,
            max_results=max_results
        )

        if not user_comments:
            return None

        title_reviews = []

        for review_data in user_comments:
            title_reviews.append(Review(review_data))
        return title_reviews

    def get_person_images(self, imdb_id):
        self.validate_imdb_id(imdb_id)
        url = self._build_url('/name/photos', {'nconst': imdb_id})
        response = self._get(url)
        return self._get_images(response)

    def get_episodes(self, imdb_id):
        self.validate_imdb_id(imdb_id)
        if self.exclude_episodes:
            raise ValueError('exclude_episodes is currently set')

        title = self.get_title_by_id(imdb_id)
        if title.type != 'tv_series':
            raise RuntimeError('Title provided is not of type TV Series')

        url = self._build_url('/title/episodes', {'tconst': imdb_id})
        response = self._get(url)

        if response is None:
            return None

        seasons = response.get('data').get('seasons')
        episodes = []

        for season in seasons:
            season_number = season.get('token')
            for idx, episode_data in enumerate(season.get('list')):
                episode_data['series_name'] = title.title
                episode_data['episode'] = idx + 1
                episode_data['season'] = season_number
                e = Episode(episode_data)
                episodes.append(e)

        return episodes

    def _get_credits_data(self, imdb_id):
        self.validate_imdb_id(imdb_id)
        url = self._build_url('/title/fullcredits', {'tconst': imdb_id})
        response = self._get(url)

        if response is None:
            return None

        return response.get('data').get('credits')

    def _get_reviews_data(self, imdb_id, max_results=None):
        self.validate_imdb_id(imdb_id)
        params = {'tconst': imdb_id}
        if max_results:
            params['limit'] = max_results
        url = self._build_url('/title/usercomments', params)
        response = self._get(url)

        if response is None:
            return None

        return response.get('data').get('user_comments')

    def _get_images(self, response):
        images = []

        for image_data in response.get('data').get('photos', []):
            images.append(Image(image_data))

        return images

    @staticmethod
    def _cache_response(file_path, resp):
        with open(file_path, 'w+') as f:
            json.dump(resp, f)

    def _parse_dirty_json(self, data):
        match_json_within_dirty_json = r'imdb\$[\w_]+\({1}(.+)\){1}'
        data_clean = re.match(
            match_json_within_dirty_json, data, re.IGNORECASE
        ).groups()[0]
        return json.loads(data_clean)

    @staticmethod
    def validate_imdb_id(imdb_id):
        match_id = r'[a-zA-Z]{2}[0-9]{7}'
        try:
            re.match(match_id, imdb_id, re.IGNORECASE).group()
        except (AttributeError, TypeError):
            raise ValueError('invalid imdb id')

    def _get(self, url):
        resp = self.session.get(
            url,
            headers={'User-Agent': self.user_agent},
            verify=self.verify_ssl
        )

        resp.raise_for_status()
        resp_data = resp.content.decode('utf-8')
        try:
            resp_dict = json.loads(resp_data)
        except ValueError:
            resp_dict = self._parse_dirty_json(resp_data)

        if resp_dict.get('error'):
            return None

        return resp_dict

    def _build_url(self, path, params):
        default_params = {
            'api': 'v1',
            'appid': 'iphone1_1',
            'apiPolicy': 'app1_1',
            'apiKey': self.api_key,
            'locale': self.locale,
            'timestamp': self.timestamp
        }

        query_params = dict(
            list(default_params.items()) + list(params.items())
        )
        query_params = urlencode(query_params)
        url = '{base}{path}?{params}'.format(base=BASE_URI,
                                             path=path, params=query_params)

        if self.anonymize is True:
            return self.proxy_uri.format(quote(url))
        return url

    @staticmethod
    def _is_redirection_result(response):
        """
        Return True if response is that of a redirection else False
        Redirection results have no information of use.
        """
        imdb_id = response['data'].get('tconst')
        if (
            imdb_id and
            imdb_id != response['data'].get('news', {}).get('channel')
        ):
            return True
        return False
