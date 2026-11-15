# coding=utf-8
"""Verify stable weekly batches anchored to the nightly updater."""
from __future__ import unicode_literals

from collections import Counter
from datetime import datetime, timedelta
from types import SimpleNamespace

from medusa.queues.generic_queue import GenericQueue, QueueItem, QueuePriorities
from medusa.schedulers.show_updater import local_file_check_due

from mock.mock import Mock

import pytest


@pytest.mark.parametrize('paused, ended', [(True, False), (False, True), (True, True)])
def test_inactive_shows_have_one_stable_weekly_slot(paused, ended):
    """Every inactive show keeps one weekday across restarts and weekly runs."""
    monday = datetime(2026, 11, 16, 3)
    assignments = Counter()
    for identifier in range(1, 1401):
        show = SimpleNamespace(indexer=1, series_id=identifier, paused=paused,
                               status='Ended' if ended else 'Continuing')
        slots = []
        for day in range(7):
            now = (monday + timedelta(days=day)).timestamp()
            due = local_file_check_due(show, now)
            assert local_file_check_due(show, now + 7 * 86400) is due
            if due:
                slots.append(day)
        assert len(slots) == 1
        assignments[slots[0]] += 1

    assert set(assignments) == set(range(7))
    assert max(assignments.values()) < 280
    assert min(assignments.values()) > 120


def test_active_shows_remain_due_every_day():
    """The weekly schedule applies only to paused or ended shows."""
    show = SimpleNamespace(indexer=1, series_id=12, paused=False, status='Continuing')
    monday = datetime(2026, 11, 16, 3)
    for day in range(7):
        now = (monday + timedelta(days=day)).timestamp()
        assert local_file_check_due(show, now) is True


def make_job(name, priority, monkeypatch):
    """Use real queue items without starting worker threads."""
    item = QueueItem(name)
    item.priority = priority
    monkeypatch.setattr(item, 'start', Mock())
    return item


def test_queue_pause_is_respected_for_ready_checks(monkeypatch):
    """The nightly batch must respect an explicitly paused queue."""
    queue = GenericQueue()
    ready = make_job('ready', QueuePriorities.LOW, monkeypatch)
    queue.add_item(ready)
    queue.pause()

    queue.run()

    assert queue.current_item is None
    ready.start.assert_not_called()

    queue.unpause()
    queue.run()

    assert queue.current_item is ready
    ready.start.assert_called_once_with()


def test_eligible_jobs_keep_priority_and_fifo_order(monkeypatch):
    """Existing priority and insertion ordering still select ordinary ready jobs."""
    queue = GenericQueue()
    normal = make_job('normal', QueuePriorities.NORMAL, monkeypatch)
    first = make_job('first', QueuePriorities.HIGH, monkeypatch)
    second = make_job('second', QueuePriorities.HIGH, monkeypatch)
    queue.add_item(normal)
    queue.add_item(first)
    queue.add_item(second)
    first.added -= timedelta(seconds=1)

    queue.run()

    assert queue.current_item is first
    assert queue.queue == [second, normal]
