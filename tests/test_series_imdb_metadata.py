# coding=utf-8
"""Regression tests for series loading with malformed IMDb metadata."""
from __future__ import unicode_literals

import threading

from medusa import app
from medusa.common import SKIPPED
from medusa.indexers.base import Show
from medusa.indexers.config import INDEXER_TVDBV2
from medusa.indexers.tvdbv2.api import TVDBv2
from medusa.queues import show_queue
from medusa.tv import series as series_module
from medusa.tv.series import Series, SeriesIdentifier

from mock.mock import MagicMock, Mock

import pytest


@pytest.fixture
def isolated_series(monkeypatch):
    """Create a real Series while isolating database, external lookup and cache writes."""
    monkeypatch.setattr(app, 'showList', [])
    monkeypatch.setattr(app, 'SUBTITLES_DEFAULT', 0)
    monkeypatch.setattr(Series, '_load_from_db', Mock())
    monkeypatch.setattr(Series, 'init_search_templates', Mock())
    monkeypatch.setattr(series_module, 'get_externals', Mock(return_value={}))
    monkeypatch.setattr(series_module, 'Imdb', Mock())
    monkeypatch.setattr(series_module.helpers, 'title_to_imdb', Mock(return_value=None))
    series_module.Imdb.return_value.get_title.return_value = None
    series = Series(INDEXER_TVDBV2, 457780, quality=1, season_folders=1)
    monkeypatch.setattr(series, '_save_externals_to_db', Mock())
    return series


@pytest.mark.parametrize('external, raw, expected', [
    (6135388, 'tt7654321', 'tt6135388'),
    ('tt6135388', {'invalid': True}, 'tt6135388'),
    (None, 'tt6135388/episodes/?season=2&ref_=ttep', 'tt6135388'),
    (None, 'https://www.imdb.com/title/tt6135388/episodes/', 'tt6135388'),
    (None, 'tt6135388,tt7654321', 'tt6135388'),
    (None, 6135388, 'tt6135388'),
    (None, 0, 'tt0000000'),
    ('invalid', 'tt6135388', 'tt6135388'),
    (None, 'ttinvalid', None),
    (None, {'invalid': True}, None),
    (None, True, None),
    (None, None, None),
    ('invalid', 'invalid', None),
])
def test_series_normalizes_fallback_and_preserves_external_precedence(isolated_series, external, raw, expected):
    """Use a normalized external first, then a normalized raw indexer value."""
    indexed_show = Show()
    indexed_show.data.update({
        'seriesname': 'Test Show',
        'status': 'Continuing',
        'imdb_id': raw,
        'externals': {'imdb_id': external},
    })
    api = MagicMock(indexer=INDEXER_TVDBV2)
    api.__getitem__.return_value = indexed_show
    isolated_series.indexer_api = api

    isolated_series.load_from_indexer(tvapi=api)

    assert expected == isolated_series.imdb_id
    isolated_series.load_imdb_info()
    if expected:
        series_module.Imdb.return_value.get_title.assert_called_once_with(expected)
        series_module.helpers.title_to_imdb.assert_not_called()
    else:
        series_module.Imdb.return_value.get_title.assert_not_called()
        series_module.helpers.title_to_imdb.assert_called_once_with('Test Show', 0, series_module.Imdb.return_value)


@pytest.mark.parametrize('raw, expected', [
    ('tt6135388/episodes/?season=2&ref_=ttep', 'tt6135388'),
    ({'invalid': True}, None),
    ('ttinvalid', None),
    (None, None),
])
def test_tvdb_metadata_reaches_series_and_imdb_loading_safely(monkeypatch, isolated_series, raw, expected):
    """Exercise the real TVDB metadata conversion and Series add-time loading methods."""
    api = TVDBv2(session=MagicMock(), cache=False, episodes=False)
    api.indexer = INDEXER_TVDBV2
    response = Mock(return_value={'series': {
        'id': 457780,
        'seriesname': 'Test Show',
        'imdb_id': raw,
        'firstaired': '2025-01-01',
        'network': 'Test Network',
        'overview': 'Test overview',
        'status': 'Continuing',
    }})
    monkeypatch.setattr(api, '_get_show_by_id', response)
    isolated_series.indexer_api = api

    isolated_series.load_from_indexer(tvapi=api)
    isolated_series.load_imdb_info()

    response.assert_called_once_with(457780, request_language='en')
    assert expected == isolated_series.imdb_id
    assert 'Test Network' == isolated_series.network
    assert 'Test overview' == isolated_series.plot
    assert 2025 == isolated_series.start_year
    assert ('Continuing', 'Test Show') == (isolated_series.status, isolated_series.name)
    if expected:
        series_module.Imdb.return_value.get_title.assert_called_once_with(expected)
    else:
        series_module.Imdb.return_value.get_title.assert_not_called()
        series_module.helpers.title_to_imdb.assert_called_once_with('Test Show', 2025, series_module.Imdb.return_value)


