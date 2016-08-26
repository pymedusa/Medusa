# coding=utf-8
"""Request handler for general information."""

import sickbeard
from sickbeard import (
    classes, logger,
)
from .base import BaseRequestHandler


class LogHandler(BaseRequestHandler):
    """Log request handler."""

    def get(self, log_level=logger.ERROR):
        """Query general logs.

        :param log_level:
        :type log_level: str
        """
        self.api_finish(data='')

    def delete(self, log_level=logger.ERROR):
        """Delete logs.

        :param log_level:
        :type query: int
        """
        if log_level == logger.WARNING:
            classes.WarningViewer.clear()
        else:
            classes.ErrorViewer.clear()

        self.api_finish()
