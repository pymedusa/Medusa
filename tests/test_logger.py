# coding=utf-8
"""Tests for medusa.logger.py."""
from __future__ import unicode_literals

import os.path
from datetime import datetime

import medusa.logger as sut
from medusa.logger import DEBUG, INFO, LogLine, WARNING
from medusa.logger.adapters.style import BraceAdapter

import pytest

from six import text_type


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

    @pytest.mark.parametrize('p', [
        {  # p0: curly brackets style
            'message': 'This is an example: {arg1} {arg2}',
            'args': [{'arg1': 'hello', 'arg2': 'world'}],
            'expected': 'This is an example: hello world'
        },
        {  # p1: Regression
            'message': 'This is an example: {json}',
            'args': [{'json': {5: 1}}],
            'expected': 'This is an example: {5: 1}'
        },
    ])
    def test_logger__brace_adapter(self, logger, read_loglines, p):
        # Given
        logger = BraceAdapter(logger)
        message = p['message']
        args = p['args']
        kwargs = p.get('kwargs', {})

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
        'issue_title': logline.issue_title,
        'timestamp': logline.timestamp,
        'level_name': logline.level_name,
        'thread_name': logline.thread_name,
        'thread_id': logline.thread_id,
        'extra': logline.extra,
        'curhash': logline.curhash,
        'traceback_lines': logline.traceback_lines
    }


@pytest.mark.parametrize('line_pattern', [
    'This is a example of log line with number {n}',
])
def test_reverse_readlines(create_file, line_pattern):
    # Given
    no_lines = 10000
    lines = [line_pattern.format(n=i).encode('utf-8') for i in list(range(0, no_lines))]
    filename = create_file(filename='samplefile.log', lines=lines)
    expected = [line_pattern.format(n=no_lines - i - 1) for i in list(range(0, no_lines))]
    for i, v in enumerate(expected):
        if not isinstance(v, text_type):
            expected[i] = text_type(v, errors='replace')

    # When
    actual = list(sut.reverse_readlines(filename, block_size=1024))

    # Then
    assert expected == actual


