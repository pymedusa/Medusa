# coding=utf-8

"""
This module provides authentication to TheTVDB API v2.
"""

import logging

from time import time
import requests

from .jwt import JWTBearerAuth

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class TVDBAuth(JWTBearerAuth):
    """Attaches JWT Bearer Authentication to a TVDB request."""
    # TODO: Add logic to refresh the auth

    url = {
        'login': 'https://api.thetvdb.com/login',
        'refresh': 'https://api.thetvdb.com/refresh_token',
    }

    def __init__(self, api_key=None, token=None):
        """Create a new TVDB request auth."""
        self.api_key = api_key
        super(TVDBAuth, self).__init__(token)

    @property
    def authorization(self):
        """TVDB Authentication details for obtaining a JSON Web Token."""
        return {
            'apikey': self.api_key,
        }

    @property
    def token(self):
        """The JWT."""
        return getattr(self, '_token', None)

    @token.setter
    def token(self, value):
        if not value or self.is_expired:
            try:
                value = self.login().json().get('token')
            except ValueError:
                value = None
        elif self.expiration - time() < 7200:  # less than 2 hrs left
            try:
                value = self.refresh().json().get('token')
            except ValueError:
                value = None
        setattr(self, '_token', value)

    @property
    def expiration(self):
        return self.payload.get('exp', time())

    @property
    def is_expired(self):
        return self.expiration <= time()

    def login(self):
        """Acquire a JSON Web Token from TVDB."""
        log.debug('Acquiring a TVDB JWT')
        return requests.post(self.url['login'], json=self.authorization)

    def refresh(self):
        """Refresh a JSON Web Token from TVDB."""
        log.debug('Refreshing a TVDB JWT')
        return requests.get(self.url['refresh'])

    def __repr__(self):
        representation = '{obj.__class__.__name__}(api_key={obj.api_key!r})'
        return representation.format(obj=self)


class TVDBUserAuth(TVDBAuth):
    """
    Attaches a users JWT Bearer Authentication to a TVDB request.

    Providing user authentication to a TVDB session allows access to
    user-specific routes.
    """

    def __init__(self, api_key=None, username=None, account_id=None):
        """Create a new TVDB request auth with a users credentials."""
        self.username = username
        self.account_id = account_id
        super(TVDBUserAuth, self).__init__(api_key)

    @property
    def authorization(self):
        """TVDB Authentication details for obtaining a users JSON Web Token."""
        result = {
            'username': self.username,
            'userkey': self.account_id,
        }
        result.update(super(TVDBUserAuth, self).authorization)
        return result

    def __repr__(self):
        representation = (
            '{obj.__class__.__name__}('
            'api_key={obj.api_key!r}, '
            'username={obj.username!r}, '
            'account_id={obj.account_id!r}'
            ')'
        )
        return representation.format(obj=self)
