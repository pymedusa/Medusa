# coding=utf-8

"""rTorrent Client."""

from __future__ import unicode_literals

import logging

from medusa import app
from medusa.clients.torrent.generic import GenericClient
from medusa.logger.adapters.style import BraceAdapter

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

        if self.username and self.password:
            self.auth = RTorrent(self.host, self.username, self.password, True, tp_kwargs=tp_kwargs)
        else:
            self.auth = RTorrent(self.host, None, None, True)

        return self.auth

    def _add_torrent_uri(self, result):

        if not (self.auth or result):
            return False

        try:
            # Send magnet to rTorrent and start it
            torrent = self.auth.load_magnet(result.url, result.hash, start=True)

            if not torrent:
                return False

            # Set label
            label = app.TORRENT_LABEL
            if result.show.is_anime:
                label = app.TORRENT_LABEL_ANIME
            if label:
                torrent.set_custom(1, label)

            if app.TORRENT_PATH:
                torrent.set_directory(app.TORRENT_PATH)

            # Start torrent
            torrent.start()
        except Exception as msg:
            log.warning('Error while sending torrent: {error!r}',
                        {'error': msg})
            return False
        else:
            return True

    def _add_torrent_file(self, result):

        if not (self.auth or result):
            return False

        # Send request to rTorrent
        try:
            # Send torrent to rTorrent and start it
            torrent = self.auth.load_torrent(result.content, start=True)

            if not torrent:
                return False

            # Set label
            label = app.TORRENT_LABEL
            if result.show.is_anime:
                label = app.TORRENT_LABEL_ANIME
            if label:
                torrent.set_custom(1, label)

            if app.TORRENT_PATH:
                torrent.set_directory(app.TORRENT_PATH)

            # Start torrent
            torrent.start()
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
        except Exception:  # pylint: disable=broad-except
            return False, 'Error: Unable to connect to {name}'.format(name=self.name)
        else:
            if self.auth is None:
                return False, 'Error: Unable to get {name} Authentication, check your config!'.format(name=self.name)
            else:
                return True, 'Success: Connected and Authenticated'


api = RTorrentAPI
