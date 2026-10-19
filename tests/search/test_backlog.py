# coding=utf-8
"""Tests for the throttled backlog batch scheduler."""
from __future__ import unicode_literals

import datetime
import threading

from medusa import app
from medusa.search import backlog
from medusa.search.backlog import (
    BacklogSearcher,
    effective_refill_threshold,
    iter_wanted_segments,
    next_batch,
    parse_cursor,
    segment_key,
    serialize_cursor,
)
from medusa.search.queue import BacklogQueueItem, DailySearchQueueItem, SearchQueue

import pytest

EPOCH = datetime.date.fromordinal(1)


class FakeSeries(object):
    """Minimal stand-in for a Series object as used by the backlog planner."""

    def __init__(self, indexer, series_id, seasons, paused=False):
        self.indexer = indexer
        self.series_id = series_id
        self.indexerid = series_id
        self.name = 'Show {0}-{1}'.format(indexer, series_id)
        self.paused = paused
        self.seasons = seasons
        self.wanted_calls = 0

    def get_wanted_segments(self, from_date=None):
        self.wanted_calls += 1
        return {season: ['ep-{0}-s{1}'.format(self.series_id, season)] for season in self.seasons}

    def to_json(self):
        return {'id': self.series_id}


class FakeEpisode(object):
    def to_json(self):
        return {}


class FakeQueueItem(object):
    """Replacement for BacklogQueueItem that avoids touching real Series/Episode objects."""

    def __init__(self, show, segment, backlog_cursor_key=None):
        self.show = show
        self.segment = segment
        self.backlog_cursor_key = backlog_cursor_key


class FakeSearchQueue(object):
    """Search queue stub that executes one pending item each time the searcher waits.

    Executing an item mirrors ``BacklogQueueItem.run()``: the completed cursor is
    recorded first, then the item leaves the pending set, then the searcher is woken.
    """

    def __init__(self):
        self.items = []
        self.pending = []
        self.executed = []
        self.max_pending = 0
        self.waits = 0
        self.searcher = None

    def add_item(self, item):
        self.items.append(item)
        self.pending.append(item)
        self.max_pending = max(self.max_pending, len(self.pending))

    def backlog_pending(self):
        return len(self.pending)

    def run_one(self):
        item = self.pending.pop(0)
        self.executed.append(item)
        self.searcher.record_completed(item.backlog_cursor_key)
        self.searcher.notify_capacity()

    def wait(self, timeout=None):
        """Stand-in for ``Event.wait``: the provider finishes exactly one search."""
        self.waits += 1
        if self.pending:
            self.run_one()


class FakeScheduler(object):
    def __init__(self, action, stop=None):
        self.action = action
        self.stop = stop or threading.Event()


class StopAfterExecutions(object):
    """Stop event that trips once the fake queue executed ``count`` items."""

    def __init__(self, queue, count):
        self.queue = queue
        self.count = count

    def is_set(self):
        return len(self.queue.executed) >= self.count


class CursorStore(object):
    """In-memory replacement for the ``info.backlog_cursor`` column."""

    def __init__(self, value=None):
        self.value = value
        self.writes = []
        self.reads = 0
        self.pending_at_write = []
        self.queue = None

    def get(self):
        self.reads += 1
        return self.value

    def set(self, key):
        self.value = key
        self.writes.append(key)
        if self.queue is not None:
            self.pending_at_write.append(self.queue.backlog_pending())


@pytest.fixture
def library():
    # Deliberately unsorted to make sure the planner enforces its own order.
    return [
        FakeSeries(1, 30, seasons=[1]),
        FakeSeries(1, 10, seasons=[2, 1]),
        FakeSeries(1, 20, seasons=[], paused=False),
        FakeSeries(3, 5, seasons=[4]),
        FakeSeries(1, 15, seasons=[1], paused=True),
    ]


ALL_KEYS = [(1, 10, 1), (1, 10, 2), (1, 30, 1), (3, 5, 4)]


@pytest.fixture
def searcher(monkeypatch):
    monkeypatch.setattr(BacklogSearcher, '_get_last_backlog', lambda self: 1)
    # Bypass the BACKLOG_FREQUENCY property setter, which reconfigures the scheduler thread.
    monkeypatch.setattr(app, '_BACKLOG_FREQUENCY', 720)
    return BacklogSearcher()


