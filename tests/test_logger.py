# coding=utf-8
"""Tests for sickbeard.logger.py."""

import logging

from mock.mock import Mock
import pytest
from sickbeard.logger import custom_get_logger as get_logger


@pytest.fixture
def handler_write():
    return Mock()


@pytest.fixture
def handler_error():
    return Mock()


@pytest.fixture
def stream_handler(monkeypatch, handler_write, handler_error):
    stream_handler = logging.StreamHandler(Mock(write=handler_write))
    monkeypatch.setattr(stream_handler, 'handleError', handler_error)
    return stream_handler


@pytest.fixture
def sut(stream_handler):
    sut = get_logger('sickbeard')
    sut.addHandler(stream_handler)
    return sut


@pytest.mark.parametrize('p', [
    {  # p0: curly brackets style
        'message': 'This is an example: {arg1} {arg2}',
        'args': [],
        'kwargs': dict(arg1='hello', arg2='world'),
        'expected': 'This is an example: hello world'
    },
    {  # p1: legacy formatter
        'message': 'This is an example: %s %s',
        'args': ['hello', 'world'],
        'kwargs': dict(),
        'expected': 'This is an example: hello world'
    },
    {  # p2: regression test: https://github.com/pymedusa/SickRage/issues/876
        'message': "{'type': 'episode', 'season': 5}",
        'args': [],
        'kwargs': dict(),
        'expected': "{'type': 'episode', 'season': 5}"
    },
])
def test_logger__various_messages(sut, handler_write, handler_error, p):
    # Given
    message = p['message']
    args = p['args']
    kwargs = p['kwargs']
    expected = (('%s\n' % p['expected'], ), {})

    # When
    sut.error(message, *args, **kwargs)

    # Then
    assert not handler_error.called
    assert handler_write.called
    assert handler_write.call_args == expected
