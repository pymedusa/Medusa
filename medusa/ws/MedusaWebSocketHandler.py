# coding=utf-8

from __future__ import print_function
from __future__ import unicode_literals

from tornado.websocket import WebSocketHandler

clients = []
backlogged_msgs = []


def push_to_web_socket(msg):
    if len(clients):
        for client in clients:
            client.write_message(msg)
    else:
        # No clients so let's backlog this
        backlogged_msgs.append(msg)


class WebSocketUIHandler(WebSocketHandler):
    def check_origin(self, origin):
        return True

    def open(self, *args, **kwargs):
        clients.append(self)
        WebSocketHandler.open(self, *args, **kwargs)
        if len(clients) == 0 and len(backlogged_msgs):
            # We have pending messages and a new client
            for msg in backlogged_msgs:
                push_to_web_socket(msg)

    def on_message(self, message):
        print(u"Received: " + message)

    def data_received(self, chunk):
        WebSocketHandler.data_received(self, chunk)

    def on_close(self):
        clients.remove(self)
