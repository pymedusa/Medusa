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

                if self._update(data['branch']):
                    return self._created()
                else:
                    return self._bad_request('Update failed')
            else:
                ui.notifications.message('Already on branch: ', data['branch'])
                return self._bad_request('Already on branch')

        return self._bad_request('Invalid operation')

    def _update(self, branch):
        checkversion = CheckVersion()
        backup = checkversion.updater and checkversion._runbackup()  # pylint: disable=protected-access

        if backup is True:
            if branch:
                checkversion.updater.branch = branch

            if checkversion.updater.need_update() and checkversion.updater.update():
                return True
            else:
                ui.notifications.message("Update wasn't successful. Check your log for more information.", branch)
        return False
