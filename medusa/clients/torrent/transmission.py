# coding=utf-8

"""Transmission Client."""

from __future__ import unicode_literals

import json
import logging
import os
import re
from base64 import b64encode

from medusa import app
from medusa.clients.torrent.generic import GenericClient
from medusa.helper.exceptions import DownloadClientConnectionException
from medusa.logger.adapters.style import BraceAdapter
from medusa.schedulers.download_handler import ClientStatus

import requests.exceptions
from requests.compat import urljoin


log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class TransmissionAPI(GenericClient):
    """Transmission API class."""

    def __init__(self, host=None, username=None, password=None):
        """Transmission constructor.

        :param host:
        :type host: string
        :param username:
        :type username: string
        :param password:
        :type password: string
        """
        super(TransmissionAPI, self).__init__('Transmission', host, username, password)

        self.rpcurl = self.rpcurl.strip('/')
        self.url = urljoin(self.host, self.rpcurl + '/rpc')

        self._get_auth()

    def check_response(self):
        """Check if response is a valid json and its a success one."""
        try:
            return self.response.json()['result'] == 'success'
        except ValueError:
            return False

    def _get_auth(self):

        post_data = json.dumps({
            'method': 'session-get',
            'user': self.username,
            'password': self.password
        })

        try:
            self.response = self.session.post(self.url, data=post_data.encode('utf-8'), timeout=120,
                                              verify=app.TORRENT_VERIFY_CERT)
        except requests.exceptions.ConnectionError as error:
            log.warning('{name}: Unable to connect. {error}',
                        {'name': self.name, 'error': error})
            return False
        except requests.exceptions.Timeout as error:
            log.warning('{name}: Connection timed out. {error}',
                        {'name': self.name, 'error': error})
            return False

        if self.response is None:
            return False

        if self.response.status_code == 200:
            return self.response

        auth_match = re.search(r'X-Transmission-Session-Id:\s*(\w+)', self.response.text)

        if not auth_match:
            return False

        self.auth = auth_match.group(1)

        self.session.headers.update({'x-transmission-session-id': self.auth})

        # Validating Transmission authorization
        post_data = json.dumps({
            'arguments': {},
            'method': 'session-get',
        })

        self._request(method='post', data=post_data)

        return self.auth

    def _add_torrent_uri(self, result):

        arguments = {
            'filename': result.url,
            'paused': 1 if app.TORRENT_PAUSED else 0
        }
        if os.path.isabs(app.TORRENT_PATH):
            arguments['download-dir'] = app.TORRENT_PATH

        post_data = json.dumps({
            'arguments': arguments,
            'method': 'torrent-add',
        })

        self._request(method='post', data=post_data)

        return self.check_response()

    def _add_torrent_file(self, result):

        arguments = {
            'metainfo': b64encode(result.content).decode('utf-8'),
            'paused': 1 if app.TORRENT_PAUSED else 0
        }

        if os.path.isabs(app.TORRENT_PATH):
            arguments['download-dir'] = app.TORRENT_PATH

        post_data = json.dumps({
            'arguments': arguments,
            'method': 'torrent-add',
        })

        self._request(method='post', data=post_data)

        return self.check_response()

    def _set_torrent_ratio(self, result):

        ratio = result.ratio

        arguments = {
            'ids': [result.hash]
        }

        if ratio:
            # Use transmission global
            if float(ratio) == -1:
                arguments['seedRatioMode'] = 0
            # Unlimited
            elif float(ratio) == 0:
                arguments['seedRatioLimit'] = 0
                arguments['seedRatioMode'] = 2
            # Set ratio
            elif float(ratio) >= 0:
                arguments['seedRatioLimit'] = float(ratio)
                arguments['seedRatioMode'] = 1

        post_data = json.dumps({
            'arguments': arguments,
            'method': 'torrent-set',
        })

        self._request(method='post', data=post_data)

        return self.check_response()

    def _set_torrent_seed_time(self, result):

        if app.TORRENT_SEED_TIME and app.TORRENT_SEED_TIME != -1:
            time = int(60 * float(app.TORRENT_SEED_TIME))
            arguments = {
                'ids': [result.hash],
                'seedIdleLimit': time,
                'seedIdleMode': 1,
            }

            post_data = json.dumps({
                'arguments': arguments,
                'method': 'torrent-set',
            })

            self._request(method='post', data=post_data)

            return self.check_response()
        else:
            return True

    def _set_torrent_priority(self, result):

        arguments = {'ids': [result.hash]}

        if result.priority == -1:
            arguments['priority-low'] = []
        elif result.priority == 1:
            # set high priority for all files in torrent
            arguments['priority-high'] = []
            # move torrent to the top if the queue
            arguments['queuePosition'] = 0
            if app.TORRENT_HIGH_BANDWIDTH:
                arguments['bandwidthPriority'] = 1
        else:
            arguments['priority-normal'] = []

        post_data = json.dumps({
            'arguments': arguments,
            'method': 'torrent-set',
        })

        self._request(method='post', data=post_data)

        return self.check_response()

    def _set_torrent_pause(self, result):
        if app.TORRENT_PAUSED:
            self.pause_torrent(result.hash)
        return True

    def pause_torrent(self, info_hash):
        """Pause torrent."""
        post_data = json.dumps({
            'arguments': {'ids': [info_hash]},
            'method': 'torrent-stop'
        })

        self._request(method='post', data=post_data)

        return self.check_response()

    def _remove(self, info_hash, from_disk=False):
        """Remove torrent from client using given info_hash.

        :param info_hash:
        :type info_hash: string
        :return
        :rtype: bool
        """
        arguments = {
            'ids': [info_hash],
            'delete-local-data': int(from_disk),
        }

        post_data = json.dumps({
            'arguments': arguments,
            'method': 'torrent-remove',
        })

        self._request(method='post', data=post_data)

        return self.check_response()

    def remove_torrent(self, info_hash):
        """Remove torrent from client and disk using given info_hash.

        :param info_hash:
        :type info_hash: string
        :return
        :rtype: bool
        """
        return self._remove(info_hash)

    def remove_torrent_data(self, info_hash):
        """Remove torrent from client and disk using given info_hash.

        :param info_hash:
        :type info_hash: string
        :return
        :rtype: bool
        """
        return self._remove(info_hash, from_disk=True)

    def move_torrent(self, info_hash):
        """Set new torrent location given info_hash.

        :param info_hash:
        :type info_hash: string
        :return
        :rtype: bool
        """
        if not app.TORRENT_SEED_LOCATION or not info_hash:
            return

        arguments = {
            'ids': [info_hash],
            'location': app.TORRENT_SEED_LOCATION,
            'move': 'true'
        }

        post_data = json.dumps({
            'arguments': arguments,
            'method': 'torrent-set-location',
        })

        self._request(method='post', data=post_data)

        return self.check_response()

    def _torrent_properties(self, info_hash):
        """Get torrent properties."""
        log.debug('Checking {client} torrent {hash} status.', {'client': self.name, 'hash': info_hash})

        return_params = {
            'ids': info_hash,
            'fields': ['name', 'hashString', 'percentDone', 'status', 'percentDone', 'downloadDir',
                       'isStalled', 'errorString', 'seedRatioLimit', 'torrent-file', 'name',
                       'isFinished', 'uploadRatio', 'seedIdleLimit', 'activityDate']
        }

        post_data = json.dumps({'arguments': return_params, 'method': 'torrent-get'})

        if not self._request(method='post', data=post_data) or not self.check_response():
            raise DownloadClientConnectionException(f'Error while fetching torrent {info_hash} status.')

        torrent = self.response.json()['arguments']['torrents']
        if not torrent:
            log.debug('Could not locate torrent with {hash} status.', {'hash': info_hash})
            return

        return torrent[0]

    def torrent_completed(self, info_hash):
        """Check if torrent has finished downloading."""
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

        Status codes:
        ```
            0: "Stopped"
            1: "Check waiting"
            2: "Checking"
            3: "Download waiting"
            4: "Downloading"
            5: "Seed waiting"
            6: "Seeding"
        ```
        """
        torrent = self._torrent_properties(info_hash)
        if not torrent:
            return

        client_status = ClientStatus()
        if torrent['status'] == 4:
            client_status.set_status_string('Downloading')

        if torrent['status'] == 0:
            client_status.set_status_string('Paused')

        # if torrent['status'] == ?:
        #     client_status.set_status_string('Failed')

        if torrent['status'] == 6:
            client_status.set_status_string('Completed')

        if torrent['status'] == 0 and torrent['isFinished']:
            client_status.set_status_string('Seeded')

        # Store ratio
        client_status.ratio = torrent['uploadRatio'] * 1.0

        # Store progress
        client_status.progress = int(torrent['percentDone'] * 100)

        # Store destination
        client_status.destination = torrent['downloadDir']

        # Store resource
        client_status.resource = torrent['name']

        return client_status


api = TransmissionAPI
