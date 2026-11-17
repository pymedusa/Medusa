# coding=utf-8
"""Test history payloads sent to clients through WebSocket updates."""
from __future__ import unicode_literals

from medusa import app
from medusa.common import DOWNLOADED, FAILED, SNATCHED, SUBTITLED
from medusa.history import create_history_item

from mock.mock import Mock

import pytest


@pytest.fixture
def history_row(monkeypatch):
    """Provide a history row whose former provider is no longer configured."""
    for attribute in ('providerList', 'newznabProviderList', 'torrentRssProviderList', 'torznab_providers_list'):
        monkeypatch.setattr(app, attribute, [])
    return {
        'action': SNATCHED,
        'provider': 'Removed Custom Provider',
        'resource': 'Example.Show.S01E01.720p.mkv',
        'client_status': None,
        'indexer_id': None,
        'showid': None,
        'season': 1,
        'episode': 1,
        'date': 20261028000000,
        'quality': 0,
        'size': 0,
        'proper_tags': '',
        'manually_searched': 0,
        'info_hash': '',
        'provider_type': 'nzb',
        'part_of_batch': 0
    }


@pytest.mark.parametrize('action', [SNATCHED, FAILED])
def test_history_update_uses_missing_icon_for_removed_provider(history_row, action):
    """Unknown providers retain their identity without requesting a nonexistent icon."""
    history_row['action'] = action

    payload = create_history_item(history_row)

    assert payload['provider'] == {
        'id': 'removed_custom_provider',
        'name': 'Removed Custom Provider',
        'imageName': 'missing.png'
    }
    assert payload['releaseName'] == history_row['resource']


@pytest.mark.parametrize('action', [SNATCHED, FAILED])
def test_history_update_uses_configured_provider_artwork(monkeypatch, history_row, action):
    """Configured providers continue supplying their own artwork through the resolver."""
    provider = Mock()
    provider.name = 'Custom Digital Carnage'
    provider.get_id.return_value = 'custom_digital_carnage'
    provider.image_name.return_value = 'prowlarr.png'
    monkeypatch.setattr(app, 'newznabProviderList', [provider])
    history_row.update(action=action, provider=provider.name)

    payload = create_history_item(history_row)

    assert payload['provider'] == {
        'id': 'custom_digital_carnage',
        'name': 'Custom Digital Carnage',
        'imageName': 'prowlarr.png'
    }


def test_history_update_preserves_subtitle_provider(history_row):
    """Subtitle providers keep their separate image path and language metadata."""
    history_row.update(action=SUBTITLED, provider='opensubtitles', resource='eng')

    payload = create_history_item(history_row)

    assert payload['provider'] == {'name': 'opensubtitles'}
    assert payload['subtitleLanguage'] == 'eng'


def test_history_update_preserves_downloaded_release_group(history_row):
    """Downloaded rows expose the release group without provider artwork."""
    history_row.update(action=DOWNLOADED, provider='Release Group')

    payload = create_history_item(history_row)

    assert payload['provider'] == {}
    assert payload['releaseGroup'] == 'Release Group'
    assert payload['fileName'] == history_row['resource']
