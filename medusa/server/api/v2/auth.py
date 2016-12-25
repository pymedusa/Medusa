# coding=utf-8
"""Request handler for authentication."""

import base64
import tornado

from .base import BaseRequestHandler
from .... import app, helpers, logger, notifiers


class LoginHandler(BaseRequestHandler):
    """Login request handler."""

    def set_default_headers(self):
        """Set default CORS headers."""
        super(LoginHandler, self).set_default_headers()
        self.set_header('Access-Control-Allow-Methods', 'POST, OPTIONS')

    def prepare(self):
        """Prepare."""
        pass

    def post(self, *args, **kwargs):
        """Submit login."""
        self.set_header('X-Medusa-Server', app.APP_VERSION)

        roles = ['user', 'admin']
        if app.DEVELOPER:
            roles.append('developer')

        username = app.WEB_USERNAME
        password = app.WEB_PASSWORD
        submitted_username = ''
        submitted_password = ''

        # If the user hasn't set a username and/or password just let them login
        if username.strip() != '' and password.strip() != '':
            if self.request.headers.get('Authorization'):
                auth_decoded = base64.decodestring(self.request.headers.get('Authorization')[6:])
                submitted_username, submitted_password = auth_decoded.split(':', 2)
            elif self.request.body:
                data = tornado.escape.json_decode(self.request.body)
                submitted_username = data['username']
                submitted_password = data['password']
            else:
                self.api_finish(status=401, error='No Credentials Provided')

            if app.NOTIFY_ON_LOGIN and not helpers.is_ip_private(self.request.remote_ip):
                notifiers.notify_login(self.request.remote_ip)

            if username != submitted_username or password != submitted_password:
                logger.log('User attempted a failed login to the Medusa API from IP: {ip}'.format(ip=self.request.remote_ip), logger.WARNING)
                self.api_finish(status=401, error='Invalid credentials')
            else:
                logger.log('User logged into the Medusa API', logger.INFO)
                self.api_finish(data={
                    'idToken': app.API_KEY,
                    'roles': roles
                })
        else:
            logger.log('User logged into the Medusa API', logger.INFO)
            self.api_finish(data={
                'idToken': app.API_KEY,
                'roles': roles
            })
