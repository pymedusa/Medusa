# coding=utf-8

"""Configure Providers."""

from __future__ import unicode_literals

from medusa.server.web.config.handler import Config
from medusa.server.web.core import PageTemplate

from tornroutes import route

INVALID_CHARS = ['||']


@route('/config/providers(/?.*)')
class ConfigProviders(Config):
    """Handler for Provider configuration."""

    def __init__(self, *args, **kwargs):
        super(ConfigProviders, self).__init__(*args, **kwargs)

    def index(self):
        """
        Render the providers configuration page.

        [Converted to VueRouter]
        """
        t = PageTemplate(rh=self, filename='index.mako')
        return t.render()
