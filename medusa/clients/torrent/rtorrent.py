# coding=utf-8

"""rTorrent Client."""

from __future__ import absolute_import, unicode_literals

import logging

from medusa import app
from medusa.clients.torrent.generic import GenericClient
from medusa.helper.exceptions import DownloadClientConnectionException
from medusa.logger.adapters.style import BraceAdapter
from medusa.schedulers.download_handler import ClientStatus

from rtorrent import RTorrent


log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class RTorrentAPI(GenericClient):
    """rTorrent API class."""

    def __init__(self, host=None, username=None, password=None):
        """Constructor.

        :param host:
        :type host: string
        :param username:
        :type username: string
        :param password:
        :type password: string
        """
        super(RTorrentAPI, self).__init__('rTorrent', host, username, password)
        self._get_auth()

    def _get_auth(self):
        if self.auth is not None:
            return self.auth

        if not self.host:
            return

        tp_kwargs = {}
        if app.TORRENT_AUTH_TYPE != 'none':
            tp_kwargs['authtype'] = app.TORRENT_AUTH_TYPE

        if not app.TORRENT_VERIFY_CERT:
            tp_kwargs['check_ssl_cert'] = False
        else:
            if app.SSL_CA_BUNDLE:
                tp_kwargs['check_ssl_cert'] = app.SSL_CA_BUNDLE

        try:
            if self.username and self.password:
                self.auth = RTorrent(self.host, self.username, self.password, True, tp_kwargs=tp_kwargs)
            else:
                self.auth = RTorrent(self.host, None, None, True)
        except Exception as error:  # No request/connection specific exception thrown.
            raise DownloadClientConnectionException(f'Unable to authenticate with rtorrent client: {error}')

        return self.auth

    @staticmethod
    def _get_params(result):
        params = []

        # Set label
        label = app.TORRENT_LABEL
        if result.series.is_anime:
            label = app.TORRENT_LABEL_ANIME
        if label:
            params.append('d.custom1.set={0}'.format(label))

        if app.TORRENT_PATH:
            params.append('d.directory.set={0}'.format(app.TORRENT_PATH))

        return params

    def _add_torrent_uri(self, result):

        if not (self.auth or result):
            return False

        try:
            params = self._get_params(result)
            # Send magnet to rTorrent and start it
            try:
                torrent = self.auth.load_magnet(result.url, result.hash, start=True, params=params)
            except DownloadClientConnectionException:
                return False

            if not torrent:
                return False

        except Exception as msg:
            log.warning('Error while sending torrent: {error!r}',
                        {'error': msg})
            return False
        else:
            return True

    def _add_torrent_file(self, result):

        if not (self.auth or result):
            return False

        try:
            params = self._get_params(result)
            # Send torrent to rTorrent and start it
            try:
                torrent = self.auth.load_torrent(result.content, start=True, params=params)
            except DownloadClientConnectionException:
                return False

            if not torrent:
                return False

        except Exception as msg:
            log.warning('Error while sending torrent: {error!r}',
                        {'error': msg})
            return False
        else:
            return True

    def test_authentication(self):
        """Test connection using authentication.

        :return:
        :rtype: tuple(bool, str)
        """
        try:
            self.auth = None
            self._get_auth()
        except Exception:
            return False, f'Error: Unable to connect to {self.name}'
        else:
            if self.auth is None:
                return False, f'Error: Unable to get {self.name} Authentication, check your config!'
            else:
                return True, 'Success: Connected and Authenticated'

    def pause_torrent(self, info_hash):
        """Get torrent and pause."""
        log.info('Pausing {client} torrent {hash} status.', {'client': self.name, 'hash': info_hash})
        try:
            torrent = self.auth.find_torrent(info_hash.upper())
        except DownloadClientConnectionException:
            return False

        if not torrent:
            log.debug('Could not locate torrent with {hash} status.', {'hash': info_hash})
            return

        return torrent.pause()

    def remove_torrent(self, info_hash):
        """Get torrent and remove."""
        log.info('Removing {client} torrent {hash} status.', {'client': self.name, 'hash': info_hash})
        try:
            torrent = self.auth.find_torrent(info_hash.upper())
        except DownloadClientConnectionException:
            return False

        if not torrent:
            log.debug('Could not locate torrent with {hash} status.', {'hash': info_hash})
            return

        return torrent.erase()

    def _torrent_properties(self, info_hash):
        """Get torrent properties."""
        log.debug('Get {client} torrent hash {hash} properties.', {'client': self.name, 'hash': info_hash})
        torrent = self.auth.find_torrent(info_hash.upper())

        if not torrent:
            log.debug('Could not locate torrent with {hash} status.', {'hash': info_hash})
            return

        return torrent

    def torrent_completed(self, info_hash):
        """Check if torrent has finished downloading."""
        get_status = self.get_status(info_hash)
        if not get_status:
            return False

        return str(get_status) == 'Completed'

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
            complete: 'Completed download'
            is_finished: 'Finished seeding (ratio reeched)'

        ```
        """
        torrent = self._torrent_properties(info_hash)
        if not torrent:
            return

        client_status = ClientStatus()
        if torrent.started:
            client_status.set_status_string('Downloading')

        if torrent.paused:
            client_status.set_status_string('Paused')

        # # if torrent['status'] == ?:
        # #     client_status.set_status_string('Failed')

        if torrent.complete:
            client_status.set_status_string('Completed')

        # Store ratio
        client_status.ratio = torrent.ratio

        # Store progress
        if torrent.bytes_done:
            client_status.progress = int(torrent.completed_bytes / torrent.bytes_done * 100)

        # Store destination
        client_status.destination = torrent.directory

        # Store resource
        client_status.resource = torrent.base_filename

        return client_status


api = RTorrentAPI
