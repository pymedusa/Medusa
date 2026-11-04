# coding=utf-8
"""Test provider image metadata in History API responses."""
from __future__ import unicode_literals

import json

from medusa import db
from medusa.common import DOWNLOADED, FAILED, SNATCHED, SUBTITLED
from medusa.providers.generic_provider import GenericProvider
from medusa.server.api.v2 import episode_history
from medusa.tv.episode import Episode
from medusa.tv.series import Series

from mock.mock import Mock

import pytest


def history_row(series, action, provider, rowid):
    """Return a controlled DB history row for a series episode."""
    return {
        'rowid': rowid,
        'date': 20261028000000,
        'action': action,
        'quality': 0,
        'provider': provider,
        'version': '',
        'resource': 'Example.Show.S01E01.720p.mkv',
        'size': 0,
        'proper_tags': '',
        'indexer_id': series.indexer,
        'showid': series.series_id,
        'season': 1,
        'episode': 1,
        'manually_searched': 0,
        'info_hash': '',
        'provider_type': 'nzb',
        'client_status': None,
        'part_of_batch': 0
    }


@pytest.mark.gen_test
async def test_episode_history_resolves_provider_icon_and_preserves_other_statuses(
        monkeypatch, http_client, create_url, auth_headers, create_tvshow, create_tvepisode):
    """Resolve configured provider artwork and use a local fallback for unknown providers."""
    series = create_tvshow(indexerid=123)
    episode = create_tvepisode(series, season=1, episode=1)
    custom_provider_id = GenericProvider.make_id('Custom Digital Carnage')
    custom_provider = Mock()
    custom_provider.get_id.return_value = custom_provider_id
    custom_provider.name = 'Digital Carnage'
    custom_provider.image_name.return_value = 'prowlarr.png'
    nyaa_provider = Mock()
    nyaa_provider.get_id.return_value = 'nyaa'
    nyaa_provider.name = 'Nyaa'
    nyaa_provider.image_name.return_value = 'nyaa.png'
    provider_classes = {custom_provider_id: custom_provider, 'nyaa': nyaa_provider}
    monkeypatch.setattr(Series, 'find_by_identifier', classmethod(lambda cls, identifier: series))
    monkeypatch.setattr(
        Episode, 'find_by_series_and_episode', classmethod(lambda cls, found_series, number: episode))
    monkeypatch.setattr(
        episode_history, 'get_provider_class', lambda provider_id: provider_classes.get(provider_id), raising=False)
    rows = [
        history_row(series, SNATCHED, 'Custom Digital Carnage', 1),
        history_row(series, SNATCHED, 'Nyaa', 2),
        history_row(series, FAILED, 'Tokyo Toshokan', 3),
        history_row(series, SUBTITLED, 'Subtitles', 4),
        history_row(series, DOWNLOADED, 'Release Group', 5)
    ]
    monkeypatch.setattr(db, 'DBConnection', lambda: Mock(select=Mock(return_value=rows)))

    response = await http_client.fetch(
        create_url('/history/tvdb123/episode/s01e01'), **auth_headers)

    assert response.code == 200
    actual = json.loads(response.body)
    assert actual[0]['provider'] == {
        'id': custom_provider_id, 'name': 'Custom Digital Carnage', 'imageName': 'prowlarr.png'
    }
    assert actual[1]['provider'] == {'id': 'nyaa', 'name': 'Nyaa', 'imageName': 'nyaa.png'}
    assert actual[2]['provider'] == {
        'id': GenericProvider.make_id('Tokyo Toshokan'),
        'name': 'Tokyo Toshokan',
        'imageName': 'missing.png'
    }
    assert actual[3]['provider'] == {'id': 'Subtitles', 'name': 'Subtitles'}
    assert actual[3]['subtitleLanguage'] == 'Example.Show.S01E01.720p.mkv'
    assert actual[4]['statusName'] == 'Downloaded'
    assert actual[4]['provider'] == {}
    assert actual[4]['releaseGroup'] == 'Release Group'


@pytest.mark.gen_test
@pytest.mark.parametrize('compact', [False, True])
async def test_history_unknown_provider_uses_missing_icon_in_both_layouts(
        compact, monkeypatch, http_client, create_url, auth_headers, create_tvshow):
    """Both global History serializers provide the same missing icon for unknown providers."""
    series = create_tvshow(indexerid=123)
    row = history_row(series, SNATCHED, 'Nyaa SI', 1)
    monkeypatch.setattr(Series, 'find_by_identifier', classmethod(lambda cls, identifier: None))
    monkeypatch.setattr(db, 'DBConnection', lambda: Mock(select=Mock(return_value=[row])))

    url = create_url('/history', compact='true') if compact else create_url('/history')
    response = await http_client.fetch(url, **auth_headers)

    assert response.code == 200
    actual = json.loads(response.body)
    assert actual
    item = actual[0]['rows'][0] if compact else actual[0]
    assert 'provider' in item, item
    provider = item['provider']
    assert provider == {
        'id': GenericProvider.make_id('Nyaa SI'), 'name': 'Nyaa SI', 'imageName': 'missing.png'
    }
