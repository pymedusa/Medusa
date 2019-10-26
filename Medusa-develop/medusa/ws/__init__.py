# coding: utf-8
"""WebSocket module."""

from __future__ import unicode_literals

import json
import logging

from medusa import app
from medusa.logger.adapters.style import BraceAdapter
from medusa.ws.handler import backlogged_msgs, clients  # noqa: F401

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class Message(object):
    """Represents a WebSocket message."""

    def __init__(self, event, data):
        """
        Construct a new WebSocket message.

        :param event: A string representing the type of message (e.g. notification)
        :param data: A JSON-serializable object containing the message data.
        """
        self.event = event
        self.data = data

    @property
    def content(self):
        """Get the message content."""
        return {
            'event': self.event,
            'data': self.data
        }

    def json(self):
        """Return the message content as a JSON-serialized string."""
        try:
            return json.dumps(self.content)
        except TypeError as error:
            log.warning('Unhashable type encountered. Please report this warning to the developers.\n{error!r}', {
                'error': error,
                'exc_info': True
            })
            # Fall back to using the APIv2 default encoder. This is a safety measure.
            from medusa.server.api.v2.base import json_default_encoder
            return json.dumps(self.content, default=json_default_encoder)

    def push(self):
        """Push the message to all connected WebSocket clients."""
        msg = self.json()

        if not clients:
            # No clients so let's backlog this
            # @TODO: This has a chance to spam the user with notifications
            # backlogged_msgs.append(msg)
            return
        main_io_loop = app.instance.web_server.io_loop
        for client in clients:
            main_io_loop.add_callback(client.write_message, msg)
