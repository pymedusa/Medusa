# coding=utf-8
"""SQLite integration coverage for conditional batch writes."""

import sqlite3
import threading

from medusa import db

from mock.mock import Mock

import pytest


@pytest.fixture
def database(monkeypatch):
    """Run the real batch writer against a private in-memory database."""
    connection = sqlite3.connect(':memory:')
    connection.execute('CREATE TABLE records (id INTEGER PRIMARY KEY, state TEXT)')
    connection.executemany('INSERT INTO records VALUES (?, ?)', [(1, 'before'), (2, 'before')])
    connection.commit()

    database = object.__new__(db.DBConnection)
    database.filename = 'conditional-batch-{0}'.format(id(connection))
    database.row_type = 'dict'
    database.connection = connection
    monkeypatch.setitem(db.db_locks, database.filename, threading.Lock())
    monkeypatch.setattr(db.logger, 'log', Mock())

    yield database
    connection.close()


def record_states(database):
    """Read state after a completed commit or rollback."""
    return [row['state'] for row in database.connection.execute('SELECT state FROM records ORDER BY id')]


def test_conditional_batch_commits_every_matching_record(database):
    """All guarded updates become visible together when every condition matches."""
    results = database.mass_action([
        ['UPDATE records SET state = ? WHERE id = ? AND state = ?', ['after', 1, 'before']],
        ['UPDATE records SET state = ? WHERE id = ? AND state = ?', ['after', 2, 'before']],
    ], expected_rowcount=1)

    assert record_states(database) == ['after', 'after']
    assert [cursor.rowcount for cursor in results] == [1, 1]
    assert not database.connection.in_transaction


def test_conditional_batch_rolls_back_earlier_updates_when_later_record_changed(database):
    """A stale second record rolls back the first record while preserving its newer owner."""
    database.connection.execute('UPDATE records SET state = ? WHERE id = 2', ['other writer'])
    database.connection.commit()

    with pytest.raises(db.StaleRecordError):
        database.mass_action([
            ['UPDATE records SET state = ? WHERE id = ? AND state = ?', ['after', 1, 'before']],
            ['UPDATE records SET state = ? WHERE id = ? AND state = ?', ['after', 2, 'before']],
        ], expected_rowcount=1)

    assert record_states(database) == ['before', 'other writer']
    assert not database.connection.in_transaction


def test_legacy_batch_allows_updates_matching_no_records(database):
    """Existing callers retain their optional zero-row update behavior."""
    results = database.mass_action([
        ['UPDATE records SET state = ? WHERE id = ?', ['after', 1]],
        ['UPDATE records SET state = ? WHERE id = ?', ['after', 99]],
    ])

    assert record_states(database) == ['after', 'before']
    assert [cursor.rowcount for cursor in results] == [1, 0]


def test_legacy_batch_fetchall_preserves_dictionary_rows(database):
    """Existing read batches keep the same fetchall result shape."""
    results = database.mass_action([['SELECT id, state FROM records WHERE id = ?', [1]]], fetchall=True)

    assert results == [[{'id': 1, 'state': 'before'}]]


def test_conditional_batch_rejects_fetchall_before_work(database):
    """Affected-row guards apply to write cursors rather than consumed read results."""
    with pytest.raises(ValueError):
        database.mass_action([['UPDATE records SET state = ?', ['after']]], fetchall=True, expected_rowcount=1)

    database.connection.row_factory = db.DBConnection._dict_factory
    assert record_states(database) == ['before', 'before']


@pytest.mark.parametrize('expected_rowcount', [None, 1])
def test_locked_batch_retries_all_queries_after_rolling_back(database, monkeypatch, expected_rowcount):
    """A retry after the second query fails must replay the complete transaction."""
    execute = database._execute
    attempted_records = []

    def execute_with_one_lock_failure(query, args=None, **kwargs):
        attempted_records.append(args[1])
        if len(attempted_records) == 2:
            raise sqlite3.OperationalError('database is locked')
        if len(attempted_records) == 3:
            assert record_states(database) == ['before', 'before']
        return execute(query, args, **kwargs)

    monkeypatch.setattr(database, '_execute', execute_with_one_lock_failure)
    monkeypatch.setattr(db.time, 'sleep', Mock())

    results = database.mass_action([
        ['UPDATE records SET state = ? WHERE id = ? AND state = ?', ['after', 1, 'before']],
        ['UPDATE records SET state = ? WHERE id = ? AND state = ?', ['after', 2, 'before']],
    ], expected_rowcount=expected_rowcount)

    assert attempted_records == [1, 2, 1, 2]
    assert record_states(database) == ['after', 'after']
    assert [cursor.rowcount for cursor in results] == [1, 1]
    assert not database.connection.in_transaction
