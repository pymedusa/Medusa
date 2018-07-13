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

        return menu[::-1]

    def index(self):
        """
        Render the Help & Info page.

        [Converted to VueRouter]
        """
        t = PageTemplate(rh=self, filename='index.mako')
        return t.render(submenu=self.ConfigMenu())
