# coding=utf-8

"""
This module provides authentication to TheTVDB API v2.
"""

import logging

import requests
from ....sessions.auth.utils.jwt import jwt_payload
from ....sessions.auth.jwt import JWTBearerAuth

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class TVDBAuth(JWTBearerAuth):
    """Attaches JWT Bearer Authentication to a TVDB request."""

    url = {
        'login': 'https://api.thetvdb.com/login',
        'refresh': 'https://api.thetvdb.com/refresh_token',
    }

    def __init__(self, api_key=None, session=None, token=None):
        """Create a new TVDB request auth."""
        self.session = session or requests.Session()
        self.api_key = api_key
        self.payload = None
        super(TVDBAuth, self).__init__(token)

    @property
    def authorization(self):
        """TVDB Authentication details for obtaining a JSON Web Token."""
        return {
            'apikey': self.api_key,
        }

    @property
    def token(self):
        """A JSON Web Token containing TVDB authentication."""
        return getattr(self, '_token', None)

    @token.setter
    def token(self, value):
        if value is None:
            value = self.login().json().pop('token')
        self.payload = jwt_payload(value)
        setattr(self, '_token', value)

    def login(self):
        """Acquire a JSON Web Token from TVDB."""
        log.debug('Acquiring a TVDB JWT')
        return self.session.post(self.url['login'], json=self.authorization)

    def refresh(self):
        """Refresh a JSON Web Token from TVDB."""
        log.debug('Refreshing a TVDB JWT')
        return self.session.get(self.url['refresh'])


class TVDBUserAuth(TVDBAuth):
    """
    Attaches a users JWT Bearer Authentication to a TVDB request.

    Providing user authentication to a TVDB session allows access to
    user-specific routes.
    """

    def __init__(self, username, account_id, api_key, session=None):
        """Create a new TVDB request auth with a users credentials."""
        self.username = username
        self.account_id = account_id
        super(TVDBUserAuth, self).__init__(api_key, session)
        assert self.username.lower() == self.payload['username'].lower()

    @property
    def authorization(self):
        """TVDB Authentication details for obtaining a users JSON Web Token."""
        result = {
            'username': self.username,
            'userkey': self.account_id,
        }
        result.update(super(TVDBUserAuth, self).authorization)
        return result
