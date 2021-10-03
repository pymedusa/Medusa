# coding=utf-8
"""Request handler for log reporter."""
from __future__ import unicode_literals

import logging

from medusa.classes import ErrorViewer, WarningViewer
from medusa.logger.adapters.style import BraceAdapter
from medusa.server.api.v2.base import BaseRequestHandler

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class LogReporterHandler(BaseRequestHandler):
    """Log Reporter request handler."""

    #: resource name
    name = 'logreporter'
    #: identifier
    identifier = None
    #: allowed HTTP methods
    allowed_methods = ('GET',)

    LEVEL_WARNING = '30'
    LEVEL_ERROR = '40'

    def get(self):
        """Query logs."""
        log_level = self.get_argument('level', 'ERROR').upper()
        if log_level not in (LogReporterHandler.LEVEL_WARNING, LogReporterHandler.LEVEL_ERROR):
            return self._bad_request('Invalid log level')

        if log_level == LogReporterHandler.LEVEL_WARNING:
            return self._ok(data=WarningViewer.errors)

        if log_level == LogReporterHandler.LEVEL_ERROR:
            return self._ok(data=ErrorViewer.errors)

        return self._bad_request()
