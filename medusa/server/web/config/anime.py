# coding=utf-8

"""Configure Anime Look & Feel and AniDB authentication."""

from __future__ import unicode_literals

from medusa.server.web.config.handler import Config
from medusa.server.web.core import PageTemplate

from tornroutes import route


@route('/config/anime(/?.*)')
class ConfigAnime(Config):
    """Handler for Anime configuration."""

    def __init__(self, *args, **kwargs):
        super(ConfigAnime, self).__init__(*args, **kwargs)

    def index(self):
        """
        Render the anime configuration page.

        [Converted to VueRouter]
        """
        t = PageTemplate(rh=self, filename='index.mako')
        return t.render()
