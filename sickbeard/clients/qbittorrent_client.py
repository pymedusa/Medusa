# coding=utf-8

# Author: Mr_Orange <mr_orange@hotmail.it>
# URL: http://code.google.com/p/sickbeard/
#
# This file is part of SickRage.
#
# SickRage is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# SickRage is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with SickRage. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

from requests.auth import HTTPDigestAuth

import sickbeard
from sickbeard.clients.generic import GenericClient


class qbittorrentAPI(GenericClient):

    def __init__(self, host=None, username=None, password=None):

        super(qbittorrentAPI, self).__init__('qbittorrent', host, username, password)

        self.url = self.host
        self.session.auth = HTTPDigestAuth(self.username, self.password)

    @property
    def api(self):
        try:
            self.url = '{host}version/api'.format(host=self.host)
            version = int(self.session.get(self.url, verify=sickbeard.TORRENT_VERIFY_CERT).content)
        except Exception:
            version = 1
        return version

    def _get_auth(self):

        if self.api > 1:
            self.url = '{host}login'.format(host=self.host)
            data = {
                'username': self.username,
                'password': self.password,
            }
            try:
                self.response = self.session.post(self.url, data=data)
            except Exception:
                return None

        else:
            try:
                self.response = self.session.get(self.host, verify=sickbeard.TORRENT_VERIFY_CERT)
                self.auth = self.response.content
            except Exception:
                return None

        self.session.cookies = self.response.cookies
        self.auth = self.response.content

        return self.auth if not self.response.status_code == 404 else None

    def _add_torrent_uri(self, result):

        self.url = '{host}command/download'.format(host=self.host)
        data = {
            'urls': result.url,
        }
        return self._request(method='post', data=data, cookies=self.session.cookies)

    def _add_torrent_file(self, result):

        self.url = '{host}command/upload'.format(host=self.host)
        files = {
            'torrents': (
                '{result}.torrent'.format(result=result.name),
                result.content,
            ),
        }
        return self._request(method='post', files=files, cookies=self.session.cookies)

    def _set_torrent_label(self, result):

        label = sickbeard.TORRENT_LABEL_ANIME if result.show.is_anime else sickbeard.TORRENT_LABEL

        if self.api > 6 and label:
            self.url = '{host}command/setLabel'.format(host=self.host)
            data = {
                'hashes': result.hash.lower(),
                'label': label.replace(' ', '_'),
            }
            return self._request(method='post', data=data, cookies=self.session.cookies)
        return None

    def _set_torrent_priority(self, result):

        self.url = '{host}command/{method}Prio'.format(host=self.host,
                                                       method='increase' if result.priority == 1 else 'decrease')
        data = {
            'hashes': result.hash.lower(),
        }
        return self._request(method='post', data=data, cookies=self.session.cookies)

    def _set_torrent_pause(self, result):
        self.url = '{host}command/{state}'.format(host=self.host,
                                                  state='pause' if sickbeard.TORRENT_PAUSED else 'resume')
        data = {
            'hash': result.hash,
        }
        return self._request(method='post', data=data, cookies=self.session.cookies)

api = qbittorrentAPI()
