# coding=utf-8
"""Test targeted show statistics against recorded episode rows."""
from __future__ import unicode_literals

import json
import sqlite3
from datetime import date

from medusa import db
from medusa.common import DOWNLOADED, SNATCHED, WANTED
from medusa.server.api.v2.stats import per_show_stats

from mock.mock import Mock

import pytest


@pytest.fixture
def stats_database(monkeypatch):
    """Run the actual aggregation SQL in an isolated database."""
    connection = sqlite3.connect(':memory:', check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute('CREATE TABLE tv_shows (indexer INTEGER, indexer_id INTEGER, airs TEXT, network TEXT)')
    connection.execute(
        'CREATE TABLE tv_episodes (indexer INTEGER, showid INTEGER, season INTEGER, episode INTEGER, '
        'airdate INTEGER, status INTEGER, file_size INTEGER)'
    )
    connection.executemany('INSERT INTO tv_shows VALUES (?, ?, "", "")', [(1, 123), (1, 124), (3, 123)])
    aired = date.today().toordinal() - 1
    connection.executemany('INSERT INTO tv_episodes VALUES (?, ?, ?, ?, ?, ?, ?)', [
        (1, 123, 1, 1, aired, WANTED, 0),
        (1, 123, 1, 2, aired, DOWNLOADED, 100),
        (1, 123, 0, 1, aired, DOWNLOADED, 50),
        (1, 124, 1, 1, aired, SNATCHED, 200),
        (3, 123, 1, 1, aired, SNATCHED, 300)
    ])
    connection.commit()
    database = Mock()
    database.select.side_effect = lambda query, args=None: [
        dict(row) for row in connection.execute(query, args or []).fetchall()
    ]
    monkeypatch.setattr(db, 'DBConnection', Mock(return_value=database))
    yield connection, database
    connection.close()


@pytest.mark.gen_test
@pytest.mark.parametrize('show_slug, expected', [
    ('tvdb123', {(1, 123)}),
    ('tvmaze123', {(3, 123)}),
    ('tvdb999', set()),
    (None, {(1, 123), (1, 124), (3, 123)})
])
async def test_show_stats_filter_exact_show_and_indexer(
        stats_database, http_client, create_url, auth_headers, show_slug, expected):
    """Target one show without mixing matching IDs from other indexers or other shows."""
    params = {'showslug': show_slug} if show_slug is not None else {}
    response = await http_client.fetch(create_url('/stats/show', **params), **auth_headers)

    assert response.code == 200
    payload = json.loads(response.body)
    assert {(row['indexerId'], row['seriesId']) for row in payload['stats']} == expected
    assert isinstance(payload['maxDownloadCount'], int)
    if show_slug == 'tvdb123':
        assert payload['stats'][0]['epTotal'] == 2
        assert payload['stats'][0]['epDownloaded'] == 1
        assert payload['stats'][0]['epSnatched'] == 0
        assert payload['stats'][0]['seriesSize'] == 150


@pytest.mark.gen_test
async def test_show_stats_reject_invalid_slug_before_query(stats_database, http_client, create_url, auth_headers):
    """Malformed show filters must not turn into unfiltered library requests."""
    response = await http_client.fetch(create_url('/stats/show', showslug='invalid'), raise_error=False, **auth_headers)

    assert response.code == 400
    stats_database[1].select.assert_not_called()


def test_targeted_show_stats_read_committed_status_changes(stats_database):
    """A targeted refresh reflects the saved status without a statistics cache reset."""
    connection, _ = stats_database
    assert per_show_stats(show_slug='tvdb123')['stats'][0]['epSnatched'] == 0

    connection.execute(
        'UPDATE tv_episodes SET status = ? WHERE indexer = 1 AND showid = 123 AND season = 1 AND episode = 1',
        [SNATCHED]
    )
    connection.commit()

    result = per_show_stats(show_slug='tvdb123')['stats'][0]
    assert result['epSnatched'] == 1
    assert result['epDownloaded'] == 1
    assert result['epTotal'] == 2
