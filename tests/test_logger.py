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


def test_logger__using_brackets(sut, handler_write, handler_error):
    # Given
    message = '{arg1} {arg2}'
    args = {'arg1': 'hello', 'arg2': 'world'}
    expected = (('hello world\n', ), {})

    # When
    sut.error(message, **args)

    # Then
    assert not handler_error.called
    assert handler_write.called
    assert handler_write.call_args == expected


def test_logger__legacy_formatter(sut, handler_write, handler_error):
    # Given
    message = '%s %s'
    args = ['hello', 'world']
    expected = (('hello world\n', ), {})

    # When
    sut.error(message, *args)

    # Then
    assert not handler_error.called
    assert handler_write.called
    assert handler_write.call_args == expected


def test_logger__regression_876(sut, handler_write, handler_error):
    """Regression for https://github.com/pymedusa/SickRage/issues/876 issue."""
    # Given
    message = "{'type': 'episode', 'season': 5}"
    expected = (("{'type': 'episode', 'season': 5}\n", ), {})

    # When
    sut.error(message)

    # Then
    assert not handler_error.called
    assert handler_write.called
    assert handler_write.call_args == expected
