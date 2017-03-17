# coding=utf-8
"""Request handler for series and episodes."""

from medusa.server.api.v2.base import BaseRequestHandler
from medusa.server.api.v2.series import SeriesHandler
from medusa.tv.episode import Episode, EpisodeIdentifier
from medusa.tv.series import Series, SeriesIdentifier


class EpisodeHandler(BaseRequestHandler):
    """Episodes request handler."""

    #: parent resource handler
    parent_handler = SeriesHandler
    #: resource name
    name = 'episode'
    #: identifier
    identifier = ('identifier', r'(?:\d{4}-\d{2}-\d{2})|(?:s\d{1,4})|(?:s\d{1,4})(?:e\d{1,3})|(?:e\d{1,3})')
    #: path param
    path_param = ('path_param', r'\w+')
    #: allowed HTTP methods
    allowed_methods = ('GET', )

    def get(self, series_slug, identifier, path_param):
        """Query show information.

        :param series_slug: show slug. E.g.: tvdb1234
        :param identifier:
        :param path_param:
        """
        series_identifier = SeriesIdentifier.from_slug(series_slug)
        if not series_identifier:
            return self._bad_request('Invalid series slug')

        series = Series.find_by_identifier(series_identifier)
        if not series:
            return self._not_found('Series not found')

        if not identifier:
            detailed = self._parse_boolean(self.get_argument('detailed', default=False))
            season = self._parse(self.get_argument('season', None), int)
            data = [e.to_json(detailed=detailed) for e in series.get_all_episodes(season=season)]
            return self._paginate(data, sort='airDate')

        identifier = EpisodeIdentifier.from_identifier(identifier)
        if not identifier:
            return self._bad_request('Invalid episode identifier')

        episode = Episode.find_by_identifier(series, identifier)
        if not episode:
            return self._not_found('Episode not found')

        detailed = self._parse_boolean(self.get_argument('detailed', default=True))
        data = episode.to_json(detailed=detailed)
        if path_param:
            if path_param == 'metadata':
                data = episode.metadata() if episode.is_location_valid() else {}
            elif path_param in data:
                data = data[path_param]
            else:
                return self._bad_request("Invalid path parameter'{0}'".format(path_param))

        return self._ok(data=data)
