# coding=utf-8

from __future__ import unicode_literals

import os
import time
from tornado.routes import route
import sickbeard
from sickbeard import helpers
from sickrage.helper.encoding import ek
from sickbeard.server.web.core import PageTemplate
from sickbeard.server.web.config.handler import Config


@route('/config/backuprestore(/?.*)')
class ConfigBackupRestore(Config):
    def __init__(self, *args, **kwargs):
        super(ConfigBackupRestore, self).__init__(*args, **kwargs)

    def index(self):
        t = PageTemplate(rh=self, filename='config_backuprestore.mako')

        return t.render(submenu=self.ConfigMenu(), title='Config - Backup/Restore',
                        header='Backup/Restore', topmenu='config',
                        controller='config', action='backupRestore')

    @staticmethod
    def backup(backupDir=None):

        final_result = ''

        if backupDir:
            source = [ek(os.path.join, sickbeard.DATA_DIR, 'sickbeard.db'), sickbeard.CONFIG_FILE,
                      ek(os.path.join, sickbeard.DATA_DIR, 'failed.db'),
                      ek(os.path.join, sickbeard.DATA_DIR, 'cache.db')]
            target = ek(os.path.join, backupDir, 'medusa-{date}.zip'.format(date=time.strftime('%Y%m%d%H%M%S')))

            for (path, dirs, files) in ek(os.walk, sickbeard.CACHE_DIR, topdown=True):
                for dirname in dirs:
                    if path == sickbeard.CACHE_DIR and dirname not in ['images']:
                        dirs.remove(dirname)
                for filename in files:
                    source.append(ek(os.path.join, path, filename))

            if helpers.backupConfigZip(source, target, sickbeard.DATA_DIR):
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
            target_dir = ek(os.path.join, sickbeard.DATA_DIR, 'restore')

            if helpers.restoreConfigZip(source, target_dir):
                final_result += 'Successfully extracted restore files to {location}'.format(location=target_dir)
                final_result += '<br>Restart Medusa to complete the restore.'
            else:
                final_result += 'Restore FAILED'
        else:
            final_result += 'You need to select a backup file to restore!'

        final_result += '<br>\n'

        return final_result
