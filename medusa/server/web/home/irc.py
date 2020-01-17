# coding=utf-8
"""Base handler for the IRC page."""

from __future__ import unicode_literals

from medusa.server.web.core import PageTemplate
from medusa.server.web.home.handler import Home

from tornroutes import route


@route('/IRC(/?.*)')
class HomeIRC(Home):
    """Base handler for the IRC page."""

    def __init__(self, *args, **kwargs):
        super(HomeIRC, self).__init__(*args, **kwargs)

    def index(self):
        """
        Render the IRC page.

        [Converted to VueRouter]
        """
        t = PageTemplate(rh=self, filename='index.mako')
        return t.render()
