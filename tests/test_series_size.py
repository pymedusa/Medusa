# coding=utf-8
"""Regression tests for show totals based on recorded episode sizes."""
from __future__ import unicode_literals

import sqlite3

from medusa.common import ARCHIVED, DOWNLOADED, SKIPPED, WANTED
from medusa.tv import series as series_module
from medusa.tv.series import Series

from mock.mock import Mock

import pytest


@pytest.fixture
def recorded_series(monkeypatch):
    """Run the real size query against isolated saved episode records."""
    connection = sqlite3.connect(':memory:')
    connection.row_factory = sqlite3.Row
    connection.execute(
        'CREATE TABLE tv_episodes ('
        'indexer INTEGER, showid INTEGER, season INTEGER, episode INTEGER, '
        'status INTEGER, location TEXT, file_size NUMERIC)'
    )
    database = Mock()
    database.select.side_effect = lambda query, args=None: connection.execute(query, args or []).fetchall()
    monkeypatch.setattr(series_module.db, 'DBConnection', Mock(return_value=database))

    series = Series.__new__(Series)
    series.__dict__.update(indexer=1, indexerid=12, _location='missing-show')
    yield series, connection
    connection.close()


def test_series_size_keeps_missing_file_size_without_scanning(recorded_series, monkeypatch):
    """Moving a file does not change its recorded size until a rescan updates it."""
    series, connection = recorded_series
    connection.execute(
        'INSERT INTO tv_episodes (indexer, showid, location, file_size) VALUES (?, ?, ?, ?)',
        (1, 12, 'missing-show/Season 01/Show.S01E01.mkv', 418670005),
    )
    scan = Mock(side_effect=AssertionError('Reading the show total must not scan its directory'))
    monkeypatch.setattr(series_module.helpers, 'get_size', scan)

    assert series.size == 418670005
    scan.assert_not_called()


@pytest.mark.parametrize('sizes', [[], [None], [None, 0]])
def test_series_size_empty_or_unknown_sizes_are_zero(recorded_series, sizes):
    """Shows without a recorded file size have an integer zero total."""
    series, connection = recorded_series
    connection.executemany(
        'INSERT INTO tv_episodes (indexer, showid, file_size) VALUES (?, ?, ?)',
        [(1, 12, size) for size in sizes],
    )

    assert series.size == 0
    assert isinstance(series.size, int)


def test_series_size_isolates_both_show_and_indexer(recorded_series):
    """Exclude other shows and matching show IDs belonging to another indexer."""
    series, connection = recorded_series
    connection.executemany(
        'INSERT INTO tv_episodes (indexer, showid, file_size) VALUES (?, ?, ?)',
        [(1, 12, 100), (1, 12, 200), (2, 12, 1000), (1, 13, 2000)],
    )

    assert series.size == 300


def test_series_size_matches_all_recorded_episode_rows(recorded_series):
    """Include specials and shared files exactly as episode rows and season totals do."""
    series, connection = recorded_series
    connection.executemany(
        'INSERT INTO tv_episodes VALUES (?, ?, ?, ?, ?, ?, ?)',
        [
            (1, 12, 0, 1, ARCHIVED, 'special.mkv', 100),
            (1, 12, 1, 1, DOWNLOADED, 'Show.S01E01E02.mkv', 200),
            (1, 12, 1, 2, DOWNLOADED, 'Show.S01E01E02.mkv', 200),
            (1, 12, 2, 1, SKIPPED, 'Show.S02E01.mkv', 300),
            (1, 12, 2, 2, WANTED, 'Show.S02E02.mkv', 400),
            (1, 12, 2, 3, WANTED, '', None),
        ],
    )

    assert series.size == 1200


def test_series_size_changes_when_recorded_file_is_cleared(recorded_series):
    """Read the updated total after rescan clears a missing episode's saved size."""
    series, connection = recorded_series
    connection.execute(
        'INSERT INTO tv_episodes (indexer, showid, location, file_size) VALUES (?, ?, ?, ?)',
        (1, 12, 'missing-show/Show.S01E01.mkv', 418670005),
    )
    assert series.size == 418670005

    connection.execute(
        'UPDATE tv_episodes SET location = ?, file_size = ? WHERE indexer = ? AND showid = ?',
        ('', 0, 1, 12),
    )

    assert series.size == 0
