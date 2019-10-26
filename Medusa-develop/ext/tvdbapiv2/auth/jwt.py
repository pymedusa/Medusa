# coding=utf-8

"""
This module provides JSON Web Token (JWT) Authentication.

See:
    https://jwt.io/introduction/
"""

from __future__ import absolute_import, unicode_literals

import json
import logging
from base64 import urlsafe_b64decode

import requests.auth

from six import text_type

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class JWTBearerAuth(requests.auth.AuthBase):
    """Attaches JWT Bearer Authentication to a given Request object."""

    def __init__(self, token=None):
        """Create a new request auth with a JWT token."""
        self.token = token

    @property
    def auth_header(self):
        """A Bearer schema authentication header using the provided token."""
        return {
            'Authorization': 'Bearer {token}'.format(token=self.token)
        }

    @property
    def token(self):
        """The JWT token."""
        return getattr(self, '_token', None)

    @token.setter
    def token(self, value):
        if self.token != value:
            setattr(self, '_token', value)
            setattr(self, '_payload', jwt_payload(value))

    @property
    def payload(self):
        """The JWT payload."""
        return getattr(self, '_payload', {})

    def __eq__(self, other):
        """Allow comparison of Auth objects."""
        return all([
            self.token == getattr(other, 'token', None),
        ])

    def __ne__(self, other):
        """Allow comparison of Auth objects."""
        return not self == other

    def __call__(self, request):
        """Apply authentication to the current request."""
        log.debug('Adding JWT Bearer token to request')
        request.headers.update(self.auth_header)
        return request

    def __repr__(self):
        return '{obj.__class__.__name__}({obj.token!r})'.format(obj=self)


def jwt_decode(data):
    """Decode a JSON Web Token (JWT)."""
    # make sure data is binary
    if isinstance(data, text_type):
        log.debug('Encoding the JWT token as UTF-8')
        data = data.encode('utf-8')

    # pad the data to a multiple of 4 bytes
    remainder = len(data) % 4
    if remainder > 0:
        length = 4 - remainder
        log.debug('Padding the JWT with {x} bytes'.format(x=length))
        data += b'=' * length

    # base64 decode the data
    data = urlsafe_b64decode(data)

    # convert the decoded json to a string
    data = data.decode('utf-8')

    # return the json string as a dict
    result = json.loads(data)
    log.info('JWT Successfully decoded')
    return result


def jwt_payload(token):
    """Get the payload from a JSON Web Token."""
    # split the token into its header, payload, and signature
    result = {}
    try:
        header, payload, signature = token.split('.')
    except AttributeError:
        log.debug('Unable to extract payload from JWT: {}'.format(token))
    else:
        del header  # unused
        del signature  # unused
        result = jwt_decode(payload)
        log.debug('Payload extracted from JWT: {}'.format(result))
    finally:
        return result
