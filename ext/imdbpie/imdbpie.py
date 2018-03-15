# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import re
import json
import tempfile
import logging

import requests
from six import text_type
from six.moves import http_client as httplib
from six.moves.urllib.parse import (
    urlencode, urljoin, quote, unquote, urlparse
)

from .constants import BASE_URI, SEARCH_BASE_URI
from .auth import Auth
from .exceptions import ImdbAPIError

logger = logging.getLogger(__name__)


# client method name -> api path
_SIMPLE_GET_ENDPOINTS = {
    'get_name_images': '/name/{imdb_id}/images',
    'get_name_videos': '/name/{imdb_id}/videos',
    'get_title_metacritic_reviews': '/title/{imdb_id}/metacritic',
    'get_title_user_reviews': '/title/{imdb_id}/userreviews',
    'get_title_videos': '/title/{imdb_id}/videos',
    'get_title_images': '/title/{imdb_id}/images',
    'get_title_companies': '/title/{imdb_id}/companies',
    'get_title_technical': '/title/{imdb_id}/technical',
    'get_title_trivia': '/title/{imdb_id}/trivia',
    'get_title_goofs': '/title/{imdb_id}/goofs',
    'get_title_soundtracks': '/title/{imdb_id}/soundtracks',
    'get_title_news': '/title/{imdb_id}/news',
    'get_title_plot': '/title/{imdb_id}/plot',
    'get_title_plot_synopsis': '/title/{imdb_id}/plotsynopsis',
    'get_title_plot_taglines': '/title/{imdb_id}/taglines',
    'get_title_versions': '/title/{imdb_id}/versions',
    'get_title_releases': '/title/{imdb_id}/releases',
    'get_title_quotes': '/title/{imdb_id}/quotes',
    'get_title_connections': '/title/{imdb_id}/connections',
    'get_title_genres': '/title/{imdb_id}/genres',
    'get_title_similarities': '/title/{imdb_id}/similarities',
    'get_title_awards': '/title/{imdb_id}/awards',
    'get_title_ratings': '/title/{imdb_id}/ratings',
    'get_title_credits': '/title/{imdb_id}/fullcredits',
    'get_name': '/name/{imdb_id}/fulldetails',
    'get_name_filmography': '/name/{imdb_id}/filmography',
}


class Imdb(Auth):

    def __init__(self, locale=None, exclude_episodes=False, session=None):
        self.locale = locale or 'en_US'
        self.exclude_episodes = exclude_episodes
        self.session = session or requests.Session()
        self._cachedir = tempfile.gettempdir()

    def __getattr__(self, method_name):
        if method_name not in _SIMPLE_GET_ENDPOINTS:
            return super(Imdb).__getattr__(method_name)
        return self._simple_get_method(
            method=method_name, path=_SIMPLE_GET_ENDPOINTS[method_name]
        )

    def get_title(self, imdb_id):
        logger.info('called get_title %s', imdb_id)
        self.validate_imdb_id(imdb_id)
        self._redirection_title_check(imdb_id)
        try:
            resource = self._get_resource(
                '/title/{0}/auxiliary'.format(imdb_id)
            )
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

    def _simple_get_method(self, method, path):
        """Return client method generated from ``_SIMPLE_GET_ENDPOINTS``."""
        def get(imdb_id):
            logger.info('called %s %s', method, imdb_id)
            self.validate_imdb_id(imdb_id)
            self._redirection_title_check(imdb_id)
            return self._get_resource(path.format(imdb_id=imdb_id))
        return get

    def title_exists(self, imdb_id):
        self.validate_imdb_id(imdb_id)
        page_url = 'http://www.imdb.com/title/{0}/'.format(imdb_id)

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
        logger.info('called search_for_name %s', name)
        name = re.sub(r'\W+', '_', name).strip('_')
        query = quote(name)
        first_alphanum_char = self._query_first_alpha_num(name)
        url = (
            '{0}/suggests/{1}/{2}.json'.format(SEARCH_BASE_URI,
                                               first_alphanum_char, query)
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
        logger.info('called search_for_title %s', title)
        title = re.sub(r'\W+', '_', title).strip('_')
        query = quote(title)
        first_alphanum_char = self._query_first_alpha_num(title)
        url = (
            '{0}/suggests/{1}/{2}.json'.format(SEARCH_BASE_URI,
                                               first_alphanum_char, query)
        )
        search_results = self._get(url=url, query=query)
        results = []
        for result in search_results.get('d', ()):
            result_item = {
                'title': result['l'],
                'year': text_type(result['y']) if result.get('y') else None,
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

    def get_title_episodes(self, imdb_id):
        logger.info('called get_title_episodes %s', imdb_id)
        self.validate_imdb_id(imdb_id)
        if self.exclude_episodes:
            raise ValueError('exclude_episodes is current set to true')
        return self._get_resource('/title/{0}/episodes'.format(imdb_id))

    def get_title_episodes_detailed(
        self, imdb_id, season, limit=500, region=None, offset=0
    ):
        """
        Request detailed information for a tv series, for a specific season.

        :param imdb_id: The imdb id including the TT prefix.
        :param limit: Limit the amound of episodes returned for a season.
        :param region: Two capital letter region code in ISO 3166-1 alpha-2.
        :param season: The season you want the detailed information for.
        :param offset: Offset episode results by this value.
        """
        logger.info('called get_title_episodes_detailed %s', imdb_id)
        self.validate_imdb_id(imdb_id)
        if season < 1:
            raise ValueError('season must be greater than zero')
        params = {
            'end': limit,
            'start': offset,
            'season': season - 1,  # api seasons are zero indexed
            'tconst': imdb_id,
        }
        if region:
            params.update({'region': region})

        return self._get(urljoin(
            BASE_URI, '/template/imdb-ios-writable/tv-episodes-v2.jstl/render'
        ), params=params)

    @staticmethod
    def _parse_dirty_json(data, query=None):
        if query is None:
            match_json_within_dirty_json = r'imdb\$.+\({1}(.+)\){1}'
        else:
            query_match = ''.join(
                char if char.isalnum() else '[{0}]'.format(char)
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
        url = '{0}{1}'.format(BASE_URI, path)
        return self._get(url=url)['resource']

    def _get(self, url, query=None, params=None):
        path = urlparse(url).path
        if params:
            path += '?' + urlencode(params)
        headers = {'Accept-Language': self.locale}
        headers.update(self.get_auth_headers(path))
        resp = self.session.get(url, headers=headers, params=params)

        if not resp.ok:
            if resp.status_code == httplib.NOT_FOUND:
                raise LookupError('Resource {0} not found'.format(path))
            else:
                msg = '{0} {1}'.format(resp.status_code, resp.text)
                raise ImdbAPIError(msg)
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
            self._title_not_found(
                msg='{0} is a redirection imdb id'.format(imdb_id)
            )

    def is_redirection_title(self, imdb_id):
        self.validate_imdb_id(imdb_id)
        page_url = 'http://www.imdb.com/title/{0}/'.format(imdb_id)
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
            msg = ' {0}'.format(msg)
        raise LookupError('Title not found.{0}'.format(msg))
