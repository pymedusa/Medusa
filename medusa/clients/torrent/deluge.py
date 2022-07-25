# coding=utf-8

"""Deluge Web Client."""
from __future__ import unicode_literals

import json
import logging
from base64 import b64encode

from medusa import app
from medusa.clients.torrent.generic import GenericClient
from medusa.helper.exceptions import DownloadClientConnectionException
from medusa.helpers import (
    get_extension,
    is_already_processed_media,
    is_info_hash_in_history,
    is_info_hash_processed,
    is_media_file,
)
from medusa.logger.adapters.style import BraceAdapter
from medusa.schedulers.download_handler import ClientStatus

from requests.compat import urljoin
from requests.exceptions import RequestException

from six import text_type, viewitems

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


def read_torrent_status(torrent_data):
    """Read torrent status from Deluge and Deluged client."""
    found_torrents = False
    info_hash_to_remove = []
    for torrent in viewitems(torrent_data):
        info_hash = text_type(torrent[0])
        details = torrent[1]
        if not is_info_hash_in_history(info_hash):
            continue
        found_torrents = True

        to_remove = False
        for i in details['files']:
            # Need to check only the media file or the .rar file to avoid checking all .r0* files in history
            if not (is_media_file(i['path']) or get_extension(i['path']) == 'rar'):
                continue
            # Check if media was processed
            # OR check hash in case of RARed torrents
            if is_already_processed_media(i['path']) or is_info_hash_processed(info_hash):
                to_remove = True

        # Don't need to check status if we are not going to remove it.
        if not to_remove:
            log.info('Torrent not yet post-processed. Skipping: {torrent}',
                     {'torrent': details['name']})
            continue

        if details['is_finished']:
            status = 'completed'
        elif details['is_seed']:
            status = 'seeding'
        elif details['paused']:
            status = 'paused'
        else:
            status = details['state']

        if status == 'completed':
            log.info(
                'Torrent completed and reached minimum'
                ' ratio: [{ratio:.3f}/{ratio_limit:.3f}] or'
                ' seed idle limit'
                ' Removing it: [{name}]',
                ratio=details['ratio'],
                ratio_limit=details['stop_ratio'],
                name=details['name']
            )
            info_hash_to_remove.append(info_hash)
        elif status == 'seeding':
            if float(details['ratio']) < float(details['stop_ratio']):
                log.info(
                    'Torrent did not reach minimum'
                    ' ratio: [{ratio:.3f}/{ratio_limit:.3f}].'
                    ' Keeping it: [{name}]',
                    ratio=details['ratio'],
                    ratio_limit=details['stop_ratio'],
                    name=details['name']
                )
            else:
                log.info(
                    'Torrent completed and reached minimum ratio but it'
                    ' was force started again. Current'
                    ' ratio: [{ratio:.3f}/{ratio_limit:.3f}].'
                    ' Keeping it: [{name}]',
                    ratio=details['ratio'],
                    ratio_limit=details['stop_ratio'],
                    name=details['name']
                )
        else:
            log.info('Torrent is {status}. Keeping it: [{name}]', status=status, name=details['name'])

    if not found_torrents:
        log.info('No torrents found that were snatched by Medusa')
    return info_hash_to_remove


