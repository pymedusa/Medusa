# coding=utf-8
"""Request handler for history."""
import json
import logging

from .base import BaseRequestHandler
from ....logger import LOGGING_LEVELS, filter_logline, read_loglines


logger = logging.getLogger(__name__)


class HistoryHandler(BaseRequestHandler):
    """History request handler."""

    def get(self, query=None):
        """Query history.

        :param query:
        :type query: str
        """
        self.api_finish()

    def delete(self, query=None):
        """Delete history item or all history.

        :param query:
        """
        self.api_finish()

    def post(self, query=None):
        """Create a history entry.

        By definition this method is NOT idempotent.
        """
        self.api_finish()
