# coding=utf-8
"""Tests for the Medusa web server."""
from __future__ import unicode_literals

import errno
import os
import socket
import stat

from medusa.server import core

from mock.mock import MagicMock, Mock

import pytest


def test_bind_unix_socket_rejects_unsupported_platform(monkeypatch):
    monkeypatch.delattr(core.socket, 'AF_UNIX', raising=False)

    with pytest.raises(RuntimeError, match='not supported'):
        core._bind_unix_socket('/tmp/medusa.sock')


def test_remove_stale_unix_socket_preserves_regular_file(tmpdir):
    path = str(tmpdir.ensure('medusa.sock'))

    with pytest.raises(ValueError, match='is not a socket'):
        core._remove_stale_unix_socket(path)

    assert os.path.isfile(path)


def test_remove_stale_unix_socket_preserves_socket_on_unexpected_error(monkeypatch):
    path_stat = Mock(st_mode=stat.S_IFSOCK)
    probe = MagicMock()
    probe.__enter__.return_value = probe
    probe.connect.side_effect = OSError(errno.EACCES, 'Permission denied')
    unlink = Mock()

    monkeypatch.setattr(core.os, 'stat', Mock(return_value=path_stat))
    monkeypatch.setattr(core.socket, 'AF_UNIX', 1, raising=False)
    monkeypatch.setattr(core.socket, 'socket', Mock(return_value=probe))
    monkeypatch.setattr(core.os, 'unlink', unlink)

    with pytest.raises(OSError) as error:
        core._remove_stale_unix_socket('/tmp/medusa.sock')

    assert error.value.errno == errno.EACCES
    unlink.assert_not_called()


def test_remove_stale_unix_socket_removes_refused_socket(monkeypatch):
    path_stat = Mock(st_mode=stat.S_IFSOCK)
    probe = MagicMock()
    probe.__enter__.return_value = probe
    probe.connect.side_effect = OSError(errno.ECONNREFUSED, 'Connection refused')
    unlink = Mock()

    monkeypatch.setattr(core.os, 'stat', Mock(return_value=path_stat))
    monkeypatch.setattr(core.socket, 'AF_UNIX', 1, raising=False)
    monkeypatch.setattr(core.socket, 'socket', Mock(return_value=probe))
    monkeypatch.setattr(core.os, 'unlink', unlink)

    core._remove_stale_unix_socket('/tmp/medusa.sock')

    unlink.assert_called_once_with('/tmp/medusa.sock')


def test_remove_stale_unix_socket_preserves_active_socket(monkeypatch):
    path_stat = Mock(st_mode=stat.S_IFSOCK)
    probe = MagicMock()
    probe.__enter__.return_value = probe
    unlink = Mock()

    monkeypatch.setattr(core.os, 'stat', Mock(return_value=path_stat))
    monkeypatch.setattr(core.socket, 'AF_UNIX', 1, raising=False)
    monkeypatch.setattr(core.socket, 'socket', Mock(return_value=probe))
    monkeypatch.setattr(core.os, 'unlink', unlink)

    with pytest.raises(OSError) as error:
        core._remove_stale_unix_socket('/tmp/medusa.sock')

    assert error.value.errno == errno.EADDRINUSE
    unlink.assert_not_called()


def test_remove_owned_unix_socket_preserves_replacement_file(tmpdir):
    path = str(tmpdir.ensure('medusa.sock'))

    core._remove_owned_unix_socket(path, os.stat(path))

    assert os.path.isfile(path)


@pytest.mark.skipif(not hasattr(socket, 'AF_UNIX'), reason='Unix sockets are not supported')
def test_remove_stale_unix_socket(tmpdir):
    path = str(tmpdir.join('medusa.sock'))
    stale_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    stale_socket.bind(path)
    stale_socket.close()

    core._remove_stale_unix_socket(path)

    assert not os.path.exists(path)


@pytest.mark.skipif(not hasattr(socket, 'AF_UNIX'), reason='Unix sockets are not supported')
def test_remove_stale_unix_socket_preserves_real_active_socket(tmpdir):
    path = str(tmpdir.join('medusa.sock'))
    active_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    active_socket.bind(path)
    active_socket.listen(1)

    try:
        with pytest.raises(OSError) as error:
            core._remove_stale_unix_socket(path)

        assert error.value.errno == errno.EADDRINUSE
        assert os.path.exists(path)
    finally:
        active_socket.close()
        if os.path.exists(path):
            os.unlink(path)
