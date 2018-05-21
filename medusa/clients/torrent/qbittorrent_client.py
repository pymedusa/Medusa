# coding=utf-8

"""qBittorrent Client."""

from __future__ import unicode_literals

import logging

from medusa import app
from medusa.clients.torrent.generic import GenericClient
from medusa.logger.adapters.style import BraceAdapter

from requests.auth import HTTPDigestAuth

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class QBittorrentAPI(GenericClient):
    """qBittorrent API class."""

    def __init__(self, host=None, username=None, password=None):
        """Constructor.

        :param host:
        :type host: string
        :param username:
        :type username: string
        :param password:
        :type password: string
        """
        super(QBittorrentAPI, self).__init__('qbittorrent', host, username, password)
        self.url = self.host
        self.session.auth = HTTPDigestAuth(self.username, self.password)

    @property
    def api(self):
        """Get API version."""
        try:
            self.url = '{host}version/api'.format(host=self.host)
            version = int(self.session.get(self.url, verify=app.TORRENT_VERIFY_CERT).content)
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
                self.response = self.session.get(self.host, verify=app.TORRENT_VERIFY_CERT)
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
            'torrents': result.content
        }
        return self._request(method='post', files=files, cookies=self.session.cookies)

    def _set_torrent_label(self, result):

        label = app.TORRENT_LABEL_ANIME if result.series.is_anime else app.TORRENT_LABEL

        if self.api > 6 and label:
            label_key = 'Category' if self.api >= 10 else 'Label'
            self.url = '{host}command/set{key}'.format(
                host=self.host,
                key=label_key,
            )
            data = {
                'hashes': result.hash.lower(),
                label_key.lower(): label.replace(' ', '_'),
            }
            return self._request(method='post', data=data, cookies=self.session.cookies)
        return True

    def _set_torrent_priority(self, result):

        self.url = '{host}command/{method}Prio'.format(host=self.host,
                                                       method='increase' if result.priority == 1 else 'decrease')
        data = {
            'hashes': result.hash.lower(),
        }
        ok = self._request(method='post', data=data, cookies=self.session.cookies)

        if self.response.status_code == 403:
            log.info('{name}: Unable to set torrent priority because torrent queueing'
                     ' is disabled in {name} settings.', {'name': self.name})
            ok = True

        return ok

    def _set_torrent_pause(self, result):
        self.url = '{host}command/{state}'.format(host=self.host,
                                                  state='pause' if app.TORRENT_PAUSED else 'resume')
        hashes_key = 'hashes' if self.api >= 18 else 'hash'
        data = {
            hashes_key: result.hash.lower(),
        }
        return self._request(method='post', data=data, cookies=self.session.cookies)

    def remove_torrent(self, info_hash):
        """Remove torrent from client using given info_hash.

        :param info_hash:
        :type info_hash: string
        :return
        :rtype: bool
        """
        self.url = '{host}command/deletePerm'.format(host=self.host)
        data = {
            'hashes': info_hash.lower(),
        }

        return self._request(method='post', data=data, cookies=self.session.cookies)


api = QBittorrentAPI
