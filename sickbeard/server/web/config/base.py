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


@route('/config(/?.*)')
class Config(WebRoot):
    def __init__(self, *args, **kwargs):
        super(Config, self).__init__(*args, **kwargs)

    @staticmethod
    def ConfigMenu():
        menu = [
            {'title': 'General', 'path': 'config/general/', 'icon': 'menu-icon-config'},
            {'title': 'Backup/Restore', 'path': 'config/backuprestore/', 'icon': 'menu-icon-backup'},
            {'title': 'Search Settings', 'path': 'config/search/', 'icon': 'menu-icon-manage-searches'},
            {'title': 'Search Providers', 'path': 'config/providers/', 'icon': 'menu-icon-provider'},
            {'title': 'Subtitles Settings', 'path': 'config/subtitles/', 'icon': 'menu-icon-backlog'},
            {'title': 'Post Processing', 'path': 'config/postProcessing/', 'icon': 'menu-icon-postprocess'},
            {'title': 'Notifications', 'path': 'config/notifications/', 'icon': 'menu-icon-notification'},
            {'title': 'Anime', 'path': 'config/anime/', 'icon': 'menu-icon-anime'},
        ]

        return menu

    def index(self):
        t = PageTemplate(rh=self, filename="config.mako")

        try:
            import pwd
            sr_user = pwd.getpwuid(os.getuid()).pw_name
        except ImportError:
            try:
                import getpass
                sr_user = getpass.getuser()
            except StandardError:
                sr_user = 'Unknown'

        try:
            import locale
            sr_locale = locale.getdefaultlocale()
        except StandardError:
            sr_locale = 'Unknown', 'Unknown'

        try:
            import ssl
            ssl_version = ssl.OPENSSL_VERSION
        except StandardError:
            ssl_version = 'Unknown'

        sr_version = ''
        if sickbeard.VERSION_NOTIFY:
            updater = CheckVersion().updater
            if updater:
                sr_version = updater.get_cur_version()

        return t.render(
            submenu=self.ConfigMenu(), title='Medusa Configuration',
            header='Medusa Configuration', topmenu="config",
            sr_user=sr_user, sr_locale=sr_locale, ssl_version=ssl_version,
            sr_version=sr_version
        )
