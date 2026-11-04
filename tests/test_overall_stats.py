# coding=utf-8
"""Test library counters using actual SQLite aggregation."""
from __future__ import unicode_literals

import sqlite3
from datetime import date
from types import SimpleNamespace

from medusa import app
from medusa.common import ARCHIVED, DOWNLOADED, FAILED, IGNORED, SKIPPED, SNATCHED, SNATCHED_BEST, SNATCHED_PROPER, UNAIRED, WANTED
from medusa.show import show as show_module
from medusa.show.show import Show

from mock.mock import Mock

import pytest


@pytest.fixture
def library(monkeypatch):
    """Execute the production query and record how many rows reach Python."""
    connection = sqlite3.connect(':memory:')
    connection.row_factory = sqlite3.Row
    connection.execute('CREATE TABLE tv_episodes (season INTEGER, episode INTEGER, airdate INTEGER, status INTEGER, quality INTEGER)')
    returned_rows = []

    def select(query, args=None):
        rows = [dict(row) for row in connection.execute(query, args or []).fetchall()]
        returned_rows.append(len(rows))
        return rows

    database = Mock(select=Mock(side_effect=select))
    monkeypatch.setattr(show_module, 'DBConnection', Mock(return_value=database))
    monkeypatch.setattr(app, 'showList', [])
    yield SimpleNamespace(connection=connection, database=database, returned_rows=returned_rows)
    connection.close()


def test_overall_stats_empty_library_has_integer_zeros(library):
    assert Show.overall_stats() == {
        'episodes': {'downloaded': 0, 'snatched': 0, 'total': 0},
        'shows': {'active': 0, 'total': 0}
    }


def test_overall_stats_preserves_status_and_airdate_rules(library):
    """Completed/snatched future episodes count; only aired wanted/skipped episodes count."""
    today = date.today().toordinal()
    statuses = [DOWNLOADED, ARCHIVED, SNATCHED, SNATCHED_PROPER, SNATCHED_BEST, SKIPPED, WANTED, FAILED, IGNORED, UNAIRED, None]
    library.connection.executemany('INSERT INTO tv_episodes VALUES (1, 1, ?, ?, 0)', [
        (today + offset, status) for status in statuses for offset in (-1, 0, 1)
    ])

    assert Show.overall_stats()['episodes'] == {'downloaded': 6, 'snatched': 9, 'total': 19}


def test_overall_stats_excludes_specials_and_unknown_airdates(library):
    today = date.today().toordinal()
    library.connection.executemany('INSERT INTO tv_episodes VALUES (?, ?, ?, ?, 0)', [
        (0, 1, today, DOWNLOADED),
        (-1, 1, today, DOWNLOADED),
        (1, 0, today, DOWNLOADED),
        (1, -1, today, DOWNLOADED),
        (1, 1, 1, DOWNLOADED),
        (1, 1, 0, DOWNLOADED),
        (1, 1, None, DOWNLOADED),
        (1, 1, today, SNATCHED)
    ])

    assert Show.overall_stats()['episodes'] == {'downloaded': 0, 'snatched': 1, 'total': 1}


def test_overall_stats_preserves_in_memory_show_counts(library, monkeypatch):
    monkeypatch.setattr(app, 'showList', [
        SimpleNamespace(paused=0, status='Continuing'),
        SimpleNamespace(paused=1, status='Continuing'),
        SimpleNamespace(paused=0, status='Ended'),
        SimpleNamespace(paused=0, status='Unknown')
    ])

    assert Show.overall_stats()['shows'] == {'active': 1, 'total': 4}


def test_overall_stats_reads_new_status_without_caching(library):
    library.connection.execute('INSERT INTO tv_episodes VALUES (1, 1, ?, ?, 0)', [date.today().toordinal(), WANTED])
    assert Show.overall_stats()['episodes'] == {'downloaded': 0, 'snatched': 0, 'total': 1}

    library.connection.execute('UPDATE tv_episodes SET status = ?', [SNATCHED])
    library.connection.commit()

    assert Show.overall_stats()['episodes'] == {'downloaded': 0, 'snatched': 1, 'total': 1}


def test_overall_stats_returns_one_aggregate_row_to_python(library):
    """Refreshing the footer must not materialize every eligible episode in Python."""
    library.connection.executemany('INSERT INTO tv_episodes VALUES (1, 1, ?, ?, 0)', [
        (date.today().toordinal(), DOWNLOADED) for _ in range(100)
    ])

    assert Show.overall_stats()['episodes'] == {'downloaded': 100, 'snatched': 0, 'total': 100}
    library.database.select.assert_called_once()
    assert library.returned_rows == [1]
