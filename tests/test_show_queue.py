# coding=utf-8
"""Tests for the show queue."""
from __future__ import unicode_literals

from medusa import app
from medusa.indexers.config import INDEXER_IMDB, INDEXER_TVDBV2, INDEXER_TVMAZE
from medusa.indexers.exceptions import IndexerShowNotFound
from medusa.queues import show_queue
from medusa.tv.series import SeriesIdentifier

from mock.mock import MagicMock, Mock


def test_refresh_queue_item_logs_rescan_terminology(monkeypatch):
    """Use the user-facing rescan name while preserving the internal refresh action."""
    series = Mock()
    series.series_id = 477783
    series.name = 'The Rookie: North'
    series.to_json.return_value = {}
    queue_item = show_queue.QueueItemRefresh(series)
    log_info = Mock()

    monkeypatch.setattr(show_queue.log, 'info', log_info)
    monkeypatch.setattr(show_queue.ws, 'Message', Mock())
    monkeypatch.setattr(show_queue.scene_numbering, 'xem_refresh', Mock())
    monkeypatch.setattr(queue_item, 'finish', Mock())

    queue_item.run()

    log_info.assert_called_once_with(
        '{id}: Performing rescan on {show}',
        {'id': 477783, 'show': 'The Rookie: North'}
    )
    assert show_queue.ShowQueueActions.REFRESH == queue_item.action_id


def test_change_indexer_resolves_stale_tvdb_id(monkeypatch):
    old_show = Mock(
        imdb_id='tt30051064',
        externals={'imdb_id': 30051064},
        start_year=2026,
    )
    old_show.name = 'American Hostage'
    stale_show = Mock(indexer=INDEXER_TVDBV2, series_id=443213)
    corrected_show = Mock(indexer=INDEXER_TVDBV2, series_id=462907)
    api = MagicMock()
    api.__getitem__.side_effect = [
        IndexerShowNotFound('Not found'),
        Mock(seriesname='American Hostage'),
    ]
    api.resolve_series_id.return_value = 462907
    stale_show.identifier.get_indexer_api.return_value = api
    corrected_show.identifier.get_indexer_api.return_value = api

    def create_show(identifier):
        return stale_show if identifier.id == 443213 else corrected_show

    monkeypatch.setattr(show_queue.Series, 'from_identifier', create_show)
    queue_item = show_queue.QueueItemChangeIndexer('tvmaze84262', 'tvdb443213')
    queue_item.old_show = old_show

    assert api is queue_item._load_new_show_from_indexer()
    assert 'tvdb462907' == queue_item.new_slug
    api.resolve_series_id.assert_called_once_with(
        'American Hostage', imdb_id='tt30051064', year=2026
    )
    corrected_show.load_from_indexer.assert_called_once_with(tvapi=api)


def test_change_indexer_resolves_stale_id_for_other_indexers(monkeypatch):
    old_show = Mock(imdb_id='tt1234567', externals={}, start_year=2026)
    old_show.name = 'Test Show'
    stale_show = Mock(indexer=INDEXER_TVMAZE, series_id=123)
    corrected_show = Mock(indexer=INDEXER_TVMAZE, series_id=456)
    api = MagicMock()
    api.__getitem__.side_effect = [
        IndexerShowNotFound('Not found'),
        Mock(seriesname='Test Show'),
    ]
    api.resolve_series_id.return_value = 456
    stale_show.identifier.get_indexer_api.return_value = api
    corrected_show.identifier.get_indexer_api.return_value = api

    def create_show(identifier):
        return stale_show if identifier.id == 123 else corrected_show

    monkeypatch.setattr(show_queue.Series, 'from_identifier', create_show)
    queue_item = show_queue.QueueItemChangeIndexer('tvdb789', 'tvmaze123')
    queue_item.old_show = old_show

    assert api is queue_item._load_new_show_from_indexer()
    assert 'tvmaze456' == queue_item.new_slug
    corrected_show.load_from_indexer.assert_called_once_with(tvapi=api)


