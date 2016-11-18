# coding=utf-8
"""Request handler for authentication."""

import base64
import medusa as app
from .base import BaseRequestHandler
from .... import logger, helpers


class LoginHandler(BaseRequestHandler):
    """Login request handler."""

    def set_default_headers(self):
        BaseRequestHandler.set_default_headers(self)
        self.set_header('Access-Control-Allow-Methods', 'POST, OPTIONS')

    def prepare(self):
        pass

    def post(self, *args, **kwargs):
        """Submit login
        """

        username = app.WEB_USERNAME
        password = app.WEB_PASSWORD

        if self.request.headers.get('Authorization'):
            auth_decoded = base64.decodestring(self.request.headers.get('Authorization')[6:])
            decoded_username, decoded_password = auth_decoded.split(':', 2)

            if app.NOTIFY_ON_LOGIN and not helpers.is_ip_private(self.request.remote_ip):
                notifiers.notify_login(self.request.remote_ip)

            if (username != decoded_username or password != decoded_password):
                logger.log('User attempted a failed login to the Medusa API from IP: {ip}'.format(ip=self.request.remote_ip), logger.WARNING)
                self.api_finish(status=401, error='Invalid credentials')
            else:
                logger.log('User logged into the Medusa API', logger.INFO)
                self.api_finish(data={
                    'apiKey': app.API_KEY
                })
        else:
            self.api_finish(status=401, error='No Credentials Provided')
