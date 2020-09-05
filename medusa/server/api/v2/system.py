# coding=utf-8
"""Request handler for statistics."""
from __future__ import unicode_literals

from medusa import app, ui
from medusa.server.api.v2.base import BaseRequestHandler
from medusa.system.restart import Restart
from medusa.system.shutdown import Shutdown
from medusa.updater.version_checker import CheckVersion

from tornado.escape import json_decode


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
                    return self._bad_request('Backup failed')
            else:
                ui.notifications.message('Already on branch: ', data['branch'])
                return self._bad_request('Already on branch')

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

    def _update(self, branch=None):
        checkversion = CheckVersion()
        if branch:
            checkversion.updater.branch = branch

        if checkversion.updater.need_update() and checkversion.updater.update():
            return True
        else:
            ui.notifications.message('Update failed{branch}'.format(
                branch=' for branch {0}'.format(branch) if branch else ''
            ), 'Check logs for more information.')

        return False
