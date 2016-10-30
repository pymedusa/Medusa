# coding=utf-8
"""Request handler for logs."""
import json
import logging

from .base import BaseRequestHandler
from ....logger import LOGGING_LEVELS


logger = logging.getLogger(__name__)


class LogHandler(BaseRequestHandler):
    """Log request handler."""

    def get(self, log_level='ERROR'):
        """Query logs.

        :param log_level:
        :type log_level: str
        """
        self.api_finish()

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
