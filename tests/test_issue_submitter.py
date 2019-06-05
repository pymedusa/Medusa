# coding=utf-8
"""Tests for medusa.server.web.core.error_logs.py."""
from __future__ import unicode_literals

import logging

from github.GithubException import BadCredentialsException, RateLimitExceededException
from medusa import app, classes
from medusa.classes import ErrorViewer
from medusa.issue_submitter import IssueSubmitter
from medusa.logger import LogLine
from mock.mock import Mock
import pytest

from six import itervalues

sut = IssueSubmitter()


@pytest.mark.parametrize('p', [
    {  # p0: debug not enabled
        'debug': False,
        'expected': [(IssueSubmitter.DEBUG_NOT_ENABLED, None)]
    },
    {  # p1: debug not set
        'expected': [(IssueSubmitter.DEBUG_NOT_ENABLED, None)]
    },
    {  # p2: username and password set, but debug not enabled
        'debug': False,
        'username': 'user',
        'password': 'pass',
        'expected': [(IssueSubmitter.DEBUG_NOT_ENABLED, None)]
    },
    {  # p3: debug enabled, but no username
        'debug': True,
        'password': 'pass',
        'expected': [(IssueSubmitter.MISSING_CREDENTIALS, None)]
    },
    {  # p4: debug enabled, but no password
        'debug': True,
        'username': 'user',
        'expected': [(IssueSubmitter.MISSING_CREDENTIALS, None)]
    },
    {  # p5: debug enabled, username and password set, but no errors to report
        'debug': True,
        'username': 'user',
        'password': 'pass',
        'expected': [(IssueSubmitter.NO_ISSUES, None)]
    },
    {  # p6: debug enabled, username and password set, errors to report but update is needed
        'debug': True,
        'username': 'user',
        'password': 'pass',
        'errors': ['Some Error'],
        'need_update': True,
        'expected': [(IssueSubmitter.UNSUPPORTED_VERSION, None)]
    },
    {  # p7: debug enabled, username and password set, errors to report, no update is needed, but it's already running
        'debug': True,
        'username': 'user',
        'password': 'pass',
        'errors': ['Some Error'],
        'running': True,
        'expected': [(IssueSubmitter.ALREADY_RUNNING, None)]
    },
    {  # p8: debug enabled, username and password set, errors to report, update is needed but I'M A DEVELOPER :-)
        'debug': True,
        'username': 'user',
        'password': 'pass',
        'errors': ['Some Error'],
        'need_update': True,
        'developer': True,
        'exception': [BadCredentialsException, 401],
        'expected': [(IssueSubmitter.BAD_CREDENTIALS, None)]
    },
    {  # p9: debug enabled, username and password set, errors to report, update is not needed but rate limit exception happened
        'debug': True,
        'username': 'user',
        'password': 'pass',
        'errors': ['Some Error'],
        'exception': [RateLimitExceededException, 429],
        'expected': [(IssueSubmitter.RATE_LIMIT, None)]
    },
])
def test_submit_github_issue__basic_validations(monkeypatch, logger, version_checker, raise_github_exception, p):
    # Given
    classes.ErrorViewer.clear()
    for error in p.get('errors', []):
        logger.error(error)
    monkeypatch.setattr(app, 'DEBUG', p.get('debug'))
    monkeypatch.setattr(app, 'GIT_USERNAME', p.get('username'))
    monkeypatch.setattr(app, 'GIT_PASSWORD', p.get('password'))
    monkeypatch.setattr(app, 'DEVELOPER', p.get('developer', False))
    monkeypatch.setattr(version_checker, 'need_update', lambda: p.get('need_update', False))
    monkeypatch.setattr(sut, 'running', p.get('running', False))
    if 'exception' in p:
        monkeypatch.setattr('github.MainClass.Github', lambda *args, **kwargs: raise_github_exception(*p['exception']))

    # When
    actual = sut.submit_github_issue(version_checker)

    # Then
    assert p['expected'] == actual
    assert p.get('running', False) == sut.running


@pytest.mark.parametrize('p', [
    {  # p0: Same Title
        'text1': 'My Issue Title',
        'text2': 'My Issue Title',
        'ratio': None,
        'expected': True
    },
    {  # p1: Similar
        'text1': 'My Issue Title',
        'text2': 'My Issue Title 1',
        'ratio': None,
        'expected': True
    },
    {  # p2: Unsimilar with a different ratio
        'text1': 'My Issue Title',
        'text2': 'My Issue\'s Title',
        'ratio': 1.0,
        'expected': False
    },
    {  # p3: Similar
        'text1': 'SSLError: [SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] sslv3 alert handshake failure (_ssl.c:590)',
        'text2': '[SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] sslv3 alert handshake failure (_ssl.c:645)',
        'ratio': None,
        'expected': True
    },
    {  # p4: Similar
        'text1': 'SSLError: [Errno 1] _ssl.c:504: error:14077438:SSL routines:SSL23_GET_SERVER_HELLO:tlsv1 alert internal error',
        'text2': '[Errno 1] _ssl.c:510: error:14077438:SSL routines:SSL23_GET_SERVER_HELLO:tlsv1 alert internal error',
        'ratio': None,
        'expected': True
    },
    {  # p5: Unsimilar
        'text1': 'Another Issue',
        'text2': 'My Issue',
        'ratio': None,
        'expected': False
    }
])
def test_similar(p):
    # Given
    text1 = p['text1']
    text2 = p['text2']
    ratio = p['ratio']
    expected = p['expected']

    # When
    if ratio:
        actual = sut.similar(text1, text2, ratio)
    else:
        actual = sut.similar(text1, text2)

    # Then
    assert expected == actual


