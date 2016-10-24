# coding=utf-8
# Author: Paul Wollaston
# Contributions: Luke Mullan
#
# This client script allows connection to Deluge Daemon directly, completely
# circumventing the requirement to use the WebUI.
"""Deluge Daemon Client."""

from __future__ import unicode_literals

import logging
from base64 import b64encode

import medusa as app
from synchronousdeluge import DelugeClient
from .generic import GenericClient


logger = logging.getLogger(__name__)


class DelugeDAPI(GenericClient):
    """Deluge Daemon API class."""

    drpc = None

    def __init__(self, host=None, username=None, password=None):
        """Constructor.

        :param host:
        :type host: string
        :param username:
        :type username: string
        :param password:
        :type password: string
        """
        super(DelugeDAPI, self).__init__('DelugeD', host, username, password)

    def _get_auth(self):
        return True if self.connect() else None

    def connect(self, reconnect=False):
        """Create and return Deluge RPC client to the host.

        :param reconnect:
        :type reconnect: bool
        :return:
        :rtype: DelugeRPC
        """
        hostname = self.host.replace('/', '').split(':')

        if not self.drpc or reconnect:
            self.drpc = DelugeRPC(hostname[1], port=hostname[2], username=self.username, password=self.password)

        return self.drpc

    def _add_torrent_uri(self, result):
        options = {
            'add_paused': app.TORRENT_PAUSED
        }

        remote_torrent = self.drpc.add_torrent_magnet(result.url, options, result.hash)

        if remote_torrent:
            result.hash = remote_torrent

        return remote_torrent or None

    def _add_torrent_file(self, result):
        if not result.content:
            result.content = {}
            return None

        options = {
            'add_paused': app.TORRENT_PAUSED
        }

        remote_torrent = self.drpc.add_torrent_file('{name}.torrent'.format(name=result.name),
                                                    result.content, options, result.hash)

        if remote_torrent:
            result.hash = remote_torrent

        return remote_torrent or None

    def _remove_torrent(self, torrent_hash):
        return self.drpc.remove_torrent_ratio(torrent_hash, True)

    def _set_torrent_label(self, result):

        label = app.TORRENT_LABEL.lower()
        if result.show.is_anime:
            label = app.TORRENT_LABEL_ANIME.lower()
        if ' ' in label:
            logger.error('{name}: Invalid label. Label must not contain a space', name=self.name)
            return False

        return self.drpc.set_torrent_label(result.hash, label) if label else True

    def _set_torrent_ratio(self, result):
        return self.drpc.set_torrent_ratio(result.hash, float(result.ratio)) if result.ratio else True

    def _set_torrent_priority(self, result):
        return self.drpc.set_torrent_priority(result.hash, True) if result.priority == 1 else True

    def _set_torrent_path(self, result):
        path = app.TORRENT_PATH
        return self.drpc.set_torrent_path(result.hash, path) if path else True

    def _set_torrent_pause(self, result):
        return self.drpc.pause_torrent(result.hash) if app.TORRENT_PAUSED else True

    def test_authentication(self):
        """Test connection using authentication.

        :return:
        :rtype: tuple(bool, str)
        """
        if self.connect(True) and self.drpc.test():
            return True, 'Success: Connected and Authenticated'
        else:
            return False, 'Error: Unable to Authenticate!  Please check your config!'


