# coding=utf-8

"""qBittorrent Client."""

from __future__ import unicode_literals

import logging
import os

from medusa import app
from medusa.clients.torrent.generic import GenericClient
from medusa.logger.adapters.style import BraceAdapter

from requests.auth import HTTPDigestAuth
from requests.compat import urljoin

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class APIUnavailableError(Exception):
    """Raised when the API version is not available."""


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
        super(QBittorrentAPI, self).__init__('qBittorrent', host, username, password)
        self.url = self.host
        # Auth for API v1.0.0 (qBittorrent v3.1.x and older)
        self.session.auth = HTTPDigestAuth(self.username, self.password)

        self.api = None

    def _get_auth(self):
        """Authenticate with the client using the most recent API version available for use."""
        try:
            auth = self._get_auth_v2()
            version = 2
        except APIUnavailableError:
            auth = self._get_auth_legacy()
            version = 1

        if not auth:
            # Authentication failed
            return auth

        # Get API version
        if version == 2:
            self.url = urljoin(self.host, 'api/v2/app/webapiVersion')
            try:
                response = self.session.get(self.url, verify=app.TORRENT_VERIFY_CERT)
                if not response.text:
                    raise ValueError('Response from client is empty. [Status: {0}]'.format(response.status_code))
                # Make sure version is using the (major, minor, release) format
                version = tuple(map(int, response.text.split('.')))
                # Fill up with zeros to get the correct format. e.g: (2, 3) => (2, 3, 0)
                self.api = version + (0,) * (3 - len(version))
            except (AttributeError, ValueError) as error:
                log.error('{name}: Unable to get API version. Error: {error!r}',
                          {'name': self.name, 'error': error})
        elif version == 1:
            try:
                self.url = urljoin(self.host, 'version/api')
                version = int(self.session.get(self.url, verify=app.TORRENT_VERIFY_CERT).text)
                # Convert old API versioning to new versioning (major, minor, release)
                self.api = (1, version % 100, 0)
            except Exception:
                self.api = (1, 0, 0)

        return auth

    def _get_auth_v2(self):
        """Authenticate using API v2."""
        self.url = urljoin(self.host, 'api/v2/auth/login')
        data = {
            'username': self.username,
            'password': self.password,
        }
        try:
            self.response = self.session.post(self.url, data=data, verify=app.TORRENT_VERIFY_CERT)
        except Exception as error:
            log.warning('{name}: Exception while trying to authenticate: {error}',
                        {'name': self.name, 'error': error}, exc_info=1)
            return None

        if self.response.status_code == 200:
            if self.response.text == 'Fails.':
                log.warning('{name}: Invalid Username or Password, check your config',
                            {'name': self.name})
                return None

            # Successful log in
            self.session.cookies = self.response.cookies
            self.auth = self.response.text

            return self.auth

        if self.response.status_code == 404:
            # API v2 is not available
            raise APIUnavailableError()

        if self.response.status_code == 403:
            log.warning('{name}: Your IP address has been banned after too many failed authentication attempts.'
                        ' Restart {name} to unban.',
                        {'name': self.name})
            return None

    def _get_auth_legacy(self):
        """Authenticate using legacy API."""
        self.url = urljoin(self.host, 'login')
        data = {
            'username': self.username,
            'password': self.password,
        }
        try:
            self.response = self.session.post(self.url, data=data, verify=app.TORRENT_VERIFY_CERT)
        except Exception as error:
            log.warning('{name}: Exception while trying to authenticate: {error}',
                        {'name': self.name, 'error': error}, exc_info=1)
            return None

        # API v1.0.0 (qBittorrent v3.1.x and older)
        if self.response.status_code == 404:
            try:
                self.response = self.session.get(self.host, verify=app.TORRENT_VERIFY_CERT)
            except Exception as error:
                log.warning('{name}: Exception while trying to authenticate: {error}',
                            {'name': self.name, 'error': error}, exc_info=1)
                return None

        self.session.cookies = self.response.cookies
        self.auth = (self.response.status_code != 404) or None

        return self.auth

    def _add_torrent_uri(self, result):

        command = 'api/v2/torrents/add' if self.api >= (2, 0, 0) else 'command/download'
        self.url = urljoin(self.host, command)
        data = {
            'urls': result.url,
        }
        if self.api >= (2, 0, 0):
            if os.path.isabs(app.TORRENT_PATH):
                data['savepath'] = app.TORRENT_PATH
        return self._request(method='post', data=data, cookies=self.session.cookies)

    def _add_torrent_file(self, result):

        command = 'api/v2/torrents/add' if self.api >= (2, 0, 0) else 'command/upload'
        self.url = urljoin(self.host, command)
        files = {
            'torrents': result.content
        }
        data = {}
        if self.api >= (2, 0, 0):
            if os.path.isabs(app.TORRENT_PATH):
                data['savepath'] = app.TORRENT_PATH
        return self._request(method='post', data=data, files=files, cookies=self.session.cookies)

    def _set_torrent_label(self, result):

        label = app.TORRENT_LABEL_ANIME if result.series.is_anime else app.TORRENT_LABEL
        if not label:
            return True

        api = self.api
        if api >= (2, 0, 0):
            self.url = urljoin(self.host, 'api/v2/torrents/setCategory')
            label_key = 'category'
        elif api > (1, 6, 0):
            label_key = 'Category' if api >= (1, 10, 0) else 'Label'
            self.url = urljoin(self.host, 'command/set' + label_key)

        data = {
            'hashes': result.hash.lower(),
            label_key.lower(): label.replace(' ', '_'),
        }
        ok = self._request(method='post', data=data, cookies=self.session.cookies)

        if self.response.status_code == 409:
            log.warning('{name}: Unable to set torrent label. You need to create the label '
                        ' in {name} first.', {'name': self.name})
            ok = True

        return ok

    def _set_torrent_priority(self, result):

        command = 'api/v2/torrents' if self.api >= (2, 0, 0) else 'command'
        method = 'increase' if result.priority == 1 else 'decrease'
        self.url = urljoin(self.host, '{command}/{method}Prio'.format(command=command, method=method))
        data = {
            'hashes': result.hash.lower(),
        }
        ok = self._request(method='post', data=data, cookies=self.session.cookies)

        if self.response.status_code == (409 if self.api >= (2, 0, 0) else 403):
            log.info('{name}: Unable to set torrent priority because torrent queueing'
                     ' is disabled in {name} settings.', {'name': self.name})
            ok = True

        return ok

    def _set_torrent_pause(self, result):
        api = self.api
        state = 'pause' if app.TORRENT_PAUSED else 'resume'
        command = 'api/v2/torrents' if api >= (2, 0, 0) else 'command'
        hashes_key = 'hashes' if self.api >= (1, 18, 0) else 'hash'
        self.url = urljoin(self.host, '{command}/{state}'.format(command=command, state=state))
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
            self.url = urljoin(self.host, 'api/v2/torrents/delete')
            data['deleteFiles'] = True
        else:
            self.url = urljoin(self.host, 'command/deletePerm')

        return self._request(method='post', data=data, cookies=self.session.cookies)


api = QBittorrentAPI
