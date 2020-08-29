# coding=utf-8
"""Request handler for statistics."""
from __future__ import unicode_literals

from medusa.server.api.v2.base import BaseRequestHandler
from medusa.system.restart import Restart
from medusa.system.shutdown import Shutdown

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

        return self._bad_request('Invalid operation')
