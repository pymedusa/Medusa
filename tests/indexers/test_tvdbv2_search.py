# coding=utf-8
"""Tests for TVDB website show search."""
from __future__ import unicode_literals

from medusa.indexers.exceptions import IndexerUnavailable
from medusa.indexers.tvdbv2.api import TVDB_WEB_SEARCH_URL, TVDBv2
from medusa.session.core import IndexerSession

import pytest


def create_indexer(**kwargs):
    """Create a TVDB indexer with a fresh legacy session."""
    return TVDBv2(session=IndexerSession(), cache=False, **kwargs)


def mock_web_search(requests_mock, hits):
    """Mock a successful TVDB website search response."""
    return requests_mock.post(
        TVDB_WEB_SEARCH_URL,
        json={'results': [{'hits': hits}]},
    )


def test_search_uses_website_endpoint_and_maps_results(requests_mock):
    mock_web_search(requests_mock, [{
        'id': '123',
        'name': 'Original Name',
        'translations': {'eng': 'Test Show'},
        'first_air_date': '2026-08-18',
        'aliases': ['Test Alias', 'Another Alias'],
        'network': 'Test Network',
        'overviews': {'eng': 'Test overview'},
        'image_url': 'https://artworks.thetvdb.com/test.jpg',
    }])

    assert [{
        'id': 123,
        'seriesname': 'Test Show',
        'firstaired': '2026-08-18',
        'aliases': 'Test Alias|Another Alias',
        'network': 'Test Network',
        'overview': 'Test overview',
        'poster_thumb': 'https://artworks.thetvdb.com/test.jpg',
    }] == create_indexer().search('test')

    request = requests_mock.request_history[0]
    assert {
        'requests': [{
            'indexName': 'TVDB',
            'params': {
                'query': 'test',
                'filters': 'type:series AND NOT is_official=0',
            },
        }],
    } == request.json()
    assert 'Authorization' not in request.headers


def test_search_uses_requested_language(requests_mock):
    mock_web_search(requests_mock, [{
        'id': 123,
        'name': 'Test Show',
        'translations': {'fra': 'Série de test'},
        'overview': 'Default overview',
        'overviews': {'fra': 'Résumé de test'},
        'poster': 'https://artworks.thetvdb.com/poster.jpg',
    }])

    assert [{
        'id': 123,
        'seriesname': 'Série de test',
        'overview': 'Résumé de test',
        'poster_thumb': 'https://artworks.thetvdb.com/poster.jpg',
    }] == create_indexer(language='fr').search('test')


def test_search_ignores_invalid_results(requests_mock):
    mock_web_search(requests_mock, [
        {'id': 'invalid', 'name': 'Invalid ID'},
        {'id': 123, 'name': ''},
        {'id': 456, 'name': 'Valid Show', 'year': '2026'},
    ])

    assert [{
        'id': 456,
        'seriesname': 'Valid Show',
        'firstaired': '2026',
    }] == create_indexer().search('test')


def test_search_returns_none_without_hits(requests_mock):
    mock_web_search(requests_mock, [])

    assert create_indexer().search('test') is None


def test_search_rejects_invalid_website_response(requests_mock):
    requests_mock.post(TVDB_WEB_SEARCH_URL, json={'results': []})

    with pytest.raises(IndexerUnavailable):
        create_indexer().search('test')


def test_search_rejects_website_error(requests_mock):
    requests_mock.post(TVDB_WEB_SEARCH_URL, status_code=503)

    with pytest.raises(IndexerUnavailable):
        create_indexer().search('test')


def test_resolve_series_id_uses_unique_imdb_match(requests_mock):
    mock_web_search(requests_mock, [
        {
            'id': 443213,
            'name': 'American Hostage',
            'year': '2024',
            'remote_ids': [{'id': 'tt1234567', 'sourceName': 'IMDB'}],
        },
        {
            'id': 462907,
            'name': 'American Hostage',
            'year': '2026',
            'remote_ids': [{'id': 'tt30051064', 'sourceName': 'IMDB'}],
        },
    ])

    assert 462907 == create_indexer().resolve_series_id(
        'American Hostage', imdb_id='tt30051064', year=2026
    )


def test_resolve_series_id_uses_unique_title_and_year_match(requests_mock):
    mock_web_search(requests_mock, [
        {'id': 123, 'name': 'Test Show', 'year': '2025'},
        {'id': 456, 'name': 'Test Show', 'first_air_date': '2026-03-12'},
    ])

    assert 456 == create_indexer().resolve_series_id('  test SHOW ', year=2026)


def test_resolve_series_id_rejects_ambiguous_match(requests_mock):
    mock_web_search(requests_mock, [
        {'id': 123, 'name': 'Test Show', 'year': '2026'},
        {'id': 456, 'name': 'Test Show', 'year': '2026'},
    ])

    assert create_indexer().resolve_series_id('Test Show', year=2026) is None


def test_resolve_series_id_rejects_conflicting_imdb_match(requests_mock):
    mock_web_search(requests_mock, [{
        'id': 456,
        'name': 'Test Show',
        'year': '2026',
        'remote_ids': [{'id': 'tt7654321', 'sourceName': 'IMDB'}],
    }])

    assert create_indexer().resolve_series_id(
        'Test Show', imdb_id='tt1234567', year=2026
    ) is None