def test_change_indexer_does_not_verify_stale_imdb_id_against_itself(monkeypatch):
    old_show = Mock(imdb_id='tt0000123', externals={}, start_year=2026)
    old_show.name = 'Test Show'
    stale_show = Mock(indexer=INDEXER_IMDB, series_id=123)
    corrected_show = Mock(indexer=INDEXER_IMDB, series_id=456)
    api = MagicMock()
    api.__getitem__.side_effect = [
        IndexerShowNotFound('Not found'),
        Mock(seriesname='Test Show'),
    ]
    api.resolve_series_id.return_value = 456
    stale_show.identifier.get_indexer_api.return_value = api
    corrected_show.identifier.get_indexer_api.return_value = api

    monkeypatch.setattr(
        show_queue.Series,
        'from_identifier',
        lambda identifier: stale_show if identifier.id == 123 else corrected_show,
    )
    queue_item = show_queue.QueueItemChangeIndexer('tvdb789', 'imdb123')
    queue_item.old_show = old_show

    assert api is queue_item._load_new_show_from_indexer()
    api.resolve_series_id.assert_called_once_with('Test Show', imdb_id=None, year=2026)


def test_change_indexer_does_not_search_when_tvdb_id_loads(monkeypatch):
    old_show = Mock(imdb_id='tt30051064', externals={}, start_year=2026)
    old_show.name = 'American Hostage'
    new_show = Mock(indexer=INDEXER_TVDBV2, series_id=462907)
    api = MagicMock()
    api.__getitem__.return_value = Mock(seriesname='American Hostage')
    new_show.identifier.get_indexer_api.return_value = api

    monkeypatch.setattr(show_queue.Series, 'from_identifier', Mock(return_value=new_show))
    queue_item = show_queue.QueueItemChangeIndexer('tvmaze84262', 'tvdb462907')
    queue_item.old_show = old_show

    assert api is queue_item._load_new_show_from_indexer()
    api.resolve_series_id.assert_not_called()


def test_change_indexer_keeps_old_show_when_tvdb_id_cannot_be_resolved(monkeypatch):
    old_show = Mock(
        series_id=84262,
        imdb_id='tt30051064',
        externals={'imdb_id': 30051064},
        start_year=2026,
        qualities_preferred=[],
        qualities_allowed=[],
        season_folders=True,
        lang='en',
        subtitles=False,
        anime=False,
        scene=False,
        paused=False,
        release_groups=None,
        default_ep_status=5,
        show_lists='series',
        _location='/shows/American Hostage',
    )
    old_show.name = 'American Hostage'
    old_show.identifier = SeriesIdentifier.from_id(INDEXER_TVMAZE, 84262)
    old_show.to_json.return_value = {}
    stale_show = Mock(indexer=INDEXER_TVDBV2, series_id=443213)
    api = MagicMock()
    api.__getitem__.side_effect = IndexerShowNotFound('Not found')
    api.resolve_series_id.return_value = None
    stale_show.identifier.get_indexer_api.return_value = api

    monkeypatch.setattr(app, 'showList', [old_show])
    monkeypatch.setattr(app, 'USE_TRAKT', False)
    monkeypatch.setattr(show_queue.Series, 'find_by_identifier', Mock(return_value=old_show))
    monkeypatch.setattr(show_queue.Series, 'from_identifier', Mock(return_value=stale_show))
    monkeypatch.setattr(show_queue.ws, 'Message', Mock(return_value=Mock()))

    queue_item = show_queue.QueueItemChangeIndexer('tvmaze84262', 'tvdb443213')
    monkeypatch.setattr(queue_item, 'finish', Mock())
    queue_item.run()

    assert queue_item.success is False
    old_show.delete_show.assert_not_called()
    assert app.showList == [old_show]