class DelugeRPC(object):
    """Deluge RPC client class."""

    host = 'localhost'
    port = 58846
    username = None
    password = None
    client = None

    def __init__(self, host='localhost', port=58846, username=None, password=None):
        """Constructor.

        :param host:
        :type host: str
        :param port:
        :type port: int
        :param username:
        :type username: str
        :param password:
        :type password: str
        """
        super(DelugeRPC, self).__init__()
        self.host = host
        self.port = port
        self.username = username
        self.password = password

    def connect(self):
        """Connect to the host using synchronousdeluge API."""
        self.client = DelugeClient()
        self.client.connect(self.host, int(self.port), self.username, self.password)

    def test(self):
        """Test connection.

        :return:
        :rtype: bool
        """
        try:
            self.connect()
        except Exception:
            return False
        else:
            return True

    def add_torrent_magnet(self, torrent, options, torrent_hash):
        """Add Torrent magnet and return torrent id/hash.

        :param torrent:
        :type torrent: str
        :param options:
        :type options: dict
        :param torrent_hash:
        :type torrent_hash: str
        :return:
        :rtype: str or bool
        """
        try:
            self.connect()
            torrent_id = self.client.core.add_torrent_magnet(torrent, options).get()
            if not torrent_id:
                torrent_id = self._check_torrent(torrent_hash)
        except Exception:
            return False
        else:
            return torrent_id
        finally:
            if self.client:
                self.disconnect()

    def add_torrent_file(self, filename, torrent, options, torrent_hash):
        """Add Torrent file and return torrent id/hash.

        :param filename:
        :type filename: str
        :param torrent:
        :type torrent: str
        :param options:
        :type options: dict
        :param torrent_hash:
        :type torrent_hash: str
        :return:
        :rtype: str or bool
        """
        try:
            self.connect()
            torrent_id = self.client.core.add_torrent_file(filename, b64encode(torrent), options).get()
            if not torrent_id:
                torrent_id = self._check_torrent(torrent_hash)
        except Exception:
            return False
        else:
            return torrent_id
        finally:
            if self.client:
                self.disconnect()

    def set_torrent_label(self, torrent_id, label):
        """Set Torrent label.

        :param torrent_id:
        :type torrent_id: str
        :param label:
        :type label: str
        :return:
        :rtype: bool
        """
        try:
            self.connect()
            self.client.label.set_torrent(torrent_id, label).get()
        except Exception:
            return False
        else:
            return True
        finally:
            if self.client:
                self.disconnect()

    def set_torrent_path(self, torrent_id, path):
        """Set Torrent path.

        :param torrent_id:
        :type torrent_id: str
        :param path:
        :type path: str
        :return:
        :rtype: bool
        """
        try:
            self.connect()
            self.client.core.set_torrent_move_completed_path(torrent_id, path).get()
            self.client.core.set_torrent_move_completed(torrent_id, 1).get()
        except Exception:
            return False
        else:
            return True
        finally:
            if self.client:
                self.disconnect()

    def set_torrent_priority(self, torrent_id, priority):
        """Set Torrent priority.

        :param torrent_id:
        :type torrent_id: str
        :param priority:
        :type priority: bool
        :return:
        :rtype: bool
        """
        try:
            self.connect()
            if priority:
                self.client.core.queue_top([torrent_id]).get()
        except Exception:
            return False
        else:
            return True
        finally:
            if self.client:
                self.disconnect()

    def set_torrent_ratio(self, torrent_id, ratio):
        """Set Torrent ratio.

        :param torrent_id:
        :type torrent_id: str
        :param ratio:
        :type ratio: float
        :return:
        :rtype: bool
        """
        try:
            self.connect()
            self.client.core.set_torrent_stop_at_ratio(torrent_id, True).get()
            self.client.core.set_torrent_stop_ratio(torrent_id, ratio).get()
        except Exception:
            return False
        else:
            return True
        finally:
            if self.client:
                self.disconnect()

    def pause_torrent(self, torrent_ids):
        """Pause torrent.

        :param torrent_ids:
        :type torrent_ids: list of str
        :return:
        :rtype: bool
        """
        try:
            self.connect()
            self.client.core.pause_torrent(torrent_ids).get()
        except Exception:
            return False
        else:
            return True
        finally:
            if self.client:
                self.disconnect()

    def disconnect(self):
        """Disconnect RPC client."""
        self.client.disconnect()

    def _check_torrent(self, torrent_hash):
        torrent_id = self.client.core.get_torrent_status(torrent_hash, {}).get()
        if torrent_id['hash']:
            logger.debug('DelugeD: Torrent already exists in Deluge')
            return torrent_hash
        return False

api = DelugeDAPI
