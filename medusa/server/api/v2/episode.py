# coding=utf-8
"""Request handler for show and episodes."""
from __future__ import unicode_literals

from medusa.server.api.v2.base import BaseRequestHandler
from medusa.server.api.v2.show import ShowHandler
from medusa.tv.episode import Episode, EpisodeNumber
from medusa.tv.show import Show, ShowIdentifier


class EpisodeHandler(BaseRequestHandler):
    """Episodes request handler."""

    #: parent resource handler
    parent_handler = ShowHandler
    #: resource name
    name = 'episode'
    #: identifier
    identifier = ('episode_slug', r'[\w-]+')
    #: path param
    path_param = ('path_param', r'\w+')
    #: allowed HTTP methods
    allowed_methods = ('GET', )

    def get(self, show_slug, episode_slug, path_param):
        """Query episode information.

        :param show_slug: show slug. E.g.: tvdb1234
        :param episode_number:
        :param path_param:
        """
        show_identifier = ShowIdentifier.from_slug(show_slug)
        if not show_identifier:
            return self._bad_request('Invalid show slug')

        show = Show.find_by_identifier(show_identifier)
        if not show:
            return self._not_found('Show not found')

        if not episode_slug:
            detailed = self._parse_boolean(self.get_argument('detailed', default=False))
            season = self._parse(self.get_argument('season', None), int)
            data = [e.to_json(detailed=detailed) for e in show.get_all_episodes(season=season)]
            return self._paginate(data, sort='airDate')

        episode_number = EpisodeNumber.from_slug(episode_slug)
        if not episode_number:
            return self._bad_request('Invalid episode number')

        episode = Episode.find_by_show_and_episode(show, episode_number)
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
