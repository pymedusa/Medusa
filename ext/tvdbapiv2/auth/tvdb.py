# coding=utf-8

"""
This module provides authentication to TheTVDB API v2.
"""

from __future__ import absolute_import, unicode_literals

import logging
from time import time

import requests
from requests.compat import urljoin

from .jwt import JWTBearerAuth
from ..exceptions import AuthError

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class TVDBAuth(JWTBearerAuth):
    """Attaches JWT Bearer Authentication to a TVDB request."""

    refresh_window = 7200  # seconds

    def __init__(self, api_key=None, token=None, api_base='https://api.thetvdb.com'):
        """Create a new TVDB request auth."""
        super(TVDBAuth, self).__init__(token)
        self.api_key = api_key
        self.api_base = api_base

    @property
    def authorization(self):
        """TVDB Authentication details for obtaining a JSON Web Token."""
        return {
            'apikey': self.api_key,
        }

    @property
    def expiration(self):
        """Authentication expiration in epoch time."""
        return self.payload.get('exp', time())

    @property
    def time_remaining(self):
        """Remaining authentication time in seconds."""
        return max(self.expiration - time(), 0)

    @property
    def is_expired(self):
        """True if authentication has expired, else False."""
        return self.expiration <= time()

    def _get_token(self, response):
        try:
            data = response.json()
        except ValueError as error:
            log.warning('Failed to extract token: {msg}'.format(msg=error))
        else:
            self.token = data['token']
        finally:
            return response

    def login(self):
        """Acquire a JSON Web Token."""
        log.debug('Acquiring a TVDB JWT')
        if not self.api_key:
            raise AuthError('Missing API key')
        response = requests.post(
            urljoin(self.api_base, 'login'),
            json=self.authorization,
            verify=False,
        )
        try:
            self._get_token(response)
        finally:
            return response

    def refresh(self):
        """Refresh a JSON Web Token."""

        log.debug('Refreshing a TVDB JWT')

        if not self.token:
            log.debug('No token to refresh')
            return self.login()
        elif self.is_expired:
            log.debug('Token has expired')
            return self.login()

        response = requests.get(
            urljoin(self.api_base, 'refresh_token'),
            headers=self.auth_header,
            verify=False,
        )

        try:
            self._get_token(response)
        finally:
            return response

    def authenticate(self):
        """Acquire or refresh a JSON Web Token."""
        if not self.token or self.is_expired:
            self.login()
        elif self.time_remaining < self.refresh_window:
            self.refresh()

    def __call__(self, request):
        self.authenticate()
        return super(TVDBAuth, self).__call__(request)

    def __repr__(self):
        representation = '{obj.__class__.__name__}(api_key={obj.api_key!r})'
        return representation.format(obj=self)


class TVDBUser(TVDBAuth):
    """
    Attaches a users JWT Bearer Authentication to a TVDB request.

    Providing user authentication to a TVDB session allows access to
    user-specific routes.
    """

    def __init__(self, api_key=None, username=None, account_id=None):
        """Create a new TVDB request auth with a users credentials."""
        super(TVDBUser, self).__init__(api_key)
        self.username = username
        self.account_id = account_id

    @property
    def authorization(self):
        """TVDB Authentication details for obtaining a users JSON Web Token."""
        result = {
            'username': self.username,
            'userkey': self.account_id,
        }
        result.update(super(TVDBUser, self).authorization)
        return result

    def __repr__(self):
        representation = (
            '{obj.__class__.__name__}'
            '('
            'api_key={obj.api_key!r}, '
            'username={obj.username!r}, '
            'account_id={obj.account_id!r}'
            ')'
        )
        return representation.format(obj=self)
