# coding=utf-8
"""Request handler for series operations."""
from __future__ import unicode_literals

from medusa.server.api.v2.base import BaseRequestHandler
from medusa.server.api.v2.series import SeriesHandler
from medusa.tv.series import Series, SeriesIdentifier

from tornado.escape import json_decode


class SeriesOperationHandler(BaseRequestHandler):
    """Operation request handler for series."""

    #: parent resource handler
    parent_handler = SeriesHandler
    #: resource name
    name = 'operation'
    #: identifier
    identifier = None
    #: path param
    path_param = None
    #: allowed HTTP methods
    allowed_methods = ('POST', )

    def post(self, series_slug):
        """Query series information.

        :param series_slug: series slug. E.g.: tvdb1234
        """
        series_identifier = SeriesIdentifier.from_slug(series_slug)
        if not series_identifier:
            return self._bad_request('Invalid series slug')

        series = Series.find_by_identifier(series_identifier)
        if not series:
            return self._not_found('Series not found')

        data = json_decode(self.request.body)
        if not data or not all([data.get('type')]) or len(data) != 1:
            return self._bad_request('Invalid request body')

        if data['type'] == 'ARCHIVE_EPISODES':
            if series.set_all_episodes_archived(final_status_only=True):
                return self._created()
            return self._no_content()

        return self._bad_request('Invalid operation')
