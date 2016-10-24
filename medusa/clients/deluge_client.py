# coding=utf-8
# Author: Mr_Orange <mr_orange@hotmail.it>
#
# This file is part of Medusa.
#
# Medusa is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Medusa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Medusa. If not, see <http://www.gnu.org/licenses/>.
"""Deluge Web Client."""

from __future__ import unicode_literals

import json
import logging
from base64 import b64encode

import medusa as app
from requests.exceptions import RequestException
from .generic import GenericClient


logger = logging.getLogger(__name__)


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
        self.url = '{host}json'.format(host=self.host)

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
            self.response = self.session.post(self.url, data=post_data.encode('utf-8'),
                                              verify=app.TORRENT_VERIFY_CERT)
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
                self.response = self.session.post(self.url, data=post_data.encode('utf-8'),
                                                  verify=app.TORRENT_VERIFY_CERT)
            except RequestException:
                return None

            hosts = self.response.json()['result']
            if not hosts:
                logger.error('{name}: WebUI does not contain daemons', name=self.name)
                return None

            post_data = json.dumps({
                'method': 'web.connect',
                'params': [
                    hosts[0][0],
                ],
                'id': 11,
            })

            try:
                self.response = self.session.post(self.url, data=post_data.encode('utf-8'),
                                                  verify=app.TORRENT_VERIFY_CERT)
            except RequestException:
                return None

            post_data = json.dumps({
                'method': 'web.connected',
                'params': [],
                'id': 10,
            })

            try:
                self.response = self.session.post(self.url, data=post_data.encode('utf-8'),
                                                  verify=app.TORRENT_VERIFY_CERT)
            except RequestException:
                return None

            connected = self.response.json()['result']
            if not connected:
                logger.error('{name}: WebUI could not connect to daemon', name=self.name)
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

        self._request(method='post', data=post_data)

        result.hash = self.response.json()['result']

        return self.response.json()['result']

    def _add_torrent_file(self, result):

        post_data = json.dumps({
            'method': 'core.add_torrent_file',
            'params': [
                '{name}.torrent'.format(name=result.name),
                b64encode(result.content),
                {},
            ],
            'id': 2,
        })

        self._request(method='post', data=post_data)

        result.hash = self.response.json()['result']

        return self.response.json()['result']

    def _remove_torrent(self, torrent_hash):

        post_data = json.dumps({
            'method': 'core.remove_torrent',
            'params': [
                torrent_hash,
                True,
            ],
            'id': 5,
        })

        self._request(method='post', data=post_data)
        return not self.response.json()['error']

    def _set_torrent_label(self, result):

        label = app.TORRENT_LABEL.lower()
        if result.show.is_anime:
            label = app.TORRENT_LABEL_ANIME.lower()
        if ' ' in label:
            logger.error('{name}: Invalid label. Label must not contain a space', name=self.name)
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
                    logger.debug('{name}: {label} label does not exist in Deluge we must add it', name=self.name, label=label)
                    post_data = json.dumps({
                        'method': 'label.add',
                        'params': [
                            label,
                        ],
                        'id': 4,
                    })

                    self._request(method='post', data=post_data)
                    logger.debug('{name}: {label} label added to Deluge', name=self.name, label=label)

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
                logger.debug('{name}: {label} label added to torrent', name=self.name, label=label)
            else:
                logger.debug('{name}: label plugin not detected', name=self.name)
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

            # Return false if we couldn't enable setting set_torrent_stop_at_ratio. No reason to set ratio.
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
            post_data = json.dumps({"method": "core.set_torrent_stop_at_ratio",
                                    "params": [result.hash, False],
                                    "id": 5})

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


api = DelugeAPI
