# coding=utf-8

from __future__ import unicode_literals

from medusa.server.web.config.handler import Config
from medusa.server.web.core import PageTemplate

from tornroutes import route


@route('/config/backuprestore(/?.*)')
class ConfigBackupRestore(Config):
    def __init__(self, *args, **kwargs):
        super(ConfigBackupRestore, self).__init__(*args, **kwargs)

    def index(self):
        """
        Render the Backup & Restore page.

        [Converted to VueRouter]
        """
        return PageTemplate(rh=self, filename='index.mako').render()
