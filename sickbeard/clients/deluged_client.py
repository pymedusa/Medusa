# coding=utf-8
# Author: Paul Wollaston
# Contributions: Luke Mullan
#
# This client script allows connection to Deluge Daemon directly, completely
# circumventing the requirement to use the WebUI.

from __future__ import unicode_literals

from base64 import b64encode

import sickbeard
from sickbeard import logger
from sickbeard.clients.generic import GenericClient
from synchronousdeluge import DelugeClient


class DelugeDAPI(GenericClient):

    drpc = None

    def __init__(self, host=None, username=None, password=None):
        super(DelugeDAPI, self).__init__('DelugeD', host, username, password)

    def _get_auth(self):
        return True if self.connect() else None

    def connect(self, reconnect=False):
        hostname = self.host.replace('/', '').split(':')

        if not self.drpc or reconnect:
            self.drpc = DelugeRPC(hostname[1], port=hostname[2], username=self.username, password=self.password)

        return self.drpc

    def _add_torrent_uri(self, result):
        options = {
            'add_paused': sickbeard.TORRENT_PAUSED
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
            'add_paused': sickbeard.TORRENT_PAUSED
        }

        remote_torrent = self.drpc.add_torrent_file('{name}.torrent'.format(name=result.name),
                                                    result.content, options, result.hash)

        if remote_torrent:
            result.hash = remote_torrent

        return remote_torrent or None

    def _set_torrent_label(self, result):

        label = sickbeard.TORRENT_LABEL.lower()
        if result.show.is_anime:
            label = sickbeard.TORRENT_LABEL_ANIME.lower()
        if ' ' in label:
            logger.log('{name}: Invalid label. Label must not contain a space'.format
                       (name=self.name), logger.ERROR)
            return False

        return self.drpc.set_torrent_label(result.hash, label) if label else True

    def _set_torrent_ratio(self, result):
        return self.drpc.set_torrent_ratio(result.hash, float(result.ratio)) if result.ratio else True

    def _set_torrent_priority(self, result):
        return self.drpc.set_torrent_priority(result.hash, True) if result.priority == 1 else True

    def _set_torrent_path(self, result):
        path = sickbeard.TORRENT_PATH
        return self.drpc.set_torrent_path(result.hash, path) if path else True

    def _set_torrent_pause(self, result):
        return self.drpc.pause_torrent(result.hash) if sickbeard.TORRENT_PAUSED else True

    def test_authentication(self):
        if self.connect(True) and self.drpc.test():
            return True, 'Success: Connected and Authenticated'
        else:
            return False, 'Error: Unable to Authenticate!  Please check your config!'


class DelugeRPC(object):

    host = 'localhost'
    port = 58846
    username = None
    password = None
    client = None

    def __init__(self, host='localhost', port=58846, username=None, password=None):
        super(DelugeRPC, self).__init__()

        self.host = host
        self.port = port
        self.username = username
        self.password = password

    def connect(self):
        self.client = DelugeClient()
        self.client.connect(self.host, int(self.port), self.username, self.password)

    def test(self):
        try:
            self.connect()
        except Exception:
            return False
        else:
            return True

    def add_torrent_magnet(self, torrent, options, torrent_hash):
        try:
            self.connect()
            torrent_id = self.client.core.add_torrent_magnet(torrent, options).get()  # pylint:disable=no-member
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
        try:
            self.connect()
            torrent_id = self.client.core.add_torrent_file(filename, b64encode(torrent), options).get()  # pylint:disable=no-member
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
        try:
            self.connect()
            self.client.label.set_torrent(torrent_id, label).get()  # pylint:disable=no-member
        except Exception:
            return False
        else:
            return True
        finally:
            if self.client:
                self.disconnect()

    def set_torrent_path(self, torrent_id, path):
        try:
            self.connect()
            self.client.core.set_torrent_move_completed_path(torrent_id, path).get()  # pylint:disable=no-member
            self.client.core.set_torrent_move_completed(torrent_id, 1).get()  # pylint:disable=no-member
        except Exception:
            return False
        else:
            return True
        finally:
            if self.client:
                self.disconnect()

    def set_torrent_priority(self, torrent_ids, priority):
        try:
            self.connect()
            if priority:
                self.client.core.queue_top([torrent_ids]).get()  # pylint:disable=no-member
        except Exception:
            return False
        else:
            return True
        finally:
            if self.client:
                self.disconnect()

    def set_torrent_ratio(self, torrent_ids, ratio):
        try:
            self.connect()
            self.client.core.set_torrent_stop_at_ratio(torrent_ids, True).get()  # pylint:disable=no-member
            self.client.core.set_torrent_stop_ratio(torrent_ids, ratio).get()  # pylint:disable=no-member
        except Exception:
            return False
        else:
            return True
        finally:
            if self.client:
                self.disconnect()

    def pause_torrent(self, torrent_ids):
        try:
            self.connect()
            self.client.core.pause_torrent(torrent_ids).get()  # pylint:disable=no-member
        except Exception:
            return False
        else:
            return True
        finally:
            if self.client:
                self.disconnect()

    def disconnect(self):
        self.client.disconnect()

    def _check_torrent(self, torrent_hash):
        torrent_id = self.client.core.get_torrent_status(torrent_hash, {}).get()  # pylint:disable=no-member
        if torrent_id['hash']:
            logger.log('DelugeD: Torrent already exists in Deluge', logger.DEBUG)
            return torrent_hash
        return False

api = DelugeDAPI()
