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
        # Update the auth method to v2
        self._get_auth = self._get_auth_v2
        # Attempt to get API v2 version first
        self.url = '{host}api/v2/app/webapiVersion'.format(host=self.host)
        try:
            version = self.session.get(self.url, verify=app.TORRENT_VERIFY_CERT,
                                       cookies=self.session.cookies)
            # Make sure version is using the (major, minor, release) format
            version = list(map(int, version.text.split('.')))
            if len(version) < 2:
                version.append(0)
            return tuple(version)
        except (AttributeError, ValueError) as error:
            log.error('{name}: Unable to get API version. Error: {error!r}',
                      {'name': self.name, 'error': error})

        # Fall back to API v1
        self._get_auth = self._get_auth_legacy
        try:
            self.url = '{host}version/api'.format(host=self.host)
            version = int(self.session.get(self.url, verify=app.TORRENT_VERIFY_CERT).content)
            # Convert old API versioning to new versioning (major, minor, release)
            version = (1, version % 100, 0)
        except Exception:
            version = (1, 0, 0)
        return version

    def _get_auth(self):
        """Select between api v2 and legacy."""
        return self._get_auth_v2() or self._get_auth_legacy()

    def _get_auth_v2(self):
        """Authenticate using the new method (API v2)."""
        self.url = '{host}api/v2/auth/login'.format(host=self.host)
        data = {
            'username': self.username,
            'password': self.password,
        }
        try:
            self.response = self.session.post(self.url, data=data)
        except Exception:
            return None

        if self.response.status_code == 404:
            return None

        self.session.cookies = self.response.cookies
        self.auth = self.response.content

        return self.auth

    def _get_auth_legacy(self):
        """Authenticate using the legacy method (API v1)."""
        self.url = '{host}login'.format(host=self.host)
        data = {
            'username': self.username,
            'password': self.password,
        }
        try:
            self.response = self.session.post(self.url, data=data)
        except Exception:
            return None

        # Pre-API v1
        if self.response.status_code == 404:
            try:
                self.response = self.session.get(self.host, verify=app.TORRENT_VERIFY_CERT)
            except Exception:
                return None

        self.session.cookies = self.response.cookies
        self.auth = self.response.content

        return self.auth if not self.response.status_code == 404 else None

    def _add_torrent_uri(self, result):

        command = 'api/v2/torrents/add' if self.api >= (2, 0, 0) else 'command/download'
        self.url = '{host}{command}'.format(host=self.host, command=command)
        data = {
            'urls': result.url,
        }
        return self._request(method='post', data=data, cookies=self.session.cookies)

    def _add_torrent_file(self, result):

        command = 'api/v2/torrents/add' if self.api >= (2, 0, 0) else 'command/upload'
        self.url = '{host}{command}'.format(host=self.host, command=command)
        files = {
            'torrents': (
                '{result}.torrent'.format(result=result.name),
                result.content,
            ),
        }
        return self._request(method='post', files=files, cookies=self.session.cookies)

    def _set_torrent_label(self, result):

        label = app.TORRENT_LABEL_ANIME if result.series.is_anime else app.TORRENT_LABEL
        if not label:
            return True

        api = self.api
        if api >= (2, 0, 0):
            self.url = '{host}api/v2/torrents/setCategory'.format(host=self.host)
            label_key = 'category'
        elif api > (1, 6, 0):
            label_key = 'Category' if api >= (1, 10, 0) else 'Label'
            self.url = '{host}command/set{key}'.format(
                host=self.host,
                key=label_key,
            )

        data = {
            'hashes': result.hash.lower(),
            label_key.lower(): label.replace(' ', '_'),
        }
        return self._request(method='post', data=data, cookies=self.session.cookies)

    def _set_torrent_priority(self, result):

        command = 'api/v2/torrents' if self.api >= (2, 0, 0) else 'command'
        method = 'increase' if result.priority == 1 else 'decrease'
        self.url = '{host}{command}/{method}Prio'.format(
            host=self.host, command=command, method=method)
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
        api = self.api
        state = 'pause' if app.TORRENT_PAUSED else 'resume'
        command = 'api/v2/torrents' if api >= (2, 0, 0) else 'command'
        hashes_key = 'hashes' if self.api >= (1, 18, 0) else 'hash'
        self.url = '{host}{command}/{state}'.format(host=self.host, command=command, state=state)
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
        data = {
            'hashes': info_hash.lower(),
        }
        if self.api >= (2, 0, 0):
            self.url = '{host}api/v2/torrents/delete'.format(host=self.host)
            data['deleteFiles'] = True
        else:
            self.url = '{host}command/deletePerm'.format(host=self.host)

        return self._request(method='post', data=data, cookies=self.session.cookies)


api = QBittorrentAPI
