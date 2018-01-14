# -*- coding: utf-8 -*-
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
from six import text_type
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
        logger.info('getting name {0}'.format(imdb_id))
        self.validate_imdb_id(imdb_id)
        return self._get_resource('/name/{0}/fulldetails'.format(imdb_id))

    def get_name_filmography(self, imdb_id):
        logger.info('getting name {0} filmography'.format(imdb_id))
        self.validate_imdb_id(imdb_id)
        return self._get_resource('/name/{0}/filmography'.format(imdb_id))

    def get_title(self, imdb_id):
        logger.info('getting title {0}'.format(imdb_id))
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

    def get_title_credits(self, imdb_id):
        logger.info('getting title {0} credits'.format(imdb_id))
        self.validate_imdb_id(imdb_id)
        self._redirection_title_check(imdb_id)
        return self._get_resource('/title/{0}/fullcredits'.format(imdb_id))

    def get_title_quotes(self, imdb_id):
        logger.info('getting title {0} quotes'.format(imdb_id))
        self.validate_imdb_id(imdb_id)
        self._redirection_title_check(imdb_id)
        return self._get_resource('/title/{0}/quotes'.format(imdb_id))

    def get_title_ratings(self, imdb_id):
        logger.info('getting title {0} ratings'.format(imdb_id))
        self.validate_imdb_id(imdb_id)
        self._redirection_title_check(imdb_id)
        return self._get_resource('/title/{0}/ratings'.format(imdb_id))

    def get_title_genres(self, imdb_id):
        logger.info('getting title {0} genres'.format(imdb_id))
        self.validate_imdb_id(imdb_id)
        self._redirection_title_check(imdb_id)
        return self._get_resource('/title/{0}/genres'.format(imdb_id))

    def get_title_similarities(self, imdb_id):
        logger.info('getting title {0} similarities'.format(imdb_id))
        self.validate_imdb_id(imdb_id)
        self._redirection_title_check(imdb_id)
        return self._get_resource('/title/{0}/similarities'.format(imdb_id))

    def get_title_awards(self, imdb_id):
        logger.info('getting title {0} awards'.format(imdb_id))
        self.validate_imdb_id(imdb_id)
        self._redirection_title_check(imdb_id)
        return self._get_resource('/title/{0}/awards'.format(imdb_id))

    def get_title_connections(self, imdb_id):
        logger.info('getting title {0} connections'.format(imdb_id))
        self.validate_imdb_id(imdb_id)
        self._redirection_title_check(imdb_id)
        return self._get_resource('/title/{0}/connections'.format(imdb_id))

    def get_title_releases(self, imdb_id):
        logger.info('getting title {0} releases'.format(imdb_id))
        self.validate_imdb_id(imdb_id)
        self._redirection_title_check(imdb_id)
        return self._get_resource('/title/{0}/releases'.format(imdb_id))

    def get_title_versions(self, imdb_id):
        logger.info('getting title {0} versions'.format(imdb_id))
        self.validate_imdb_id(imdb_id)
        self._redirection_title_check(imdb_id)
        return self._get_resource('/title/{0}/versions'.format(imdb_id))

    def get_title_plot(self, imdb_id):
        logger.info('getting title {0} plot'.format(imdb_id))
        self.validate_imdb_id(imdb_id)
        self._redirection_title_check(imdb_id)
        return self._get_resource('/title/{0}/plot'.format(imdb_id))

    def get_title_plot_synopsis(self, imdb_id):
        logger.info('getting title {0} plot synopsis'.format(imdb_id))
        self.validate_imdb_id(imdb_id)
        self._redirection_title_check(imdb_id)
        return self._get_resource('/title/{0}/plotsynopsis'.format(imdb_id))

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
        logger.info('searching for name {0}'.format(name))
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
        logger.info('searching for title {0}'.format(title))
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

    def get_title_images(self, imdb_id):
        logger.info('getting title {0} images'.format(imdb_id))
        self.validate_imdb_id(imdb_id)
        self._redirection_title_check(imdb_id)
        return self._get_resource('/title/{0}/images'.format(imdb_id))

    def get_title_videos(self, imdb_id):
        logger.info('getting title {0} videos'.format(imdb_id))
        self.validate_imdb_id(imdb_id)
        self._redirection_title_check(imdb_id)
        return self._get_resource('/title/{0}/videos'.format(imdb_id))

    def get_title_user_reviews(self, imdb_id):
        logger.info('getting title {0} reviews'.format(imdb_id))
        self.validate_imdb_id(imdb_id)
        self._redirection_title_check(imdb_id)
        return self._get_resource('/title/{0}/userreviews'.format(imdb_id))

    def get_title_metacritic_reviews(self, imdb_id):
        logger.info('getting title {0} metacritic reviews'.format(imdb_id))
        self.validate_imdb_id(imdb_id)
        self._redirection_title_check(imdb_id)
        return self._get_resource('/title/{0}/metacritic'.format(imdb_id))

    def get_name_images(self, imdb_id):
        logger.info('getting namne {0} images'.format(imdb_id))
        self.validate_imdb_id(imdb_id)
        return self._get_resource('/name/{0}/images'.format(imdb_id))

    def get_name_videos(self, imdb_id):
        logger.info('getting namne {0} videos'.format(imdb_id))
        self.validate_imdb_id(imdb_id)
        return self._get_resource('/name/{0}/videos'.format(imdb_id))

    def get_title_episodes(self, imdb_id):
        logger.info('getting title {0} episodes'.format(imdb_id))
        self.validate_imdb_id(imdb_id)
        if self.exclude_episodes:
            raise ValueError('exclude_episodes is current set to true')
        return self._get_resource('/title/{0}/episodes'.format(imdb_id))

    @staticmethod
    def _cache_response(file_path, resp):
        with open(file_path, 'w+') as f:
            json.dump(resp, f)

    def _parse_dirty_json(self, data, query=None):
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

    def _get(self, url, query=None):
        path = urlparse(url).path
        headers = {'Accept-Language': self.locale}
        headers.update(self.get_auth_headers(path))
        resp = self.session.get(url, headers=headers)

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