@pytest.mark.parametrize('p', [
    {  # p0: gist not needed since context lines
       #     are exactly the same as the error in the issue report
        'lines': [
            'Some Log Line'
        ],
        'expected': False
    },
    {  # p1: Gist created
        'lines': [
            'Some Log Line',
            'Other Log Line',
            'Different Log Line'
        ],
        'expected': True
    }
])
def test_create_gist(p, logger, read_loglines, github):
    # Given
    lines = p['lines']
    expected = p['expected']

    for line in lines:
        logger.error(line)
    logline = list(read_loglines)[0]
    filename = 'application.log'

    # When
    actual = sut.create_gist(github, logline)

    # Then
    if expected:
        assert actual
        assert not actual.public
        assert filename in actual.files
        for line in lines:
            assert line in actual.files[filename]
    else:
        assert actual is None


def test_create_gist__logline_not_found(github):
    """If the log line is very old and can't be found in the logs, a gist can not be created."""
    # Given
    logline = LogLine.from_line('2016-08-24 07:42:39 ERROR    CHECKVERSION :: [7d1534c] Very Old Log Message')
    assert logline is not None

    # When
    actual = sut.create_gist(github, logline)

    # Then
    assert actual is None


def test_find_similar_issues(monkeypatch, logger, github_repo, read_loglines, create_github_issue, caplog):
    # Given
    lines = {
        1: 'Some Issue Like This',
        2: 'Unexpected thing happened',
        3: 'Really strange this one',
        4: 'Missing time zone for network: USA Network',
        5: "AttributeError: 'NoneType' object has no attribute 'findall'",
        6: 'Am I a duplicate?',
    }
    for line in itervalues(lines):
        logger.warning(line)
    loglines = list(read_loglines)

    raw_issues = [
        # (number, title, labels, pull_request)
        (1, '[APP SUBMITTED]: Really strange that one', [], False),
        (2, 'Some Issue like This', [], False),
        (3, 'Fix Some Issue like This', [], True),  # Pull request
        (4, '[APP SUBMITTED]: Missing time zone for network: Hub Network', [], False),
        (5, '[APP SUBMITTED]: Missing time zone for network: USA Network', [], False),
        (6, "AttributeError: 'NoneType' object has no attribute 'findall'", [], False),
        (7, "AttributeError: 'NoneType' object has no attribute 'lower'", [], False),
        (8, 'Am I a duplicate?', ['Bug', 'Duplicate'], False),
        (9, 'Am I a duplicate?', [], False),
        (10, 'Am I a duplicate?', ['Duplicate'], False),
    ]
    issues = dict()
    for (number, title, labels, pull_request) in raw_issues:
        kwargs = {} if not pull_request else {'pull_request': 'mock'}
        issues[number] = create_github_issue(title=title, number=number, labels=labels, **kwargs)

    monkeypatch.setattr(github_repo, 'get_issues', lambda *args, **kwargs: itervalues(issues))

    expected = {
        lines[1]: issues[2],
        lines[3]: issues[1],
        lines[4]: issues[5],
        lines[5]: issues[6],
        lines[6]: issues[9],
    }

    # When
    caplog.set_level(logging.DEBUG, logger='medusa')
    actual = sut.find_similar_issues(github_repo, loglines)

    # Then
    assert len(list(issues.values())) == len(issues)  # all issues should be different
    assert expected == actual


@pytest.mark.parametrize('p', [
    {  # p0: Has a similar issue, then it should just comment the issue
        'input': 'Really strange that one',
        'similar': (123, '[APP SUBMITTED]: Really strange that one!'),
        'expected': (IssueSubmitter.COMMENTED_EXISTING_ISSUE.format(number='123'), 123)
    },
    {  # p1: Has a similar issue but it's locked. Cannot comment it.
        'input': 'Really strange that one',
        'similar': (456, '[APP SUBMITTED]: Really strange that one!'),
        'locked': True,
        'expected': (IssueSubmitter.EXISTING_ISSUE_LOCKED.format(number='456'), None)
    },
    {  # p2: No similar issue found. Creating a new one
        'input': 'Really strange that one',
        'expected': (IssueSubmitter.ISSUE_CREATED.format(number='1'), 1)
    }
])
def test_submit_issues(monkeypatch, github, github_repo, create_github_issue, p):
    # Given
    message = p['input']
    logline = LogLine.from_line('2016-08-25 20:12:03 ERROR SEARCHQUEUE-MANUAL-290853 :: [ProviderName] :: [d4ea5af] {message}'.format(message=message))
    ErrorViewer.add(logline)
    create_comment = Mock()
    similar_issues = dict()
    locked = p.get('locked', False)
    similar = p.get('similar')
    if similar:
        similar_issue = create_github_issue(similar[1], number=similar[0], locked=locked)
        monkeypatch.setattr(similar_issue, 'create_comment', create_comment)
        similar_issues[logline.key] = similar_issue
    monkeypatch.setattr(github_repo, 'create_issue', create_github_issue)
    expected = p['expected']

    # When
    actual = sut.submit_issues(github, github_repo, [logline], similar_issues)

    # Then
    assert [expected] == actual
    if expected[1] is not None:
        assert logline not in ErrorViewer.errors
        if similar:
            assert create_comment.called
            assert message in create_comment.call_args[0][0]
        else:
            assert not create_comment.called
    else:
        assert logline in ErrorViewer.errors
        assert not create_comment.called
