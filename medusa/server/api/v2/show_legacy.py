# coding=utf-8
"""Request handler for show operations."""
from __future__ import unicode_literals

from builtins import map

from medusa.server.api.v2.base import BaseRequestHandler
from medusa.server.api.v2.show import ShowHandler
from medusa.tv.show import Show, ShowIdentifier


class ShowLegacyHandler(BaseRequestHandler):
    """To be removed/redesigned."""

    #: parent resource handler
    parent_handler = ShowHandler
    #: resource name
    name = 'legacy'
    #: identifier
    identifier = ('identifier', r'\w+')
    #: path param
    path_param = None
    #: allowed HTTP methods
    allowed_methods = ('GET', )

    def get(self, show_slug, identifier):
        """Query show information.

        :param show_slug: show slug. E.g.: tvdb1234
        :param identifier:
        """
        show_identifier = ShowIdentifier.from_slug(show_slug)
        if not show_identifier:
            return self._bad_request('Invalid show slug')

        show = Show.find_by_identifier(show_identifier)
        if not show:
            return self._not_found('Show not found')

        if identifier == 'backlogged':
            # TODO: revisit
            allowed_qualities = self._parse(self.get_argument('allowed', default=None), str)
            allowed_qualities = list(map(int, allowed_qualities.split(','))) if allowed_qualities else []
            preferred_qualities = self._parse(self.get_argument('preferred', default=None), str)
            preferred_qualities = list(map(int, preferred_qualities.split(','))) if preferred_qualities else []
            new, existing = show.get_backlogged_episodes(allowed_qualities=allowed_qualities,
                                                           preferred_qualities=preferred_qualities)
            data = {'new': new, 'existing': existing}
            return self._ok(data=data)

        return self._bad_request('Invalid request')
