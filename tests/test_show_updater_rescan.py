# coding=utf-8
"""Test nightly file rescans independently of metadata updates."""
from __future__ import unicode_literals

import time

from medusa import app
from medusa.indexers.exceptions import IndexerUnavailable
from medusa.queues.generic_queue import QueuePriorities
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
    """Paused, ended, and unchanged shows only need local file checks."""
    updater, indexer, _, queue = nightly_updater
    app.showList = [make_show(1, paused=True), make_show(2, ended=True), make_show(3)]

    updater.run()

    expected = [show for show in app.showList if show_updater.local_file_check_due(show, time.time())]
    assert [item.show for item in queue.queue] == expected
    assert all(item.action_id == ShowQueueActions.REFRESH and not item.force for item in queue.queue)
    assert all(item.local_only and item.priority == QueuePriorities.LOW for item in queue.queue)
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


@pytest.mark.parametrize('paused, ended', [(True, False), (False, True), (True, True)])
def test_paused_and_ended_shows_never_request_nightly_metadata(nightly_updater, paused, ended):
    """A stale metadata timestamp must not reactivate an inactive show."""
    updater, indexer, provider, queue = nightly_updater
    show = make_show(1, paused=paused, ended=ended)
    show.last_update_indexer = 0
    app.showList = [show]
    indexer.get_last_updated_series.return_value = [1]

    updater.run()

    provider.indexer.assert_not_called()
    indexer.get_last_updated_seasons.assert_not_called()
    due_today = show_updater.local_file_check_due(show, time.time())
    assert len(queue.queue) == int(due_today)
    assert all(item.local_only for item in queue.queue)


@pytest.mark.parametrize('running', [False, True])
def test_previous_file_check_pass_finishes_before_another_starts(nightly_updater, running):
    """Finished shows are not requeued while an older automatic pass remains."""
    updater, _, _, queue = nightly_updater
    app.showList = [make_show(1, paused=True), make_show(2, paused=True)]
    pending = QueueItemRefresh(app.showList[1], local_only=True)
    if running:
        queue.current_item = pending
    else:
        queue.add_item(pending)

    updater.run()

    assert queue.queue == ([] if running else [pending])


def test_manual_rescan_upgrades_a_queued_local_file_check():
    """A pending automatic check cannot swallow a requested full refresh."""
    queue = ShowQueue()
    show = make_show(1)
    pending = queue.refreshShow(show, local_only=True)

    manual = queue.refreshShow(show, True)

    assert queue.queue == [pending]
    assert manual is pending
    assert manual.local_only is False
    assert manual.force is True
    assert manual.priority == QueuePriorities.HIGH
    assert manual.to_json['priority'] == QueuePriorities.HIGH
    assert queue.hasPendingFileChecks() is False


def test_manual_rescan_can_follow_a_running_local_file_check():
    """A lightweight scan in progress must not block a manual full refresh."""
    queue = ShowQueue()
    show = make_show(1)
    queue.current_item = QueueItemRefresh(show, local_only=True)

    manual = queue.refreshShow(show)

    assert queue.queue == [manual]
    assert manual.local_only is False
    assert manual.priority == QueuePriorities.HIGH


def test_automatic_check_reuses_a_pending_manual_rescan():
    """Nightly scheduling must not downgrade higher-priority manual work."""
    queue = ShowQueue()
    show = make_show(1)
    manual = queue.refreshShow(show, True)

    result = queue.refreshShow(show, local_only=True)

    assert result is None
    assert queue.queue == [manual]
    assert manual.local_only is False
    assert manual.force is True


@pytest.mark.parametrize('complete', [True, False])
def test_local_file_check_has_no_full_refresh_side_effects(monkeypatch, complete):
    """The automatic path must never invoke metadata, caches, or XEM refreshes."""
    show = make_show(1, paused=True, ended=True)
    show.reconcile_local_files.return_value = complete
    item = QueueItemRefresh(show, local_only=True)
    monkeypatch.setattr(item, 'finish', Mock())
    monkeypatch.setattr('medusa.queues.show_queue.ws.Message', Mock())
    xem_refresh = Mock()
    monkeypatch.setattr('medusa.queues.show_queue.scene_numbering.xem_refresh', xem_refresh)

    item.run()

    assert item.success is complete
    show.reconcile_local_files.assert_called_once_with()
    show.refresh_dir.assert_not_called()
    show.update_metadata.assert_not_called()
    show.write_metadata.assert_not_called()
    show.populate_cache.assert_not_called()
    xem_refresh.assert_not_called()
    item.finish.assert_called_once_with()


