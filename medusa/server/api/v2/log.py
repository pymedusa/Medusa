# coding=utf-8
"""Request handler for logs."""
import json
import logging

from medusa.logger.adapters.style import BraceAdapter
from .base import BaseRequestHandler
from ....logger import LOGGING_LEVELS, filter_logline, read_loglines


log = BraceAdapter(logging.getLogger(__name__))


class LogHandler(BaseRequestHandler):
    """Log request handler."""

    #: resource name
    name = 'log'
    #: identifier
    identifier = ('log_level', r'[a-zA-Z]+')
    #: allowed HTTP methods
    allowed_methods = ('GET', 'POST', 'OPTIONS')

    def get(self, log_level):
        """Query logs.

        :param log_level:
        :type log_level: str
        """
        log_level = log_level or 'INFO'
        if log_level not in LOGGING_LEVELS:
            return self._not_found('Log level not found')

        arg_page = self._get_page()
        arg_limit = self._get_limit()
        min_level = LOGGING_LEVELS[log_level.upper()]

        def data_generator():
            """Read log lines based on the specified criteria."""
            start = arg_limit * (arg_page - 1)
            for i, l in enumerate(read_loglines(max_lines=arg_limit * arg_page,
                                                predicate=lambda li: filter_logline(li, min_level=min_level))):
                if i >= start:
                    yield l.to_json()

        return self._paginate(data_generator=data_generator)

    def post(self, log_level):
        """Create a log line.

        By definition this method is NOT idempotent.
        """
        data = json.loads(self.request.body)
        log_level = data.get('level', 'INFO').upper()
        if log_level not in LOGGING_LEVELS:
            return self._bad_request('Invalid log level')

        message = data['message']
        args = data.get('args', [])
        kwargs = data.get('kwargs', {})
        level = LOGGING_LEVELS[log_level]
        log.log(level, message, exc_info=False, *args, **kwargs)
        self._created()
