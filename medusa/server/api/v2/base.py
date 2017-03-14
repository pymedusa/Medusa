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

    #: resource name
    name = None
    #: identifier
    identifier = None
    #: path param
    path_param = None
    #: allowed HTTP methods
    allowed_methods = ('OPTIONS', )
    #: parent resource handler
    parent_handler = None

    def __init__(self, application, request, **kwargs):
        super(BaseRequestHandler, self).__init__(application, request, **kwargs)

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
                        self._unauthorized('Token has expired.')
                    except jwt.DecodeError:
                        self._unauthorized('Invalid token.')
                if self.request.headers.get('Authorization').startswith('Basic'):
                    auth_decoded = base64.decodestring(self.request.headers.get('Authorization')[6:])
                    username, password = auth_decoded.split(':', 2)
                    if username != app.WEB_USERNAME or password != app.WEB_PASSWORD:
                        self._unauthorized('Invalid user/pass.')

            if self.get_argument('api_key', default='') and self.get_argument('api_key', default='') == app.API_KEY:
                api_key = self.get_argument('api_key', default='')
            if self.request.headers.get('X-Api-Key') and self.request.headers.get('X-Api-Key') == app.API_KEY:
                api_key = self.request.headers.get('X-Api-Key')
            if token == '' and api_key == '':
                self._unauthorized('Invalid token or API key.')

    def write_error(self, *args, **kwargs):
        """Only send traceback if app.DEVELOPER is true."""
        if app.DEVELOPER and 'exc_info' in kwargs:
            self.set_header('content-type', 'text/plain')
            self.set_status(500)
            for line in traceback.format_exception(*kwargs["exc_info"]):
                self.write(line)
            self.finish()
        else:
            self._internal_server_error()

    def options(self, *args, **kwargs):
        """Options."""
        self._no_content()

    def set_default_headers(self):
        """Set default CORS headers."""
        if app.APP_VERSION:
            self.set_header('X-Medusa-Server', app.APP_VERSION)
        self.set_header('Access-Control-Allow-Origin', '*')
        self.set_header('Access-Control-Allow-Headers', 'Origin, Accept, Authorization, Content-Type,'
                                                        'X-Requested-With, X-CSRF-Token, X-Api-Key, X-Medusa-Server')
        self.set_header('Access-Control-Allow-Methods', ', '.join(self.allowed_methods))

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

    @classmethod
    def _create_base_url(cls, prefix_url, resource_name, *args):
        elements = [prefix_url, resource_name] + \
                   [r'(?P<{key}>{value})'.format(key=key, value=value) for (key, value) in args]
        return '/'.join(elements)

    @classmethod
    def _create_url(cls, prefix_url, resource_name, *args):
        resource_url = prefix_url + '/' + resource_name
        path_params = ''

        for arg in args:
            if not arg:
                continue

            key, value = arg
            q = r'(?:/(?P<{key}>{value}))'.format(key=key, value=value)
            if path_params:
                path_params = r'(?:{previous}(?:{current}|/?))'.format(previous=path_params, current=q)
            else:
                path_params = q

            path_params = r'(?:{path}|/?)'.format(path=path_params)

        return resource_url + path_params + '/?$'

    @classmethod
    def create_app_handler(cls, base):
        if cls.parent_handler:
            base = cls._create_base_url(base, cls.parent_handler.name, cls.parent_handler.identifier)

        return cls._create_url(base, cls.name, *(cls.identifier, cls.path_param)), cls

    def _ok(self, data=None, headers=None, stream=None):
        self.api_finish(200, data=data, headers=headers, stream=stream)

    def _created(self):
        self.api_finish(201)

    def _accepted(self):
        self.api_finish(202)

    def _no_content(self):
        self.api_finish(204)

    def _bad_request(self, error):
        self.api_finish(400, error=error)

    def _unauthorized(self, error):
        self.api_finish(401, error=error)

    def _not_found(self, error='Resource not found'):
        self.api_finish(404, error=error)

    def _method_not_allowed(self, error):
        self.api_finish(405, error=error)

    def _conflict(self, error):
        self.api_finish(409, error=error)

    def _internal_server_error(self, error='Internal Server Error'):
        self.api_finish(500, error=error)

    def _not_implemented(self):
        self.api_finish(501)

    def _get_sort(self, default):
        return self.get_argument('sort', default=default)

    def _get_sort_order(self, default='asc'):
        return self.get_argument('sort_order', default=default).lower()

    def _get_page(self):
        return max(1, int(self.get_argument('page', default=1)))

    def _get_limit(self, default=20, maximum=1000):
        return min(max(1, int(self.get_argument('limit', default=default))), maximum)

    def _paginate(self, data=None, data_generator=None, sort=None):
        arg_page = self._get_page()
        arg_limit = self._get_limit()

        headers = {
            'X-Pagination-Page': arg_page,
            'X-Pagination-Limit': arg_limit
        }

        results = []
        if data_generator:
            results = data_generator()
        elif sort:
            arg_sort = self._get_sort(default=sort)
            arg_sort_order = self._get_sort_order()
            start = (arg_page - 1) * arg_limit
            end = start + arg_limit
            results = sorted(data, key=operator.itemgetter(arg_sort), reverse=arg_sort_order == 'desc')
            results = results[start:end]
            headers['X-Pagination-Count'] = len(results)

        return self._ok(data=results, headers=headers)

    @classmethod
    def _parse(cls, value, function=int):
        """Parse value using the specified function.

        :param value:
        :param function:
        :type function: callable
        :return:
        """
        if value is not None:
            return function(value)

    @classmethod
    def _parse_boolean(cls, value):
        """Parse value using the specified function.

        :param value:
        :return:
        """
        if isinstance(value, text_type):
            return value.lower() == 'true'

        return cls._parse(value, bool)

    @classmethod
    def _parse_date(cls, value, fmt='%Y-%m-%d'):
        """Parse a date value using the specified format.

        :param value:
        :param fmt:
        :return:
        """
        return cls._parse(value, lambda d: datetime.strptime(d, fmt))


class NotFoundHandler(BaseRequestHandler):
    """A class used for the API v2 404 page."""

    def get(self, *args, **kwargs):
        """Get."""
        self.api_finish(status=404)

    @classmethod
    def create_app_handler(cls, base):
        """Capture everything."""
        return r'{base}(/?.*)'.format(base=base), cls


def json_string_encoder(o):
    """Convert properties to string."""
    if isinstance(o, Language):
        return getattr(o, 'name')

    return text_type(o)