@pytest.fixture
def batch_env(monkeypatch, searcher):
    """Wire a searcher to a fake queue and cursor store for batch mode tests."""
    def setup(batch_size, threshold, cursor=None, stop=None):
        queue = FakeSearchQueue()
        queue.searcher = searcher
        store = CursorStore(cursor)
        store.queue = queue

        monkeypatch.setattr(app, 'search_queue_scheduler', FakeScheduler(queue))
        monkeypatch.setattr(app, 'backlog_search_scheduler', FakeScheduler(searcher, stop=stop))
        monkeypatch.setattr(app, 'forced_search_queue_scheduler',
                            FakeScheduler(type('Forced', (object,), {'is_forced_search_in_progress': lambda self: False})()))
        monkeypatch.setattr(app, 'BACKLOG_BATCH_SIZE', batch_size)
        monkeypatch.setattr(app, 'BACKLOG_BATCH_REFILL_THRESHOLD', threshold)
        monkeypatch.setattr(backlog, 'BacklogQueueItem', FakeQueueItem)
        monkeypatch.setattr(searcher, '_get_cursor', store.get)
        monkeypatch.setattr(searcher, '_set_cursor', store.set)
        monkeypatch.setattr(searcher._capacity, 'wait', queue.wait)
        return queue, store

    return setup


def keys_of(items):
    return [item.backlog_cursor_key for item in items]


# --- cursor serialization ---------------------------------------------------

@pytest.mark.parametrize('key,expected', [
    ((1, 10, 2), '1:10:2'),
    (None, ''),
    ((), ''),
])
def test_serialize_cursor(key, expected):
    assert serialize_cursor(key) == expected


@pytest.mark.parametrize('value,expected', [
    ('1:10:2', (1, 10, 2)),
    ('', None),
    (None, None),
    ('1:10', None),
    ('a:b:c', None),
])
def test_parse_cursor(value, expected):
    assert parse_cursor(value) == expected


def test_segment_key_coerces_to_int():
    assert segment_key(FakeSeries('1', '10', []), '3') == (1, 10, 3)


# --- planner ordering -------------------------------------------------------

def test_iter_wanted_segments_is_deterministic_and_skips_paused(library):
    keys = [key for _, _, _, key in iter_wanted_segments(library, EPOCH)]

    assert keys == ALL_KEYS


def test_iter_wanted_segments_resumes_after_cursor_without_querying_earlier_shows(library):
    keys = [key for _, _, _, key in iter_wanted_segments(library, EPOCH, cursor=(1, 20, 0))]

    assert keys == [(1, 30, 1), (3, 5, 4)]
    # Shows sorting strictly before the cursor must be skipped without a DB query.
    show_10 = next(series for series in library if series.series_id == 10)
    assert show_10.wanted_calls == 0
    # The show holding the cursor still has to be queried for later seasons.
    show_20 = next(series for series in library if series.series_id == 20)
    assert show_20.wanted_calls == 1


def test_iter_wanted_segments_resumes_mid_show(library):
    keys = [key for _, _, _, key in iter_wanted_segments(library, EPOCH, cursor=(1, 10, 1))]

    assert keys == [(1, 10, 2), (1, 30, 1), (3, 5, 4)]


def test_next_batch_limits_size_and_returns_empty_at_end(library):
    first = next_batch(library, EPOCH, None, 3)
    assert [key for _, _, _, key in first] == [(1, 10, 1), (1, 10, 2), (1, 30, 1)]

    second = next_batch(library, EPOCH, first[-1][3], 3)
    assert [key for _, _, _, key in second] == [(3, 5, 4)]

    assert next_batch(library, EPOCH, second[-1][3], 3) == []


# --- refill threshold -------------------------------------------------------

@pytest.mark.parametrize('batch_size,threshold,expected', [
    (3, 2, 2),
    (3, 3, 2),
    (3, 10, 2),
    (3, -5, 0),
    (1, 0, 0),
    (1, 5, 0),
    (0, 7, 7),   # batching disabled: value is irrelevant but kept sane
    (0, -1, 0),
])
def test_effective_refill_threshold(batch_size, threshold, expected):
    assert effective_refill_threshold(batch_size, threshold) == expected


def test_threshold_above_batch_size_is_clamped_and_still_throttles(batch_env, library):
    queue, store = batch_env(batch_size=3, threshold=10)

    assert searcher_run(library) is True
    # Effective threshold is 2: never more than batch_size + 2 in flight, and the
    # planner had to wait at least once instead of queueing everything up front.
    assert queue.max_pending <= 3 + 2
    assert queue.waits >= 1
    assert keys_of(queue.executed) == ALL_KEYS


