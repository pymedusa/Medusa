# coding=utf-8

from __future__ import unicode_literals

import re
import time
from hashlib import sha1
from base64 import b16encode, b32decode

import sickbeard
from sickbeard import logger, helpers, db
from bencode import bencode, bdecode
import requests
import cookielib
from bencode.BTL import BTFailure
from sickrage.helper.common import http_code_description


class GenericClient(object):
    def __init__(self, name, host=None, username=None, password=None):

        self.name = name
        self.username = sickbeard.TORRENT_USERNAME if username is None else username
        self.password = sickbeard.TORRENT_PASSWORD if password is None else password
        self.host = sickbeard.TORRENT_HOST if host is None else host
        self.rpcurl = sickbeard.TORRENT_RPCURL

        self.url = None
        self.response = None
        self.auth = None
        self.last_time = time.time()
        self.session = helpers.make_session()
        self.session.auth = (self.username, self.password)
        self.session.cookies = cookielib.CookieJar()

    def _request(self, method='get', params=None, data=None, files=None, cookies=None):

        if time.time() > self.last_time + 1800 or not self.auth:
            self.last_time = time.time()
            self._get_auth()

        data_str = str(data)
        logger.log('{name}: Requested a {method} connection to {url} with Params: {params} Data: {data}{etc}'.format
                   (name=self.name, method=method.upper(), url=self.url,
                    params=params, data=data_str[0:99],
                    etc='...' if len(data_str) > 99 else ''), logger.DEBUG)

        if not self.auth:
            logger.log('{name}: Authentication Failed'.format(name=self.name), logger.WARNING)

            return False
        try:
            self.response = self.session.__getattribute__(method)(self.url, params=params, data=data, files=files, cookies=cookies,
                                                                  timeout=120, verify=False)
        except requests.exceptions.ConnectionError as msg:
            logger.log('{name}: Unable to connect {error}'.format
                       (name=self.name, error=msg), logger.ERROR)
            return False
        except (requests.exceptions.MissingSchema, requests.exceptions.InvalidURL):
            logger.log('{name}: Invalid Host'.format(name=self.name), logger.ERROR)
            return False
        except requests.exceptions.HTTPError as msg:
            logger.log('{name}: Invalid HTTP Request {error}'.format(name=self.name, error=msg), logger.ERROR)
            return False
        except requests.exceptions.Timeout as msg:
            logger.log('{name}: Connection Timeout {error}'.format(name=self.name, error=msg), logger.WARNING)
            return False
        except Exception as msg:
            logger.log('{name}: Unknown exception raised when send torrent to {name} : {error}'.format
                       (name=self.name, error=msg), logger.ERROR)
            return False

        if self.response.status_code == 401:
            logger.log('{name}: Invalid Username or Password, check your config'.format
                       (name=self.name), logger.ERROR)
            return False

        code_description = http_code_description(self.response.status_code)

        if code_description is not None:
            logger.log('{name}: {code}'.format(name=self.name, code=code_description), logger.INFO)
            return False

        logger.log('{name}: Response to {method} request is {response}'.format
                   (name=self.name, method=method.upper(), response=self.response.text), logger.DEBUG)

        return True

    def _get_auth(self):  # pylint:disable=no-self-use
        """
        This should be overridden and should return the auth_id needed for the client
        """
        return None

    def _add_torrent_uri(self, result):  # pylint:disable=unused-argument, no-self-use
        """
        This should be overridden should return the True/False from the client
        when a torrent is added via url (magnet or .torrent link)
        """
        return False

    def _add_torrent_file(self, result):  # pylint:disable=unused-argument, no-self-use
        """
        This should be overridden should return the True/False from the client
        when a torrent is added via result.content (only .torrent file)
        """
        return False

    def _set_torrent_label(self, result):  # pylint:disable=unused-argument, no-self-use
        """
        This should be overridden should return the True/False from the client
        when a torrent is set with label
        """
        return True

    def _set_torrent_ratio(self, result):  # pylint:disable=unused-argument, no-self-use
        """
        This should be overridden should return the True/False from the client
        when a torrent is set with ratio
        """
        return True

    def _set_torrent_seed_time(self, result):  # pylint:disable=unused-argument, no-self-use
        """
        This should be overridden should return the True/False from the client
        when a torrent is set with a seed time
        """
        return True

    def _set_torrent_priority(self, result):  # pylint:disable=unused-argument, no-self-use
        """
        This should be overriden should return the True/False from the client
        when a torrent is set with result.priority (-1 = low, 0 = normal, 1 = high)
        """
        return True

    def _set_torrent_path(self, torrent_path):  # pylint:disable=unused-argument, no-self-use
        """
        This should be overridden should return the True/False from the client
        when a torrent is set with path
        """
        return True

    def _set_torrent_pause(self, result):  # pylint:disable=unused-argument, no-self-use
        """
        This should be overridden should return the True/False from the client
        when a torrent is set with pause
        """
        return True

    @staticmethod
    def _get_torrent_hash(result):

        if result.url.startswith('magnet'):
            result.hash = re.findall(r'urn:btih:([\w]{32,40})', result.url)[0]
            if len(result.hash) == 32:
                result.hash = b16encode(b32decode(result.hash)).lower()
        else:

            try:
                torrent_bdecode = bdecode(result.content)
                info = torrent_bdecode['info']
                result.hash = sha1(bencode(info)).hexdigest()
            except (BTFailure, KeyError):
                logger.log('Unable to bdecode torrent. Invalid torrent', logger.WARNING)
                logger.log('Deleting cached result if exists: {result}'.format(result=result.name), logger.DEBUG)
                cache_db_con = db.DBConnection('cache.db')
                cache_db_con.action(
                    b'DELETE FROM [{provider}] '
                    b'WHERE name = ? '.format(provider=result.provider.get_id()),
                    [result.name]
                )
            except Exception:
                logger.log(traceback.format_exc(), logger.ERROR)

        return result

    def send_torrent(self, result):

        r_code = False

        logger.log('Calling {name} Client'.format(name=self.name), logger.DEBUG)

        if not self.auth:
            if not self._get_auth():
                logger.log('{name}: Authentication Failed'.format(name=self.name), logger.WARNING)
                return r_code

        try:
            # Sets per provider seed ratio
            result.ratio = result.provider.seed_ratio()

            # lazy fix for now, I'm sure we already do this somewhere else too
            result = self._get_torrent_hash(result)
            
            if not result.hash:
                return False

            if result.url.startswith('magnet'):
                r_code = self._add_torrent_uri(result)
            else:
                r_code = self._add_torrent_file(result)

            if not r_code:
                logger.log('{name}: Unable to send Torrent'.format(name=self.name), logger.WARNING)
                return False

            if not self._set_torrent_pause(result):
                logger.log('{name}: Unable to set the pause for Torrent'.format(name=self.name), logger.ERROR)

            if not self._set_torrent_label(result):
                logger.log('{name}: Unable to set the label for Torrent'.format(name=self.name), logger.ERROR)

            if not self._set_torrent_ratio(result):
                logger.log('{name}: Unable to set the ratio for Torrent'.format(name=self.name), logger.ERROR)

            if not self._set_torrent_seed_time(result):
                logger.log('{name}: Unable to set the seed time for Torrent'.format(name=self.name), logger.ERROR)

            if not self._set_torrent_path(result):
                logger.log('{name}: Unable to set the path for Torrent'.format(name=self.name), logger.ERROR)

            if result.priority != 0 and not self._set_torrent_priority(result):
                logger.log('{name}: Unable to set priority for Torrent'.format(name=self.name), logger.ERROR)

        except Exception as msg:
            logger.log('{name}: Failed Sending Torrent'.format(name=self.name), logger.ERROR)
            logger.log('{name}: Exception raised when sending torrent: {result}. Error: {error}'.format
                       (name=self.name, result=result, error=msg), logger.DEBUG)
            return r_code

        return r_code

    def test_authentication(self):

        try:
            self.response = self.session.get(self.url, timeout=120, verify=False)
        except requests.exceptions.ConnectionError:
            return False, 'Error: {name} Connection Error'.format(name=self.name)
        except (requests.exceptions.MissingSchema, requests.exceptions.InvalidURL):
            return False, 'Error: Invalid {name} host'.format(name=self.name)

        if self.response.status_code == 401:
            return False, 'Error: Invalid {name} Username or Password, check your config!'.format(name=self.name)

        try:
            self._get_auth()
            if self.response.status_code == 200 and self.auth:
                return True, 'Success: Connected and Authenticated'
            else:
                return False, 'Error: Unable to get {name} Authentication, check your config!'.format(name=self.name)
        except Exception:
            return False, 'Error: Unable to connect to {name}'.format(name=self.name)
