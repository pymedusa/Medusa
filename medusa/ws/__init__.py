# coding: utf-8
"""WebSocket module."""

from __future__ import unicode_literals

import json

from medusa import app
from medusa.ws.handler import backlogged_msgs, clients  # noqa: F401


class Message(object):
    """Represents a WebSocket message."""

    def __init__(self, event, data):
        """
        @TODO: Docstring.

        :param event: @TODO:
        :param data: @TODO:
        """
        self.event = event
        self.data = data

    @property
    def content(self):
        """@TODO: Docstring."""
        return {
            'event': self.event,
            'data': self.data
        }

    def json(self):
        """@TODO: Docstring."""
        return json.dumps(self.content)

    def push(self):
        """Push a message to all connected WebSocket clients."""
        msg = self.json()

        if not clients:
            # No clients so let's backlog this
            # @TODO: This has a chance to spam the user with notifications
            # backlogged_msgs.append(msg)
            return
        main_io_loop = app.instance.web_server.io_loop
        for client in clients:
            main_io_loop.add_callback(client.write_message, msg)
