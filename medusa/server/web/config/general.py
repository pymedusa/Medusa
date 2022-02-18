# coding=utf-8

from __future__ import unicode_literals

from medusa import (
    app,
    config,
    helpers,
)
from medusa.common import (
    Quality,
    WANTED,
)
from medusa.server.web.config.handler import Config
from medusa.server.web.core import PageTemplate

from tornroutes import route


@route('/config/general(/?.*)')
class ConfigGeneral(Config):
    def __init__(self, *args, **kwargs):
        super(ConfigGeneral, self).__init__(*args, **kwargs)

    def index(self):
        """
        Render the general configuration page.

        [Converted to VueRouter]
        """
        t = PageTemplate(rh=self, filename='index.mako')
        return t.render()

    @staticmethod
    def generate_api_key():
        return helpers.generate_api_key()

    @staticmethod
    def saveAddShowDefaults(default_status, allowed_qualities, preferred_qualities, default_season_folders,
                            subtitles=False, anime=False, scene=False, default_status_after=WANTED):

        allowed_qualities = [_.strip() for _ in allowed_qualities.split(',')] if allowed_qualities else []
        preferred_qualities = [_.strip() for _ in preferred_qualities.split(',')] if preferred_qualities else []

        new_quality = Quality.combine_qualities([int(quality) for quality in allowed_qualities],
                                                [int(quality) for quality in preferred_qualities])

        app.STATUS_DEFAULT = int(default_status)
        app.STATUS_DEFAULT_AFTER = int(default_status_after)
        app.QUALITY_DEFAULT = int(new_quality)

        app.SEASON_FOLDERS_DEFAULT = config.checkbox_to_value(default_season_folders)
        app.SUBTITLES_DEFAULT = config.checkbox_to_value(subtitles)

        app.ANIME_DEFAULT = config.checkbox_to_value(anime)

        app.SCENE_DEFAULT = config.checkbox_to_value(scene)
        app.instance.save_config()
