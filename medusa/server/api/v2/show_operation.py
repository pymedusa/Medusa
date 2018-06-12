# coding=utf-8
"""Request handler for show operations."""
from __future__ import unicode_literals

from medusa.server.api.v2.base import BaseRequestHandler
from medusa.server.api.v2.show import ShowHandler
from medusa.tv.show import Show, ShowIdentifier

from tornado.escape import json_decode


class ShowOperationHandler(BaseRequestHandler):
    """Operation request handler for show."""

    #: parent resource handler
    parent_handler = ShowHandler
    #: resource name
    name = 'operation'
    #: identifier
    identifier = None
    #: path param
    path_param = None
    #: allowed HTTP methods
    allowed_methods = ('POST', )

    def post(self, show_slug):
        """Query show information.

        :param show_slug: show slug. E.g.: tvdb1234
        """
        show_identifier = ShowIdentifier.from_slug(show_slug)
        if not show_identifier:
            return self._bad_request('Invalid show slug')

        show = Show.find_by_identifier(show_identifier)
        if not show:
            return self._not_found('Show not found')

        data = json_decode(self.request.body)
        if not data or not all([data.get('type')]) or len(data) != 1:
            return self._bad_request('Invalid request body')

        if data['type'] == 'ARCHIVE_EPISODES':
            if show.set_all_episodes_archived(final_status_only=True):
                return self._created()
            return self._no_content()

        return self._bad_request('Invalid operation')