def test_batch_size_one_forces_strict_serialization(batch_env, library):
    queue, store = batch_env(batch_size=1, threshold=5)

    assert searcher_run(library) is True
    assert queue.max_pending == 1
    assert keys_of(queue.executed) == ALL_KEYS


def searcher_run(library, resume=True):
    return app.backlog_search_scheduler.action._search_in_batches(library, EPOCH, resume=resume)


# --- at-least-once cursor semantics ------------------------------------------

def test_queued_but_not_executed_segments_do_not_advance_persisted_cursor(batch_env, library, searcher):
    queue, store = batch_env(batch_size=3, threshold=0)

    # The provider never completes anything; shutdown hits after the first wait,
    # so the first batch is queued but nothing ran.
    def wait_without_progress(timeout=None):
        queue.waits += 1
    searcher._capacity.wait = wait_without_progress

    class StopAfterFirstWait(object):
        def is_set(self):
            return queue.waits >= 1
    app.backlog_search_scheduler.stop = StopAfterFirstWait()

    assert searcher_run(library) is False
    assert keys_of(queue.items) == [(1, 10, 1), (1, 10, 2), (1, 30, 1)]
    assert store.writes == []
    assert store.value is None


def test_completing_one_item_advances_cursor_to_exactly_that_segment(batch_env, library, searcher):
    queue, store = batch_env(batch_size=3, threshold=0)
    app.backlog_search_scheduler.stop = StopAfterExecutions(queue, 1)

    assert searcher_run(library) is False
    assert keys_of(queue.executed) == [(1, 10, 1)]
    assert store.writes == [(1, 10, 1)]
    assert store.value == (1, 10, 1)


def test_shutdown_with_later_items_queued_resumes_from_last_completed(batch_env, library, searcher):
    queue, store = batch_env(batch_size=3, threshold=0)
    app.backlog_search_scheduler.stop = StopAfterExecutions(queue, 1)

    assert searcher_run(library) is False
    # A ran, B and C were queued but lost with the process.
    assert keys_of(queue.items) == [(1, 10, 1), (1, 10, 2), (1, 30, 1)]
    assert store.value == (1, 10, 1)

    # "Restart": fresh queue, same persisted cursor.
    queue2, store2 = batch_env(batch_size=3, threshold=0, cursor=store.value)
    assert searcher_run(library) is True
    assert keys_of(queue2.items) == [(1, 10, 2), (1, 30, 1), (3, 5, 4)]
    assert store2.value is None


def test_record_completed_is_monotonic(batch_env, searcher):
    queue, store = batch_env(batch_size=3, threshold=0, cursor=(1, 10, 2))
    searcher._completed_cursor = (1, 10, 2)

    searcher.record_completed((1, 10, 1))
    assert store.writes == []

    searcher.record_completed((1, 30, 1))
    assert store.writes == [(1, 30, 1)]

    searcher.record_completed(None)
    assert store.writes == [(1, 30, 1)]


# --- final drain -------------------------------------------------------------

def test_end_of_planner_with_pending_items_does_not_clear_cursor(batch_env, library, searcher):
    queue, store = batch_env(batch_size=3, threshold=2)
    # Planner: queue 3, wait (1 runs), queue the 4th, planner ends with 3 pending.
    # Stop during the final drain, after the second execution.
    app.backlog_search_scheduler.stop = StopAfterExecutions(queue, 2)

    assert searcher_run(library) is False
    assert keys_of(queue.items) == ALL_KEYS
    assert keys_of(queue.executed) == [(1, 10, 1), (1, 10, 2)]
    assert None not in store.writes
    assert store.value == (1, 10, 2)


def test_cursor_is_cleared_only_after_pending_reaches_zero(batch_env, library):
    queue, store = batch_env(batch_size=3, threshold=2)

    assert searcher_run(library) is True
    assert keys_of(queue.executed) == ALL_KEYS
    assert store.writes == ALL_KEYS + [None]
    # The clear happened with nothing pending; every key was written after it ran.
    assert store.pending_at_write[-1] == 0
    assert store.value is None


