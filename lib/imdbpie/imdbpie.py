# -*- coding: future_fstrings -*-
from __future__ import absolute_import, unicode_literals

import re
import json
import tempfile
import time
import random
import logging
import datetime
import warnings

import requests
from requests.exceptions import HTTPError
from six.moves import http_client as httplib
from six.moves.urllib.parse import (
    urlencode, quote, quote_plus, unquote, urlparse
)

from .constants import BASE_URI, HOST, SEARCH_BASE_URI
from .auth import Auth
from .exceptions import ImdbAPIError

logger = logging.getLogger(__name__)


class Imdb(Auth):

    def __init__(self, locale=None, exclude_episodes=False, session=None):
        self.locale = locale or 'en_US'
        self.exclude_episodes = exclude_episodes
        self.session = session or requests.Session()
        self._cachedir = tempfile.gettempdir()

    def get_name(self, imdb_id):
        logger.info('getting name %s', imdb_id)
        self.validate_imdb_id(imdb_id)
        return self._get_resource(f'/name/{imdb_id}/fulldetails')

    def get_title(self, imdb_id):
        logger.info('getting title %s', imdb_id)
        self.validate_imdb_id(imdb_id)
        self._redirection_title_check(imdb_id)
        try:
            resource = self._get_resource(f'/title/{imdb_id}/fulldetails')
        except LookupError:
            self._title_not_found()

        if (
            self.exclude_episodes is True and
            resource['base']['titleType'] == 'tvEpisode'
        ):
            raise LookupError(
                'Title not found. Title was an episode and '
                '"exclude_episodes" is set to true'
            )
        return resource

    def get_title_credits(self, imdb_id):
        logger.info('getting title %s credits', imdb_id)
        self.validate_imdb_id(imdb_id)
        self._redirection_title_check(imdb_id)
        return self._get_resource(f'/title/{imdb_id}/fullcredits')

    def get_title_plot(self, imdb_id):
        logger.info('getting title %s plot', imdb_id)
        self.validate_imdb_id(imdb_id)
        self._redirection_title_check(imdb_id)
        return self._get_resource(f'/title/{imdb_id}/plot')

    def title_exists(self, imdb_id):
        self.validate_imdb_id(imdb_id)
        page_url = f'http://www.imdb.com/title/{imdb_id}/'

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

    def search_for_name(self, name):
        logger.info('searching for name %s', name)
        name = re.sub(r'\W+', '_', name).strip('_')
        query = quote(name)
        first_alphanum_char = self._query_first_alpha_num(name)
        url = (
            f'{SEARCH_BASE_URI}/suggests/{first_alphanum_char}/{query}.json'
        )
        search_results = self._get(url=url, query=query)
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
        logger.info('searching for title %s', title)
        title = re.sub(r'\W+', '_', title).strip('_')
        query = quote(title)
        first_alphanum_char = self._query_first_alpha_num(title)
        url = (
            f'{SEARCH_BASE_URI}/suggests/{first_alphanum_char}/{query}.json'
        )
        search_results = self._get(url=url, query=query)
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

    def get_popular_titles(self):
        return self._get_resource('/chart/titlemeter')

    def get_popular_shows(self):
        return self._get_resource('/chart/tvmeter')

    def get_popular_movies(self):
        return self._get_resource('/chart/moviemeter')

    def get_title_images(self, imdb_id):
        logger.info('getting title %s images', imdb_id)
        self.validate_imdb_id(imdb_id)
        self._redirection_title_check(imdb_id)
        return self._get_resource(f'/title/{imdb_id}/images')

    def get_title_user_reviews(self, imdb_id):
        logger.info('getting title %s reviews', imdb_id)
        self.validate_imdb_id(imdb_id)
        self._redirection_title_check(imdb_id)
        return self._get_resource(f'/title/{imdb_id}/userreviews')

    def get_title_metacritic_reviews(self, imdb_id):
        logger.info('getting title %s metacritic reviews', imdb_id)
        self.validate_imdb_id(imdb_id)
        self._redirection_title_check(imdb_id)
        return self._get_resource(f'/title/{imdb_id}/metacritic')

    def get_name_images(self, imdb_id):
        logger.info('getting namne %s images', imdb_id)
        self.validate_imdb_id(imdb_id)
        return self._get_resource(f'/name/{imdb_id}/images')

    def get_title_episodes(self, imdb_id):
        logger.info('getting title %s episodes', imdb_id)
        self.validate_imdb_id(imdb_id)
        if self.exclude_episodes:
            raise ValueError('exclude_episodes is current set to true')
        return self._get_resource(f'/title/{imdb_id}/episodes')

    @staticmethod
    def _cache_response(file_path, resp):
        with open(file_path, 'w+') as f:
            json.dump(resp, f)

    def _parse_dirty_json(self, data, query=None):
        if query is None:
            match_json_within_dirty_json = r'imdb\$.+\({1}(.+)\){1}'
        else:
            query_match = ''.join(
                char if char.isalnum() else f'[{char}]'
                for char in unquote(query)
            )
            query_match = query_match.replace('[ ]', '.+')
            match_json_within_dirty_json = (
                r'imdb\${}\((.+)\)'.format(query_match)
            )
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

    def _get_resource(self, path):
        url = f'{BASE_URI}{path}'
        return self._get(url=url)['resource']

    def _get(self, url, query=None):
        path = urlparse(url).path
        headers = {'Accept-Language': self.locale}
        headers.update(self.get_auth_headers(path))
        resp = self.session.get(url, headers=headers)

        if not resp.ok:
            if resp.status_code == httplib.NOT_FOUND:
                raise LookupError(f'Resource {path} not found')
            else:
                raise ImdbAPIError(resp.text)
        resp_data = resp.content.decode('utf-8')
        try:
            resp_dict = json.loads(resp_data)
        except ValueError:
            resp_dict = self._parse_dirty_json(
                data=resp_data, query=query
            )

        if resp_dict.get('error'):
            return None

        return resp_dict

    def _redirection_title_check(self, imdb_id):
        if self.is_redirection_title(imdb_id):
            self._title_not_found(msg=f'{imdb_id} is a redirection imdb id')

    def is_redirection_title(self, imdb_id):
        self.validate_imdb_id(imdb_id)
        page_url = f'http://www.imdb.com/title/{imdb_id}/'
        response = self.session.head(page_url)
        if response.status_code == httplib.MOVED_PERMANENTLY:
            return True
        else:
            return False

    def _query_first_alpha_num(self, query):
        for char in query.lower():
            if char.isalnum():
                return char
        raise ValueError(
            'invalid query, does not contain any alphanumeric characters'
        )

    def _title_not_found(self, msg=''):
        if msg:
            msg = f' {msg}'
        raise LookupError(f'Title not found.{msg}')
