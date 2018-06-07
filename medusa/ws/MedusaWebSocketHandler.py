# coding=utf-8

from __future__ import unicode_literals

import logging

from medusa import app
from medusa.logger.adapters.style import BraceAdapter

from tornado.websocket import WebSocketClosedError, WebSocketHandler

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())

clients = []
backlogged_msgs = []


def push_to_web_socket(msg):
    if not clients:
        # No clients so let's backlog this
        backlogged_msgs.append(msg)
        return
    main_io_loop = app.instance.web_server.io_loop
    for client in clients:
        main_io_loop.add_callback(client.write_message, msg)


class WebSocketUIHandler(WebSocketHandler):
    def check_origin(self, origin):
        return True

    def open(self, *args, **kwargs):
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
        super(WebSocketUIHandler, self).write_message(message, binary)

    def on_message(self, message):
        log.debug('WebSocket received message from {client}: {message}',
                  {'client': self.request.remote_ip, 'message': message})

    def data_received(self, chunk):
        super(WebSocketUIHandler, self).data_received(chunk)

    def on_close(self):
        clients.remove(self)
