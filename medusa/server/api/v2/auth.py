# coding=utf-8
"""Request handler for authentication."""

import random
import string
import time
import jwt
import tornado

from .base import BaseRequestHandler
from .... import app, helpers, logger, notifiers


class AuthHandler(BaseRequestHandler):
    """Auth request handler."""

    def set_default_headers(self):
        """Set default CORS headers."""
        super(AuthHandler, self).set_default_headers()
        if app.APP_VERSION:
            self.set_header('X-Medusa-Server', app.APP_VERSION)
        self.set_header('Access-Control-Allow-Methods', 'POST, OPTIONS')

    def prepare(self):
        """Prepare."""
        pass

    def post(self, *args, **kwargs):
        """Request JWT."""
        username = app.WEB_USERNAME
        password = app.WEB_PASSWORD
        submitted_username = ''
        submitted_password = ''
        submitted_exp = 86400  # 1 day
        request_body = {}

        # If the user hasn't set a username and/or password just let them login
        if username.strip() != '' and password.strip() != '':
            if self.request.body:
                if self.request.headers['content-type'] == 'application/json':
                    request_body = tornado.escape.json_decode(self.request.body)
                else:
                    self._failed_login(error='Incorrect content-type')
                if all(x in request_body for x in ['username', 'password']):
                    submitted_username = request_body['username']
                    submitted_password = request_body['password']
                    if 'exp' in request_body:
                        submitted_exp = request_body['exp']
            else:
                self._failed_login(error='No Credentials Provided')

            if username != submitted_username or password != submitted_password:
                self._failed_login(error='Invalid credentials')
            else:
                self._login(submitted_exp)
        else:
            self._login()

    def _login(self, exp=86400):
        self.set_header('Content-Type', 'application/jwt')
        if app.NOTIFY_ON_LOGIN and not helpers.is_ip_private(self.request.remote_ip):
            notifiers.notify_login(self.request.remote_ip)

        logger.log('{user} logged into the API v2'.format(user=app.WEB_USERNAME), logger.INFO)
        time_now = int(time.time())
        self.api_finish(data=jwt.encode({
            'iss': 'Medusa ' + app.APP_VERSION,
            'iat': time_now,
            # @TODO: The jti should be saved so we can revoke tokens
            'jti': ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(20)),
            'exp': time_now + int(exp),
            'scopes': ['show:read', 'show:write'],  # @TODO: This should be reaplce with scopes or roles/groups
            'username': app.WEB_USERNAME,
            'apiKey': app.API_KEY  # TODO: This should be replaced with the JWT itself
        }, app.ENCRYPTION_SECRET, algorithm='HS256'))

    def _failed_login(self, error=None):
        self.api_finish(status=401, error=error)
        logger.log('{user} attempted a failed login to the API v2 from IP: {ip}'.format(
            user=app.WEB_USERNAME,
            ip=self.request.remote_ip
        ), logger.WARNING)
