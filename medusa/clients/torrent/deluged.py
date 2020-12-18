# coding=utf-8

"""
Deluge Daemon Client.

This client script allows connection to Deluge Daemon directly, completely
circumventing the requirement to use the WebUI.
"""
from __future__ import unicode_literals

import logging
from base64 import b64encode
from builtins import object

from deluge_client import DelugeRPCClient

from medusa import app
from medusa.clients.torrent.deluge import read_torrent_status
from medusa.clients.torrent.generic import GenericClient
from medusa.logger.adapters.style import BraceAdapter


log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class DelugeDAPI(GenericClient):
    """Deluge Daemon API class."""

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
        self.drpc = None

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
            drpc = DelugeRPC(hostname[1], port=hostname[2], username=self.username, password=self.password)
            if drpc.test():
                self.drpc = drpc

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

    def remove_torrent(self, info_hash):
        """Remove torrent from client using given info_hash.

        :param info_hash:
        :type info_hash: string
        :return
        :rtype: bool
        """
        return self.drpc.remove_torrent_data(info_hash)

    def move_torrent(self, info_hash):
        """Set new torrent location given info_hash.

        :param info_hash:
        :type info_hash: string
        :return
        :rtype: bool
        """
        if not app.TORRENT_SEED_LOCATION or not info_hash:
            return

        if not self.connect():
            log.warning('Error while moving torrent. Could not connect to daemon.')
            return

        return self.drpc.move_storage(info_hash, app.TORRENT_SEED_LOCATION)

    def _set_torrent_label(self, result):

        label = app.TORRENT_LABEL.lower()
        if result.series.is_anime:
            label = app.TORRENT_LABEL_ANIME.lower()
        if ' ' in label:
            log.error('{name}: Invalid label. Label must not contain a space',
                      {'name': self.name})
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

    def remove_ratio_reached(self):
        """Remove all Medusa torrents that ratio was reached.

        It loops in all hashes returned from client and check if it is in the snatch history
        if its then it checks if we already processed media from the torrent (episode status `Downloaded`)
        If is a RARed torrent then we don't have a media file so we check if that hash is from an
        episode that has a `Downloaded` status
        """
        log.info('Checking DelugeD torrent status.')

        if not self.connect():
            log.warning('Error while fetching torrents status')
            return

        torrent_data = self.drpc.get_all_torrents()
        info_hash_to_remove = read_torrent_status(torrent_data)
        for info_hash in info_hash_to_remove:
            self.remove_torrent(info_hash)


class DelugeRPC(object):
    """Deluge RPC client class."""

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
        self.port = int(port)
        self.username = username
        self.password = password

    def connect(self):
        """Connect to the host using synchronousdeluge API."""
        self.client = DelugeRPCClient(self.host, self.port, self.username, self.password, decode_utf8=True)
        self.client.connect()

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

    def remove_torrent_data(self, torrent_id):
        """Remove torrent from client using given info_hash.

        :param torrent_id:
        :type torrent_id: str
        :return:
        :rtype: str or bool
        """
        try:
            self.connect()
            self.client.core.remove_torrent(torrent_id, True)
        except Exception:
            return False
        else:
            return True
        finally:
            if self.client:
                self.disconnect()

    def move_storage(self, torrent_id, location):
        """Move torrent to new location and return torrent id/hash.

        :param torrent_id:
        :type torrent_id: str
        :param location:
        :type location: str
        :return:
        :rtype: str or bool
        """
        try:
            self.connect()
            self.client.core.move_storage([torrent_id], location)
        except Exception:
            return False
        else:
            return True
        finally:
            if self.client:
                self.disconnect()

    def add_torrent_magnet(self, torrent, options, info_hash):
        """Add Torrent magnet and return torrent id/hash.

        :param torrent:
        :type torrent: str
        :param options:
        :type options: dict
        :param info_hash:
        :type info_hash: str
        :return:
        :rtype: str or bool
        """
        try:
            self.connect()
            torrent_id = self.client.core.add_torrent_magnet(torrent, options)
            if not torrent_id:
                torrent_id = self._check_torrent(info_hash)
        except Exception:
            raise
            return False
        else:
            return torrent_id
        finally:
            if self.client:
                self.disconnect()

    def add_torrent_file(self, filename, torrent, options, info_hash):
        """Add Torrent file and return torrent id/hash.

        :param filename:
        :type filename: str
        :param torrent:
        :type torrent: str
        :param options:
        :type options: dict
        :param info_hash:
        :type info_hash: str
        :return:
        :rtype: str or bool
        """
        try:
            self.connect()
            torrent_id = self.client.core.add_torrent_file(filename, b64encode(torrent), options)
            if not torrent_id:
                torrent_id = self._check_torrent(info_hash)
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
            self.client.label.set_torrent(torrent_id, label)
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
            self.client.core.set_torrent_move_completed_path(torrent_id, path)
            self.client.core.set_torrent_move_completed(torrent_id, 1)
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
                self.client.core.queue_top([torrent_id])
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
            self.client.core.set_torrent_stop_at_ratio(torrent_id, True)
            self.client.core.set_torrent_stop_ratio(torrent_id, ratio)
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
            self.client.core.pause_torrent(torrent_ids)
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

    def _check_torrent(self, info_hash):
        torrent_id = self.client.core.get_torrent_status(info_hash, {})
        if torrent_id.get('hash'):
            log.debug('DelugeD: Torrent already exists in Deluge')
            return info_hash
        return False

    def get_all_torrents(self):
        """Get all torrents in client.

        :return:
        :rtype: bool
        """
        try:
            self.connect()
            torrents_data = self.client.core.get_torrents_status({}, ('name', 'hash', 'progress', 'state',
                                                                      'ratio', 'stop_ratio', 'is_seed', 'is_finished',
                                                                      'paused', 'files'))
        except Exception:
            return False
        else:
            return torrents_data
        finally:
            if self.client:
                self.disconnect()


api = DelugeDAPI
