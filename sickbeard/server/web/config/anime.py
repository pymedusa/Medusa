# coding=utf-8

"""
Configure Anime Look & Feel and AniDB authentication.
"""

from __future__ import unicode_literals

import os
from tornado.routes import route
import sickbeard
from sickbeard import (
    config, logger, ui,
)
from sickrage.helper.encoding import ek
from sickbeard.server.web.core import PageTemplate
from sickbeard.server.web.config.handler import Config


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

        sickbeard.USE_ANIDB = config.checkbox_to_value(use_anidb)
        sickbeard.ANIDB_USERNAME = anidb_username
        sickbeard.ANIDB_PASSWORD = anidb_password
        sickbeard.ANIDB_USE_MYLIST = config.checkbox_to_value(anidb_use_mylist)
        sickbeard.ANIME_SPLIT_HOME = config.checkbox_to_value(split_home)

        sickbeard.save_config()

        if results:
            for x in results:
                logger.log(x, logger.ERROR)
            ui.notifications.error('Error(s) Saving Configuration',
                                   '<br>\n'.join(results))
        else:
            ui.notifications.message('Configuration Saved', ek(os.path.join, sickbeard.CONFIG_FILE))

        return self.redirect('/config/anime/')
