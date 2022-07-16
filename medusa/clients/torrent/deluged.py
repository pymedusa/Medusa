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
from medusa.helper.exceptions import DownloadClientConnectionException
from medusa.logger.adapters.style import BraceAdapter
from medusa.schedulers.download_handler import ClientStatus

from requests.exceptions import RequestException

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class DelugeDAPI(GenericClient):
    """Deluge Daemon API class."""

    def __init__(self, host=None, username=None, password=None):
        """Deluge deamon Constructor.

        :param host:
        :type host: string
        :param username:
        :type username: string
        :param password:
        :type password: string
        """
        super(DelugeDAPI, self).__init__('DelugeD', host, username, password)
        self.drpc = None

        self._get_auth()

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
        if app.TORRENT_PAUSED:
            return self.pause_torrent(result.hash)
        return True

    def pause_torrent(self, info_hash):
        """Pause torrent."""
        return self.drpc.pause_torrent(info_hash)

    def test_authentication(self):
        """Test connection using authentication.

        :return:
        :rtype: tuple(bool, str)
        """
        if self.connect(True) and self.drpc.test():
            return True, 'Success: Connected and Authenticated'
        else:
            return False, 'Error: Unable to Authenticate! Please check your config!'

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

        torrent_data = self.drpc._torrent_properties()
        info_hash_to_remove = read_torrent_status(torrent_data)
        for info_hash in info_hash_to_remove:
            self.remove_torrent(info_hash)

    def torrent_completed(self, info_hash):
        """Check if the torrent has finished downloading."""
        get_status = self.get_status(info_hash)
        if not get_status:
            return False

        return str(get_status) == 'Completed'

    def torrent_seeded(self, info_hash):
        """Check if the torrent has finished seeding."""
        get_status = self.get_status(info_hash)
        if not get_status:
            return False

        return str(get_status) == 'Seeded'

    def torrent_ratio(self, info_hash):
        """Get torrent ratio."""
        get_status = self.get_status(info_hash)
        if not get_status:
            return False

        return get_status.ratio

    def torrent_progress(self, info_hash):
        """Get torrent download progress."""
        get_status = self.get_status(info_hash)
        if not get_status:
            return False

        return get_status.progress

    def get_status(self, info_hash):
        """
        Return torrent status.

        Example result:
        ```
            'hash': '35b814f1438054158b0bd07d305dc0edeb20b704'
            'is_finished': False
            'ratio': 0.0
            'paused': False
            'name': '[FFA] Haikyuu!!: To the Top 2nd Season - 11 [1080p][HEVC][Multiple Subtitle].mkv'
            'stop_ratio': 2.0
            'state': 'Downloading'
            'progress': 23.362499237060547
            'files': ({'index': 0, 'offset': 0, 'path': '[FFA] Haikyuu!!: To ...title].mkv', 'size': 362955692},)
            'is_seed': False
        ```
        """
        if not self.connect():
            raise DownloadClientConnectionException(f'Error while fetching torrent info_hash {info_hash}')

        torrent = self.drpc._torrent_properties(info_hash)
        if not torrent:
            return False

        client_status = ClientStatus()
        if torrent['state'] == 'Downloading':
            client_status.add_status_string('Downloading')

        if torrent['paused']:
            client_status.add_status_string('Paused')

        # TODO: Find out which state the torrent get's when it fails.
        # if torrent[1] & 16:
        #     client_status.add_status_string('Failed')

        if torrent['is_finished']:
            client_status.add_status_string('Completed')

        if torrent['ratio'] >= torrent['stop_ratio']:
            client_status.add_status_string('Seeded')

        # Store ratio
        client_status.ratio = torrent['ratio']

        # Store progress
        client_status.progress = int(torrent['progress'])

        # Store destination
        if torrent.get('download_location'):
            client_status.destination = torrent['download_location']

        # Store resource
        client_status.resource = torrent['name']

        return client_status


class DelugeRPC(object):
    """Deluge RPC client class."""

    def __init__(self, host='localhost', port=58846, username=None, password=None):
        """Deluge RPC Constructor.

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
        try:
            self.client = DelugeRPCClient(self.host, self.port, self.username, self.password, decode_utf8=True)
            self.client.connect()
        except Exception as error:
            log.warning('Error while trying to connect to deluge daemon. Error: {error}', {'error': error})
            raise

    def get_version(self):
        """Return the deluge daemon major, minor version as a tuple."""
        version = None
        try:
            version = self.client.daemon.get_version()
            split_version = version.split('.')[0:2]
            version = tuple(int(x) for x in split_version)
        except Exception as error:
            log.warning('Error while trying to get the deluge daemon version. Error: {error}', {'error': error})
            raise

        return version

    def disconnect(self):
        """Disconnect RPC client."""
        self.client.disconnect()

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
        except Exception:
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
            if self.get_version() >= (2, 0):
                self.client.core.set_torrent_options(torrent_id, {'completed_path': path})
                self.client.core.set_torrent_options(torrent_id, {'move_completed': 1})
            else:
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
            # blank is default client ratio, so we also shouldn't set ratio
            self.connect()
            version = self.get_version()
            if float(ratio) >= 0:
                if version >= (2, 0):
                    self.client.core.set_torrent_options(torrent_id, {'stop_at_ratio': True})
                else:
                    self.client.core.set_torrent_stop_at_ratio(torrent_id, True)

                if version >= (2, 0):
                    self.client.core.set_torrent_options(torrent_id, {'stop_ratio': ratio})
                else:
                    self.client.core.set_torrent_stop_ratio(torrent_id, ratio)

            elif float(ratio) == -1:
                # Disable stop at ratio to seed forever
                if version >= (2, 0):
                    self.client.core.set_torrent_options(torrent_id, {'stop_at_ratio': False})
                else:
                    self.client.core.set_torrent_stop_at_ratio(torrent_id, False)
        except Exception:
            return False
        else:
            return True
        finally:
            if self.client:
                self.disconnect()

    def remove_torrent_data(self, torrent_id):
        """Remove torrent from client and disk using given info_hash.

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

    def remove_torrent(self, torrent_id):
        """Remove torrent from client using given info_hash.

        :param torrent_id:
        :type torrent_id: str
        :return:
        :rtype: str or bool
        """
        try:
            self.connect()
            self.client.core.remove_torrent(torrent_id, False)
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

    def _torrent_properties(self, info_hash):
        """Get torrent properties."""
        try:
            self.connect()
            log.debug('Checking DelugeD torrent {hash} status.', {'hash': info_hash})
            torrent_data = self.client.core.get_torrent_status(
                info_hash, ('name', 'hash', 'progress', 'state', 'ratio', 'stop_ratio',
                            'is_seed', 'is_finished', 'paused', 'files', 'download_location'))
        except RequestException as error:
            raise DownloadClientConnectionException(f'Error while fetching torrent info_hash {info_hash}. Error: {error}')
        except Exception:
            log.warning('Error while fetching torrent {hash} status.', {'hash': info_hash})
            return
        else:
            return torrent_data
        finally:
            if self.client:
                self.disconnect()


api = DelugeDAPI
