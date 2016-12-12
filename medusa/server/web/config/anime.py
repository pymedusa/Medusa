# coding=utf-8

"""Configure Anime Look & Feel and AniDB authentication."""

from __future__ import unicode_literals

import os

from tornroutes import route
from .handler import Config
from ..core import PageTemplate
from .... import app, config, logger, ui


@route('/config/anime(/?.*)')
class ConfigAnime(Config):
    """
    Handler for Anime configuration
    """
    def __init__(self, *args, **kwargs):
        super(ConfigAnime, self).__init__(*args, **kwargs)

    def index(self):
        """
        Render the Anime configuration page
        """

        t = PageTemplate(rh=self, filename='config_anime.mako')

        return t.render(submenu=self.ConfigMenu(), title='Config - Anime',
                        header='Anime', topmenu='config',
                        controller='config', action='anime')

    def saveAnime(self, use_anidb=None, anidb_username=None, anidb_password=None, anidb_use_mylist=None,
                  split_home=None):
        """
        Save anime related settings
        """

        results = []

        app.USE_ANIDB = config.checkbox_to_value(use_anidb)
        app.ANIDB_USERNAME = anidb_username
        app.ANIDB_PASSWORD = anidb_password
        app.ANIDB_USE_MYLIST = config.checkbox_to_value(anidb_use_mylist)
        app.ANIME_SPLIT_HOME = config.checkbox_to_value(split_home)

        app.instance.save_config()

        if results:
            for x in results:
                logger.log(x, logger.ERROR)
            ui.notifications.error('Error(s) Saving Configuration',
                                   '<br>\n'.join(results))
        else:
            ui.notifications.message('Configuration Saved', os.path.join(app.CONFIG_FILE))

        return self.redirect('/config/anime/')
