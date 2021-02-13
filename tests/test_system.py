# coding=utf-8
"""Tests for medusa.system module."""
from __future__ import unicode_literals

from medusa.queues.event_queue import Events
from medusa.system.restart import Restart
from medusa.system.shutdown import Shutdown

import pytest


@pytest.mark.parametrize('pid,expected', [
    # bytes test cases
    (0, False),
    (b'0', False),
    (123, False),
    (b'123', False),
    (123456, True),

    # unicode test cases
    (u'0', False),
    (u'123', False),
    (u'123456', True),
])
def test_restart(pid, expected, app_config):
    """Test restart."""
    # Given:
    app_config('PID', 123456)
    app_config('events', Events(None))

    # When
    actual = Restart.restart(pid)

    # Then
    assert actual == expected


@pytest.mark.parametrize('pid,expected', [
    # bytes test cases
    (0, False),
    (b'0', False),
    (123, False),
    (b'123', False),
    (123456, True),

    # unicode test cases
    (u'0', False),
    (u'123', False),
    (u'123456', True),
])
def test_shutdown(pid, expected, app_config):
    """Test shutdown."""
    # Given:
    app_config('PID', 123456)
    app_config('events', Events(None))

    # When
    actual = Shutdown.stop(pid)

    # Then
    assert actual == expected


def test_init():
    assert Restart()
    assert Shutdown()
