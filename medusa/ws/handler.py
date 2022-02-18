# coding=utf-8

"""WebSocket handler."""

from __future__ import unicode_literals

import logging

from medusa.logger.adapters.style import BraceAdapter

from tornado.websocket import WebSocketClosedError, WebSocketHandler

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())

clients = []
backlogged_msgs = []


class WebSocketUIHandler(WebSocketHandler):
    """WebSocket handler to send and receive data to and from a web client."""

    def check_origin(self, origin):
        """Allow alternate origins."""
        return True

    def open(self, *args, **kwargs):
        """Client connected to the WebSocket."""
        clients.append(self)
        super(WebSocketUIHandler, self).open(*args, **kwargs)
        # If we have pending messages send them to the new client
        for msg in backlogged_msgs:
            try:
                self.write_message(msg)
            except WebSocketClosedError:
                pass
            else:
                backlogged_msgs.remove(msg)

    def write_message(self, message, binary=False):
        """Send a message to the client."""
        super(WebSocketUIHandler, self).write_message(message, binary)

    def on_message(self, message):
        """Received a message from the client."""
        log.debug('WebSocket received message from {client}: {message}',
                  {'client': self.request.remote_ip, 'message': message})

    def data_received(self, chunk):
        """Received a streamed data chunk from the client."""
        super(WebSocketUIHandler, self).data_received(chunk)

    def on_close(self):
        """Client disconnected from the WebSocket."""
        clients.remove(self)

    def __repr__(self):
        """Client representation."""
        return '<{name} Client: {ip}>'.format(
            name=type(self).__name__, ip=self.request.remote_ip)
