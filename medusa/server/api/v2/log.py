# coding=utf-8
"""Request handler for logs."""
from __future__ import unicode_literals

import json
import logging

from medusa.logger import LOGGING_LEVELS, filter_logline, read_loglines
from medusa.logger.adapters.style import BraceAdapter
from medusa.server.api.v2.base import BaseRequestHandler


log = BraceAdapter(logging.getLogger(__name__))


class LogHandler(BaseRequestHandler):
    """Log request handler."""

    #: resource name
    name = 'log'
    #: identifier
    identifier = None
    #: allowed HTTP methods
    allowed_methods = ('GET', 'POST', )

    def get(self):
        """Query logs."""
        log_level = self.get_argument('level', 'INFO').upper()
        if log_level not in LOGGING_LEVELS:
            return self._bad_request('Invalid log level')

        arg_page = self._get_page()
        arg_limit = self._get_limit()
        min_level = LOGGING_LEVELS[log_level]

        def data_generator():
            """Read log lines based on the specified criteria."""
            start = arg_limit * (arg_page - 1) + 1
            for l in read_loglines(start_index=start, max_lines=arg_limit * arg_page,
                                   predicate=lambda li: filter_logline(li, min_level=min_level)):
                yield l.to_json()

        return self._paginate(data_generator=data_generator)

    def post(self):
        """Create a log line.

        By definition this method is NOT idempotent.
        """
        data = json.loads(self.request.body)
        if not data or not all([data.get('message')]):
            return self._bad_request('Invalid request')

        data['level'] = data.get('level', 'INFO').upper()
        if data['level'] not in LOGGING_LEVELS:
            return self._bad_request('Invalid log level')

        message = data['message']
        args = data.get('args', [])
        kwargs = data.get('kwargs', {})
        level = LOGGING_LEVELS[data['level']]
        log.log(level, message, exc_info=False, *args, **kwargs)
        self._created()
