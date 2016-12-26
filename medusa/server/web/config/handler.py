# coding=utf-8

"""Base handler for Config pages."""

from __future__ import unicode_literals

import os

from tornroutes import route
from ..core import PageTemplate, WebRoot
from .... import app, db
from ....version_checker import CheckVersion


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
            app_user = pwd.getpwuid(os.getuid()).pw_name
        except ImportError:
            try:
                import getpass
                app_user = getpass.getuser()
            except StandardError:
                app_user = 'Unknown'

        try:
            import locale
            app_locale = locale.getdefaultlocale()
        except StandardError:
            app_locale = 'Unknown', 'Unknown'

        try:
            import ssl
            ssl_version = ssl.OPENSSL_VERSION
        except StandardError:
            ssl_version = 'Unknown'

        app_version = ''
        if app.VERSION_NOTIFY:
            updater = CheckVersion().updater
            if updater:
                app_version = updater.get_cur_version()

        main_db_con = db.DBConnection()
        cur_branch_major_db_version, cur_branch_minor_db_version = main_db_con.checkDBVersion()

        return t.render(
            submenu=self.ConfigMenu(), title='Medusa Configuration',
            header='Medusa Configuration', topmenu='config',
            app_user=app_user, app_locale=app_locale, ssl_version=ssl_version,
            app_version=app_version, cur_branch_major_db_version=cur_branch_major_db_version,
            cur_branch_minor_db_version=cur_branch_minor_db_version
        )
