"""Traktor Trakt module."""
# coding=utf-8
#
# URL: https://medusa.github.io
#
# This file is part of medusa.
#
# Medusa is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Medusa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Medusa. If not, see <http://www.gnu.org/licenses/>.

import json
import logging
import time

import certifi

import requests

from .exceptions import (AuthException, MissingTokenException, ResourceUnavailable,
                         TokenExpiredException, TraktException, UnavailableException)


log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class TraktApi(object):
    """A base class to use for recommended shows client API's."""

    def __init__(self, headers=None, timeout=None, api_url=None, auth_url=None, ssl_verify=None, **trakt_settings):
        """Initialize TraktApi class."""
        headers = {
            'Content-Type': 'application/json',
            'trakt-api-version': '2',
            'trakt-api-key': trakt_settings.get('trakt_api_key') or ''
        }

        self.session = requests.Session()
        self.ssl_verify = certifi.where() if ssl_verify else False
        self.timeout = timeout if timeout else None
        self.auth_url = trakt_settings.get('trakt_auth_url', 'https://trakt.tv/')  # oauth url
        self.api_url = trakt_settings.get('trakt_api_url', 'https://api.trakt.tv/')  # api url
        self.access_token = trakt_settings.get('trakt_access_token', '')
        self.refresh_token = trakt_settings.get('trakt_refresh_token', '')
        self.access_token_refreshed = False
        self.headers = headers
        self.trakt_settings = trakt_settings

    def get_token(self, refresh_token=None, trakt_pin=None, count=0):
        """Function or refreshing a trakt token."""
        if count > 3:
            self.access_token = ''
            return False, False
        elif count > 0:
            time.sleep(2)

        data = {
            'client_id': self.trakt_settings.get('trakt_api_key'),
            'client_secret': self.trakt_settings.get('trakt_api_secret'),
            'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob'
        }

        if refresh_token and self.refresh_token and not trakt_pin:
            data['grant_type'] = 'refresh_token'
            data['refresh_token'] = self.refresh_token
        else:
            data['grant_type'] = 'authorization_code'
            if trakt_pin is not None:
                data['code'] = trakt_pin

        headers = {
            'Content-Type': 'application/json'
        }

        resp = self.request('oauth/token', data=data, headers=headers, url=self.auth_url, method='POST', count=count)

        if 'access_token' in resp:
            self.access_token = resp['access_token']
            if 'refresh_token' in resp:
                self.refresh_token = resp['refresh_token']
                self.access_token_refreshed = True
            return self.access_token, self.refresh_token
        return None, None

    def request(self, path, data=None, headers=None, url=None, method='GET', count=0):
        """Function for performing the trakt request."""
        if not self.access_token and count >= 2:
            raise MissingTokenException(u'You must get a Trakt TOKEN. Check your Trakt settings')

        if headers is None:
            headers = self.headers

        if self.access_token:
            headers['Authorization'] = 'Bearer ' + self.access_token

        if url is None:
            url = self.api_url

        count += 1

        data = json.dumps(data) if data else []

        try:
            resp = self.session.request(method, url + path, headers=headers, timeout=self.timeout,
                                        data=data, verify=self.ssl_verify)

            # check for http errors and raise if any are present
            resp.raise_for_status()

            # convert response to json
            resp = resp.json()
        except requests.RequestException as e:
            code = getattr(e.response, 'status_code', None)
            if code == 502:
                # Retry the request, cloudflare had a proxying issue
                log.debug(u'Retrying trakt api request: {0} (attempt: {1})'.format(path, count))
                return self.request(path, data, headers, url, method, count=count)
            elif code == 401:
                if self.get_token(refresh_token=True, count=count):
                    return self.request(path, data, headers, url, method)
                else:
                    log_message = u'Unauthorized. Please check your Trakt settings'
                    log.warning(log_message)
                    raise AuthException(log_message)
            elif code in (None, 500, 501, 503, 504, 520, 521, 522):
                # Report Trakt as unavailable when Timeout to connect (no status code)
                # http://docs.trakt.apiary.io/#introduction/status-codes
                raise UnavailableException(u"Trakt may have some issues and it's unavailable. Try again later please")
            elif code == 404:
                log_message = u'Trakt error (404) Not found - the resource does not exist: {0}'.format(url + path)
                log.error(log_message)
                raise ResourceUnavailable(log_message)
            elif code == 410:
                log_message = u'Trakt error (410) Expired - the tokens have expired. Get a new one'
                log.warning(log_message)
                raise TokenExpiredException(log_message)
            elif code == 413:
                # Cause of error unknown - https://github.com/pymedusa/Medusa/issues/4090
                log_message = u'Trakt error (413) Request Entity Too Large for url {0}'.format(url + path)
                log.warning(log_message)
                # Dumping data for debugging purposes
                log.debug(u'Trakt request headers:\n{0}'.format(e.request.headers))
                log.debug(u'Trakt request body:\n{0}'.format(e.request.body))
                log.debug(u'Trakt response headers:\n{0}'.format(e.response.headers))
                log.debug(u'Trakt response body:\n{0}'.format(e.response.body))
                raise TraktException(log_message)
            else:
                log_message = u'Unknown Trakt request exception. Error: {0}'.format(code or e)
                log.error(log_message)
                raise TraktException(log_message)

        # check and confirm trakt call did not fail
        if isinstance(resp, dict) and resp.get('status', False) == 'failure':
            if 'message' in resp:
                raise TraktException(resp['message'])
            if 'error' in resp:
                raise TraktException(resp['error'])
            else:
                raise TraktException('Unknown Error')

        # If it got this far, the access token should be correct. It could be the access token
        # has been refreshed in the mean time.
        return resp

    def validate_account(self):
        """Function for validation of trakt account."""
        resp = self.request('users/settings')

        if 'account' in resp:
            return True
        return False
