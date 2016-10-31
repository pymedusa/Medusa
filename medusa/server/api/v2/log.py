# coding=utf-8
"""Request handler for logs."""
import json
import logging

from .base import BaseRequestHandler
from ....logger import LOGGING_LEVELS, filter_logline, read_loglines


logger = logging.getLogger(__name__)


class LogHandler(BaseRequestHandler):
    """Log request handler."""

    def get(self, log_level):
        """Query logs.

        :param log_level:
        :type log_level: str
        """
        log_level = log_level or 'INFO'
        arg_page = self._get_page()
        arg_limit = self._get_limit()
        min_level = LOGGING_LEVELS[log_level.upper()]

        data = [line.to_json() for line in read_loglines(max_lines=arg_limit + arg_page,
                                                         predicate=lambda l: filter_logline(l, min_level=min_level))]
        start = (arg_page - 1) * arg_limit
        end = start + arg_limit
        data = data[start:end]

        self.api_finish(data=data, headers={
            'X-Pagination-Page': arg_page,
            'X-Pagination-Limit': arg_limit
        })

    def delete(self, log_level='ERROR'):
        """Delete logs.

        :param log_level:
        """
        self.api_finish()

    def post(self, log_level):
        """Create a log line.

        By definition this method is NOT idempotent.
        """
        data = json.loads(self.request.body)
        message = data['message']
        args = data.get('args', [])
        kwargs = data.get('kwargs', dict())
        level = LOGGING_LEVELS[data.get('level', 'ERROR').upper()]
        logger.log(level, message, exc_info=False, *args, **kwargs)
        self.api_finish(status=201)
