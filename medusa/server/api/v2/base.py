# coding=utf-8
"""Base module for request handlers."""

import base64
import json

from datetime import datetime
from babelfish.language import Language

import medusa as app
from six import text_type

from tornado.web import RequestHandler


class BaseRequestHandler(RequestHandler):
    """A base class used for shared RequestHandler methods."""

    def prepare(self):
        """Prepare request headers with authorization keys."""
        web_username = app.WEB_USERNAME
        web_password = app.WEB_PASSWORD
        api_key = self.get_argument('api_key', default='')
        api_username = ''
        api_password = ''

        if self.request.headers.get('Authorization'):
            auth_header = self.request.headers.get('Authorization')
            auth_decoded = base64.decodestring(auth_header[6:])
            api_username, api_password = auth_decoded.split(':', 2)

        if (web_username != api_username and web_password != api_password) and (app.API_KEY != api_key):
            self.api_finish(status=401, error='Invalid API key')

    def api_finish(self, status=None, error=None, data=None, headers=None, **kwargs):
        """End the api request writing error or data to http response."""
        if headers is not None:
            for header in headers:
                self.set_header(header, headers[header])
        if error is not None and status is not None:
            self.set_status(status)
            self.finish({
                'error': error
            })
        else:
            self.set_status(200)
            self.finish(StringEncoder().encode(data) if data is not None else kwargs)

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
    def _parse_date(value, fmt='%Y-%m-%d'):
        """Parse a date value using the specified format.

        :param value:
        :param fmt:
        :return:
        """
        return BaseRequestHandler._parse(value, lambda d: datetime.strptime(d, fmt))


class StringEncoder(json.JSONEncoder):
    """String json encoder."""

    def default(self, o):
        """Convert properties to string."""
        if isinstance(o, Language):
            return getattr(o, 'name')

        return text_type(o)
