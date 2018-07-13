# coding=utf-8

from __future__ import unicode_literals

import os
import time

from medusa import (
    app,
    helpers,
)
from medusa.server.web.config.handler import Config
from medusa.server.web.core import PageTemplate

from tornroutes import route


@route('/config/backuprestore(/?.*)')
class ConfigBackupRestore(Config):
    def __init__(self, *args, **kwargs):
        super(ConfigBackupRestore, self).__init__(*args, **kwargs)

    def index(self):
        t = PageTemplate(rh=self, filename='config_backuprestore.mako')

        return t.render(submenu=self.ConfigMenu(),
                        controller='config', action='backupRestore')

    @staticmethod
    def backup(backupDir=None):

        final_result = ''

        if backupDir:
            source = [os.path.join(app.DATA_DIR, app.APPLICATION_DB), app.CONFIG_FILE,
                      os.path.join(app.DATA_DIR, app.FAILED_DB),
                      os.path.join(app.DATA_DIR, app.CACHE_DB)]
            target = os.path.join(backupDir, 'medusa-{date}.zip'.format(date=time.strftime('%Y%m%d%H%M%S')))

            for (path, dirs, files) in os.walk(app.CACHE_DIR, topdown=True):
                for dirname in dirs:
                    if path == app.CACHE_DIR and dirname not in ['images']:
                        dirs.remove(dirname)
                for filename in files:
                    source.append(os.path.join(path, filename))

            if helpers.backup_config_zip(source, target, app.DATA_DIR):
                final_result += 'Successful backup to {location}'.format(location=target)
            else:
                final_result += 'Backup FAILED'
        else:
            final_result += 'You need to choose a folder to save your backup to!'

        final_result += '<br>\n'

        return final_result

    @staticmethod
    def restore(backupFile=None):

        final_result = ''

        if backupFile:
            source = backupFile
            target_dir = os.path.join(app.DATA_DIR, 'restore')

            if helpers.restore_config_zip(source, target_dir):
                final_result += 'Successfully extracted restore files to {location}'.format(location=target_dir)
                final_result += '<br>Restart Medusa to complete the restore.'
            else:
                final_result += 'Restore FAILED'
        else:
            final_result += 'You need to select a backup file to restore!'

        final_result += '<br>\n'

        return final_result
