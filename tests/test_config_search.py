# coding=utf-8
"""Regression tests for ConfigSearch.saveSearch() backlog batch settings."""
from __future__ import unicode_literals

from medusa import app, config, ui
from medusa.server.web.config.search import ConfigSearch

import pytest


@pytest.fixture
def save_search(monkeypatch):
    """Call ``ConfigSearch.saveSearch`` with side effects stubbed out."""
    handler = object.__new__(ConfigSearch)
    saved = []

    class FakeInstance(object):
        def save_config(self):
            saved.append((app.BACKLOG_BATCH_SIZE, app.BACKLOG_BATCH_REFILL_THRESHOLD))

    monkeypatch.setattr(app, 'instance', FakeInstance())
    monkeypatch.setattr(app, 'CONFIG_FILE', 'config.ini')
    monkeypatch.setattr(handler, 'redirect', lambda *args, **kwargs: 'ok')
    monkeypatch.setattr(ui.notifications, 'message', lambda *args, **kwargs: None)
    monkeypatch.setattr(ui.notifications, 'error', lambda *args, **kwargs: None)
    # Frequency changers may schedule work; keep them as no-ops for this unit test.
    for name in (
        'change_DAILYSEARCH_FREQUENCY',
        'change_DOWNLOAD_HANDLER_FREQUENCY',
        'change_BACKLOG_FREQUENCY',
        'change_CHECK_PROPERS_INTERVAL',
    ):
        monkeypatch.setattr(config, name, lambda *args, **kwargs: None)
    # Pre-existing helper referenced by saveSearch(); stub it so the unit test
    # can reach the backlog-batch logic without depending on that path.
    monkeypatch.setattr(config, 'change_remove_from_client',
                        lambda *args, **kwargs: None, raising=False)

    def call(**kwargs):
        defaults = {
            'sab_apikey': '',
            'sab_host': '',
            'nzbget_host': '',
            'torrent_host': '',
            'torrent_path': '',
            'torrent_seed_location': '',
            'torrent_method': 'blackhole',
        }
        defaults.update(kwargs)
        result = ConfigSearch.saveSearch(handler, **defaults)
        assert result == 'ok'
        return saved

    return call


@pytest.mark.parametrize('p', [
    {  # Case 1: batching disabled, threshold field omitted → keep 7
        'initial': (0, 7),
        'kwargs': {'backlog_batch_size': 0},
        'expected': (0, 7),
    },
    {  # Case 2: unrelated search setting while threshold is hidden
        'initial': (0, 9),
        'kwargs': {'backlog_batch_size': 0, 'backlog_days': 15},
        'expected': (0, 9),
        'extra': {'BACKLOG_DAYS': 15},
    },
    {  # Case 3: enabled batching, valid threshold omitted → keep 3
        'initial': (5, 3),
        'kwargs': {'backlog_batch_size': 5},
        'expected': (5, 3),
    },
    {  # Case 4: size lowered, threshold omitted → clamp preserved value
        'initial': (10, 8),
        'kwargs': {'backlog_batch_size': 3},
        'expected': (3, 2),
    },
    {  # Case 5: size becomes 1, high threshold omitted → 0
        'initial': (10, 8),
        'kwargs': {'backlog_batch_size': 1},
        'expected': (1, 0),
    },
    {  # Case 6: explicit threshold still accepted
        'initial': (5, 2),
        'kwargs': {'backlog_batch_size': 5, 'backlog_batch_refill_threshold': 4},
        'expected': (5, 4),
    },
    {  # Case 7: explicit invalid threshold still normalized
        'initial': (5, 2),
        'kwargs': {'backlog_batch_size': 5, 'backlog_batch_refill_threshold': 99},
        'expected': (5, 4),
    },
])
def test_save_search_preserves_or_normalizes_backlog_batch_threshold(monkeypatch, save_search, p):
    """Omitted threshold preserves current value; explicit values still normalize."""
    monkeypatch.setattr(app, 'BACKLOG_BATCH_SIZE', p['initial'][0])
    monkeypatch.setattr(app, 'BACKLOG_BATCH_REFILL_THRESHOLD', p['initial'][1])

    saved = save_search(**p['kwargs'])

    assert (app.BACKLOG_BATCH_SIZE, app.BACKLOG_BATCH_REFILL_THRESHOLD) == p['expected']
    assert saved == [p['expected']]
    for attr, value in p.get('extra', {}).items():
        assert getattr(app, attr) == value
