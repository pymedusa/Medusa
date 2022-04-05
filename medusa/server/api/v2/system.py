# coding=utf-8
"""Request handler for statistics."""
from __future__ import unicode_literals

import logging
import os
import time

from medusa import app, ui
from medusa import helpers
from medusa.logger.adapters.style import BraceAdapter
from medusa.server.api.v2.base import BaseRequestHandler
from medusa.system.restart import Restart
from medusa.system.shutdown import Shutdown
from medusa.updater.version_checker import CheckVersion

from tornado.escape import json_decode

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class SystemHandler(BaseRequestHandler):
    """System operation calls request handler."""

    #: resource name
    name = 'system'
    #: identifier
    identifier = ('identifier', r'\w+')
    #: path param
    path_param = None
    #: allowed HTTP methods
    allowed_methods = ('POST', )

    def post(self, identifier, *args, **kwargs):
        """Perform an operation on the config."""
        if identifier != 'operation':
            return self._bad_request('Invalid operation')

        data = json_decode(self.request.body)

        if data['type'] == 'RESTART' and data['pid']:
            if not Restart.restart(data['pid']):
                self._not_found('Pid does not match running pid')
            return self._created()

        if data['type'] == 'SHUTDOWN' and data['pid']:
            if not Shutdown.stop(data['pid']):
                self._not_found('Pid does not match running pid')
            return self._created()

        if data['type'] == 'CHECKOUT_BRANCH' and data['branch']:
            if app.BRANCH != data['branch']:
                app.BRANCH = data['branch']
                ui.notifications.message('Checking out branch: ', data['branch'])

                if self._backup():
                    if self._update(data['branch']):
                        return self._created()
                    else:
                        return self._bad_request('Update failed')
                else:
                    return self._bad_request('Backup failed')
            else:
                ui.notifications.message('Already on branch: ', data['branch'])
                return self._bad_request('Already on branch')

        if data['type'] == 'NEED_UPDATE':
            if self._need_update():
                return self._created()
            else:
                return self._bad_request('Update not needed')

        if data['type'] == 'UPDATE':
            if self._update():
                return self._created()
            else:
                return self._bad_request('Update failed')

        if data['type'] == 'BACKUP':
            if self._backup():
                return self._created()
            else:
                return self._bad_request('Backup failed')

        if data['type'] == 'CHECKFORUPDATE':
            check_version = CheckVersion()
            if check_version.check_for_new_version():
                return self._created()
            else:
                return self._bad_request('Version already up to date')

        if data['type'] == 'FORCEADH':
            if app.download_handler_scheduler.forceRun():
                return self._created()
            else:
                return self._bad_request('Failed starting download handler')

        if data['type'] == 'BACKUPTOZIP':
            return self._backup_to_zip(data.get('backupDir'))

        if data['type'] == 'RESTOREFROMZIP':
            return self._restore_from_zip(data.get('backupFile'))

        return self._bad_request('Invalid operation')

    def _backup(self, branch=None):
        checkversion = CheckVersion()
        backup = checkversion.updater and checkversion._runbackup()  # pylint: disable=protected-access

        if backup is True:
            return True
        else:
            ui.notifications.message('Update failed{branch}'.format(
                branch=' for branch {0}'.format(branch) if branch else ''
            ), 'Check logs for more information.')

        return False

    def _need_update(self, branch=None):
        """Check if we need an update."""
        checkversion = CheckVersion()
        if branch:
            checkversion.updater.branch = branch
        if checkversion.updater.need_update():
            return True
        else:
            ui.notifications.message('No updated needed{branch}'.format(
                branch=' for branch {0}'.format(branch) if branch else ''
            ), 'Check logs for more information.')

    def _update(self, branch=None):
        checkversion = CheckVersion()
        if branch:
            checkversion.updater.branch = branch

        if checkversion.updater.update():
            return True
        else:
            ui.notifications.message('Update failed{branch}'.format(
                branch=' for branch {0}'.format(branch) if branch else ''
            ), 'Check logs for more information.')

        return False

    def _backup_to_zip(self, backup_dir):
        """Create a backup and save to zip."""
        final_result = ''

        if backup_dir:
            source = [
                os.path.join(app.DATA_DIR, app.APPLICATION_DB), app.CONFIG_FILE
            ]

            if app.BACKUP_CACHE_DB:
                source += [
                    os.path.join(app.DATA_DIR, app.FAILED_DB),
                    os.path.join(app.DATA_DIR, app.CACHE_DB),
                    os.path.join(app.DATA_DIR, app.RECOMMENDED_DB)
                ]
            target = os.path.join(backup_dir, 'medusa-{date}.zip'.format(date=time.strftime('%Y%m%d%H%M%S')))
            log.info(u'Starting backup to location: {location} ', {'location': target})

            if app.BACKUP_CACHE_FILES:
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

        log.info(u'Finished backup to location: {location} ', {'location': target})
        return self._ok(data={'result': final_result})

    def _restore_from_zip(self, backup_file):
        """Restore from zipped backup."""
        final_result = ''

        if backup_file:
            source = backup_file
            target_dir = os.path.join(app.DATA_DIR, 'restore')
            log.info(u'Restoring backup from location: {location} ', {'location': backup_file})

            if helpers.restore_config_zip(source, target_dir):
                final_result += 'Successfully extracted restore files to {location}'.format(location=target_dir)
                final_result += '<br>Restart Medusa to complete the restore.'
            else:
                final_result += 'Restore FAILED'
        else:
            final_result += 'You need to select a backup file to restore!'

        final_result += '<br>\n'

        log.info(u'Finished restore from location: {location}', {'location': backup_file})
        return self._ok(data={'result': final_result})