def test_interrupted_final_drain_does_not_update_last_backlog(batch_env, library, searcher, monkeypatch):
    queue, store = batch_env(batch_size=3, threshold=2)
    app.backlog_search_scheduler.stop = StopAfterExecutions(queue, 2)
    last_backlog = []
    monkeypatch.setattr(app, 'showList', library)
    monkeypatch.setattr(searcher, '_set_last_backlog', last_backlog.append)

    searcher.search_backlog()

    assert last_backlog == []
    assert store.value == (1, 10, 2)
    assert searcher.amActive is False


def test_completed_pass_updates_last_backlog(batch_env, library, searcher, monkeypatch):
    queue, store = batch_env(batch_size=2, threshold=1)
    last_backlog = []
    monkeypatch.setattr(app, 'showList', library)
    monkeypatch.setattr(searcher, '_set_last_backlog', last_backlog.append)

    searcher.search_backlog()

    assert keys_of(queue.executed) == ALL_KEYS
    assert last_backlog == [datetime.date.today().toordinal()]
    assert store.value is None


class SearchBoom(Exception):
    """Marker exception raised by a failing search path."""


@pytest.mark.parametrize('batch_size,failing_method', [
    (0, '_search_all'),
    (2, '_search_in_batches'),
])
def test_search_backlog_propagates_search_errors_and_resets_state(batch_env, library, searcher, monkeypatch,
                                                                  batch_size, failing_method):
    queue, store = batch_env(batch_size=batch_size, threshold=1)
    last_backlog = []
    resets = []
    original_reset = searcher._reset_pi

    def reset_pi():
        resets.append(True)
        original_reset()

    def boom(*args, **kwargs):
        raise SearchBoom('provider exploded')

    monkeypatch.setattr(app, 'showList', library)
    monkeypatch.setattr(searcher, '_set_last_backlog', last_backlog.append)
    monkeypatch.setattr(searcher, '_reset_pi', reset_pi)
    monkeypatch.setattr(searcher, failing_method, boom)

    # The original exception must propagate unchanged (no UnboundLocalError, nothing swallowed).
    with pytest.raises(SearchBoom, match='provider exploded'):
        searcher.search_backlog()

    assert searcher.amActive is False
    assert resets == [True]
    assert last_backlog == []
    assert store.writes == []


# --- limited / targeted / legacy paths --------------------------------------

def test_limited_forced_backlog_never_touches_persistent_cursor(batch_env, library, searcher, monkeypatch):
    queue, store = batch_env(batch_size=2, threshold=1, cursor=(1, 10, 2))
    monkeypatch.setattr(app, 'showList', library)
    monkeypatch.setattr(app, 'BACKLOG_DAYS', 7)
    monkeypatch.setattr(searcher, '_set_last_backlog', lambda when: pytest.fail('limited pass must not record last_backlog'))
    searcher.forced = True

    searcher.search_backlog()

    # Batched, starting from the beginning, and without any cursor key on the items.
    assert len(queue.executed) == 4
    assert keys_of(queue.items) == [None, None, None, None]
    assert store.reads == 0
    assert store.writes == []
    assert store.value == (1, 10, 2)


def test_targeted_backlog_is_immediate_and_does_not_touch_cursor(batch_env, library, searcher, monkeypatch):
    queue, store = batch_env(batch_size=2, threshold=1, cursor=(1, 10, 2))
    monkeypatch.setattr(searcher, '_set_last_backlog', lambda when: pytest.fail('targeted run is not a full pass'))
    monkeypatch.setattr(searcher, '_search_in_batches',
                        lambda *args, **kwargs: pytest.fail('targeted backlog must stay immediate'))

    searcher.search_backlog(which_shows=[library[0]])

    assert [item.show.series_id for item in queue.items] == [30]
    assert keys_of(queue.items) == [None]
    assert queue.waits == 0
    assert store.reads == 0
    assert store.writes == []


def test_batching_disabled_preserves_legacy_behavior(batch_env, library, searcher, monkeypatch):
    queue, store = batch_env(batch_size=0, threshold=2, cursor=(1, 10, 2))
    last_backlog = []
    monkeypatch.setattr(app, 'showList', library)
    monkeypatch.setattr(searcher, '_set_last_backlog', last_backlog.append)
    monkeypatch.setattr(searcher, '_search_in_batches',
                        lambda *args, **kwargs: pytest.fail('batched path must not run when disabled'))

    searcher.search_backlog()

    # Everything is queued at once, nothing waits, the cursor is ignored entirely.
    assert len(queue.items) == 4
    assert queue.max_pending == 4
    assert queue.waits == 0
    assert keys_of(queue.items) == [None] * 4
    assert store.reads == 0
    assert store.writes == []
    assert last_backlog == [datetime.date.today().toordinal()]
    assert searcher.amActive is False


