# coding=utf-8

"""
This module provides JSON Web Token (JWT) Authentication.

See:
    https://jwt.io/introduction/
"""

import logging

import requests
from requests.auth import AuthBase

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class JWTBearerAuth(AuthBase):
    """Attaches JWT Bearer Authentication to a given Request object."""

    def __init__(self, token):
        """Create a new request auth with a JWT token."""
        self.token = token
        log.debug('New auth created with token: {value}'.format(value=token))

    @property
    def auth_header(self):
        """A Bearer schema authentication header using the provided token."""
        return {
            'Authorization': 'Bearer {token}'.format(token=self.token)
        }

    def __eq__(self, other):
        """Allow comparison of Auth objects."""
        return all([
            self.token == getattr(other, 'token', None),
        ])

    def __ne__(self, other):
        """Allow comparison of Auth objects."""
        return not self == other

    def __call__(self, r=requests.Request()):
        """Apply authentication to the current request."""
        log.debug('Adding JWT Bearer token to request')
        r.headers.update(self.auth_header)
        return r
