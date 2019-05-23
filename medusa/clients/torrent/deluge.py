# coding=utf-8

"""Deluge Web Client."""
from __future__ import unicode_literals

import json
import logging
from base64 import b64encode

from medusa import app
from medusa.clients.torrent.generic import GenericClient
from medusa.helpers import (
    get_extension,
    is_already_processed_media,
    is_info_hash_in_history,
    is_info_hash_processed,
    is_media_file,
)
from medusa.logger.adapters.style import BraceAdapter

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

        return self.auth

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

    def remove_torrent(self, info_hash):
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
                True,
            ],
            'id': 5,
        })

        self._request(method='post', data=post_data)
        return not self.response.json()['error']

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

        ratio = None
        if result.ratio:
            ratio = result.ratio

        # blank is default client ratio, so we also shouldn't set ratio
        if ratio and float(ratio) >= 0:
            post_data = json.dumps({
                'method': 'core.set_torrent_stop_at_ratio',
                'params': [
                    result.hash,
                    True,
                ],
                'id': 5,
            })

            self._request(method='post', data=post_data)

            # if unable to set_torrent_stop_at_ratio return False
            # No reason to set ratio.
            if self.response.json()['error']:
                return False

            post_data = json.dumps({
                'method': 'core.set_torrent_stop_ratio',
                'params': [
                    result.hash,
                    float(ratio),
                ],
                'id': 6,
            })

            self._request(method='post', data=post_data)

            return not self.response.json()['error']

        elif ratio and float(ratio) == -1:
            # Disable stop at ratio to seed forever
            post_data = json.dumps({'method': 'core.set_torrent_stop_at_ratio',
                                    'params': [result.hash, False],
                                    'id': 5})

            self._request(method='post', data=post_data)

            return not self.response.json()['error']

        return True

    def _set_torrent_path(self, result):

        if app.TORRENT_PATH:
            post_data = json.dumps({
                'method': 'core.set_torrent_move_completed',
                'params': [
                    result.hash,
                    True,
                ],
                'id': 7,
            })

            self._request(method='post', data=post_data)

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

        if app.TORRENT_PAUSED:
            post_data = json.dumps({
                'method': 'core.pause_torrent',
                'params': [
                    [result.hash],
                ],
                'id': 9,
            })

            self._request(method='post', data=post_data)

            return not self.response.json()['error']

        return True

    def remove_ratio_reached(self):
        """Remove all Medusa torrents that ratio was reached.

        It loops in all hashes returned from client and check if it is in the snatch history
        if its then it checks if we already processed media from the torrent (episode status `Downloaded`)
        If is a RARed torrent then we don't have a media file so we check if that hash is from an
        episode that has a `Downloaded` status
        """
        post_data = json.dumps({
            'method': 'core.get_torrents_status',
            'params': [
                {},
                ['name', 'hash', 'progress', 'state', 'ratio', 'stop_ratio',
                 'is_seed', 'is_finished', 'paused', 'files'],
            ],
            'id': 72,
        })

        log.info('Checking Deluge torrent status.')
        if self._request(method='post', data=post_data):
            if self.response.json()['error']:
                log.warning('Error while fetching torrents status')
                return
            else:
                torrent_data = self.response.json()['result']
                info_hash_to_remove = read_torrent_status(torrent_data)
                for info_hash in info_hash_to_remove:
                    self.remove_torrent(info_hash)


api = DelugeAPI
