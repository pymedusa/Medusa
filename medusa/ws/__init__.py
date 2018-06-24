# coding: utf-8
"""WebSocket module."""

from __future__ import unicode_literals

from medusa import app
from medusa.ws.handler import backlogged_msgs, clients  # noqa: F401


def push_message(msg):
    """Push a message to all connected WebSocket clients."""
    if not clients:
        # No clients so let's backlog this
        # @TODO: This has a chance to spam the user with notifications
        # backlogged_msgs.append(msg)
        return
    main_io_loop = app.instance.web_server.io_loop
    for client in clients:
        main_io_loop.add_callback(client.write_message, msg)
