# coding=utf-8
"""Test provider result filtering against recorded cache rows."""
from __future__ import unicode_literals

import json
import sqlite3

from medusa import app
from medusa.tv.cache import Cache

from mock.mock import Mock

import pytest


@pytest.fixture
def cached_provider(monkeypatch):
    """Use the real cache query and API serializer with an isolated SQLite database."""
    connection = sqlite3.connect(':memory:', check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute(
        'CREATE TABLE test_provider ('
        'identifier TEXT, name TEXT DEFAULT "Release", season INTEGER, episodes TEXT, '
        'indexer INTEGER, indexerid INTEGER, url TEXT DEFAULT "https://example.invalid/release", '
        'time INTEGER DEFAULT 0, quality INTEGER DEFAULT 0, release_group TEXT DEFAULT "Group", '
        'date_added INTEGER DEFAULT 0, version INTEGER DEFAULT 1, seeders INTEGER DEFAULT 1, '
        'size INTEGER DEFAULT 100, leechers INTEGER DEFAULT 0, pubdate TEXT)'
    )
    connection.executemany(
        'INSERT INTO test_provider (identifier, indexer, indexerid, season, episodes) VALUES (?, ?, ?, ?, ?)',
        [
            ('single', 1, 123, 1, '|1|'),
            ('multi_first', 1, 123, 1, '|1|2|'),
            ('multi_last', 1, 123, 1, '|2|1|'),
            ('eleven', 1, 123, 1, '|11|'),
            ('season_pack', 1, 123, 1, '||'),
            ('other_season', 1, 123, 2, '|1|'),
            ('other_show', 1, 124, 1, '|1|'),
            ('other_indexer', 3, 123, 1, '|1|'),
            ('special_single', 1, 123, 0, '|1|'),
            ('special_multi', 1, 123, 0, '|1|2|'),
            ('zero_single', 1, 123, 1, '|0|'),
            ('zero_multi', 1, 123, 1, '|0|1|')
        ]
    )
    provider = Mock()
    provider.name = 'Test Provider'
    provider.get_id.return_value = 'test_provider'
    provider.image_name.return_value = 'missing.png'
    provider.cache = Cache(provider)
    provider.cache.provider_db = Mock()
    provider.cache.provider_db.select.side_effect = lambda query, args: connection.execute(query, args).fetchall()
    monkeypatch.setattr(app, 'providerList', [provider])
    for attribute in ('newznabProviderList', 'torrentRssProviderList', 'torznab_providers_list'):
        monkeypatch.setattr(app, attribute, [])

    yield provider
    connection.close()


@pytest.mark.gen_test
@pytest.mark.parametrize('episode, expected', [
    (1, {'single', 'multi_first', 'multi_last', 'zero_multi'}),
    (2, {'multi_first', 'multi_last'}),
    (11, {'eleven'}),
    (0, {'zero_single', 'zero_multi'})
])
async def test_provider_results_match_episode_membership(
        cached_provider, http_client, create_url, auth_headers, episode, expected):
    """Include each multi-episode release containing the requested complete episode number."""
    response = await http_client.fetch(create_url(
        '/providers/test_provider/results', showslug='tvdb123', season=1, episode=episode, limit=100
    ), raise_error=False, **auth_headers)

    assert response.code == 200
    results = json.loads(response.body)
    assert {row['identifier'] for row in results} == expected
    assert all(episode in row['episodes'] for row in results)


@pytest.mark.gen_test
@pytest.mark.parametrize('season, expected', [
    (0, {'special_single', 'special_multi'}),
    (1, {'single', 'multi_first', 'multi_last', 'eleven', 'season_pack', 'zero_single', 'zero_multi'})
])
async def test_provider_results_without_episode_keep_all_season_releases(
        cached_provider, http_client, create_url, auth_headers, season, expected):
    """Omitting the episode retains season packs while respecting show, indexer, and specials."""
    response = await http_client.fetch(create_url(
        '/providers/test_provider/results', showslug='tvdb123', season=season, limit=100
    ), **auth_headers)

    assert response.code == 200
    assert {row['identifier'] for row in json.loads(response.body)} == expected


@pytest.mark.gen_test
async def test_provider_results_paginate_after_episode_filtering(
        cached_provider, http_client, create_url, auth_headers):
    """Matching multi-episode results remain available across API pages without duplicates."""
    pages = []
    for page in (1, 2, 3):
        response = await http_client.fetch(create_url(
            '/providers/test_provider/results', showslug='tvdb123', season=1, episode=1, limit=2, page=page
        ), **auth_headers)
        assert response.code == 200
        assert response.headers['X-Pagination-Page'] == str(page)
        assert response.headers['X-Pagination-Limit'] == '2'
        pages.append(json.loads(response.body))

    assert [len(page) for page in pages] == [2, 2, 0]
    identifiers = [row['identifier'] for page in pages for row in page]
    assert len(identifiers) == len(set(identifiers))
    assert set(identifiers) == {'single', 'multi_first', 'multi_last', 'zero_multi'}


@pytest.mark.parametrize('filters, expected', [
    ({'season': 0}, {'special_single', 'special_multi'}),
    ({'season': 1, 'episode': 0}, {'zero_single', 'zero_multi'})
])
def test_cache_results_preserve_numeric_zero_filters(cached_provider, filters, expected):
    """Numeric zero is a season or episode filter, rather than an omitted value."""
    results = cached_provider.cache.get_results(show_slug='tvdb123', **filters)

    assert {row['identifier'] for row in results} == expected
