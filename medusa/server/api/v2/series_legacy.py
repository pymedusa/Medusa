# coding=utf-8
"""Request handler for series operations."""
from __future__ import unicode_literals

from builtins import map

from medusa.server.api.v2.base import BaseRequestHandler
from medusa.server.api.v2.series import SeriesHandler
from medusa.tv.series import Series, SeriesIdentifier


class SeriesLegacyHandler(BaseRequestHandler):
    """To be removed/redesigned."""

    #: parent resource handler
    parent_handler = SeriesHandler
    #: resource name
    name = 'legacy'
    #: identifier
    identifier = ('identifier', r'\w+')
    #: path param
    path_param = None
    #: allowed HTTP methods
    allowed_methods = ('GET', )

    def get(self, series_slug, identifier):
        """Query series information.

        :param series_slug: series slug. E.g.: tvdb1234
        :param identifier:
        """
        series_identifier = SeriesIdentifier.from_slug(series_slug)
        if not series_identifier:
            return self._bad_request('Invalid series slug')

        series = Series.find_by_identifier(series_identifier)
        if not series:
            return self._not_found('Series not found')

        if identifier == 'backlogged':
            # TODO: revisit
            allowed_qualities = self._parse(self.get_argument('allowed', default=None), str)
            allowed_qualities = list(map(int, allowed_qualities.split(','))) if allowed_qualities else []
            preferred_qualities = self._parse(self.get_argument('preferred', default=None), str)
            preferred_qualities = list(map(int, preferred_qualities.split(','))) if preferred_qualities else []
            new, existing = series.get_backlogged_episodes(allowed_qualities=allowed_qualities,
                                                           preferred_qualities=preferred_qualities)
            data = {'new': new, 'existing': existing}
            return self._ok(data=data)

        return self._bad_request('Invalid request')
