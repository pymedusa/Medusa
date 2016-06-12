# coding=utf-8

"""
Base handler for Config pages
"""

from __future__ import unicode_literals

import os
from tornado.routes import route
import sickbeard
from sickbeard.versionChecker import CheckVersion
from sickbeard.server.web.core import WebRoot, PageTemplate


@route('/config(/?.*)')
class Config(WebRoot):
    """
    Base handler for Config pages
    """
    def __init__(self, *args, **kwargs):
        super(Config, self).__init__(*args, **kwargs)

    @staticmethod
    def ConfigMenu():
        """
        Config menu
        """
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
        """
        Render the Help & Info page
        """
        t = PageTemplate(rh=self, filename='config.mako')

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
            header='Medusa Configuration', topmenu='config',
            sr_user=sr_user, sr_locale=sr_locale, ssl_version=ssl_version,
            sr_version=sr_version
        )