def test_read_loglines(logger, commit_hash, logfile):
    # Given
    no_msgs = 200
    line_pattern = 'This is a example of log line with number {n}'
    for i in list(range(0, no_msgs)):
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
        1 // 0
    except ZeroDivisionError as error:
        logger.exception(error)

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
            'issue_title': 'git ls-remote --heads origin : returned successful',
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
            'issue_title': 'Performing episode search for Show Name',
            'timestamp': datetime(year=2016, month=8, day=25, hour=20, minute=12, second=3),
            'level_name': 'INFO',
            'thread_name': 'SEARCHQUEUE-MANUAL',
            'thread_id': 290853,
            'extra': 'ProviderName',
            'curhash': 'd4ea5af',
            'traceback_lines': []
        }
    },
    {  # p2: without hash
        'line': '2016-08-25 20:12:03 INFO     SEARCHQUEUE-MANUAL-290853 :: [ProviderName] :: [] Performing episode search for Show Name',
        'expected': {
            'message': 'Performing episode search for Show Name',
            'issue_title': 'Performing episode search for Show Name',
            'timestamp': datetime(year=2016, month=8, day=25, hour=20, minute=12, second=3),
            'level_name': 'INFO',
            'thread_name': 'SEARCHQUEUE-MANUAL',
            'thread_id': 290853,
            'extra': 'ProviderName',
            'curhash': None,
            'traceback_lines': []
        }
    },
    {  # p3: traceback lines (last line is empty)
        'line': (
            "2018-03-18 12:11:29 ERROR    Thread_17 :: [e11c71e] Exception generated: invalid literal for int() with base 10: 'false'"
            '\nTraceback (most recent call last):'
            '\n  File "/usr/Medusa/medusa/server/web/core/base.py", line 281, in async_call'
            '\n    result = function(**kwargs)'
            '\n  File "/usr/Medusa/medusa/server/web/core/file_browser.py", line 23, in index'
            '\n    return json.dumps(list_folders(path, True, bool(int(includeFiles))))'
            "\nValueError: invalid literal for int() with base 10: 'false'"
            '\n'
        ),
        'expected': {
            'message': "Exception generated: invalid literal for int() with base 10: 'false'",
            'issue_title': "ValueError: invalid literal for int() with base 10: 'false'",
            'timestamp': datetime(year=2018, month=3, day=18, hour=12, minute=11, second=29),
            'level_name': 'ERROR',
            'thread_name': 'Thread',
            'thread_id': 17,
            'extra': None,
            'curhash': 'e11c71e',
            'traceback_lines': [
                'Traceback (most recent call last):',
                '  File "/usr/Medusa/medusa/server/web/core/base.py", line 281, in async_call',
                '    result = function(**kwargs)',
                '  File "/usr/Medusa/medusa/server/web/core/file_browser.py", line 23, in index',
                '    return json.dumps(list_folders(path, True, bool(int(includeFiles))))',
                "ValueError: invalid literal for int() with base 10: 'false'",
                ''
            ]
        }
    },
    {  # p4: Guessit error
       # NOTE: The traceback lines are truncated, but still true to Guessit's template
        'line': (
            '2019-06-13 16:13:15 ERROR    FINDSUBTITLES :: [c1675ff] Exception generated: An internal error has occured in guessit.'
            '\n===================== Guessit Exception Report ====================='
            '\nversion=3.0.4.dev0'
            '\nstring=Unit,.The.3x08.Play.16.HDTV-Caph.[tvu.org.ru].srt'
            "\noptions={'type': 'episode'}"
            '\n--------------------------------------------------------------------'
            '\nTraceback (most recent call last):'
            '\n  File "/home/pi/Medusa/ext/guessit/api.py", line 210, in guessit'
            '\n    matches = self.rebulk.matches(string, options)'
            '\n  File "/home/pi/Medusa/ext/rebulk/rebulk.py", line 288, in matches'
            '\n    self._execute_rules(matches, context)'
            '\n  File "/home/pi/Medusa/ext/rebulk/rebulk.py", line 319, in _execute_rules'
            '\n    rules.execute_all_rules(matches, context)'
            '\n  File "/home/pi/Medusa/ext/rebulk/rules.py", line 316, in execute_all_rules'
            '\n    when_response = execute_rule(rule, matches, context)'
            '\n  File "/home/pi/Medusa/ext/rebulk/rules.py", line 341, in execute_rule'
            '\n    rule.then(matches, when_response, context)'
            '\n  File "/home/pi/Medusa/ext/rebulk/rules.py", line 127, in then'
            '\n    cons.then(matches, when_response, context)'
            '\n  File "/home/pi/Medusa/ext/rebulk/rules.py", line 140, in then'
            '\n    matches.remove(match)'
            '\n  File "/usr/lib/python3.7/_collections_abc.py", line 1004, in remove'
            '\n    del self[self.index(value)]'
            '\n  File "/home/pi/Medusa/ext/rebulk/match.py", line 569, in __delitem__'
            '\n    self._remove_match(match)'
            '\n  File "/home/pi/Medusa/ext/rebulk/match.py", line 137, in _remove_match'
            '\n    _BaseMatches._base_remove(self._tag_dict[tag], match)'
            '\nValueError: list.remove(x): x not in list'
            '\n--------------------------------------------------------------------'
            '\nPlease report at https://github.com/guessit-io/guessit/issues.'
            '\n===================================================================='
        ),
        'expected': {
            'message': 'Exception generated: An internal error has occured in guessit.',
            'issue_title': 'ValueError: list.remove(x): x not in list',
            'timestamp': datetime(year=2019, month=6, day=13, hour=16, minute=13, second=15),
            'level_name': 'ERROR',
            'thread_name': 'FINDSUBTITLES',
            'thread_id': None,
            'extra': None,
            'curhash': 'c1675ff',
            'traceback_lines': [
                '===================== Guessit Exception Report =====================',
                'version=3.0.4.dev0',
                'string=Unit,.The.3x08.Play.16.HDTV-Caph.[tvu.org.ru].srt',
                "options={'type': 'episode'}",
                '--------------------------------------------------------------------',
                'Traceback (most recent call last):',
                '  File "/home/pi/Medusa/ext/guessit/api.py", line 210, in guessit',
                '    matches = self.rebulk.matches(string, options)',
                '  File "/home/pi/Medusa/ext/rebulk/rebulk.py", line 288, in matches',
                '    self._execute_rules(matches, context)',
                '  File "/home/pi/Medusa/ext/rebulk/rebulk.py", line 319, in _execute_rules',
                '    rules.execute_all_rules(matches, context)',
                '  File "/home/pi/Medusa/ext/rebulk/rules.py", line 316, in execute_all_rules',
                '    when_response = execute_rule(rule, matches, context)',
                '  File "/home/pi/Medusa/ext/rebulk/rules.py", line 341, in execute_rule',
                '    rule.then(matches, when_response, context)',
                '  File "/home/pi/Medusa/ext/rebulk/rules.py", line 127, in then',
                '    cons.then(matches, when_response, context)',
                '  File "/home/pi/Medusa/ext/rebulk/rules.py", line 140, in then',
                '    matches.remove(match)',
                '  File "/usr/lib/python3.7/_collections_abc.py", line 1004, in remove',
                '    del self[self.index(value)]',
                '  File "/home/pi/Medusa/ext/rebulk/match.py", line 569, in __delitem__',
                '    self._remove_match(match)',
                '  File "/home/pi/Medusa/ext/rebulk/match.py", line 137, in _remove_match',
                '    _BaseMatches._base_remove(self._tag_dict[tag], match)',
                'ValueError: list.remove(x): x not in list',
                '--------------------------------------------------------------------',
                'Please report at https://github.com/guessit-io/guessit/issues.',
                '====================================================================',
            ]
        }
    },
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
        'thread_name': 'Thread_19',
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
    for i in list(range(1, 200)):
        logger.debug('line {0}'.format(i))
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
        1 // 0
    except ZeroDivisionError:
        logger.exception('Expected exception message')
    try:
        123 // 0
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


def test_format_to_html(logger, read_loglines, app_config):
    # When
    prog_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    base_url = '../base'
    try:
        1 // 0
    except ZeroDivisionError:
        logger.exception('Expected exception message')
    loglines = list(read_loglines)
    logline = loglines[0]

    # When
    app_config('PROG_DIR', prog_dir)
    actual = logline.format_to_html(base_url)

    # Then
    assert '<a href="../base/' in actual
    assert '">tests' + os.path.sep + 'test_logger.py</a>' in actual
