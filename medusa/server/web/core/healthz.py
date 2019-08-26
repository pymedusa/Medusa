# coding=utf-8
"""Route to healthcheck (healthz) endpoint."""

from __future__ import unicode_literals

from medusa.server.web.core.base import WebRoot
from medusa.system.schedulers import generate_schedulers

from tornroutes import route


@route('/healthz(/?.*)')
class Healthz(WebRoot):
    """Route to healthcheck (healthz) endpoint."""

    def __init__(self, *args, **kwargs):
        """Initialize class with default constructor."""
        super(WebRoot, self).__init__(*args, **kwargs)

    def index(self):
        """Render healthz endpoint based."""
        response = 'Schedules no beuno:\n'

        for gen in generate_schedulers():
            if not gen['isAlive']:
                response += gen['name'] + '\n'
                self.set_status(500)

        self.finish(response)
