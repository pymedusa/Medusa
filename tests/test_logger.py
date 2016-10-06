# coding=utf-8
"""Tests for medusa.logger.py."""
from datetime import datetime

import medusa.logger as sut
from medusa.logger import DEBUG, INFO, LogLine, WARNING
import pytest


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
        {  # p2: regression test: https://github.com/pymedusa/Medusa/issues/876
            'message': "{'type': 'episode', 'season': 5}",
            'args': [],
            'kwargs': dict(),
            'expected': "{'type': 'episode', 'season': 5}"
        },
    ])
    def test_logger__various_messages(self, logger, read_loglines, p):
        # Given
        message = p['message']
        args = p['args']
        kwargs = p['kwargs']

        # When
        logger.error(message, *args, **kwargs)

        # Then
        loglines = list(read_loglines)
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


@pytest.mark.parametrize('line_pattern', [
    b'This is a example of log line with number {n}',
    u'This is a example of unicode log line with number {n}',
    b'This is a example of log line with number {n} using \xbb',
])
def test_reverse_readlines(create_file, line_pattern):
    # Given
    no_lines = 10000
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


@pytest.mark.parametrize('p', [
    {  # p0: No filter
        'line': '2016-08-25 20:12:03 INFO     SEARCHQUEUE-MANUAL-290853 :: [ProviderName] :: [d4ea5af] Performing episode search for Show Name',
        'expected': True,
    },
    {  # p1: level matches
        'line': '2016-08-25 20:12:03 INFO     SEARCHQUEUE-MANUAL-290853 :: [ProviderName] :: [d4ea5af] Performing episode search for Show Name',
        'min_level': INFO,
        'expected': True,
    },
    {  # p2: actual level is bigger than min level
        'line': '2016-08-25 20:12:03 INFO     SEARCHQUEUE-MANUAL-290853 :: [ProviderName] :: [d4ea5af] Performing episode search for Show Name',
        'min_level': DEBUG,
        'expected': True,
    },
    {  # p3: actual level is smaller than min level
        'line': '2016-08-25 20:12:03 INFO     SEARCHQUEUE-MANUAL-290853 :: [ProviderName] :: [d4ea5af] Performing episode search for Show Name',
        'min_level': WARNING,
        'expected': False,
    },
    {  # p4: thread_name matches
        'line': '2016-08-25 20:12:03 INFO     SEARCHQUEUE-MANUAL-290853 :: [ProviderName] :: [d4ea5af] Performing episode search for Show Name',
        'thread_name': 'SEARCHQUEUE-MANUAL',
        'expected': True,
    },
    {  # p4: thread_name doesn't match
        'line': '2016-08-25 20:12:03 INFO     SEARCHQUEUE-MANUAL-290853 :: [ProviderName] :: [d4ea5af] Performing episode search for Show Name',
        'thread_name': 'Thread-19',
        'expected': False,
    },
    {  # p5: everything matches
        'line': '2016-08-25 20:12:03 INFO     SEARCHQUEUE-MANUAL-290853 :: [ProviderName] :: [d4ea5af] Performing episode search for Show Name',
        'min_level': INFO,
        'thread_name': 'SEARCHQUEUE-MANUAL',
        'search_query': 'pisod',
        'expected': True,
    },
    {  # p6: search_query doesn't match
        'line': '2016-08-25 20:12:03 INFO     SEARCHQUEUE-MANUAL-290853 :: [ProviderName] :: [d4ea5af] Performing episode search for Show Name',
        'min_level': INFO,
        'thread_name': 'SEARCHQUEUE-MANUAL',
        'search_query': 'nomatchhere',
        'expected': False,
    }
])
def test_filter_logline(p):
    # Given
    logline = LogLine.from_line(p['line'])

    # When
    actual = sut.filter_logline(logline, min_level=p.get('min_level'), thread_name=p.get('thread_name'), search_query=p.get('search_query'))

    # Then
    assert p['expected'] == actual


def test_get_context_loglines__without_timestamp():
    # Given
    logline = LogLine('logline without timestamp')

    # When
    with pytest.raises(ValueError):  # Then
        logline.get_context_loglines()


def test_get_context_loglines(logger, read_loglines):
    # Given
    max_lines = 100
    for i in range(1, 200):
        logger.debug('line {}'.format(i))
    loglines = list(read_loglines)
    logline = loglines[0]
    expected = reversed(loglines[:max_lines])

    # When
    actual = logline.get_context_loglines(max_lines=max_lines)

    # Then
    assert [l.line for l in expected] == [l.line for l in actual]


def test_read_loglines__max_traceback_depth(logger):
    # Given
    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception('Expected exception message')
    try:
        123 / 0
    except ZeroDivisionError:
        logger.exception('Another Expected exception message')

    # When
    actual = list(sut.read_loglines(max_traceback_depth=2, max_lines=4))

    # Then
    assert len(actual) == 4
    # because max depth is too low, each traceback will be splitted in 2
    assert len(actual[0].traceback_lines) == 2
    assert len(actual[1].traceback_lines) == 0
    assert len(actual[2].traceback_lines) == 2
    assert len(actual[3].traceback_lines) == 0


def test_format_to_html(logger, read_loglines):
    # When
    base_url = '../base'
    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception('Expected exception message')
    loglines = list(read_loglines)
    logline = loglines[0]

    # When
    actual = logline.format_to_html(base_url)

    # Then
    assert '<a href="../base/' in actual