def test_manual_full_refresh_retains_metadata_and_xem(monkeypatch):
    """An explicitly forced rescan keeps its existing behavior."""
    show = make_show(1, paused=True, ended=True)
    item = QueueItemRefresh(show, force=True)
    monkeypatch.setattr(item, 'finish', Mock())
    monkeypatch.setattr('medusa.queues.show_queue.ws.Message', Mock())
    xem_refresh = Mock()
    monkeypatch.setattr('medusa.queues.show_queue.scene_numbering.xem_refresh', xem_refresh)

    item.run()

    assert item.success is True
    show.reconcile_local_files.assert_not_called()
    show.refresh_dir.assert_called_once_with()
    show.update_metadata.assert_called_once_with()
    show.write_metadata.assert_called_once_with()
    show.populate_cache.assert_called_once_with()
    xem_refresh.assert_called_once_with(show, force=True)


@pytest.mark.parametrize('running', [False, True])
def test_season_update_keeps_full_rescan_during_an_older_file_check_pass(nightly_updater, running):
    """An earlier automatic check must not replace the season update's full rescan."""
    updater, indexer, _, queue = nightly_updater
    show = make_show(1)
    app.showList = [show]
    indexer.get_last_updated_series.return_value = [1]
    indexer.get_last_updated_seasons.return_value = {1: [2]}
    pending = QueueItemRefresh(show, local_only=True)
    if running:
        queue.current_item = pending
    else:
        queue.add_item(pending)

    updater.run()

    rescans = [item for item in queue.queue if item.action_id == ShowQueueActions.REFRESH]
    assert len(rescans) == 1
    assert rescans[0].local_only is False
    assert rescans[0].force is True
    assert rescans[0].priority == QueuePriorities.HIGH


def test_repeated_manual_requests_reuse_pending_full_rescan():
    """Repeated requests retain a forced full rescan without duplicate work."""
    queue = ShowQueue()
    show = make_show(1)
    pending = queue.refreshShow(show, True)

    manual = queue.refreshShow(show)

    assert queue.queue == [pending]
    assert manual is pending
    assert manual.force is True


def test_weekly_batch_after_downtime_does_not_replay_missed_days(nightly_updater, monkeypatch):
    """Restarting schedules only today's bucket, without replaying missed weekdays."""
    from datetime import datetime, timedelta

    updater, indexer, provider, queue = nightly_updater
    shows = [make_show(identifier, ended=True) for identifier in range(1, 141)]
    app.showList = shows
    monday = datetime(2026, 11, 16, 3)
    clock = Mock(wraps=time)
    monkeypatch.setattr(show_updater, 'time', clock)
    clock.time.return_value = monday.timestamp()

    updater.run()

    monday_shows = {item.show for item in queue.queue}
    expected = {show for show in shows if show_updater.local_file_check_due(show, clock.time())}
    assert monday_shows == expected
    assert 0 < len(monday_shows) < len(shows)

    # Pending work is in memory; a new process starts with a new queue.
    restarted_queue = ShowQueue()
    app.show_queue_scheduler.action = restarted_queue
    clock.time.return_value = (monday + timedelta(days=4)).timestamp()

    updater.run()

    friday_shows = {item.show for item in restarted_queue.queue}
    expected = {show for show in shows if show_updater.local_file_check_due(show, clock.time())}
    assert friday_shows == expected
    assert monday_shows.isdisjoint(friday_shows)
    assert 0 < len(friday_shows) < len(shows)
    provider.indexer.assert_not_called()
    indexer.get_last_updated_seasons.assert_not_called()

    updater.run()

    assert {item.show for item in restarted_queue.queue} == friday_shows
    assert len(restarted_queue.queue) == len(friday_shows)


def test_nightly_weekly_batch_starts_without_daytime_delay(nightly_updater, monkeypatch):
    """The due weekday's jobs can start as soon as the nightly updater queues them."""
    from datetime import datetime

    updater, _, _, queue = nightly_updater
    app.showList = [make_show(identifier, ended=True) for identifier in range(1, 141)]
    clock = Mock(wraps=time)
    clock.time.return_value = datetime(2026, 11, 16, 3).timestamp()
    monkeypatch.setattr(show_updater, 'time', clock)

    updater.run()

    batch = list(queue.queue)
    assert batch
    for item in batch:
        monkeypatch.setattr(item, 'start', Mock())

    queue.run()

    assert queue.current_item in batch
    queue.current_item.start.assert_called_once_with()
    assert queue.current_item.local_only is True
    assert queue.current_item.priority == QueuePriorities.LOW
