# coding=utf-8
"""Base module for all torrent clients."""

from __future__ import unicode_literals

import logging
import re
import traceback
from base64 import b16encode, b32decode
from builtins import object
from hashlib import sha1

from bencodepy import BencodeDecodeError, DEFAULT as BENCODE

import certifi

from medusa import app, db
from medusa.helper.common import http_code_description
from medusa.logger.adapters.style import BraceAdapter
from medusa.session.core import ClientSession

import requests


log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class GenericClient(object):
    """Base class for all torrent clients."""

    def __init__(self, name, host=None, username=None, password=None, torrent_path=None):
        """Genericclient Constructor.

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

    def _request(self, method='get', params=None, data=None, files=None, cookies=None):

        try:
            self.response = self.session.request(
                method, self.url, params=params, data=data, files=files, timeout=60, cookies=cookies,
                verify=self.verify if app.TORRENT_VERIFY_CERT else False
            )
        except (requests.exceptions.MissingSchema, requests.exceptions.InvalidURL) as error:
            log.warning('{name}: Invalid Host: {error}', {'name': self.name, 'error': error})
            return False
        except requests.exceptions.RequestException as error:
            log.warning('{name}: Error occurred during request: {error}',
                        {'name': self.name, 'error': error})
            # We want to raise connection errors for the download_handler. As we need to know
            # explicitely if there was a connection error when untracking tracked torrents/nzb.
            raise
        except Exception as error:
            log.error('{name}: Unknown exception raised when sending torrent to'
                      ' {name}: {error}', {'name': self.name, 'error': error})
            return False

        if self.response.status_code == 401:
            log.error('{name}: Invalid Username or Password,'
                      ' check your config', {'name': self.name})
            return False

        code_description = http_code_description(self.response.status_code)

        if code_description is not None:
            log.info('{name}: {code}',
                     {'name': self.name, 'code': code_description})
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
        if not result.hash and not self._get_info_hash(result):
            return False

        if result.url.startswith('magnet:'):
            log.info('Adding "{url}" to {name}', {'url': result.url, 'name': self.name})
            r_code = self._add_torrent_uri(result)
        else:
            log.info('Adding "{result_name}" torrent to {name}', {
                'result_name': result.name, 'name': self.name
            })
            r_code = self._add_torrent_file(result)

        if not r_code:
            log.warning('{name}: Unable to send Torrent', {'name': self.name})
            return False

        if not self._set_torrent_pause(result):
            log.error('{name}: Unable to set the pause for Torrent', {'name': self.name})

        if not self._set_torrent_label(result):
            log.error('{name}: Unable to set the label for Torrent', {'name': self.name})

        if not self._set_torrent_ratio(result):
            log.error('{name}: Unable to set the ratio for Torrent', {'name': self.name})

        if not self._set_torrent_seed_time(result):
            log.error('{name}: Unable to set the seed time for Torrent', {'name': self.name})

        if not self._set_torrent_path(result):
            log.error('{name}: Unable to set the path for Torrent', {'name': self.name})

        if result.priority != 0 and not self._set_torrent_priority(result):
            log.error('{name}: Unable to set priority for Torrent', {'name': self.name})

        return r_code

    def test_authentication(self):
        """Test authentication.

        :return:
        :rtype: tuple(bool, str)
        """
        r_code = self._get_auth()
        if self.message:
            return bool(r_code), self.message
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
