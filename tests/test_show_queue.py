# coding=utf-8
"""Tests for the show queue."""
from __future__ import unicode_literals

from medusa.queues import show_queue

from mock.mock import Mock


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
