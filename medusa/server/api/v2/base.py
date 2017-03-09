# coding=utf-8
"""Base module for request handlers."""

import base64
import json
import operator
import traceback

from datetime import datetime
from babelfish.language import Language
import jwt
from six import text_type
from tornado.web import RequestHandler

from .... import app


class BaseRequestHandler(RequestHandler):
    """A base class used for shared RequestHandler methods."""

    def prepare(self):
        """Check if JWT or API key is provided and valid."""
        if self.request.method != 'OPTIONS':
            token = ''
            api_key = ''
            if self.request.headers.get('Authorization'):
                if self.request.headers.get('Authorization').startswith('Bearer'):
                    try:
                        token = jwt.decode(self.request.headers.get('Authorization').replace('Bearer ', ''), app.ENCRYPTION_SECRET, algorithms=['HS256'])
                    except jwt.ExpiredSignatureError:
                        self.api_finish(status=401, error='Token has expired.')
                    except jwt.DecodeError:
                        self.api_finish(status=401, error='Invalid token.')
                if self.request.headers.get('Authorization').startswith('Basic'):
                    auth_decoded = base64.decodestring(self.request.headers.get('Authorization')[6:])
                    username, password = auth_decoded.split(':', 2)
                    if username != app.WEB_USERNAME or password != app.WEB_PASSWORD:
                        self.api_finish(status=401, error='Invalid user/pass.')

            if self.get_argument('api_key', default='') and self.get_argument('api_key', default='') == app.API_KEY:
                api_key = self.get_argument('api_key', default='')
            if self.request.headers.get('X-Api-Key') and self.request.headers.get('X-Api-Key') == app.API_KEY:
                api_key = self.request.headers.get('X-Api-Key')
            if token == '' and api_key == '':
                self.api_finish(status=401, error='Invalid token or API key.')

    def write_error(self, *args, **kwargs):
        """Only send traceback if app.DEVELOPER is true."""
        if app.DEVELOPER and 'exc_info' in kwargs:
            self.set_header('content-type', 'text/plain')
            for line in traceback.format_exception(*kwargs["exc_info"]):
                self.write(line)
            self.finish()
        else:
            self.api_finish(status=500, error='Internal Server Error')

    def options(self, *args, **kwargs):
        """Options."""
        self.set_status(204)
        self.finish()

    def set_default_headers(self):
        """Set default CORS headers."""
        self.set_header('Access-Control-Allow-Origin', '*')
        self.set_header('Access-Control-Allow-Headers', 'Origin, Accept, Authorization, Content-Type,'
                                                        'X-Requested-With, X-CSRF-Token, X-Api-Key, X-Medusa-Server')
        self.set_header('Access-Control-Allow-Methods', 'GET, OPTIONS')

    def api_finish(self, status=None, error=None, data=None, headers=None, stream=None, **kwargs):
        """End the api request writing error or data to http response."""
        if headers is not None:
            for header in headers:
                self.set_header(header, headers[header])
        if error is not None and status is not None:
            self.set_header('content-type', 'application/json')
            self.set_status(status)
            self.finish({
                'error': error
            })
        else:
            self.set_status(status or 200)
            if data is not None:
                self.set_header('content-type', 'application/json')
                self.finish(json.JSONEncoder(default=json_string_encoder).encode(data))
            elif stream:
                # This is mainly for assets
                self.finish(stream)
            elif kwargs:
                self.finish(kwargs)

    def _get_sort(self, default):
        return self.get_argument('sort', default=default)

    def _get_sort_order(self, default='asc'):
        return self.get_argument('sort_order', default=default).lower()

    def _get_page(self):
        return max(1, int(self.get_argument('page', default=1)))

    def _get_limit(self, default=20, maximum=1000):
        return min(max(1, int(self.get_argument('limit', default=default))), maximum)

    def _paginate(self, data, sort_property):
        arg_sort = self._get_sort(default=sort_property)
        arg_sort_order = self._get_sort_order()
        arg_page = self._get_page()
        arg_limit = self._get_limit()

        results = sorted(data, key=operator.itemgetter(arg_sort), reverse=arg_sort_order == 'desc')
        count = len(results)
        start = (arg_page - 1) * arg_limit
        end = start + arg_limit
        results = results[start:end]
        headers = {
            'X-Pagination-Count': count,
            'X-Pagination-Page': arg_page,
            'X-Pagination-Limit': arg_limit
        }

        return self.api_finish(data=results, headers=headers)

    @staticmethod
    def _parse(value, function=int):
        """Parse value using the specified function.

        :param value:
        :param function:
        :type function: callable
        :return:
        """
        if value is not None:
            return function(value)

    @staticmethod
    def _parse_boolean(value):
        """Parse value using the specified function.

        :param value:
        :return:
        """
        if isinstance(value, text_type):
            return value.lower() == 'true'

        return bool(value)

    @staticmethod
    def _parse_date(value, fmt='%Y-%m-%d'):
        """Parse a date value using the specified format.

        :param value:
        :param fmt:
        :return:
        """
        return BaseRequestHandler._parse(value, lambda d: datetime.strptime(d, fmt))


class NotFoundHandler(BaseRequestHandler):
    """A class used for the API v2 404 page."""

    def get(self, *args, **kwargs):
        """Get."""
        self.api_finish(status=404)


def json_string_encoder(o):
    """Convert properties to string."""
    if isinstance(o, Language):
        return getattr(o, 'name')

    return text_type(o)
