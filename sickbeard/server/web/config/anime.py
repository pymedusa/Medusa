# coding=utf-8

import os
import time
from unrar2 import RarFile

import sickbeard
from sickbeard import (
    config, helpers, logger, naming, subtitles, ui,
)
from sickbeard.common import (
    Quality, WANTED,
)
from sickbeard.providers import newznab, rsstorrent
from sickbeard.versionChecker import CheckVersion

from sickrage.helper.common import try_int
from sickrage.helper.encoding import ek
from sickrage.helper.exceptions import (
    ex
)
from sickrage.providers.GenericProvider import GenericProvider

from tornado.routes import route
from sickbeard.server.web.core import (
    WebRoot, PageTemplate
)

# Conditional imports
try:
    import json
except ImportError:
    import simplejson as json

from sickbeard.server.web.config.base import Config


@route('/config/anime(/?.*)')
class ConfigAnime(Config):
    def __init__(self, *args, **kwargs):
        super(ConfigAnime, self).__init__(*args, **kwargs)

    def index(self):

        t = PageTemplate(rh=self, filename="config_anime.mako")

        return t.render(submenu=self.ConfigMenu(), title='Config - Anime',
                        header='Anime', topmenu='config',
                        controller="config", action="anime")

    def saveAnime(self, use_anidb=None, anidb_username=None, anidb_password=None, anidb_use_mylist=None,
                  split_home=None):

        results = []

        sickbeard.USE_ANIDB = config.checkbox_to_value(use_anidb)
        sickbeard.ANIDB_USERNAME = anidb_username
        sickbeard.ANIDB_PASSWORD = anidb_password
        sickbeard.ANIDB_USE_MYLIST = config.checkbox_to_value(anidb_use_mylist)
        sickbeard.ANIME_SPLIT_HOME = config.checkbox_to_value(split_home)

        sickbeard.save_config()

        if len(results) > 0:
            for x in results:
                logger.log(x, logger.ERROR)
            ui.notifications.error('Error(s) Saving Configuration',
                                   '<br>\n'.join(results))
        else:
            ui.notifications.message('Configuration Saved', ek(os.path.join, sickbeard.CONFIG_FILE))

        return self.redirect("/config/anime/")
