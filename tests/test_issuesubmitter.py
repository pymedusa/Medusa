# coding=utf-8
"""Tests for sickbeard.server.web.core.error_logs.py."""

from github.GithubException import BadCredentialsException, RateLimitExceededException
from medusa import classes
from medusa.classes import ErrorViewer
from medusa.issuesubmitter import IssueSubmitter
from medusa.logger import LogLine
from mock.mock import Mock
import pytest


sut = IssueSubmitter()


@pytest.mark.parametrize('p', [
    {  # p0: debug not enabled
        'debug': False,
        'expected': [(IssueSubmitter.INVALID_CONFIG, None)]
    },
    {  # p1: debug not set
        'expected': [(IssueSubmitter.INVALID_CONFIG, None)]
    },
    {  # p2: debug enabled, but no username
        'debug': True,
        'password': 'pass',
        'expected': [(IssueSubmitter.INVALID_CONFIG, None)]
    },
    {  # p3: debug enabled, but no password
        'debug': True,
        'username': 'user',
        'expected': [(IssueSubmitter.INVALID_CONFIG, None)]
    },
    {  # p4: debug enabled, username and password set, but no errors to report
        'debug': True,
        'username': 'user',
        'password': 'pass',
        'expected': [(IssueSubmitter.NO_ISSUES, None)]
    },
    {  # p5: debug enabled, username and password set, errors to report but update is needed
        'debug': True,
        'username': 'user',
        'password': 'pass',
        'errors': ['Some Error'],
        'need_update': True,
        'expected': [(IssueSubmitter.UNSUPPORTED_VERSION, None)]
    },
    {  # p6: debug enabled, username and password set, errors to report, no update is needed, but it's already running
        'debug': True,
        'username': 'user',
        'password': 'pass',
        'errors': ['Some Error'],
        'running': True,
        'expected': [(IssueSubmitter.ALREADY_RUNNING, None)]
    },
    {  # p7: debug enabled, username and password set, errors to report, update is needed but I'M A DEVELOPER :-)
        'debug': True,
        'username': 'user',
        'password': 'pass',
        'errors': ['Some Error'],
        'need_update': True,
        'developer': True,
        'exception': [BadCredentialsException, 401],
        'expected': [(IssueSubmitter.BAD_CREDENTIALS, None)]
    },
    {  # p8: debug enabled, username and password set, errors to report, update is not needed but rate limit exception happened
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
    monkeypatch.setattr('medusa.DEBUG', p.get('debug'))
    monkeypatch.setattr('medusa.GIT_USERNAME', p.get('username'))
    monkeypatch.setattr('medusa.GIT_PASSWORD', p.get('password'))
    monkeypatch.setattr('medusa.DEVELOPER', p.get('developer', False))
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
        'expected': True
    },
    {  # p1: Similar
        'text1': 'My Issue Title',
        'text2': 'My Issue Title 1',
        'expected': True
    },
    {  # p2: Similar
        'text1': 'SSLError: [SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] sslv3 alert handshake failure (_ssl.c:590)',
        'text2': '[SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] sslv3 alert handshake failure (_ssl.c:645)',
        'expected': True
    },
    {  # p3: Similar
        'text1': 'SSLError: [Errno 1] _ssl.c:504: error:14077438:SSL routines:SSL23_GET_SERVER_HELLO:tlsv1 alert internal error',
        'text2': '[Errno 1] _ssl.c:510: error:14077438:SSL routines:SSL23_GET_SERVER_HELLO:tlsv1 alert internal error',
        'expected': True
    },
    {  # p4: Similar
        'text1': 'Another Issue',
        'text2': 'My Issue',
        'expected': False
    }
])
def test_similar(p):
    # Given
    text1 = p['text1']
    text2 = p['text2']
    expected = p['expected']

    # When
    actual = sut.similar(text1, text2)

    # Then
    assert expected == actual


def test_create_gist(logger, read_loglines, github):
    # Given
    line = 'Some Log Line'
    logger.error(line)
    logline = list(read_loglines)[0]
    filename = 'sickrage.log'

    # When
    actual = sut.create_gist(github, logline)

    # Then
    assert actual
    assert not actual.public
    assert filename in actual.files
    assert line in actual.files[filename]


def test_find_similar_issues(monkeypatch, logger, github_repo, read_loglines, create_github_issue):
    # Given
    line1 = 'Some Issue Like This'
    line2 = 'Unexpected thing happened'
    line3 = 'Really strange this one'
    for line in [line1, line2, line3]:
        logger.warn(line)
    loglines = list(read_loglines)
    issue1 = create_github_issue('[APP SUBMITTED]: Really strange that one')
    issue2 = create_github_issue('Some Issue like This')
    monkeypatch.setattr(github_repo, 'get_issues', lambda *args, **kwargs: [issue1, issue2])
    expected = {
        line1: issue2,
        line3: issue1,
    }

    # When
    actual = sut.find_similar_issues(github_repo, list(loglines))

    # Then
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
