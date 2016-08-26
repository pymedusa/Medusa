# coding=utf-8
"""Request handler for logs."""

from sickbeard import logger
from .base import BaseRequestHandler


class LogHandler(BaseRequestHandler):
    """Log request handler."""

    def get(self, log_level=logger.ERROR):
        """Query logs.

        :param log_level:
        :type log_level: str
        """
        self.api_finish()

    def delete(self, log_level=logger.ERROR):
        """Delete logs.

        :param log_level:
        :type query: int
        """
        self.api_finish()
