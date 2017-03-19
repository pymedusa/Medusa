# coding=utf-8
"""Request handler for series and episodes."""

from medusa.server.api.v2.base import BaseRequestHandler
from medusa.tv.series import Series, SeriesIdentifier
from tornado.escape import json_decode


class SeriesHandler(BaseRequestHandler):
    """Series request handler."""

    #: resource name
    name = 'series'
    #: identifier
    identifier = ('series_slug', r'[a-z]+\d+')
    #: path param
    path_param = ('path_param', r'\w+')
    #: allowed HTTP methods
    allowed_methods = ('GET', 'PATCH', 'DELETE', )

    def get(self, series_slug, path_param=None):
        """Query series information.

        :param series_slug: series slug. E.g.: tvdb1234
        :param path_param:
        """
        arg_paused = self._parse_boolean(self.get_argument('paused', default=None))

        def filter_series(current):
            return arg_paused is None or current.paused == arg_paused

        if not series_slug:
            detailed = self._parse_boolean(self.get_argument('detailed', default=False))
            data = [s.to_json(detailed=detailed) for s in Series.find_series(predicate=filter_series)]
            return self._paginate(data, sort='title')

        identifier = SeriesIdentifier.from_slug(series_slug)
        if not identifier:
            return self._bad_request('Invalid series slug')

        series = Series.find_by_identifier(identifier, predicate=filter_series)
        if not series:
            return self._not_found('Series not found')

        detailed = self._parse_boolean(self.get_argument('detailed', default=True))
        data = series.to_json(detailed=detailed)
        if path_param:
            if path_param not in data:
                return self._bad_request("Invalid path parameter'{0}'".format(path_param))
            data = data[path_param]

        return self._ok(data)

    def patch(self, identifier):
        """Patch series."""
        if not identifier:
            return self._method_not_allowed('Patching multiple series are not allowed')

        identifier = SeriesIdentifier.from_slug(identifier)
        if not identifier:
            return self._bad_request('Invalid series identifier')

        series = Series.find_by_identifier(identifier)
        if not series:
            return self._not_found('Series not found')

        data = json_decode(self.request.body)
        done = {}
        for key, value in data.items():
            if key == 'pause':
                if value is True:
                    series.pause()
                elif value is False:
                    series.unpause()
                else:
                    return self._bad_request('Invalid request body: pause')
                done[key] = value

        return self._ok(done)

    def delete(self, identifier):
        """Delete the series."""
        if not identifier:
            return self._method_not_allowed('Deleting multiple series are not allowed')

        identifier = SeriesIdentifier.from_slug(identifier)
        if not identifier:
            return self._bad_request('Invalid series identifier')

        series = Series.find_by_identifier(identifier)
        if not series:
            return self._not_found('Series not found')

        remove_files = self._parse_boolean(self.get_argument('remove_files', default=None))
        if not series.delete(remove_files):
            return self._conflict('Unable to delete series')

        return self._no_content()
