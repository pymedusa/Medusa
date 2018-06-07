# coding=utf-8

from __future__ import print_function
from __future__ import unicode_literals

from tornado.ioloop import IOLoop
from tornado.websocket import WebSocketClosedError, WebSocketHandler

clients = []
backlogged_msgs = []


def push_to_web_socket(msg):
    if not clients:
        # No clients so let's backlog this
        backlogged_msgs.append(msg)
        return
    io_loop = IOLoop.current()
    for client in clients:
        io_loop.add_callback(client.write_message, msg)


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

    def on_message(self, message):
        print('Received: {0}'.format(message))

    def data_received(self, chunk):
        super(WebSocketUIHandler, self).data_received(chunk)

    def on_close(self):
        clients.remove(self)
