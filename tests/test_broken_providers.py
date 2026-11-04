# coding=utf-8
"""Tests for scheduled broken-provider updates."""
from __future__ import unicode_literals

import datetime

from medusa import app, helpers
from medusa.updater.version_checker import CheckVersion

from mock.mock import Mock

import pytest


@pytest.fixture
def provider_session(monkeypatch):
    """Isolate provider requests and their last-attempt timestamp."""
    monkeypatch.setattr(app, 'BROKEN_PROVIDERS_UPDATE', None)
    monkeypatch.setattr(app, 'BROKEN_PROVIDERS', ['existing-provider'])
    session = Mock()
    monkeypatch.setattr(helpers, 'MedusaSafeSession', Mock(return_value=session))
    return session


@pytest.mark.parametrize('response, expected', [
    (['broken-provider'], ['broken-provider']),
    ([], []),
    (None, None),
    ({'error': 'unavailable'}, None),
    (False, None),
    ('unavailable', None),
])
def test_broken_provider_fetch_distinguishes_empty_list_from_failure(provider_session, response, expected):
    """An empty successful list is usable, while a failed request has no replacement."""
    provider_session.get_json.return_value = response

    assert helpers.get_broken_providers() == expected
    provider_session.get_json.assert_called_once_with(
        '{0}/providers/broken_providers.json'.format(app.BASE_PYMEDUSA_URL))
    assert isinstance(app.BROKEN_PROVIDERS_UPDATE, datetime.datetime)
    assert app.BROKEN_PROVIDERS == ['existing-provider']


def test_broken_provider_fetch_skips_recent_attempt(provider_session, monkeypatch):
    """Repeated calls within an hour do not make another request."""
    last_attempt = datetime.datetime.now() - datetime.timedelta(minutes=30)
    monkeypatch.setattr(app, 'BROKEN_PROVIDERS_UPDATE', last_attempt)

    assert helpers.get_broken_providers() is None
    helpers.MedusaSafeSession.assert_not_called()
    assert app.BROKEN_PROVIDERS_UPDATE == last_attempt


@pytest.mark.parametrize('elapsed', [datetime.timedelta(minutes=61), datetime.timedelta(days=1, minutes=30)])
def test_broken_provider_fetch_refreshes_after_an_hour(provider_session, monkeypatch, elapsed):
    """Elapsed days must not wrap the hourly throttle back into its skipped interval."""
    last_attempt = datetime.datetime.now() - elapsed
    monkeypatch.setattr(app, 'BROKEN_PROVIDERS_UPDATE', last_attempt)
    provider_session.get_json.return_value = ['new-provider']

    assert helpers.get_broken_providers() == ['new-provider']
    provider_session.get_json.assert_called_once()
    assert app.BROKEN_PROVIDERS_UPDATE > last_attempt


@pytest.mark.parametrize('fresh, expected', [
    (['new-provider'], ['new-provider']),
    ([], []),
    (None, ['existing-provider']),
    (['existing-provider'], ['existing-provider']),
])
def test_version_job_refreshes_providers_without_an_updater(monkeypatch, fresh, expected):
    """Refresh provider data independently and save only changed successful results."""
    monkeypatch.setattr(app, 'BROKEN_PROVIDERS', ['existing-provider'])
    instance = Mock()
    monkeypatch.setattr(app, 'instance', instance)
    fetch = Mock(return_value=fresh)
    monkeypatch.setattr(helpers, 'get_broken_providers', fetch)
    checker = CheckVersion.__new__(CheckVersion)
    checker.updater = None
    checker.list_remote_branches = Mock()

    checker.run()

    fetch.assert_called_once_with()
    assert app.BROKEN_PROVIDERS == expected
    if expected != ['existing-provider']:
        instance.save_config.assert_called_once_with()
    else:
        instance.save_config.assert_not_called()
    assert checker.amActive is False


def test_version_job_continues_when_provider_list_cannot_be_saved(monkeypatch):
    """A configuration write failure must not stop future background checks."""
    monkeypatch.setattr(app, 'BROKEN_PROVIDERS', ['existing-provider'])
    monkeypatch.setattr(helpers, 'get_broken_providers', Mock(return_value=['new-provider']))
    instance = Mock()
    instance.save_config.side_effect = OSError('Configuration file is not writable')
    monkeypatch.setattr(app, 'instance', instance)
    checker = CheckVersion.__new__(CheckVersion)
    checker.updater = None
    checker.list_remote_branches = Mock()

    checker.run()

    assert app.BROKEN_PROVIDERS == ['new-provider']
    instance.save_config.assert_called_once_with()
    checker.list_remote_branches.assert_called_once_with()
    assert checker.amActive is False