@pytest.mark.parametrize('initial, search_result, expected', [
    ('tt6135388,tt7654321', None, 'tt6135388'),
    ('ttinvalid', None, None),
    ({'invalid': True}, None, None),
    (None, {'invalid': True}, None),
    (None, 'ttinvalid', None),
    (None, 6135388, 'tt6135388'),
    (None, 'tt6135388,tt7654321', 'tt6135388'),
    (None, 'tt6135388/episodes/?season=2&ref_=ttep', 'tt6135388'),
])
def test_imdb_loading_normalizes_chosen_identifier(isolated_series, initial, search_result, expected):
    """Normalize existing or searched identifiers before invoking IMDb."""
    isolated_series.imdb_id = initial
    series_module.helpers.title_to_imdb.return_value = search_result

    isolated_series.load_imdb_info()

    assert expected == isolated_series.imdb_id
    if expected:
        series_module.Imdb.return_value.get_title.assert_called_once_with(expected)
    else:
        series_module.Imdb.return_value.get_title.assert_not_called()


@pytest.mark.parametrize('raw, expected', [
    ('tt6135388', 6135388),
    ('tt6135388/episodes/?season=2&ref_=ttep', 6135388),
    ('ttinvalid', None),
    ({'invalid': True}, None),
])
def test_external_mapping_does_not_save_rejected_imdb_id(monkeypatch, isolated_series, raw, expected):
    """Save valid mappings without inserting NULL for rejected IMDb metadata."""
    connection = Mock()
    monkeypatch.setattr(series_module.db, 'DBConnection', Mock(return_value=connection))
    isolated_series.externals = {'imdb_id': raw, 'tvdb_id': 457780}

    Series._save_externals_to_db(isolated_series)

    assert expected == isolated_series.externals['imdb_id']
    queries = connection.mass_action.call_args[0][0]
    mapped_ids = [query[1][2] for query in queries]
    assert ([457780] if expected is None else [expected, 457780]) == mapped_ids


@pytest.mark.parametrize('raw, expected', [
    ('tt6135388/episodes/?season=2&ref_=ttep', 'tt6135388'),
    ({'invalid': True}, None),
])
def test_add_queue_completes_with_malformed_tvdb_imdb_metadata(monkeypatch, isolated_series, raw, expected):
    """Continue actual show addition through metadata loading, save and showAdded."""
    # QueueItem.finish renames its worker thread; restore the pytest thread afterward.
    monkeypatch.setattr(threading.current_thread(), 'name', threading.current_thread().name)
    api = TVDBv2(session=MagicMock(), cache=False, episodes=False)
    api.indexer = INDEXER_TVDBV2
    monkeypatch.setattr(api, '_get_show_by_id', Mock(return_value={'series': {
        'id': 457780,
        'seriesname': 'Test Show',
        'imdb_id': raw,
        'status': 'Continuing',
    }}))
    isolated_series.indexer_api = api
    monkeypatch.setattr(Series, 'from_identifier', Mock(return_value=isolated_series))
    monkeypatch.setattr(SeriesIdentifier, 'get_indexer_api', Mock(return_value=api))
    # Keep metadata loading real; isolate later filesystem, database and service work.
    for method in ('configure', 'save_to_db', 'load_episodes_from_indexer', 'write_metadata',
                   'update_metadata', 'populate_cache', 'flush_episodes', 'sync_trakt', 'add_scene_numbering'):
        monkeypatch.setattr(isolated_series, method, Mock())
    monkeypatch.setattr(isolated_series, 'to_json', Mock(return_value={'id': 'tvdb457780'}))
    monkeypatch.setattr(show_queue, 'build_name_cache', Mock())
    messages = Mock()
    monkeypatch.setattr(show_queue.ws, 'Message', messages)
    queue_item = show_queue.QueueItemAdd(
        INDEXER_TVDBV2, 457780, None, default_status=SKIPPED, default_status_after=SKIPPED
    )

    queue_item.run()

    assert queue_item.success
    assert isolated_series in app.showList
    isolated_series.save_to_db.assert_called_once_with()
    isolated_series.load_episodes_from_indexer.assert_called_once_with(tvapi=api)
    assert expected == isolated_series.imdb_id
    assert any(call.args == ('showAdded', {'id': 'tvdb457780'}) for call in messages.call_args_list)
    if expected:
        series_module.Imdb.return_value.get_title.assert_called_once_with(expected)
    else:
        series_module.Imdb.return_value.get_title.assert_not_called()
