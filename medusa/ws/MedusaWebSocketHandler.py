# coding=utf-8
# Author: p0psicles
# URL: http://code.google.com/p/sickbeard/
#
# This file is part of SickRage.
#
# SickRage is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# SickRage is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with SickRage. If not, see <http://www.gnu.org/licenses/>.


from tornado.websocket import WebSocketHandler

clients = []


def push_to_web_socket(msg):
    for client in clients:
        client.write_message(msg)


class WebSocketUIHandler(WebSocketHandler):
    def check_origin(self, origin):
        return True

    def open(self, *args, **kwargs):
        clients.append(self)
        WebSocketHandler.open(self, *args, **kwargs)

    def on_message(self, message):
        print(u"Received: " + message)

    def data_received(self, chunk):
        WebSocketHandler.data_received(self, chunk)

    def on_close(self):
        clients.remove(self)
