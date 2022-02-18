# coding=utf-8

"""Base handler for Config pages."""

from __future__ import unicode_literals

from medusa.server.web.core import PageTemplate, WebRoot

from tornroutes import route


@route('/config(/?.*)')
class Config(WebRoot):
    """
    Base handler for Config pages
    """
    def __init__(self, *args, **kwargs):
        super(Config, self).__init__(*args, **kwargs)

    def index(self):
        """
        Render the Help & Info page.

        [Converted to VueRouter]
        """
        return PageTemplate(rh=self, filename='index.mako').render()
