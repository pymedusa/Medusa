# coding=utf-8
"""Tests for shared stale indexer ID resolution."""
from __future__ import unicode_literals

from types import SimpleNamespace

from medusa.indexers.base import BaseIndexer
from medusa.indexers.exceptions import IndexerShowNotFound
from medusa.indexers.imdb.api import Imdb
from medusa.indexers.tmdb.api import Tmdb
from medusa.indexers.tvmaze.api import TVmaze

from mock.mock import Mock

import pytest

from requests.exceptions import HTTPError


def create_indexer(results):
    """Create an indexer with mocked normalized search results."""
    indexer = BaseIndexer(cache=False)
    indexer.name = 'test'
    indexer.search = Mock(return_value=results)
    return indexer


def test_resolve_series_id_searches_once_and_uses_imdb_match():
    indexer = create_indexer([
        {'id': 123, 'seriesname': 'Test Show', 'firstaired': '2026', 'imdb_id': 'tt7654321'},
        {'id': 456, 'seriesname': 'Test Show', 'firstaired': '2026', 'imdb_id': 'tt1234567'},
    ])

    assert 456 == indexer.resolve_series_id('Test Show', imdb_id='tt1234567', year=2026)
    indexer.search.assert_called_once_with('Test Show')


def test_resolve_series_id_uses_unique_title_and_year_without_external_ids():
    indexer = create_indexer([
        {'id': 123, 'seriesname': 'Test Show', 'firstaired': '2025-01-01'},
        {'id': 456, 'seriesname': 'Test Show', 'firstaired': '2026-01-01'},
    ])

    assert 456 == indexer.resolve_series_id('test show', imdb_id='tt1234567', year=2026)


def test_resolve_series_id_rejects_ambiguous_results():
    indexer = create_indexer([
        {'id': 123, 'seriesname': 'Test Show', 'firstaired': '2026'},
        {'id': 456, 'seriesname': 'Test Show', 'firstaired': '2026'},
    ])

    assert indexer.resolve_series_id('Test Show', year=2026) is None


def test_resolve_series_id_reads_nested_external_ids():
    indexer = create_indexer([{
        'id': 456,
        'seriesname': 'Test Show',
        'external_ids': {'imdb_id': 'tt1234567'},
    }])

    assert 456 == indexer.resolve_series_id('Test Show', imdb_id='tt1234567')


def test_tmdb_reports_missing_id_as_show_not_found():
    indexer = object.__new__(Tmdb)
    indexer.tmdb = Mock()
    response = Mock(status_code=404)
    indexer.tmdb.TV.return_value.info.side_effect = HTTPError(response=response)

    with pytest.raises(IndexerShowNotFound):
        indexer._get_show_by_id(123)


def test_tvmaze_search_results_support_stale_id_resolution():
    indexer = TVmaze(cache=False)
    indexer._show_search = Mock(return_value=[SimpleNamespace(
        id=84262,
        name='American Hostage',
        premiered='2026-09-20',
        externals=SimpleNamespace(imdb='tt30051064'),
    )])

    assert 84262 == indexer.resolve_series_id(
        'American Hostage', imdb_id='tt30051064', year=2026
    )


def test_tmdb_search_results_support_stale_id_resolution(monkeypatch):
    configuration = Mock()
    configuration.info.return_value = {}
    monkeypatch.setattr('medusa.indexers.tmdb.api.tmdb.Configuration', Mock(return_value=configuration))
    indexer = Tmdb(cache=False)
    indexer._show_search = Mock(return_value=[
        {'id': 123, 'name': 'American Hostage', 'first_air_date': '2024-01-01'},
        {'id': 239618, 'name': 'American Hostage', 'first_air_date': '2026-09-20'},
    ])

    assert 239618 == indexer.resolve_series_id(
        'American Hostage', imdb_id='tt30051064', year=2026
    )


def test_imdb_search_results_support_stale_id_resolution():
    indexer = Imdb(cache=False)
    indexer._show_search = Mock(return_value=[{
        'imdb_id': '/title/tt30051064/',
        'title': 'American Hostage',
        'type': 'TV series',
        'year': 2026,
    }])

    assert 30051064 == indexer.resolve_series_id('American Hostage', year=2026)
