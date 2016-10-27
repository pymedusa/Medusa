# coding=utf-8
"""Request handler for server status."""

from .base import BaseRequestHandler


class StatusHandler(BaseRequestHandler):
    """Status request handler."""

    def get(self, query=''):
        """Query server status.

        :param query:
        :type query: str
        """
        self.api_finish()
