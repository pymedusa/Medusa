# coding=utf-8
"""Base module for request handlers."""
from __future__ import division
from __future__ import unicode_literals

import base64
import collections
import json
import logging
import operator
import traceback
from builtins import object
from datetime import date, datetime

from babelfish.language import Language

import jwt

from medusa import app

from six import string_types, text_type, viewitems

from tornado.httpclient import HTTPError
from tornado.httputil import url_concat
from tornado.web import RequestHandler

log = logging.getLogger(__name__)


class BaseRequestHandler(RequestHandler):
    """A base class used for shared RequestHandler methods."""

    DEFAULT_ALLOWED_METHODS = ('OPTIONS', )

    #: resource name
    name = None
    #: identifier
    identifier = None
    #: path param
    path_param = None
    #: allowed HTTP methods
    allowed_methods = None
    #: parent resource handler
    parent_handler = None

    def prepare(self):
        """Check if JWT or API key is provided and valid."""
        if self.request.method == 'OPTIONS':
            return

        api_key = self.get_argument('api_key', default=None) or self.request.headers.get('X-Api-Key')
        if api_key and api_key == app.API_KEY:
            return

        authorization = self.request.headers.get('Authorization')
        if not authorization:
            return self._unauthorized('No authorization token.')

        if authorization.startswith('Bearer'):
            try:
                token = authorization.replace('Bearer ', '')
                jwt.decode(token, app.ENCRYPTION_SECRET, algorithms=['HS256'])
            except jwt.ExpiredSignatureError:
                return self._unauthorized('Token has expired.')
            except jwt.DecodeError:
                return self._unauthorized('Invalid token.')
        elif authorization.startswith('Basic'):
            auth_decoded = base64.decodestring(authorization[6:])
            username, password = auth_decoded.split(':', 2)
            if username != app.WEB_USERNAME or password != app.WEB_PASSWORD:
                return self._unauthorized('Invalid user/pass.')
        else:
            return self._unauthorized('Invalid token.')

    def write_error(self, *args, **kwargs):
        """Only send traceback if app.DEVELOPER is true."""
        if app.DEVELOPER and 'exc_info' in kwargs:
            self.set_header('content-type', 'text/plain')
            self.set_status(500)
            for line in traceback.format_exception(*kwargs['exc_info']):
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
        self.set_header('Access-Control-Allow-Methods', ', '.join(self.DEFAULT_ALLOWED_METHODS + self.allowed_methods))

    def api_finish(self, status=None, error=None, data=None, headers=None, stream=None, content_type=None, **kwargs):
        """End the api request writing error or data to http response."""
        content_type = content_type or 'application/json; charset=UTF-8'
        if headers is not None:
            for header in headers:
                self.set_header(header, headers[header])
        if error is not None and status is not None:
            self.set_status(status)
            self.set_header('content-type', content_type)
            self.finish({
                'error': error
            })
        else:
            self.set_status(status or 200)
            if data is not None:
                self.set_header('content-type', content_type)
                self.finish(json.JSONEncoder(default=json_default_encoder).encode(data))
            elif stream:
                # This is mainly for assets
                self.set_header('content-type', content_type)
                self.finish(stream)
            elif kwargs and 'chunk' in kwargs:
                self.set_header('content-type', content_type)
                self.finish(kwargs)

    @classmethod
    def _create_base_url(cls, prefix_url, resource_name, *args):
        elements = [prefix_url, resource_name] + \
                   [r'(?P<{key}>{value})'.format(key=key, value=value) for (key, value) in args]
        return '/'.join(elements)

    @classmethod
    def create_url(cls, prefix_url, resource_name, *args):
        """Create url base on resource name and path params."""
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
        """Create app handler tuple: regex, class."""
        if cls.parent_handler:
            base = cls._create_base_url(base, cls.parent_handler.name, cls.parent_handler.identifier)

        return cls.create_url(base, cls.name, *(cls.identifier, cls.path_param)), cls

    def _handle_request_exception(self, e):
        if isinstance(e, HTTPError):
            self.api_finish(e.code, e.message)
        else:
            super(BaseRequestHandler, self)._handle_request_exception(e)

    def _ok(self, data=None, headers=None, stream=None, content_type=None):
        self.api_finish(200, data=data, headers=headers, stream=stream, content_type=content_type)

    def _created(self, data=None, identifier=None):
        if identifier is not None:
            location = self.request.path
            if not location.endswith('/'):
                location += '/'

            self.set_header('Location', '{0}{1}'.format(location, identifier))
        self.api_finish(201, data=data)

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

    @classmethod
    def _raise_bad_request_error(cls, error):
        raise HTTPError(400, error)

    def _get_sort(self, default):
        values = self.get_argument('sort', default=default)
        if values:
            results = []
            for value in values.split(','):
                reverse = value.startswith('-')
                if reverse or value.startswith('+'):
                    value = value[1:]

                results.append((value, reverse))

            return results

    def _get_page(self):
        try:
            page = int(self.get_argument('page', default=1))
            if page < 1:
                self._raise_bad_request_error('Invalid page parameter')

            return page
        except ValueError:
            self._raise_bad_request_error('Invalid page parameter')

    def _get_limit(self, default=20, maximum=1000):
        try:
            limit = self._parse(self.get_argument('limit', default=default))
            if limit < 1 or limit > maximum:
                self._raise_bad_request_error('Invalid limit parameter')

            return limit
        except ValueError:
            self._raise_bad_request_error('Invalid limit parameter')

    def _paginate(self, data=None, data_generator=None, sort=None):
        arg_page = self._get_page()
        arg_limit = self._get_limit()

        headers = {
            'X-Pagination-Page': arg_page,
            'X-Pagination-Limit': arg_limit
        }

        first_page = arg_page if arg_page > 0 else 1
        previous_page = None if arg_page <= 1 else arg_page - 1
        if data_generator:
            results = list(data_generator())[:arg_limit]
            next_page = None if len(results) < arg_limit else arg_page + 1
            last_page = None
        else:
            arg_sort = self._get_sort(default=sort)
            start = (arg_page - 1) * arg_limit
            end = start + arg_limit
            results = data
            if arg_sort:
                try:
                    for field, reverse in reversed(arg_sort):
                        results = sorted(results, key=operator.itemgetter(field), reverse=reverse)
                except KeyError:
                    return self._bad_request('Invalid sort query parameter')

            count = len(results)
            headers['X-Pagination-Count'] = count
            results = results[start:end]
            next_page = None if end > count else arg_page + 1
            last_page = ((count - 1) // arg_limit) + 1
            if last_page <= arg_page:
                last_page = None

        # Reconstruct the query parameters
        query_params = []
        for arg, values in viewitems(self.request.query_arguments):
            if arg in ('page', 'limit'):
                continue
            if not isinstance(values, list):
                values = [values]
            query_params += [(arg, value) for value in values]

        bare_uri = url_concat(self.request.path, query_params)

        links = []
        for rel, page in (('next', next_page), ('last', last_page),
                          ('first', first_page), ('previous', previous_page)):
            if page is None:
                continue

            uri = url_concat(bare_uri, dict(page=page, limit=arg_limit))
            link = '<{uri}>; rel="{rel}"'.format(uri=uri, rel=rel)
            links.append(link)

        self.set_header('Link', ', '.join(links))

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
            try:
                return function(value)
            except ValueError:
                cls._raise_bad_request_error('Invalid value {value!r}'.format(value=value))

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


def json_default_encoder(o):
    """Convert properties to string."""
    if isinstance(o, Language):
        return getattr(o, 'name')

    if isinstance(o, set):
        return list(o)

    if isinstance(o, date):
        return o.isoformat()

    return text_type(o)


def iter_nested_items(data, prefix=''):
    """Iterate through the dictionary.

    Nested keys are separated with dots.
    """
    for key, value in viewitems(data):
        p = prefix + key
        if isinstance(value, collections.Mapping):
            for inner_key, inner_value in iter_nested_items(value, prefix=p + '.'):
                yield inner_key, inner_value
        else:
            yield p, value


def set_nested_value(data, key, value):
    """Set nested value to the dictionary."""
    keys = key.split('.')
    for k in keys[:-1]:
        data = data.setdefault(k, {})

    data[keys[-1]] = value


class PatchField(object):
    """Represent a field to be patched."""

    def __init__(self, target, attr, attr_type, validator=None, converter=None,
                 default_value=None, setter=None, post_processor=None):
        """Constructor."""
        if not hasattr(target, attr):
            raise ValueError('{0!r} has no attribute {1}'.format(target, attr))

        self.target = target
        self.attr = attr
        self.attr_type = attr_type
        self.validator = validator or (lambda v: isinstance(v, self.attr_type))
        self.converter = converter or (lambda v: v)
        self.default_value = default_value
        self.setter = setter
        self.post_processor = post_processor

    def patch(self, target, value):
        """Patch the field with the specified value."""
        valid = self.validator(value)

        if not valid and self.default_value is not None:
            value = self.default_value
            valid = True

        if valid:
            try:
                if self.setter:
                    self.setter(target, self.attr, self.converter(value))
                else:
                    setattr(target, self.attr, self.converter(value))
            except AttributeError:
                log.warning(
                    'Error trying to change attribute %s on target %s, you sure'
                    ' you are allowed to change this attribute?',
                    self.attr,
                    target
                )
                return False

            if self.post_processor:
                self.post_processor(value)
            return True


class StringField(PatchField):
    """Patch string fields."""

    def __init__(self, target, attr, validator=None, converter=None, default_value=None,
                 setter=None, post_processor=None):
        """Constructor."""
        super(StringField, self).__init__(target, attr, string_types, validator=validator, converter=converter,
                                          default_value=default_value, setter=setter, post_processor=post_processor)


class IntegerField(PatchField):
    """Patch integer fields."""

    def __init__(self, target, attr, validator=None, converter=None, default_value=None,
                 setter=None, post_processor=None):
        """Constructor."""
        super(IntegerField, self).__init__(target, attr, int, validator=validator, converter=converter,
                                           default_value=default_value, setter=setter, post_processor=post_processor)


class ListField(PatchField):
    """Patch list fields."""

    def __init__(self, target, attr, validator=None, converter=None, default_value=None,
                 setter=None, post_processor=None):
        """Constructor."""
        super(ListField, self).__init__(target, attr, list, validator=validator, converter=converter,
                                        default_value=default_value, setter=setter, post_processor=post_processor)


class BooleanField(PatchField):
    """Patch boolean fields."""

    def __init__(self, target, attr, validator=None, converter=int, default_value=None,
                 setter=None, post_processor=None):
        """Constructor."""
        super(BooleanField, self).__init__(target, attr, bool, validator=validator, converter=converter,
                                           default_value=default_value, setter=setter, post_processor=post_processor)


class EnumField(PatchField):
    """Patch enumeration fields."""

    def __init__(self, target, attr, enums, attr_type=text_type, converter=None,
                 default_value=None, setter=None, post_processor=None):
        """Constructor."""
        super(EnumField, self).__init__(target, attr, attr_type, validator=lambda v: v in enums,
                                        converter=converter, default_value=default_value,
                                        setter=setter, post_processor=post_processor)
