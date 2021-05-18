# coding=utf-8
"""Base module for all torrent clients."""

from __future__ import unicode_literals

import logging
import re
import time
import traceback
from base64 import b16encode, b32decode
from builtins import object
from builtins import str
from hashlib import sha1

from bencodepy import BencodeDecodeError, DEFAULT as BENCODE

from medusa import app, db
from medusa.helper.common import http_code_description
from medusa.logger.adapters.style import BraceAdapter
from medusa.session.core import ClientSession

import certifi

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class GenericClient(object):
    """Base class for all torrent clients."""

    def __init__(self, name, host=None, username=None, password=None, torrent_path=None):
        """Constructor.

        :param name:
        :type name: string
        :param host:
        :type host: string
        :param username:
        :type username: string
        :param password:
        :type password: string
        """
        self.name = name
        self.username = app.TORRENT_USERNAME if username is None else username
        self.password = app.TORRENT_PASSWORD if password is None else password
        self.host = app.TORRENT_HOST if host is None else host
        self.torrent_path = app.TORRENT_PATH if torrent_path is None else torrent_path
        self.rpcurl = app.TORRENT_RPCURL
        self.url = None
        self.response = None
        self.auth = None
        self.message = None
        self.session = ClientSession()
        self.session.auth = (self.username, self.password)
        self.verify = certifi.where()
        
        if self._get_auth():
            return False

    def _request(self, method='get', params=None, data=None, files=None, cookies=None):

        self.response = self.session.request(method, self.url, params=params, data=data, files=files, timeout=60, verify=self.verify)
        if not self.response:
            log.warning(f"{self.name} {method.upper()} call to {self.url} failed!")
            self.message = f'Connect to {self.name} on "{self.host}" failed!'
            return False
        if self.response.status_code  >= 400:
            log.warning(f'{self.name}: Unable to reach torrent client. Reason: {self.response.reason}')
            self.message = f"Failed to connect to {self.name} reason: {self.response.reason}"
            return False
        log.debug('{name}: Response to {method} request is {response}', {
            'name': self.name,
            'method': method.upper(),
            'response': self.response.text[0:1024] + '...' if len(self.response.text) > 1027 else self.response.text
        })

        return True

    def _get_auth(self):
        """Return the auth_id needed for the client."""
        raise NotImplementedError


    def _add_torrent_uri(self, result):
        """Return the True/False from the client when a torrent is added via url (magnet or .torrent link).

        :param result:
        :type result: medusa.classes.SearchResult
        """
        raise NotImplementedError

    def _add_torrent_file(self, result):
        """Return the True/False from the client when a torrent is added via result.content (only .torrent file).

        :param result:
        :type result: medusa.classes.SearchResult
        """
        raise NotImplementedError

    def _check_path(self):
        """Check if the destination path is correct."""
        log.debug('dummy check path function')
        return True


    def _set_torrent_label(self, result):
        """Return the True/False from the client when a torrent is set with label.

        :param result:
        :type result: medusa.classes.SearchResult
        :return:
        :rtype: bool
        """
        return True

    def _set_torrent_ratio(self, result):
        """Return the True/False from the client when a torrent is set with ratio.

        :param result:
        :type result: medusa.classes.SearchResult
        :return:
        :rtype: bool
        """
        return True

    def _set_torrent_seed_time(self, result):
        """Return the True/False from the client when a torrent is set with a seed time.

        :param result:
        :type result: medusa.classes.SearchResult
        :return:
        :rtype: bool
        """
        return True

    def _set_torrent_priority(self, result):
        """Return the True/False from the client when a torrent is set with result.priority (-1 = low, 0 = normal, 1 = high).

        :param result:
        :type result: medusa.classes.SearchResult
        :return:
        :rtype: bool
        """
        return True

    def _set_torrent_path(self, torrent_path):
        """Return the True/False from the client when a torrent is set with path.

        :param torrent_path:
        :type torrent_path: string
        :return:
        :rtype: bool
        """
        return True

    def _set_torrent_pause(self, result):
        """Return the True/False from the client when a torrent is set with pause.

        :param result:
        :type result: medusa.classes.SearchResult
        :return:
        :rtype: bool
        """
        return True

    @staticmethod
    def _get_info_hash(result):
        result.hash = None
        if result.url.startswith('magnet:'):
            result.hash = re.findall(r'urn:btih:([\w]{32,40})', result.url)[0]
            if len(result.hash) == 32:
                hash_b16 = b16encode(b32decode(result.hash)).lower()
                result.hash = hash_b16.decode('utf-8')
        else:
            try:
                # `bencodepy` is monkeypatched in `medusa.init`
                torrent_bdecode = BENCODE.decode(result.content, allow_extra_data=True)
                info = torrent_bdecode['info']
                result.hash = sha1(BENCODE.encode(info)).hexdigest()
            except (BencodeDecodeError, KeyError):
                log.warning(
                    'Unable to bdecode torrent. Invalid torrent: {name}. '
                    'Deleting cached result if exists', {'name': result.name}
                )
                cache_db_con = db.DBConnection('cache.db')
                cache_db_con.action(
                    'DELETE FROM [{provider}] '
                    'WHERE name = ? '.format(provider=result.provider.get_id()),
                    [result.name]
                )
                return False
            except Exception:
                log.error(traceback.format_exc())
                return False
        return True

    def send_torrent(self, result):
        """Add torrent to the client.

        :param result:
        :type result: medusa.classes.SearchResult
        :return:
        :rtype: str or bool
        """


        # Sets per provider seed ratio
        result.ratio = result.provider.seed_ratio()

        # check for the hash and add it if not there
        try:
            if not result.hash:
                raise Exception()
        except:
            if not self._get_info_hash(result):
                return False

        if result.url.startswith('magnet:'):
            log.info(f'Adding "{result.url}" to {self.name}')
            r_code = self._add_torrent_uri(result)
        else:
            log.info(f'Adding "{result.name}" torrent to {self.name}')
            r_code = self._add_torrent_file(result)

        if not r_code:
            log.warning(f'{self.name}: Unable to send Torrent')
            return False

        if not self._set_torrent_pause(result):
            log.error(f'{self.name}: Unable to set the pause for Torrent')

        if not self._set_torrent_label(result):
            log.error(f'{self.name}: Unable to set the label for Torrent')

        if not self._set_torrent_ratio(result):
            log.error(f'{self.name}: Unable to set the ratio for Torrent')

        if not self._set_torrent_seed_time(result):
            log.error(f'{self.name}: Unable to set the seed time for Torrent')

        if not self._set_torrent_path(result):
            log.error(f'{self.name}: Unable to set the path for Torrent')

        if result.priority != 0 and not self._set_torrent_priority(result):
            log.error(f'{self.name}: Unable to set priority for Torrent')

        return r_code

    def test_authentication(self):
        """Test authentication.

        :return:
        :rtype: tuple(bool, str)
        """
        r_code = self._get_auth()
        if self.message:
            return r_code, self.message
        elif not self._check_path():
            return False, self.message
        if r_code:
            return True, 'Success: Connected and Authenticated'
        else:
            return False, f'Error: Unable to get {self.name} authentication, check your input!'


    def remove_torrent(self, info_hash):
        """Remove torrent from client using given info_hash.

        :param info_hash:
        :type info_hash: string
        :return
        :rtype: bool
        """
        raise NotImplementedError

    def remove_torrent_data(self, info_hash):
        """Remove torrent from client and from disk.

        :param info_hash:
        :type info_hash: string
        :return
        :rtype: bool
        """
        raise NotImplementedError

    def pause_torrent(self, info_hash):
        """Pause torrent.

        :param info_hash:
        :type info_hash: string
        :return
        :rtype: bool
        """
        raise NotImplementedError

    def remove_ratio_reached(self):
        """Remove all Medusa torrents that ratio was reached.

        It loops in all hashes returned from client and check if it is in the snatch history
        if its then it checks if we already processed media from the torrent (episode status `Downloaded`)
        If is a RARed
       torrent then we don't have a media file so we check if that hash is from an
        episode that has a `Downloaded` status
        """
        raise NotImplementedError

    def torrent_completed(self, info_hash):
        """Check if a specific torrent has finished seeding."""
        raise NotImplementedError