class DelugeAPI(GenericClient):
    """Deluge API class."""

    def __init__(self, host=None, username=None, password=None):
        """Constructor.

        :param host:
        :type host: string
        :param username:
        :type username: string
        :param password:
        :type password: string
        """
        super(DelugeAPI, self).__init__('Deluge', host, username, password)
        self.session.headers.update({'Content-Type': 'application/json'})
        self.url = urljoin(self.host, 'json')
        self.version = None

        self._get_auth()

    def _get_auth(self):
        post_data = json.dumps({
            'method': 'auth.login',
            'params': [
                self.password,
            ],
            'id': 1,
        })

        try:
            self.response = self.session.post(self.url, data=post_data.encode('utf-8'),
                                              verify=app.TORRENT_VERIFY_CERT)
        except RequestException:
            return None

        self.auth = self.response.json()['result']

        post_data = json.dumps({
            'method': 'web.connected',
            'params': [],
            'id': 10,
        })

        try:
            self.response = self.session.post(
                self.url,
                data=post_data.encode('utf-8'),
                verify=app.TORRENT_VERIFY_CERT
            )
        except RequestException:
            return None

        connected = self.response.json()['result']

        if not connected:
            post_data = json.dumps({
                'method': 'web.get_hosts',
                'params': [],
                'id': 11,
            })
            try:
                self.response = self.session.post(
                    self.url,
                    data=post_data.encode('utf-8'),
                    verify=app.TORRENT_VERIFY_CERT
                )
            except RequestException:
                return None

            hosts = self.response.json()['result']
            if not hosts:
                log.error('{name}: WebUI does not contain daemons',
                          {'name': self.name})
                return None

            post_data = json.dumps({
                'method': 'web.connect',
                'params': [
                    hosts[0][0],
                ],
                'id': 11,
            })

            try:
                self.response = self.session.post(
                    self.url,
                    data=post_data.encode('utf-8'),
                    verify=app.TORRENT_VERIFY_CERT
                )
            except RequestException:
                return None

            post_data = json.dumps({
                'method': 'web.connected',
                'params': [],
                'id': 10,
            })

            try:
                self.response = self.session.post(
                    self.url,
                    data=post_data.encode('utf-8'),
                    verify=app.TORRENT_VERIFY_CERT
                )
            except RequestException:
                return None

            connected = self.response.json()['result']
            if not connected:
                log.error('{name}: WebUI could not connect to daemon',
                          {'name': self.name})
                return None

        if self.auth:
            self._get_version()

        return self.auth

    def _get_version(self):
        result = self.session.post(
            self.url,
            data=json.dumps({
                'method': 'daemon.get_version',
                'params': {},
                'id': 12
            }),
            verify=app.TORRENT_VERIFY_CERT
        )

        result = result.json()
        if not result.get('result'):
            # Version 1.3.15 needs a different rpc method.
            result = self.session.post(
                self.url,
                data=json.dumps({
                    'method': 'daemon.info',
                    'params': {},
                    'id': 12
                }),
                verify=app.TORRENT_VERIFY_CERT
            )
            result = result.json()

        if result.get('result'):
            split_version = result['result'].split('.')[0:2]
            self.version = tuple(int(x) for x in split_version)
            return self.version

    def _add_torrent_uri(self, result):

        post_data = json.dumps({
            'method': 'core.add_torrent_magnet',
            'params': [
                result.url,
                {},
            ],
            'id': 2,
        })

        if not self._request(method='post', data=post_data):
            return False

        data = self.response.json()
        result.hash = data['result']

        return data['result']

    def _add_torrent_file(self, result):

        post_data = json.dumps({
            'method': 'core.add_torrent_file',
            'params': [
                '{name}.torrent'.format(name=result.name),
                b64encode(result.content).decode('utf-8'),
                {},
            ],
            'id': 2,
        })

        if not self._request(method='post', data=post_data):
            return False

        data = self.response.json()
        result.hash = data['result']

        return data['result']

    def move_torrent(self, info_hash):
        """Set new torrent location given info_hash.

        :param info_hash:
        :type info_hash: string
        :return
        :rtype: bool
        """
        if not app.TORRENT_SEED_LOCATION or not info_hash:
            return

        post_data = json.dumps({
            'method': 'core.move_storage',
            'params': [
                [info_hash],
                app.TORRENT_SEED_LOCATION,
            ],
            'id': 72,
        })

        return not self.response.json()['error'] if self._request(method='post', data=post_data) else False

    def _remove(self, info_hash, from_disk=False):
        """Remove torrent from client using given info_hash.

        :param info_hash:
        :type info_hash: string
        :return
        :rtype: bool
        """
        post_data = json.dumps({
            'method': 'core.remove_torrent',
            'params': [
                info_hash,
                from_disk,
            ],
            'id': 5,
        })

        self._request(method='post', data=post_data)
        return not self.response.json()['error']

    def remove_torrent(self, info_hash):
        """Remove torrent from client using given info_hash.

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

    def _set_torrent_label(self, result):

        label = app.TORRENT_LABEL.lower()
        if result.series.is_anime:
            label = app.TORRENT_LABEL_ANIME.lower()
        if ' ' in label:
            log.error('{name}: Invalid label. Label must not contain a space',
                      {'name': self.name})

            return False

        if label:
            # check if label already exists and create it if not
            post_data = json.dumps({
                'method': 'label.get_labels',
                'params': [],
                'id': 3,
            })

            self._request(method='post', data=post_data)
            labels = self.response.json()['result']

            if labels is not None:
                if label not in labels:
                    log.debug('{name}: {label} label does not exist in Deluge'
                              ' we must add it',
                              {'name': self.name, 'label': label})
                    post_data = json.dumps({
                        'method': 'label.add',
                        'params': [
                            label,
                        ],
                        'id': 4,
                    })

                    self._request(method='post', data=post_data)
                    log.debug('{name}: {label} label added to Deluge',
                              {'name': self.name, 'label': label})

                # add label to torrent
                post_data = json.dumps({
                    'method': 'label.set_torrent',
                    'params': [
                        result.hash,
                        label,
                    ],
                    'id': 5,
                })

                self._request(method='post', data=post_data)
                log.debug('{name}: {label} label added to torrent',
                          {'name': self.name, 'label': label})

            else:
                log.debug('{name}: label plugin not detected',
                          {'name': self.name})
                return False

        return not self.response.json()['error']

    def _set_torrent_ratio(self, result):

        ratio = result.ratio
        if not ratio:
            return

        # blank is default client ratio, so we also shouldn't set ratio
        if float(ratio) >= 0:
            if self.version >= (2, 0):
                post_data = json.dumps({
                    'method': 'core.set_torrent_options',
                    'params': [
                        result.hash,
                        {'stop_at_ratio': True},
                    ],
                    'id': 5,
                })
            else:
                post_data = json.dumps({
                    'method': 'core.set_torrent_stop_ratio',
                    'params': [
                        result.hash,
                        True,
                    ],
                    'id': 6,
                })

            self._request(method='post', data=post_data)

            # if unable to set_torrent_options return False
            # No reason to set ratio.
            if self.response.json()['error']:
                return False

            if self.version >= (2, 0):
                post_data = json.dumps({
                    'method': 'core.set_torrent_options',
                    'params': [
                        result.hash,
                        {'stop_ratio': float(ratio)},
                    ],
                    'id': 5,
                })
            else:
                post_data = json.dumps({
                    'method': 'core.set_torrent_stop_ratio',
                    'params': [
                        result.hash,
                        float(ratio),
                    ],
                    'id': 5,
                })

            self._request(method='post', data=post_data)

            return not self.response.json()['error']

        elif float(ratio) == -1:
            # Disable stop at ratio to seed forever
            if self.version >= (2, 0):
                post_data = json.dumps({
                    'method': 'core.set_torrent_options',
                    'params': [
                        result.hash,
                        {'stop_at_ratio': False},
                    ],
                    'id': 5,
                })
            else:
                post_data = json.dumps({
                    'method': 'core.set_torrent_stop_at_ratio',
                    'params': [result.hash, False],
                    'id': 5
                })

            self._request(method='post', data=post_data)

            return not self.response.json()['error']

        return True

    def _set_torrent_path(self, result):

        if app.TORRENT_PATH:
            if self.version >= (2, 0):
                post_data = json.dumps({
                    'method': 'core.set_torrent_options ',
                    'params': [
                        result.hash,
                        {'move_completed': True},
                    ],
                    'id': 7,
                })
            else:
                post_data = json.dumps({
                    'method': 'core.set_torrent_move_completed',
                    'params': [
                        result.hash,
                        True,
                    ],
                    'id': 7,
                })

            self._request(method='post', data=post_data)

            if self.version >= (2, 0):
                post_data = json.dumps({
                    'method': 'core.set_torrent_options',
                    'params': [
                        result.hash,
                        {'move_completed_path': app.TORRENT_PATH},
                    ],
                    'id': 8,
                })
            else:
                post_data = json.dumps({
                    'method': 'core.set_torrent_move_completed_path',
                    'params': [
                        result.hash,
                        app.TORRENT_PATH,
                    ],
                    'id': 8,
                })

            self._request(method='post', data=post_data)

            return not self.response.json()['error']

        return True

    def _set_torrent_pause(self, result):
        """Pause torrent after adding, if setting app.TORRENT_PAUSED enabled."""
        if app.TORRENT_PAUSED:
            return self.pause_torrent(result.hash)
        return True

    def pause_torrent(self, info_hash):
        """Pause a torrent by info_hash."""
        post_data = json.dumps({
            'method': 'core.pause_torrent',
            'params': [
                [info_hash],
            ],
            'id': 9,
        })

        self._request(method='post', data=post_data)
        return not self.response.json()['error']

    def _torrent_properties(self, info_hash):
        """Get torrent properties."""
        post_data = json.dumps({
            'method': 'core.get_torrent_status',
            'params': [
                info_hash,
                ['name', 'hash', 'progress', 'state', 'ratio', 'stop_ratio',
                 'is_seed', 'is_finished', 'paused', 'files', 'download_location'],
            ],
            'id': 72,
        })

        log.debug('Checking {client} torrent {hash} status.', {'client': self.name, 'hash': info_hash})

        try:
            if not self._request(method='post', data=post_data) or self.response.json()['error']:
                log.warning('Error while fetching torrent {hash} status.', {'hash': info_hash})
                return
        except RequestException as error:
            raise DownloadClientConnectionException(f'Error while fetching torrent info_hash {info_hash}. Error: {error}')

        return self.response.json()['result']

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
        torrent = self._torrent_properties(info_hash)
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


api = DelugeAPI