# --- SearchQueue.backlog_pending() -------------------------------------------

def make_backlog_item(key=None):
    return BacklogQueueItem(FakeSeries(1, 10, []), [FakeEpisode()], backlog_cursor_key=key)


@pytest.fixture
def restore_thread_name():
    """Undo the rename of the test thread done by ``QueueItem.finish()`` when an item runs inline."""
    thread = threading.current_thread()
    original_name = thread.name
    yield
    thread.name = original_name


class RecordingLock(object):
    """Lock wrapper that records how often it was acquired."""

    def __init__(self):
        self._lock = threading.Lock()
        self.acquisitions = 0

    def __enter__(self):
        self._lock.acquire()
        self.acquisitions += 1
        return self

    def __exit__(self, *exc):
        self._lock.release()
        return False


def test_backlog_pending_counts_queued_running_and_assigned_but_not_started_items(restore_thread_name):
    queue = SearchQueue()
    queue.queue = [make_backlog_item(), make_backlog_item(), DailySearchQueueItem(None, False)]

    assert queue.backlog_pending() == 2

    # run() assigns current_item and only then starts it; the item must already count.
    current = make_backlog_item()
    queue.current_item = current
    assert current.start_time is None and not current.inProgress
    assert queue.backlog_pending() == 3

    # Running: QueueItem.run() marks it in progress.
    current.inProgress = True
    current.start_time = datetime.datetime.utcnow()
    assert queue.backlog_pending() == 3

    # Finished: finish() clears inProgress while start_time stays set.
    current.finish()
    assert queue.backlog_pending() == 2

    # A non-backlog current item never counts.
    queue.current_item = DailySearchQueueItem(None, False)
    assert queue.backlog_pending() == 2


def test_backlog_pending_snapshots_under_the_queue_lock():
    queue = SearchQueue()
    queue.lock = RecordingLock()
    queue.queue = [make_backlog_item()]

    assert queue.backlog_pending() == 1
    assert queue.lock.acquisitions == 1


def test_backlog_pending_blocks_while_run_holds_the_lock():
    """While run() holds the lock (pop + assign + start), backlog_pending() cannot take its snapshot."""
    queue = SearchQueue()
    queue.queue = [make_backlog_item()]
    result = []

    queue.lock.acquire()
    try:
        reader = threading.Thread(target=lambda: result.append(queue.backlog_pending()))
        reader.start()
        reader.join(0.2)
        assert reader.is_alive(), 'backlog_pending() must wait for the queue lock'

        # Emulate the transition run() performs under the lock.
        queue.current_item = queue.queue.pop(0)
    finally:
        queue.lock.release()

    reader.join(2)
    assert result == [1]


def test_backlog_queue_item_records_cursor_before_finish_then_wakes(monkeypatch, restore_thread_name):
    events = []

    class Searcher(object):
        def record_completed(self, key):
            events.append(('record', key))

        def notify_capacity(self):
            events.append(('wake', None))

    item = make_backlog_item(key=(1, 10, 1))
    item.show.paused = True  # skip the actual provider search
    monkeypatch.setattr(app, 'backlog_search_scheduler', FakeScheduler(Searcher()))
    monkeypatch.setattr('medusa.search.queue.ws.Message', lambda *args, **kwargs: type('M', (object,), {'push': lambda self: None})())

    original_finish = item.finish

    def finish():
        events.append(('finish', None))
        original_finish()
    monkeypatch.setattr(item, 'finish', finish)

    item.run()

    assert events == [('record', (1, 10, 1)), ('finish', None), ('wake', None)]
    assert item.inProgress is False


def test_backlog_queue_item_without_cursor_key_only_wakes(monkeypatch, restore_thread_name):
    events = []

    class Searcher(object):
        def record_completed(self, key):
            events.append(('record', key))

        def notify_capacity(self):
            events.append(('wake', None))

    item = make_backlog_item()
    item.show.paused = True
    monkeypatch.setattr(app, 'backlog_search_scheduler', FakeScheduler(Searcher()))
    monkeypatch.setattr('medusa.search.queue.ws.Message', lambda *args, **kwargs: type('M', (object,), {'push': lambda self: None})())

    item.run()

    assert events == [('wake', None)]
