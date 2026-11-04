# coding=utf-8
"""Tests for the legacy websocket history item serializer."""
from __future__ import unicode_literals

import pytest

from medusa.common import DOWNLOADED
from medusa.history import create_history_item
from medusa.schedulers.download_handler import ClientStatusEnum


def _history_row(client_status):
    """Return a fresh history row that does not require provider or show lookups."""
    return {
        'action': DOWNLOADED,
        'client_status': client_status,
        'date': '2026-08-23 00:00:00',
        'episode': 1,
        'indexer_id': 0,
        'info_hash': None,
        'manually_searched': 0,
        'part_of_batch': 0,
        'proper_tags': '',
        'provider': 'test-provider',
        'provider_type': 'torrent',
        'quality': 0,
        'resource': '/tmp/episode.mkv',
        'season': 1,
        'showid': 0,
        'size': 0,
    }


@pytest.mark.parametrize('client_status, expected', [
    (None, None),
    (ClientStatusEnum.SNATCHED.value, {'status': [0], 'string': ['Snatched']}),
    (384, {'status': [128, 256], 'string': ['Completed', 'Postprocessed']}),
    (1536, {'status': [512, 1024], 'string': ['SeededAction', 'Removed']}),
])
def test_create_history_item_client_status(client_status, expected):
    """Serialize websocket client statuses without database access."""
    history_item = create_history_item(_history_row(client_status))

    assert history_item['clientStatus'] == expected
