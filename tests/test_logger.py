# coding=utf-8
"""Tests for sickbeard.logger.py."""
from datetime import datetime

import pytest

import sickbeard.logger as sut
from sickbeard.logger import LogLine


class TestStandardLoggingApi(object):
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
    def test_logger__various_messages(self, logger, loglines, p):
        # Given
        message = p['message']
        args = p['args']
        kwargs = p['kwargs']

        # When
        logger.error(message, *args, **kwargs)

        # Then
        loglines = list(loglines)
        assert len(loglines) == 1
        assert loglines[0].message == p['expected']

    @pytest.mark.parametrize('level', [
        'debug',
        'info',
        'warn',
        'warning',
        'error',
        'exception',
        'critical',
        'fatal',
    ])
    def test_logger__various_levels(self, logger, level):
        # Given
        method = getattr(logger, level)

        # When
        method('{param} message', param='test')

        # Then
        # no exception


def describe_logline(logline):
    return {
        'message': logline.message,
        'timestamp': logline.timestamp,
        'level_name': logline.level_name,
        'thread_name': logline.thread_name,
        'thread_id': logline.thread_id,
        'extra': logline.extra,
        'curhash': logline.curhash,
        'traceback_lines': logline.traceback_lines
    }


def test_reverse_readlines(create_file):
    # Given
    no_lines = 10000
    line_pattern = 'This is a example of log line with number {n}'
    filename = create_file(filename='samplefile.log', lines=[line_pattern.format(n=i) for i in range(0, no_lines)])
    expected = [line_pattern.format(n=no_lines - i - 1) for i in range(0, no_lines)]

    # When
    actual = list(sut.reverse_readlines(filename, buf_size=1024))

    # Then
    assert expected == actual


def test_read_loglines(logger, commit_hash, logfile):
    # Given
    no_msgs = 200
    line_pattern = 'This is a example of log line with number {n}'
    for i in range(0, no_msgs):
        logger.warning(line_pattern.format(n=i + 1))

    # When
    actual = list(sut.read_loglines(logfile))

    # Then
    assert no_msgs == len(actual)
    for i, logline in enumerate(actual):
        assert commit_hash == logline.curhash
        assert logline.timestamp is not None
        assert 'WARNING' == logline.level_name
        assert logline.extra is None
        assert logline.thread_name is not None
        assert logline.thread_id is None
        assert line_pattern.format(n=no_msgs - i) == logline.message


def test_read_loglines__with_traceback(logger, commit_hash, logfile):
    # Given
    line1 = 'Everything seems good'
    line2 = 'Still fine'
    logger.info(line1)
    logger.debug(line2)
    try:
        1 / 0
    except ZeroDivisionError as e:
        logger.exception(e.message)

    # When
    actual = list(sut.read_loglines(logfile))

    # Then
    assert 3 == len(actual)
    assert 'integer division or modulo by zero' == actual[0].message
    assert 'ERROR' == actual[0].level_name
    assert actual[0].timestamp is not None
    assert commit_hash == actual[0].curhash
    assert len(actual[0].traceback_lines) > 3
    assert 'Traceback (most recent call last):' == actual[0].traceback_lines[0]
    assert 'ZeroDivisionError: integer division or modulo by zero' == actual[0].traceback_lines[3]

    assert line2 == actual[1].message
    assert 'DEBUG' == actual[1].level_name
    assert [] == actual[1].traceback_lines

    assert line1 == actual[2].message
    assert 'INFO' == actual[2].level_name
    assert [] == actual[2].traceback_lines


@pytest.mark.parametrize('p', [
    {  # p0: common case
        'line': '2016-08-24 07:42:39 DEBUG    CHECKVERSION :: [7d1534c] git ls-remote --heads origin : returned successful',
        'expected': {
            'message': 'git ls-remote --heads origin : returned successful',
            'timestamp': datetime(year=2016, month=8, day=24, hour=7, minute=42, second=39),
            'level_name': 'DEBUG',
            'thread_name': 'CHECKVERSION',
            'thread_id': None,
            'extra': None,
            'curhash': '7d1534c',
            'traceback_lines': []
        }
    },
    {  # p1: with provider name and thread id
        'line': '2016-08-25 20:12:03 INFO     SEARCHQUEUE-MANUAL-290853 :: [ProviderName] :: [d4ea5af] Performing episode search for Show Name',
        'expected': {
            'message': 'Performing episode search for Show Name',
            'timestamp': datetime(year=2016, month=8, day=25, hour=20, minute=12, second=3),
            'level_name': 'INFO',
            'thread_name': 'SEARCHQUEUE-MANUAL',
            'thread_id': 290853,
            'extra': 'ProviderName',
            'curhash': 'd4ea5af',
            'traceback_lines': []
        }
    },
    {  # p1: without hash
        'line': '2016-08-25 20:12:03 INFO     SEARCHQUEUE-MANUAL-290853 :: [ProviderName] :: [] Performing episode search for Show Name',
        'expected': {
            'message': 'Performing episode search for Show Name',
            'timestamp': datetime(year=2016, month=8, day=25, hour=20, minute=12, second=3),
            'level_name': 'INFO',
            'thread_name': 'SEARCHQUEUE-MANUAL',
            'thread_id': 290853,
            'extra': 'ProviderName',
            'curhash': None,
            'traceback_lines': []
        }
    }
])
def test_from_line(p):
    # Given
    line = p['line']
    expected = p['expected']

    # When
    actual = LogLine.from_line(line)

    # Then
    assert expected == describe_logline(actual)
