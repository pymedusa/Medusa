# coding=utf-8
"""Test nightly file rescans independently of metadata updates."""
from __future__ import unicode_literals

import time

from medusa import app
from medusa.indexers.exceptions import IndexerUnavailable
from medusa.queues.show_queue import QueueItemRefresh, ShowQueue, ShowQueueActions
from medusa.schedulers import show_updater

from mock.mock import Mock

import pytest


@pytest.fixture
def nightly_updater(monkeypatch):
    """Run the real updater and show queue with isolated indexer services."""
    updater = show_updater.ShowUpdater.__new__(show_updater.ShowUpdater)
    updater.amActive = False
    updater.update_cache = Mock()
    updater.update_cache.get_last_indexer_update.return_value = int(time.time()) - 86400
    indexer = Mock()
    indexer.get_last_updated_series.return_value = []
    provider = Mock()
    provider.name = 'Test Indexer'
    provider.api_params = {}
    provider.indexer.return_value = indexer
    monkeypatch.setattr(show_updater, 'indexerApi', Mock(return_value=provider))
    monkeypatch.setattr(show_updater.network_timezones, 'update_network_dict', Mock())
    monkeypatch.setattr(show_updater, 'refresh_exceptions_cache', Mock())
    monkeypatch.setattr(show_updater.ui.ProgressIndicators, 'setIndicator', Mock())
    monkeypatch.setattr(show_updater.ui, 'QueueProgressIndicator', Mock())
    monkeypatch.setattr(show_updater, 'logger', Mock())
    queue = ShowQueue()
    monkeypatch.setattr(app, 'show_queue_scheduler', Mock(action=queue))
    monkeypatch.setattr(app, 'showList', [])
    return updater, indexer, provider, queue


def make_show(identifier, paused=False, ended=False):
    """Provide a show that has recently been checked for metadata changes."""
    show = Mock()
    show.name = 'Example {0}'.format(identifier)
    show.indexer = 1
    show.indexerid = show.series_id = identifier
    show.paused = paused
    show.status = 'Ended' if ended else 'Continuing'
    show.last_update_indexer = int(time.time())
    show.to_json.return_value = {'id': {'slug': 'tvdb{0}'.format(identifier)}}
    return show


def test_rescans_paused_ended_and_unchanged_shows(nightly_updater):
    """Skipping metadata must still schedule the existing file rescan."""
    updater, indexer, _, queue = nightly_updater
    app.showList = [make_show(1, paused=True), make_show(2, ended=True), make_show(3)]

    updater.run()

    assert [item.show for item in queue.queue] == app.showList
    assert all(item.action_id == ShowQueueActions.REFRESH and not item.force for item in queue.queue)
    indexer.get_last_updated_seasons.assert_not_called()
    assert updater.amActive is False


def test_indexer_failure_still_schedules_file_rescans(nightly_updater):
    """An unavailable indexer does not stop local rescan scheduling."""
    updater, _, provider, queue = nightly_updater
    app.showList = [make_show(1), make_show(2)]
    provider.indexer.side_effect = IndexerUnavailable('offline')

    updater.run()

    assert [item.show for item in queue.queue] == app.showList
    assert all(item.action_id == ShowQueueActions.REFRESH for item in queue.queue)


def test_does_not_duplicate_queued_or_running_rescans(nightly_updater):
    """Reuse a rescan that is already scheduled or in progress."""
    updater, _, _, queue = nightly_updater
    app.showList = [make_show(1), make_show(2)]
    queued = queue.refreshShow(app.showList[0])
    queue.current_item = QueueItemRefresh(app.showList[1])

    updater.run()

    assert queue.queue == [queued]


def test_full_update_keeps_its_own_rescan(nightly_updater):
    """A full metadata update already schedules a rescan when it finishes."""
    updater, indexer, _, queue = nightly_updater
    app.showList = [make_show(1)]
    indexer.get_last_updated_series.return_value = [1]
    indexer.get_last_updated_seasons.return_value = {1: []}

    updater.run()

    assert [item.action_id for item in queue.queue] == [ShowQueueActions.UPDATE]


def test_season_updates_keep_their_existing_forced_rescan(nightly_updater):
    """Preserve the existing rescan behavior for partial metadata updates."""
    updater, indexer, _, queue = nightly_updater
    app.showList = [make_show(1)]
    indexer.get_last_updated_series.return_value = [1]
    indexer.get_last_updated_seasons.return_value = {1: [2]}

    updater.run()

    assert [item.action_id for item in queue.queue] == [ShowQueueActions.SEASON_UPDATE, ShowQueueActions.REFRESH]
    assert queue.queue[-1].force is True
