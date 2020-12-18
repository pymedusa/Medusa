# coding=utf-8
"""Request handler for authentication."""
from __future__ import unicode_literals

import logging
import random
import string
import time
from builtins import range

import jwt

from medusa import app, helpers, notifiers
from medusa.logger.adapters.style import BraceAdapter
from medusa.server.api.v2.base import BaseRequestHandler

from six import text_type

from tornado.escape import json_decode

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class AuthHandler(BaseRequestHandler):
    """Auth request handler."""

    #: resource name
    name = 'authenticate'
    #: allowed HTTP methods
    allowed_methods = ('POST', )

    def _check_authentication(self):
        """Override authentication check for the authentication endpoint."""
        return None

    def post(self, *args, **kwargs):
        """Request JWT."""
        username = app.WEB_USERNAME
        password = app.WEB_PASSWORD

        # If the user hasn't set a username and/or password just let them login
        if not username.strip() or not password.strip():
            return self._login()

        if not self.request.body:
            return self._failed_login(error='No Credentials Provided')

        if self.request.headers['content-type'] != 'application/json':
            return self._failed_login(error='Incorrect content-type')

        request_body = json_decode(self.request.body)
        submitted_username = request_body.get('username')
        submitted_password = request_body.get('password')
        submitted_exp = request_body.get('exp', 86400)
        if username != submitted_username or password != submitted_password:
            return self._failed_login(error='Invalid credentials')

        return self._login(submitted_exp)

    def _login(self, exp=86400):
        self.set_header('Content-Type', 'application/json')
        if app.NOTIFY_ON_LOGIN and not helpers.is_ip_private(self.request.remote_ip):
            notifiers.notify_login(self.request.remote_ip)

        log.info('{user} logged into the API v2', {'user': app.WEB_USERNAME})
        time_now = int(time.time())
        return self._ok(data={
            'token': jwt.encode({
                'iss': 'Medusa ' + text_type(app.APP_VERSION),
                'iat': time_now,
                # @TODO: The jti should be saved so we can revoke tokens
                'jti': ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(20)),
                'exp': time_now + int(exp),
                'username': app.WEB_USERNAME,
                'apiKey': app.API_KEY
            }, app.ENCRYPTION_SECRET, algorithm='HS256').decode('utf-8')
        })

    def _failed_login(self, error=None):
        log.warning('{user} attempted a failed login to the API v2 from IP: {ip}', {
            'user': app.WEB_USERNAME,
            'ip': self.request.remote_ip
        })
        return self._unauthorized(error=error)
