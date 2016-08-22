# coding=utf-8
"""Tests for sickbeard.server.web.core.error_logs.py."""

import pytest

from sickbeard import classes
from sickbeard.issuesubmitter import IssueSubmitter


sut = IssueSubmitter()


@pytest.mark.parametrize('p', [
    {  # p0: debug not enabled
        'debug': False,
        'username': 'user',
        'password': 'pass',
        'errors': ['Some Error'],
        'need_update': False,
        'running': False,
        'expected': [(IssueSubmitter.INVALID_CONFIG, None)]
    },
    {  # p1: debug not set
        'debug': None,
        'username': 'user',
        'password': 'pass',
        'errors': ['Some Error'],
        'need_update': False,
        'running': False,
        'expected': [(IssueSubmitter.INVALID_CONFIG, None)]
    },
    {  # p2: debug enabled, but no username
        'debug': None,
        'username': '',
        'password': 'pass',
        'errors': ['Some Error'],
        'need_update': False,
        'running': False,
        'expected': [(IssueSubmitter.INVALID_CONFIG, None)]
    },
    {  # p3: debug enabled, but no password
        'debug': None,
        'username': 'user',
        'password': '',
        'errors': ['Some Error'],
        'need_update': False,
        'running': False,
        'expected': [(IssueSubmitter.INVALID_CONFIG, None)]
    },
    {  # p4: debug enabled, username and password set, but no errors to report
        'debug': True,
        'username': 'user',
        'password': 'pass',
        'errors': [],
        'need_update': False,
        'running': False,
        'expected': [(IssueSubmitter.NO_ISSUES, None)]
    },
    {  # p5: debug enabled, username and password set, errors to report but update is needed
        'debug': True,
        'username': 'user',
        'password': 'pass',
        'errors': ['Some Error'],
        'need_update': True,
        'running': False,
        'expected': [(IssueSubmitter.UNSUPPORTED_VERSION, None)]
    },
    {  # p6: debug enabled, username and password set, errors to report, update is needed but I'M A DEVELOPER :-)
        'debug': True,
        'username': 'user',
        'password': 'pass',
        'errors': ['Some Error'],
        'need_update': True,
        'developer': True,
        'running': False,
        'expected': [(IssueSubmitter.BAD_CREDENTIALS, None)]
    },
    {  # p7: debug enabled, username and password set, errors to report, no update is needed, but it's already running
        'debug': True,
        'username': 'user',
        'password': 'pass',
        'errors': ['Some Error'],
        'need_update': False,
        'running': True,
        'expected': [(IssueSubmitter.ALREADY_RUNNING, None)]
    }
])
def test_submit_github_issue__basic_validations(monkeypatch, logger, version_checker, p):
    # Given
    classes.ErrorViewer.clear()
    for error in p['errors']:
        logger.error(error)
    monkeypatch.setattr('sickbeard.DEBUG', p['debug'])
    monkeypatch.setattr('sickbeard.GIT_USERNAME', p['username'])
    monkeypatch.setattr('sickbeard.GIT_PASSWORD', p['password'])
    monkeypatch.setattr('sickbeard.DEVELOPER', p.get('developer', False))
    monkeypatch.setattr(version_checker, 'need_update', lambda: p['need_update'])
    monkeypatch.setattr(sut, 'running', p['running'])

    # When
    actual = sut.submit_github_issue(version_checker)

    # Then
    assert p['expected'] == actual
