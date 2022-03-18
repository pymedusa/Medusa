# coding=utf-8
"""Handle the requests fro /token."""
from __future__ import unicode_literals

import random
import string
import time

import jwt

from medusa import app
from medusa.server.web.core.base import BaseHandler

from tornado.web import authenticated


class TokenHandler(BaseHandler):
    """Handle the request for /token, and return the app.API_KEY if authenticated."""

    def __init__(self, *args, **kwargs):
        """Initialize token handler."""
        super(TokenHandler, self).__init__(*args, **kwargs)

    @authenticated
    def get(self, *args, **kwargs):
        """Return a JWT for /token get requests."""
        time_now = int(time.time())
        self.finish(
            jwt.encode({
                'iss': f'Medusa {app.APP_VERSION}',
                'iat': int(time.time()),
                # @TODO: The jti should be saved so we can revoke tokens
                'jti': ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(20)),
                'exp': time_now + int(86400),
                'username': app.WEB_USERNAME,
                'apiKey': app.API_KEY,
                'webRoot': app.WEB_ROOT
            }, app.ENCRYPTION_SECRET, algorithm='HS256')
        )
