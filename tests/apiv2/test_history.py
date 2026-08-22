# coding=utf-8
"""Regression tests for /history episode-title and release filtering."""
from __future__ import unicode_literals

import json
import sqlite3
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
from types import SimpleNamespace
from urllib.parse import parse_qsl, urlencode

from medusa.common import DOWNLOADED, FAILED, Quality, SNATCHED
from medusa.indexers.config import indexerConfig
from medusa.schedulers.download_handler import ClientStatusEnum, status_strings
from medusa.server.api.v2 import history as history_module
from medusa.tv.series import Series, SeriesIdentifier

import pytest


def _fake_find_by_identifier(identifier, predicate):
    titles = {(1, 101): 'My English Title'}
    title = titles.get((identifier.indexer.id, identifier.id))
    if not title:
        return None
    show = SimpleNamespace(title=title)
    if predicate and not predicate(show):
        return None
    return show


def _history_url(create_url, resource_filter=None, column_filters=None, compact=False, page=None, limit=None, sort=None):
    base_url = create_url('/history')
    base, _, query = base_url.partition('?')

    query_params = dict(parse_qsl(query))
    filters = {}
    if resource_filter is not None:
        filters['resource'] = resource_filter
    if column_filters:
        filters.update(column_filters)
    query_params['filter'] = json.dumps({'columnFilters': filters}, separators=(',', ':'))
    if compact:
        query_params['compact'] = 1
    if page is not None:
        query_params['page'] = page
    if limit is not None:
        query_params['limit'] = limit
    if sort is not None:
        query_params['sort'] = json.dumps(sort, separators=(',', ':'))

    return '{0}?{1}'.format(base, urlencode(query_params))


def _insert_history_row(connection, action, resource, indexer_id=1, showid=101, season=1, episode=1,
                        provider='UnitProvider', quality=0, size=1, client_status=None, date=1):
    connection.execute(
        'INSERT INTO history (date, action, quality, provider, version, resource, size, proper_tags, indexer_id, showid, '
        'season, episode, manually_searched, info_hash, provider_type, client_status, part_of_batch) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (
            date,
            action,
            quality,
            provider,
            'unit',
            resource,
            size,
            '',
            indexer_id,
            showid,
            season,
            episode,
            0,
            '',
            '',
            client_status,
            0,
        )
    )
    return connection.execute('SELECT last_insert_rowid()').fetchone()[0]


def _insert_series_slug_row(connection, resource, action=DOWNLOADED, **kwargs):
    kwargs.setdefault('indexer_id', PRIMARY_INDEXER_ID)
    kwargs.setdefault('showid', PRIMARY_SHOWID)
    return _insert_history_row(connection, action, resource, **kwargs)


async def _fetch_series_slug_rows(fetch_history, resource_filter, **query_params):
    response = await fetch_history(resource_filter, **query_params)
    return response, json.loads(response.body)


def _build_series_slug_cases():
    cases = []
    for indexer_id, config in sorted(indexerConfig.items()):
        showid = 10000 + indexer_id
        slug = SeriesIdentifier.from_id(indexer_id, showid).slug
        cases.append((indexer_id, config['identifier'], showid, slug))
    return tuple(cases)


SERIES_SLUG_CASES = _build_series_slug_cases()
PRIMARY_SERIES_SLUG_CASE = SERIES_SLUG_CASES[0]
PRIMARY_INDEXER_ID, PRIMARY_INDEXER_NAME, PRIMARY_SHOWID, PRIMARY_SERIES_SLUG = PRIMARY_SERIES_SLUG_CASE
IMDB_SERIES_SLUG_CASE = next(case for case in SERIES_SLUG_CASES if case[1] == 'imdb')
CLIENT_STATUS_BITS = tuple(status.value for status in status_strings if status.value)
CLIENT_STATUS_SUPPORTED_MASK = sum(CLIENT_STATUS_BITS)
CLIENT_STATUS_UNSUPPORTED_MASK = CLIENT_STATUS_SUPPORTED_MASK << 1

SERIES_SLUG_VARIANTS = tuple(dict.fromkeys([
    PRIMARY_SERIES_SLUG.lower(),
    PRIMARY_SERIES_SLUG.upper(),
    PRIMARY_SERIES_SLUG[:1].upper() + PRIMARY_SERIES_SLUG[1:],
    '  {0}  '.format(PRIMARY_SERIES_SLUG),
    "'{0}'".format(PRIMARY_SERIES_SLUG),
    '"{0}"'.format(PRIMARY_SERIES_SLUG),
    '`{0}`'.format(PRIMARY_SERIES_SLUG),
    "'{0}".format(PRIMARY_SERIES_SLUG),
    '"{0}'.format(PRIMARY_SERIES_SLUG),
    '`{0}'.format(PRIMARY_SERIES_SLUG),
    "{0}'".format(PRIMARY_SERIES_SLUG),
    '{0}"'.format(PRIMARY_SERIES_SLUG),
    '{0}`'.format(PRIMARY_SERIES_SLUG),
    "'{0}\"".format(PRIMARY_SERIES_SLUG),
]))

SERIES_SLUG_GUARDS = (
    (
        'unknown{0}'.format(PRIMARY_SHOWID),
        'unknown{0}.mkv'.format(PRIMARY_SHOWID),
    ),
    (PRIMARY_INDEXER_NAME, '{0}.mkv'.format(PRIMARY_INDEXER_NAME)),
    (
        '{0}-{1}'.format(PRIMARY_INDEXER_NAME, PRIMARY_SHOWID),
        '{0}-{1}.mkv'.format(PRIMARY_INDEXER_NAME, PRIMARY_SHOWID),
    ),
    (
        '{0}_{1}'.format(PRIMARY_INDEXER_NAME, PRIMARY_SHOWID),
        '{0}_{1}.mkv'.format(PRIMARY_INDEXER_NAME, PRIMARY_SHOWID),
    ),
    (
        '{0}junk'.format(PRIMARY_SERIES_SLUG),
        '{0}junk.mkv'.format(PRIMARY_SERIES_SLUG),
    ),
    (
        '{0}0{1}'.format(PRIMARY_INDEXER_NAME, PRIMARY_SHOWID),
        '{0}0{1}.mkv'.format(PRIMARY_INDEXER_NAME, PRIMARY_SHOWID),
    ),
    (
        'tt{0}'.format(IMDB_SERIES_SLUG_CASE[2]),
        'tt{0}.mkv'.format(IMDB_SERIES_SLUG_CASE[2]),
    ),
    (
        'imdbtt{0}'.format(IMDB_SERIES_SLUG_CASE[2]),
        'imdbtt{0}.mkv'.format(IMDB_SERIES_SLUG_CASE[2]),
    ),
    (
        '" {0} "'.format(PRIMARY_SERIES_SLUG),
        ' {0} .mkv'.format(PRIMARY_SERIES_SLUG),
    ),
)


@pytest.fixture
def history_db(monkeypatch):
    connection = sqlite3.connect(':memory:', check_same_thread=False)
    connection.row_factory = sqlite3.Row

    class SharedMemoryDBConnection(object):
        def __init__(self, *_args, **_kwargs):
            self.connection = connection

        @property
        def path(self):
            return ':memory:'

        def action(self, query, args=None, fetchall=False, fetchone=False):
            cursor = self.connection.cursor()
            cursor.execute(query, args or [])
            if fetchall:
                return [dict(row) for row in cursor.fetchall()]
            if fetchone:
                row = cursor.fetchone()
                return dict(row) if row else None
            return None

        def select(self, query, args=None):
            return self.action(query, args, fetchall=True) or []

        def close(self):
            return None

    monkeypatch.setattr(history_module.db, 'DBConnection', SharedMemoryDBConnection)
    monkeypatch.setattr(
        Series,
        'find_by_identifier',
        classmethod(lambda _cls, identifier, predicate=None: _fake_find_by_identifier(identifier, predicate))
    )

    connection.execute(
        'CREATE TABLE history ('
        'date INTEGER, action INTEGER, quality INTEGER, provider TEXT, version TEXT, resource TEXT, '
        'size INTEGER, proper_tags TEXT, indexer_id INTEGER, showid INTEGER, season INTEGER, episode INTEGER, '
        'manually_searched INTEGER, info_hash TEXT, provider_type TEXT, client_status INTEGER, part_of_batch INTEGER)'
    )
    connection.execute('CREATE TABLE tv_shows (indexer INTEGER, indexer_id INTEGER, show_name TEXT)')
    connection.execute('CREATE TABLE scene_exceptions (indexer INTEGER, series_id INTEGER, title TEXT)')
    connection.commit()

    connection.execute('INSERT INTO tv_shows (indexer, indexer_id, show_name) VALUES (?, ?, ?)', (1, 101, 'My English Title'))
    connection.execute('INSERT INTO scene_exceptions (indexer, series_id, title) VALUES (?, ?, ?)', (1, 101, 'Romaji Scene Title'))
    connection.execute('INSERT INTO scene_exceptions (indexer, series_id, title) VALUES (?, ?, ?)', (1, 101, '日本語の別名'))
    connection.execute('INSERT INTO scene_exceptions (indexer, series_id, title) VALUES (?, ?, ?)', (1, 101, "Hero's Alternate Title"))
    connection.commit()

    yield connection
    connection.close()


@pytest.fixture
def fetch_history(http_client, create_url, auth_headers):
    async def _fetch(resource=None, **query_params):
        response = await http_client.fetch(_history_url(create_url, resource, **query_params), **auth_headers)
        return response

    return _fetch


@pytest.mark.gen_test
@pytest.mark.parametrize(
    'indexer_id,indexer_name,showid,slug',
    SERIES_SLUG_CASES,
    ids=[case[1] for case in SERIES_SLUG_CASES]
)
async def test_series_slug_registry_selects_exact_identity(
    history_db, fetch_history, indexer_id, indexer_name, showid, slug
):
    matching_row = _insert_series_slug_row(
        history_db,
        'series-slug-target.mkv',
        indexer_id=indexer_id,
        showid=showid
    )
    _insert_series_slug_row(
        history_db,
        'series-slug-wrong-indexer.mkv',
        indexer_id=next(candidate for candidate in indexerConfig if candidate != indexer_id),
        showid=showid
    )
    _insert_series_slug_row(
        history_db,
        'series-slug-wrong-show.mkv',
        indexer_id=indexer_id,
        showid=showid + 1
    )

    response, rows = await _fetch_series_slug_rows(fetch_history, slug)

    assert response.code == 200
    assert {row['id'] for row in rows} == {matching_row}


@pytest.mark.gen_test
@pytest.mark.parametrize('resource_filter', SERIES_SLUG_VARIANTS)
async def test_series_slug_case_whitespace_wrappers_and_malformed_boundaries(
    history_db, fetch_history, resource_filter
):
    matching_row = _insert_series_slug_row(history_db, 'series-slug-variant-target.mkv')
    _insert_series_slug_row(history_db, 'series-slug-variant-wrong-show.mkv', showid=PRIMARY_SHOWID + 1)

    _response, rows = await _fetch_series_slug_rows(fetch_history, resource_filter)

    assert {row['id'] for row in rows} == {matching_row}


@pytest.mark.gen_test
@pytest.mark.parametrize('resource_filter,direct_resource', SERIES_SLUG_GUARDS)
async def test_series_slug_strict_guards_preserve_direct_resource_matching(
    history_db, fetch_history, resource_filter, direct_resource
):
    identity_row = _insert_series_slug_row(history_db, 'series-slug-guard-identity-only.mkv')
    direct_row = _insert_series_slug_row(history_db, direct_resource, showid=PRIMARY_SHOWID + 1)

    response, rows = await _fetch_series_slug_rows(fetch_history, resource_filter)

    assert response.code == 200
    assert identity_row not in {row['id'] for row in rows}
    assert {row['id'] for row in rows} == {direct_row}


@pytest.mark.gen_test
async def test_series_slug_overlong_numeric_candidate_falls_back_without_server_error(
    history_db, http_client, create_url, auth_headers
):
    _insert_series_slug_row(history_db, 'series-slug-overlong-identity-only.mkv')
    overlong_slug = PRIMARY_INDEXER_NAME + ('9' * 5000)

    response = await http_client.fetch(
        _history_url(create_url, overlong_slug),
        raise_error=False,
        **auth_headers
    )
    rows = json.loads(response.body)

    assert response.code == 200
    assert rows == []


@pytest.mark.gen_test
async def test_series_slug_sqlite_overflow_falls_back_to_direct_resource_match(
    history_db, fetch_history
):
    overflow_slug = '{0}{1}'.format(PRIMARY_INDEXER_NAME, 1 << 63)
    direct_row = _insert_series_slug_row(
        history_db,
        '{0}.mkv'.format(overflow_slug),
        showid=PRIMARY_SHOWID + 1
    )

    response, rows = await _fetch_series_slug_rows(fetch_history, overflow_slug)

    assert response.code == 200
    assert {row['id'] for row in rows} == {direct_row}


@pytest.mark.gen_test
async def test_series_slug_sqlite_maximum_selects_exact_identity(history_db, fetch_history):
    sqlite_maximum = (1 << 63) - 1
    maximum_slug = '{0}{1}'.format(PRIMARY_INDEXER_NAME, sqlite_maximum)
    matching_row = _insert_series_slug_row(
        history_db,
        'series-slug-sqlite-maximum-identity.mkv',
        showid=sqlite_maximum
    )
    _insert_series_slug_row(
        history_db,
        'series-slug-sqlite-maximum-wrong-indexer.mkv',
        indexer_id=next(candidate for candidate in indexerConfig if candidate != PRIMARY_INDEXER_ID),
        showid=sqlite_maximum
    )
    _insert_series_slug_row(
        history_db,
        'series-slug-sqlite-maximum-wrong-show.mkv',
        showid=sqlite_maximum - 1
    )

    response, rows = await _fetch_series_slug_rows(fetch_history, maximum_slug)

    assert response.code == 200
    assert {row['id'] for row in rows} == {matching_row}


@pytest.mark.gen_test
async def test_numeric_episode_filter_remains_resource_text(history_db, fetch_history):
    identity_row = _insert_series_slug_row(history_db, 'numeric-episode-identity-only.mkv')
    direct_row = _insert_series_slug_row(
        history_db,
        'episode-{0}.mkv'.format(PRIMARY_SHOWID),
        showid=PRIMARY_SHOWID + 1
    )

    response, rows = await _fetch_series_slug_rows(fetch_history, str(PRIMARY_SHOWID))

    assert response.code == 200
    assert identity_row not in {row['id'] for row in rows}
    assert {row['id'] for row in rows} == {direct_row}


@pytest.mark.gen_test
async def test_series_slug_or_direct_resource_match(history_db, fetch_history):
    identity_row = _insert_series_slug_row(history_db, 'series-slug-or-identity-only.mkv')
    direct_row = _insert_series_slug_row(
        history_db,
        'unrelated-{0}.mkv'.format(PRIMARY_SERIES_SLUG),
        showid=PRIMARY_SHOWID + 1
    )

    _response, rows = await _fetch_series_slug_rows(fetch_history, PRIMARY_SERIES_SLUG)

    assert {row['id'] for row in rows} == {identity_row, direct_row}


@pytest.mark.gen_test
async def test_series_slug_rendered_episode_filter_targets_detailed_and_compact(
    history_db, fetch_history
):
    target_row = _insert_series_slug_row(
        history_db, 'series-slug-rendered-target.mkv', season=2, episode=7
    )
    _insert_series_slug_row(
        history_db, 'series-slug-rendered-other.mkv', season=2, episode=8
    )
    resource_filter = '{0} - s02e07'.format(PRIMARY_SERIES_SLUG)

    detailed_response, detailed_rows = await _fetch_series_slug_rows(fetch_history, resource_filter)
    compact_response, compact_rows = await _fetch_series_slug_rows(
        fetch_history, resource_filter, compact=True
    )

    assert {row['id'] for row in detailed_rows} == {target_row}
    assert compact_response.headers['X-Pagination-Count'] == '1'
    assert len(compact_rows) == 1
    assert {row['id'] for row in compact_rows[0]['rows']} == {target_row}


@pytest.mark.gen_test
@pytest.mark.parametrize(
    'resource_filter,resource_title_filter,season,episode',
    [
        (PRIMARY_SERIES_SLUG, PRIMARY_SERIES_SLUG, None, None),
        (
            '{0} - s02e07'.format(PRIMARY_SERIES_SLUG),
            PRIMARY_SERIES_SLUG,
            2,
            7
        ),
    ],
    ids=['plain', 'rendered']
)
async def test_series_slug_query_shape_avoids_constant_identity_union(
    history_db, fetch_history, monkeypatch, resource_filter, resource_title_filter, season, episode
):
    matching_row = _insert_series_slug_row(
        history_db,
        'query-shape-target.mkv',
        season=season or 1,
        episode=episode or 1
    )
    captured = []
    original_select = history_module.db.DBConnection.select

    def capture_select(connection, query, args=None):
        captured.append((query, tuple(args or ())))
        return original_select(connection, query, args)

    monkeypatch.setattr(history_module.db.DBConnection, 'select', capture_select)

    response, rows = await _fetch_series_slug_rows(fetch_history, resource_filter)

    assert response.code == 200
    assert {row['id'] for row in rows} == {matching_row}
    assert len(captured) == 1

    query, args = captured[0]
    normalized_query = ' '.join(query.split())
    history_where = normalized_query.split('FROM history', 1)[1]
    # Keeping the constant identity out of the correlated UNION CTE lets SQLite 3.51 build its automatic lookup index.
    assert 'SELECT ? AS indexer, ? AS indexer_id' not in normalized_query
    direct_identity = 'history.indexer_id = ? AND history.showid = ?'
    assert direct_identity in history_where
    if season is not None and episode is not None:
        assert '{0} AND history.season = ? AND history.episode = ?'.format(direct_identity) in history_where
        assert history_where.count('AND history.season = ? AND history.episode = ?') == 2

    expected_args = [
        '%%{0}%%'.format(resource_title_filter),
        '%%{0}%%'.format(resource_title_filter),
        '%%{0}%%'.format(resource_filter),
        PRIMARY_INDEXER_ID,
        PRIMARY_SHOWID,
    ]
    if season is not None and episode is not None:
        expected_args.extend([season, episode, season, episode])
    assert args == tuple(expected_args)


@pytest.mark.gen_test
async def test_series_slug_filters_stack_with_pagination_and_compact_grouping(
    history_db, fetch_history
):
    first_matching_row = _insert_series_slug_row(
        history_db,
        'series-slug-stack-match-one.mkv',
        provider='Target Provider',
        quality=Quality.HDTV,
        size=8 * 1024 * 1024,
        client_status=3,
        date=1
    )
    later_matching_row = _insert_series_slug_row(
        history_db,
        'series-slug-stack-match-two.mkv',
        provider='Target Provider',
        quality=Quality.HDTV,
        size=8 * 1024 * 1024,
        client_status=3,
        date=2
    )
    matching_rows = {first_matching_row, later_matching_row}
    _insert_series_slug_row(
        history_db,
        'series-slug-stack-action-miss.mkv',
        action=SNATCHED,
        provider='Target Provider',
        quality=Quality.HDTV,
        size=8 * 1024 * 1024,
        client_status=3
    )
    _insert_series_slug_row(
        history_db,
        'series-slug-stack-provider-miss.mkv',
        provider='Other Provider',
        quality=Quality.HDTV,
        size=8 * 1024 * 1024,
        client_status=3
    )
    _insert_series_slug_row(
        history_db,
        'series-slug-stack-quality-miss.mkv',
        provider='Target Provider',
        quality=Quality.FULLHDTV,
        size=8 * 1024 * 1024,
        client_status=3
    )
    _insert_series_slug_row(
        history_db,
        'series-slug-stack-size-miss.mkv',
        provider='Target Provider',
        quality=Quality.HDTV,
        size=2 * 1024 * 1024,
        client_status=3
    )
    _insert_series_slug_row(
        history_db,
        'series-slug-stack-client-miss.mkv',
        provider='Target Provider',
        quality=Quality.HDTV,
        size=8 * 1024 * 1024,
        client_status=1
    )
    _insert_series_slug_row(
        history_db,
        'series-slug-stack-identity-miss.mkv',
        showid=PRIMARY_SHOWID + 1,
        provider='Target Provider',
        quality=Quality.HDTV,
        size=8 * 1024 * 1024,
        client_status=3
    )
    column_filters = {
        'statusName': DOWNLOADED,
        'providerId': 'target provider',
        'quality': Quality.HDTV,
        'size': '> 4',
        'clientStatus': 3,
    }

    detailed_response, detailed_rows = await _fetch_series_slug_rows(
        fetch_history,
        PRIMARY_SERIES_SLUG,
        column_filters=column_filters,
        page=1,
        limit=1,
        sort=[{'field': 'actionDate', 'type': 'desc'}]
    )
    compact_response, compact_rows = await _fetch_series_slug_rows(
        fetch_history, PRIMARY_SERIES_SLUG, column_filters=column_filters, compact=True
    )

    assert detailed_response.headers['X-Pagination-Count'] == '2'
    assert len(detailed_rows) == 1
    assert detailed_rows[0]['id'] == later_matching_row
    assert compact_response.headers['X-Pagination-Count'] == '1'
    assert len(compact_rows) == 1
    assert {row['id'] for row in compact_rows[0]['rows']} == matching_rows


@pytest.mark.gen_test
@pytest.mark.parametrize('resource_filter', ['My English Title', 'English'])
async def test_resource_filter_exact_and_partial_english_title(history_db, fetch_history, resource_filter):
    row_id = _insert_history_row(history_db, DOWNLOADED, 'release_one.mkv')
    response = await fetch_history(resource_filter)
    rows = json.loads(response.body)

    assert response.code == 200
    assert {row['id'] for row in rows} == {row_id}


@pytest.mark.gen_test
@pytest.mark.parametrize('resource_filter', ['my english title', 'MY ENGLISH TITLE', 'mY EnGlIsH tItLe'])
async def test_resource_filter_case_variants(history_db, fetch_history, resource_filter):
    history_db.execute('PRAGMA case_sensitive_like = ON')
    row_id = _insert_history_row(history_db, DOWNLOADED, 'release_two.mkv')
    response = await fetch_history(resource_filter)
    rows = json.loads(response.body)

    assert response.code == 200
    assert {row['id'] for row in rows} == {row_id}


@pytest.mark.gen_test
@pytest.mark.parametrize(
    'resource_filter',
    [
        '  My English Title',
        'My English Title  ',
        '  English',
        'English  ',
        '  my english title  ',
        '  Romaji Scene Title',
        'Romaji Scene Title  ',
        '  Scene Title',
        'Scene Title  ',
    ]
)
async def test_resource_filter_outer_whitespace_is_trimmed(history_db, fetch_history, resource_filter):
    canonical_row = _insert_history_row(history_db, DOWNLOADED, 'canonical.mkv')
    alias_row = _insert_history_row(history_db, SNATCHED, 'alias-match.mkv')
    response = await fetch_history(resource_filter)
    rows = json.loads(response.body)

    assert response.code == 200
    assert {row['id'] for row in rows} == {canonical_row, alias_row}


@pytest.mark.gen_test
async def test_resource_filter_trailing_space_uses_identity_rows(history_db, fetch_history):
    spaced_row = _insert_history_row(history_db, DOWNLOADED, 'My English Title - bonus.mkv')
    identity_only_row = _insert_history_row(history_db, SNATCHED, 'identity-only.mkv')

    rows = json.loads((await fetch_history('My English Title ')).body)

    assert {row['id'] for row in rows} == {spaced_row, identity_only_row}


@pytest.mark.gen_test
@pytest.mark.parametrize(
    'resource_filter',
    [
        '  My English Title - s01e05',
        'My English Title - s01e05  ',
        '  My English Title - s01e05  ',
        '  my english title - s01e05  ',
    ]
)
async def test_rendered_episode_filter_trims_outer_whitespace(history_db, fetch_history, resource_filter):
    matching_row = _insert_history_row(history_db, DOWNLOADED, 'ep-05.mkv', episode=5)
    _insert_history_row(history_db, SNATCHED, 'ep-06.mkv', episode=6)

    rows = json.loads((await fetch_history(resource_filter)).body)

    assert {row['id'] for row in rows} == {matching_row}
    assert all(row['episode'] == 5 for row in rows)


@pytest.mark.gen_test
@pytest.mark.parametrize('resource_filter', ['  DirectResourceMatch  ', 'DirectResourceMatch  ', '  DirectResourceMatch'])
async def test_direct_resource_filter_trims_whitespace_and_stays_row_local(history_db, fetch_history, resource_filter):
    direct_resource_row = _insert_history_row(history_db, DOWNLOADED, 'DirectResourceMatch.mkv')
    _insert_history_row(history_db, SNATCHED, 'OtherResource.mkv')

    rows = json.loads((await fetch_history(resource_filter)).body)

    assert {row['id'] for row in rows} == {direct_resource_row}


@pytest.mark.gen_test
async def test_whitespace_only_resource_filter_is_treated_as_empty(history_db, fetch_history):
    alpha_row = _insert_history_row(history_db, DOWNLOADED, 'alpha.mkv', provider='ProviderAlpha')
    _insert_history_row(history_db, DOWNLOADED, 'beta.mkv', provider='ProviderBeta')

    rows = json.loads((await fetch_history('   ', column_filters={'providerId': 'provideralpha'})).body)

    assert {row['id'] for row in rows} == {alpha_row}


@pytest.mark.gen_test
@pytest.mark.parametrize('quote', ["'", '"', '`'])
async def test_quoted_episode_filter_preserves_inner_whitespace(history_db, fetch_history, quote):
    spaced_row = _insert_history_row(history_db, DOWNLOADED, '  Exact Resource  .mkv')
    _insert_history_row(history_db, DOWNLOADED, 'Exact Resource.mkv')

    resource_filter = '{0}  Exact Resource  {0}'.format(quote)
    rows = json.loads((await fetch_history(resource_filter)).body)

    assert {row['id'] for row in rows} == {spaced_row}


@pytest.mark.gen_test
@pytest.mark.parametrize(
    'resource_filter',
    [
        'Romaji Scene Title',
        'Scene Title',
        'romaji scene title',
        'ROMAJI SCENE TITLE',
        'Romaji SCENE title',
        '日本語の別名',
        "Hero's Alternate Title",
    ]
)
async def test_resource_filter_scene_alias_exact_and_partial(history_db, fetch_history, resource_filter):
    history_db.execute('PRAGMA case_sensitive_like = ON')
    row_id = _insert_history_row(history_db, DOWNLOADED, 'release_three.mkv')
    response = await fetch_history(resource_filter)
    rows = json.loads(response.body)

    assert response.code == 200
    assert {row['id'] for row in rows} == {row_id}


@pytest.mark.gen_test
async def test_english_and_alias_query_return_identical_rows(history_db, fetch_history):
    english_row = _insert_history_row(history_db, DOWNLOADED, 'episode_one.mkv')
    alias_resource_row = _insert_history_row(history_db, SNATCHED, 'mixed-release.bin')

    english_rows = json.loads((await fetch_history('My English Title')).body)
    alias_rows = json.loads((await fetch_history('Romaji Scene Title')).body)

    assert {row['id'] for row in english_rows} == {english_row, alias_resource_row}
    assert {row['id'] for row in alias_rows} == {english_row, alias_resource_row}


@pytest.mark.gen_test
@pytest.mark.parametrize(
    'resource_filter',
    ['My English Title - s01e05', 'Romaji Scene Title - s01e05', 'my english title - S01E05']
)
async def test_rendered_episode_filter_targets_only_matching_episode(history_db, fetch_history, resource_filter):
    matching_snatched = _insert_history_row(history_db, SNATCHED, 's01e05_snatched.mkv', episode=5)
    matching_downloaded = _insert_history_row(history_db, DOWNLOADED, 's01e05_downloaded.mkv', episode=5)
    _insert_history_row(history_db, FAILED, 's01e06_failed.mkv', episode=6)

    rows = json.loads((await fetch_history(resource_filter)).body)

    assert {row['id'] for row in rows} == {matching_snatched, matching_downloaded}
    assert {row['status'] for row in rows} == {SNATCHED, DOWNLOADED}
    assert all(row['episode'] == 5 for row in rows)


@pytest.mark.gen_test
async def test_multiple_aliases_for_same_identity_do_not_duplicate_rows(history_db, fetch_history):
    history_db.execute('INSERT INTO scene_exceptions (indexer, series_id, title) VALUES (?, ?, ?)', (1, 101, 'Romaji Alternative'))
    history_db.commit()

    row_id = _insert_history_row(history_db, DOWNLOADED, 'alias_release.mkv')
    response = await fetch_history('Scene')
    rows = json.loads(response.body)

    assert response.code == 200
    assert {row['id'] for row in rows} == {row_id}


@pytest.mark.gen_test
@pytest.mark.parametrize('resource_filter', ['OnlyResourceMatch', 'ResourceMatch', 'onlyresourcematch'])
async def test_direct_resource_filter_stays_row_local(history_db, fetch_history, resource_filter):
    history_db.execute('PRAGMA case_sensitive_like = ON')
    targeted = _insert_history_row(history_db, DOWNLOADED, 'OnlyResourceMatch.mkv')
    _insert_history_row(history_db, SNATCHED, 'OtherResource.mkv')

    rows = json.loads((await fetch_history(resource_filter)).body)

    assert {row['id'] for row in rows} == {targeted}


@pytest.mark.gen_test
async def test_orphan_history_rows_are_directly_searchable(history_db, fetch_history):
    orphan_row = _insert_history_row(history_db, DOWNLOADED, 'OrphanResource.mkv', indexer_id=None, showid=None)
    _insert_history_row(history_db, DOWNLOADED, 'OtherResource.mkv')

    rows = json.loads((await fetch_history('OrphanResource')).body)

    assert {row['id'] for row in rows} == {orphan_row}


@pytest.mark.gen_test
async def test_unrelated_column_matches_do_not_satisfy_episode_filter(history_db, fetch_history):
    provider_only_row = _insert_history_row(
        history_db,
        DOWNLOADED,
        'ProviderResource.mkv',
    )
    # update provider to keep test term out of the resource/identity fields.
    history_db.execute('UPDATE history SET provider = ? WHERE rowid = ?', ('ProviderOnlySearchKey', provider_only_row))
    history_db.commit()

    response = await fetch_history('ProviderOnlySearchKey')
    rows = json.loads(response.body)

    assert response.code == 200
    assert rows == []


@pytest.mark.gen_test
@pytest.mark.parametrize('resource_filter', ['My English Title', 'Romaji Scene Title'])
async def test_episode_title_and_status_filter_are_combined_as_and(history_db, fetch_history, resource_filter):
    downloaded_row_id = _insert_history_row(history_db, DOWNLOADED, 'status-match-download.mkv')
    _insert_history_row(history_db, SNATCHED, 'status-match-snatched.mkv')

    rows = json.loads((await fetch_history(resource_filter, column_filters={'statusName': DOWNLOADED})).body)

    assert {row['id'] for row in rows} == {downloaded_row_id}


@pytest.mark.gen_test
@pytest.mark.parametrize(
    'provider_filter',
    ['unit provider', ' unit provider', 'unit provider ', ' unit provider ']
)
async def test_episode_filter_with_provider_is_case_insensitive_partial_and_trims_outer_whitespace(
    history_db, fetch_history, provider_filter
):
    matching_row = _insert_history_row(
        history_db,
        DOWNLOADED,
        'provider-match.mkv',
        provider='Unit Provider Alpha'
    )
    _insert_history_row(
        history_db,
        DOWNLOADED,
        'provider-no-match.mkv',
        provider='External Source'
    )

    rows = json.loads((await fetch_history(
        'My English Title', column_filters={'providerId': provider_filter}
    )).body)

    assert {row['id'] for row in rows} == {matching_row}


@pytest.mark.gen_test
@pytest.mark.parametrize('quote', ["'", '"', '`'])
async def test_quoted_provider_filter_preserves_inner_whitespace(history_db, fetch_history, quote):
    spaced_row = _insert_history_row(
        history_db,
        DOWNLOADED,
        'provider-spaced.mkv',
        provider='  Exact Provider  '
    )
    _insert_history_row(
        history_db,
        DOWNLOADED,
        'provider-unspaced.mkv',
        provider='Exact Provider'
    )

    provider_filter = '{0}  Exact Provider  {0}'.format(quote)
    rows = json.loads((await fetch_history(
        'My English Title', column_filters={'providerId': provider_filter}
    )).body)

    assert {row['id'] for row in rows} == {spaced_row}


@pytest.mark.parametrize(
    'filter_value,expected',
    [
        ("'Episode'", 'Episode'),
        ('"  Episode  "', '  Episode  '),
        ('`  Episode  `', '  Episode  '),
        ("'Episode", 'Episode'),
        ('"Episode', 'Episode'),
        ('`Episode', 'Episode'),
        ("Episode'", 'Episode'),
        ('Episode"', 'Episode'),
        ('Episode`', 'Episode'),
        ("'Episode\"", 'Episode'),
        ('"Episode`', 'Episode'),
        ("`Episode'", 'Episode'),
        ("  'Episode  ", 'Episode'),
        ('  Episode"  ', 'Episode'),
        ('  "Episode\'  ', 'Episode'),
        ("'", None),
        ('"', None),
        ('`', None),
        ("''", None),
        ('""', None),
        ('``', None),
        ("The Ogre's Bride", "The Ogre's Bride"),
        ("O'Reilly", "O'Reilly"),
        ("Test's", "Test's"),
        ("Test ' s", "Test ' s"),
        ('Test"s', 'Test"s'),
        ('Test " s', 'Test " s'),
        ('Test`s', 'Test`s'),
        ('Test ` s', 'Test ` s'),
        ("'Test's'", "Test's"),
        ("'Test ' s'", "Test ' s"),
        ('"Test\'s"', "Test's"),
        ("'Test \" s'", 'Test " s'),
        ("`Test ' s`", "Test ' s"),
        ('"Test"s"', 'Test"s'),
        ('"Test " s"', 'Test " s'),
        ('`Test`s`', 'Test`s'),
        ('`Test ` s`', 'Test ` s'),
        ("'''", "'"),
        ("''''", "''"),
        ('"""', '"'),
        ('```', '`'),
        ('"Dog Days\'"', "Dog Days'"),
        ("'Dog Days\"'", 'Dog Days"'),
        ("'\"Kimi wo Aisuru'", '"Kimi wo Aisuru'),
        ('"Don`t Problem Children"', 'Don`t Problem Children'),
        ('The Ogre’s Bride', 'The Ogre’s Bride'),
        ('“Quoted Title”', '“Quoted Title”'),
        ('「日本語タイトル」', '「日本語タイトル」'),
        ('『日本語タイトル』', '『日本語タイトル』'),
        ('', None),
        ('   ', None),
        (None, None),
        (123, None),
        (['Episode'], None),
    ]
)
def test_text_filter_normalization_preserves_or_cleans_content(filter_value, expected):
    assert history_module._normalize_text_filter(filter_value) == expected


@pytest.mark.gen_test
@pytest.mark.parametrize(
    'resource_filter,expected_resource',
    [
        ('"Target Episode', 'Target Episode'),
        ('Target Episode"', 'Target Episode'),
        ("'Target Episode\"", 'Target Episode'),
    ]
)
async def test_malformed_episode_filter_uses_cleaned_content_and_stacks(
    history_db, fetch_history, resource_filter, expected_resource
):
    matching_row = _insert_history_row(
        history_db,
        DOWNLOADED,
        '{0} release.mkv'.format(expected_resource),
        provider='Target Provider',
        quality=Quality.HDTV
    )
    _insert_history_row(
        history_db,
        DOWNLOADED,
        '{0} other.mkv'.format(expected_resource),
        provider='Target Provider',
        quality=Quality.FULLHDTV
    )
    _insert_history_row(
        history_db,
        DOWNLOADED,
        'Different Episode release.mkv',
        provider='Target Provider',
        quality=Quality.HDTV
    )

    rows = json.loads((await fetch_history(
        resource_filter, column_filters={'quality': Quality.HDTV}
    )).body)

    assert {row['id'] for row in rows} == {matching_row}


@pytest.mark.gen_test
@pytest.mark.parametrize(
    'provider_filter,expected_provider',
    [
        ('"Target Provider', 'Target Provider'),
        ('Target Provider"', 'Target Provider'),
        ("'Target Provider\"", 'Target Provider'),
    ]
)
async def test_malformed_provider_filter_uses_cleaned_content_and_stacks(
    history_db, fetch_history, provider_filter, expected_provider
):
    matching_row = _insert_history_row(
        history_db,
        DOWNLOADED,
        'Target Episode release.mkv',
        provider=expected_provider,
        quality=Quality.HDTV
    )
    _insert_history_row(
        history_db,
        DOWNLOADED,
        'Target Episode other.mkv',
        provider='Other Provider',
        quality=Quality.HDTV
    )
    _insert_history_row(
        history_db,
        DOWNLOADED,
        'Different Episode release.mkv',
        provider=expected_provider,
        quality=Quality.HDTV
    )

    rows = json.loads((await fetch_history(
        'Target Episode',
        column_filters={'providerId': provider_filter, 'quality': Quality.HDTV}
    )).body)

    assert {row['id'] for row in rows} == {matching_row}


@pytest.mark.gen_test
async def test_malformed_episode_and_provider_filters_clean_and_stack_together(history_db, fetch_history):
    matching_row = _insert_history_row(
        history_db,
        DOWNLOADED,
        'Target Episode release.mkv',
        provider='Target Provider',
        quality=Quality.HDTV
    )
    _insert_history_row(
        history_db,
        DOWNLOADED,
        'Target Episode release.mkv',
        provider='Other Provider',
        quality=Quality.HDTV
    )
    _insert_history_row(
        history_db,
        DOWNLOADED,
        'Different Episode release.mkv',
        provider='Target Provider',
        quality=Quality.HDTV
    )
    _insert_history_row(
        history_db,
        DOWNLOADED,
        'Target Episode release.mkv',
        provider='Target Provider',
        quality=Quality.FULLHDTV
    )

    rows = json.loads((await fetch_history(
        '\'"Target Episode',
        column_filters={'providerId': 'Target Provider"\'', 'quality': Quality.HDTV}
    )).body)

    assert {row['id'] for row in rows} == {matching_row}


@pytest.mark.gen_test
async def test_episode_filter_with_whitespace_only_provider_preserves_other_filters(history_db, fetch_history):
    matching_row = _insert_history_row(
        history_db,
        DOWNLOADED,
        'provider-whitespace-match.mkv',
        quality=Quality.HDTV
    )
    _insert_history_row(
        history_db,
        DOWNLOADED,
        'provider-whitespace-quality-miss.mkv',
        quality=Quality.FULLHDTV
    )

    rows = json.loads((await fetch_history(
        'My English Title', column_filters={'providerId': '   ', 'quality': Quality.HDTV}
    )).body)

    assert {row['id'] for row in rows} == {matching_row}


@pytest.mark.gen_test
@pytest.mark.parametrize('size_filter', ['> 4', ' > 4', '> 4 ', ' > 4 '])
async def test_episode_filter_with_size_trims_outer_whitespace(history_db, fetch_history, size_filter):
    matching_row = _insert_history_row(
        history_db,
        SNATCHED,
        'size-whitespace-match.mkv',
        size=8 * 1024 * 1024
    )
    _insert_history_row(
        history_db,
        SNATCHED,
        'size-whitespace-miss.mkv',
        size=2 * 1024 * 1024
    )

    rows = json.loads((await fetch_history(
        'My English Title', column_filters={'size': size_filter}
    )).body)

    assert {row['id'] for row in rows} == {matching_row}


@pytest.mark.gen_test
@pytest.mark.parametrize(
    'size_filter,expected_size',
    [
        ('<1024', 512),
        ('< 1024', 512),
        ("'<1024'", 512),
        ('" < 1024 "', 512),
        ('`  <1024  `', 512),
        ('>1024', 2048),
        ('> 1024', 2048),
        ("'>1024'", 2048),
        ('" > 1024 "', 2048),
        ('`  >1024  `', 2048),
    ]
)
async def test_size_filter_accepts_optional_quotes_and_operator_spacing(
    history_db, fetch_history, size_filter, expected_size
):
    matching_row = _insert_history_row(
        history_db,
        SNATCHED,
        'size-operator-match.mkv',
        size=expected_size * 1024 * 1024
    )
    exact_row = _insert_history_row(
        history_db,
        SNATCHED,
        'size-operator-exact.mkv',
        size=1024 * 1024 * 1024
    )
    other_size = 2048 if expected_size == 512 else 512
    other_row = _insert_history_row(
        history_db,
        SNATCHED,
        'size-operator-other.mkv',
        size=other_size * 1024 * 1024
    )

    rows = json.loads((await fetch_history(
        'My English Title', column_filters={'size': size_filter}
    )).body)

    assert {row['id'] for row in rows} == {matching_row}
    assert exact_row not in {row['id'] for row in rows}
    assert other_row not in {row['id'] for row in rows}


@pytest.mark.gen_test
@pytest.mark.parametrize(
    'size_filter',
    [
        '1024',
        '= 1024',
        '<= 1024',
        '>= 1024',
        '>> 1024',
        '>.5',
        '>1.',
        '>1.345',
        '>1.4.5',
        '< 1024junk',
        '< 1024kb',
        '; DROP TABLE history',
        '"<1024',
        '<1024"',
        '"<1024`',
        '`<1024"',
        '>8589934592.00',
        '>8589934592.00 MB',
        '>8589934592.00 GB',
    ]
)
async def test_malformed_size_filter_is_ignored_without_affecting_other_filters(
    history_db, fetch_history, size_filter
):
    matching_row = _insert_history_row(
        history_db,
        SNATCHED,
        'size-malformed-provider-match.mkv',
        provider='Target Provider'
    )
    _insert_history_row(
        history_db,
        SNATCHED,
        'size-malformed-provider-miss.mkv',
        provider='Other Provider'
    )

    response = await fetch_history(
        'My English Title',
        column_filters={'size': size_filter, 'providerId': 'target provider'}
    )
    rows = json.loads(response.body)

    assert response.code == 200
    assert {row['id'] for row in rows} == {matching_row}


@pytest.mark.gen_test
@pytest.mark.parametrize(
    'size_filter,expected_names',
    [
        ('>1', {'small', 'large'}),
        ('>123456', set()),
        ('>123456789.99', set()),
        ('>１２３', {'zero', 'small', 'large'}),
    ]
)
async def test_size_filter_accepts_long_ascii_digits_and_rejects_unicode_digits(size_filter, expected_names, history_db, fetch_history):
    rows_by_name = {
        'zero': _insert_history_row(history_db, SNATCHED, 'size-boundary-zero.mkv', size=0),
        'small': _insert_history_row(
            history_db, SNATCHED, 'size-boundary-small.mkv', size=512 * 1024 * 1024
        ),
        'large': _insert_history_row(
            history_db, SNATCHED, 'size-boundary-large.mkv', size=2048 * 1024 * 1024
        ),
    }

    response = await fetch_history('My English Title', column_filters={'size': size_filter})
    rows = json.loads(response.body)

    assert response.code == 200
    assert {name for name, row_id in rows_by_name.items() if row_id in {row['id'] for row in rows}} == expected_names


@pytest.mark.parametrize(
    'size_filter,expected_operator,expected_numeric,size_multiplier,rounding',
    [
        ('>123456789.99', '>', Decimal('123456789.99'), Decimal(1024 ** 2), ROUND_FLOOR),
        ('>123 MB', '>', Decimal('123'), Decimal(1024 ** 2), ROUND_FLOOR),
        ('>123 Gb', '>', Decimal('123'), Decimal(1024 ** 3), ROUND_FLOOR),
        ('> 1.3', '>', Decimal('1.3'), Decimal(1024 ** 2), ROUND_FLOOR),
        ('<1.35MB', '<', Decimal('1.35'), Decimal(1024 ** 2), ROUND_CEILING),
        ('> 900.45 mB', '>', Decimal('900.45'), Decimal(1024 ** 2), ROUND_FLOOR),
        ('< 2.4 Gb', '<', Decimal('2.4'), Decimal(1024 ** 3), ROUND_CEILING),
        ('>8589934591.99', '>', Decimal('8589934591.99'), Decimal(1024 ** 2), ROUND_FLOOR),
        ('>8589934591.99 MB', '>', Decimal('8589934591.99'), Decimal(1024 ** 2), ROUND_FLOOR),
        ('<8589934591.99 gB', '<', Decimal('8589934591.99'), Decimal(1024 ** 3), ROUND_CEILING),
    ]
)
def test_size_parser_accepts_decimal_units_and_shared_cap(
    size_filter, expected_operator, expected_numeric, size_multiplier, rounding
):
    expected_size = int((expected_numeric * size_multiplier).to_integral_value(rounding=rounding))

    assert history_module._parse_size_filter(size_filter) == (expected_operator, expected_size)


@pytest.mark.parametrize(
    'size_filter',
    [
        '<8589934592.00',
        '>8589934592.00 MB',
        '<8589934592.00 mB',
        '>8589934592.00 GB',
        '<8589934592.00 gB',
    ]
)
def test_size_parser_rejects_values_above_shared_cap(size_filter):
    assert history_module._parse_size_filter(size_filter) is None


@pytest.mark.gen_test
@pytest.mark.parametrize(
    'size_filter,expected_names',
    [
        ('> 900.45 mB', {
            'nine-hundred-mb-above', 'two-point-four-gb-floor', 'two-point-four-gb-above'
        }),
        ('< 2.4 Gb', {
            'nine-hundred-mb-floor', 'nine-hundred-mb-above', 'two-point-four-gb-floor'
        }),
    ]
)
async def test_size_filter_accepts_mb_and_gb_decimal_values(size_filter, expected_names, history_db, fetch_history):
    decimal_mb = Decimal(1024 ** 2)
    decimal_gb = Decimal(1024 ** 3)
    nine_hundred_mb_floor = int(
        (Decimal('900.45') * decimal_mb).to_integral_value(rounding=ROUND_FLOOR)
    )
    two_point_four_gb_floor = int(
        (Decimal('2.4') * decimal_gb).to_integral_value(rounding=ROUND_FLOOR)
    )

    rows_by_name = {
        'nine-hundred-mb-floor': _insert_history_row(
            history_db, SNATCHED, 'size-900.45-mb-floor.mkv', size=nine_hundred_mb_floor
        ),
        'nine-hundred-mb-above': _insert_history_row(
            history_db, SNATCHED, 'size-900.45-mb-above.mkv', size=nine_hundred_mb_floor + 1
        ),
        'two-point-four-gb-floor': _insert_history_row(
            history_db, SNATCHED, 'size-2.4-gb-floor.mkv', size=two_point_four_gb_floor
        ),
        'two-point-four-gb-above': _insert_history_row(
            history_db, SNATCHED, 'size-2.4-gb-above.mkv', size=two_point_four_gb_floor + 1
        ),
    }

    rows = json.loads((await fetch_history(
        'My English Title', column_filters={'size': size_filter}
    )).body)
    returned_names = {name for name, row_id in rows_by_name.items() if row_id in {row['id'] for row in rows}}

    assert returned_names == expected_names


@pytest.mark.gen_test
@pytest.mark.parametrize(
    'size_filter,expected_names',
    [
        ('>1.3gb', {'one-point-three-gb-above', 'two-gb'}),
        ('>1.3 Gb', {'one-point-three-gb-above', 'two-gb'}),
        ('" <1.3 gb "', {'small', 'one-point-three-gb-floor'}),
        ('<1.3 gb', {'small', 'one-point-three-gb-floor'}),
        ('>1.4 gb', {'two-gb'}),
        ('`>1.4 gb`', {'two-gb'}),
        ('<0.00', set()),
    ]
)
async def test_size_filter_accepts_unit_variants_and_decimal_rounding(
    size_filter, expected_names, history_db, fetch_history
):
    decimal_gb = Decimal('1073741824')
    one_point_three_floor = int(
        (Decimal('1.3') * decimal_gb).to_integral_value(rounding=ROUND_FLOOR)
    )

    rows_by_name = {
        'small': _insert_history_row(history_db, SNATCHED, 'size-decimal-small.mkv', size=950 * 1024 * 1024),
        'one-point-three-gb-floor': _insert_history_row(
            history_db, SNATCHED, 'size-decimal-floor.mkv', size=one_point_three_floor
        ),
        'one-point-three-gb-above': _insert_history_row(
            history_db, SNATCHED, 'size-decimal-above.mkv', size=one_point_three_floor + 1
        ),
        'two-gb': _insert_history_row(history_db, SNATCHED, 'size-decimal-huge.mkv', size=2 * 1024 * 1024 * 1024),
    }

    rows = json.loads((await fetch_history('My English Title', column_filters={'size': size_filter})).body)
    returned_names = {name for name, row_id in rows_by_name.items() if row_id in {row['id'] for row in rows}}

    assert returned_names == expected_names


@pytest.mark.gen_test
@pytest.mark.parametrize('size_filter', [None, 1024, True, [], {}])
async def test_non_string_size_filter_is_ignored_without_affecting_provider_filter(
    history_db, fetch_history, size_filter
):
    matching_row = _insert_history_row(
        history_db,
        SNATCHED,
        'size-non-string-provider-match.mkv',
        provider='Target Provider'
    )
    _insert_history_row(
        history_db,
        SNATCHED,
        'size-non-string-provider-miss.mkv',
        provider='Other Provider'
    )

    response = await fetch_history(
        'My English Title',
        column_filters={'size': size_filter, 'providerId': 'target provider'}
    )
    rows = json.loads(response.body)

    assert response.code == 200
    assert {row['id'] for row in rows} == {matching_row}


@pytest.mark.gen_test
async def test_episode_filter_with_whitespace_only_size_preserves_other_filters(history_db, fetch_history):
    matching_row = _insert_history_row(
        history_db,
        SNATCHED,
        'size-whitespace-quality-match.mkv',
        quality=Quality.HDTV,
        size=2 * 1024 * 1024
    )
    _insert_history_row(
        history_db,
        SNATCHED,
        'size-whitespace-quality-miss.mkv',
        quality=Quality.FULLHDTV,
        size=8 * 1024 * 1024
    )

    rows = json.loads((await fetch_history(
        'My English Title', column_filters={'size': '   ', 'quality': Quality.HDTV}
    )).body)

    assert {row['id'] for row in rows} == {matching_row}


@pytest.mark.gen_test
async def test_history_size_sort_is_numeric(history_db, fetch_history):
    one_point_three_floor = int(
        (Decimal('1.3') * Decimal('1073741824')).to_integral_value(rounding=ROUND_FLOOR)
    )
    rows_by_size = [
        ('size-sort-2gb', _insert_history_row(history_db, SNATCHED, 'size-sort-2gb.mkv', size=2 * 1024 * 1024 * 1024)),
        ('size-sort-1.3gb', _insert_history_row(
            history_db, SNATCHED, 'size-sort-1.3gb.mkv', size=one_point_three_floor
        )),
        ('size-sort-950mb', _insert_history_row(
            history_db, SNATCHED, 'size-sort-950mb.mkv', size=950 * 1024 * 1024
        )),
    ]

    rows = json.loads((await fetch_history(
        'My English Title',
        sort=[{'field': 'size', 'type': 'desc'}]
    )).body)

    assert [row['id'] for row in rows] == [row_id for _, row_id in rows_by_size]


@pytest.mark.gen_test
async def test_episode_filter_with_quality_size_and_client_status_filters_stacks(history_db, fetch_history):
    match_row = _insert_history_row(
        history_db,
        SNATCHED,
        'stack-match.mkv',
        quality=Quality.HDTV,
        size=8 * 1024 * 1024,
        client_status=3,
        episode=10
    )
    _insert_history_row(
        history_db,
        SNATCHED,
        'stack-size-miss.mkv',
        quality=Quality.HDTV,
        size=2 * 1024 * 1024,
        client_status=3,
        episode=10
    )
    _insert_history_row(
        history_db,
        SNATCHED,
        'stack-quality-miss.mkv',
        quality=Quality.FULLHDTV,
        size=8 * 1024 * 1024,
        client_status=3,
        episode=10
    )
    _insert_history_row(
        history_db,
        SNATCHED,
        'stack-clientstatus-miss.mkv',
        quality=Quality.HDTV,
        size=8 * 1024 * 1024,
        client_status=1,
        episode=10
    )

    rows = json.loads((
        await fetch_history(
            'My English Title',
            column_filters={'quality': Quality.HDTV, 'size': '> 4', 'clientStatus': 3}
        )
    ).body)

    assert {row['id'] for row in rows} == {match_row}


@pytest.mark.gen_test
async def test_client_status_zero_filter_matches_only_zero(history_db, fetch_history):
    zero_row = _insert_history_row(history_db, SNATCHED, 'client-status-zero.mkv', client_status=0)
    _insert_history_row(history_db, SNATCHED, 'client-status-null.mkv', client_status=None)
    _insert_history_row(
        history_db,
        SNATCHED,
        'client-status-nonzero.mkv',
        client_status=CLIENT_STATUS_BITS[0]
    )

    rows = json.loads((await fetch_history(
        'My English Title', column_filters={'clientStatus': 0}
    )).body)

    assert {row['id'] for row in rows} == {zero_row}


@pytest.mark.gen_test
@pytest.mark.parametrize('clear_value', [None, ''], ids=['null', 'empty'])
async def test_client_status_clear_filter_matches_all_statuses(history_db, fetch_history, clear_value):
    rows_by_status = {
        'zero': _insert_history_row(history_db, SNATCHED, 'client-status-clear-zero.mkv', client_status=0),
        'null': _insert_history_row(history_db, SNATCHED, 'client-status-clear-null.mkv', client_status=None),
        'nonzero': _insert_history_row(
            history_db,
            SNATCHED,
            'client-status-clear-nonzero.mkv',
            client_status=CLIENT_STATUS_BITS[0]
        ),
    }

    rows = json.loads((await fetch_history(
        'My English Title', column_filters={'clientStatus': clear_value}
    )).body)

    assert {row['id'] for row in rows} == set(rows_by_status.values())


@pytest.mark.gen_test
@pytest.mark.parametrize('selected_bit', CLIENT_STATUS_BITS, ids=[str(bit) for bit in CLIENT_STATUS_BITS])
async def test_client_status_individual_bit_matches_exact_and_superset_only(
    history_db, fetch_history, selected_bit
):
    other_bit = next(bit for bit in CLIENT_STATUS_BITS if bit != selected_bit)
    exact_row = _insert_history_row(
        history_db, SNATCHED, 'client-status-bit-exact.mkv', client_status=selected_bit
    )
    superset_row = _insert_history_row(
        history_db,
        SNATCHED,
        'client-status-bit-superset.mkv',
        client_status=selected_bit | other_bit
    )
    unrelated_row = _insert_history_row(
        history_db, SNATCHED, 'client-status-bit-unrelated.mkv', client_status=other_bit
    )

    rows = json.loads((await fetch_history(
        'My English Title', column_filters={'clientStatus': selected_bit}
    )).body)

    assert {row['id'] for row in rows} == {exact_row, superset_row}
    assert unrelated_row not in {row['id'] for row in rows}


@pytest.mark.gen_test
async def test_client_status_multiple_bits_require_all_and_allow_extra(
    history_db, fetch_history
):
    selected_mask = CLIENT_STATUS_BITS[0] | CLIENT_STATUS_BITS[1]
    extra_mask = CLIENT_STATUS_BITS[2]
    exact_row = _insert_history_row(
        history_db, SNATCHED, 'client-status-mask-exact.mkv', client_status=selected_mask
    )
    extra_row = _insert_history_row(
        history_db,
        SNATCHED,
        'client-status-mask-extra.mkv',
        client_status=selected_mask | extra_mask
    )
    missing_row = _insert_history_row(
        history_db,
        SNATCHED,
        'client-status-mask-missing.mkv',
        client_status=CLIENT_STATUS_BITS[0]
    )

    rows = json.loads((await fetch_history(
        'My English Title', column_filters={'clientStatus': selected_mask}
    )).body)

    assert {row['id'] for row in rows} == {exact_row, extra_row}
    assert missing_row not in {row['id'] for row in rows}


@pytest.mark.gen_test
@pytest.mark.parametrize(
    'invalid_value',
    [True, -1, '3', 1.5, CLIENT_STATUS_UNSUPPORTED_MASK],
    ids=['bool', 'negative', 'string', 'float', 'unsupported-bit']
)
async def test_invalid_client_status_is_ignored_while_other_filters_stack(
    history_db, fetch_history, invalid_value
):
    matching_row = _insert_history_row(
        history_db,
        DOWNLOADED,
        'client-status-invalid-match.mkv',
        provider='Target Provider',
        client_status=CLIENT_STATUS_BITS[0]
    )
    _insert_history_row(
        history_db,
        DOWNLOADED,
        'client-status-invalid-provider-miss.mkv',
        provider='Other Provider',
        client_status=CLIENT_STATUS_BITS[0]
    )

    rows = json.loads((await fetch_history(
        'My English Title',
        column_filters={'providerId': 'target provider', 'clientStatus': invalid_value}
    )).body)

    assert {row['id'] for row in rows} == {matching_row}


@pytest.mark.gen_test
async def test_client_status_zero_serializes_snatched_label(history_db, fetch_history):
    row_id = _insert_history_row(
        history_db, SNATCHED, 'client-status-zero-serialization.mkv', client_status=0
    )

    rows = json.loads((await fetch_history('My English Title')).body)

    row = next(row for row in rows if row['id'] == row_id)
    assert row['clientStatus'] == {
        'status': [ClientStatusEnum.SNATCHED.value],
        'string': [status_strings[ClientStatusEnum.SNATCHED]],
    }


@pytest.mark.gen_test
async def test_client_status_composed_serialization_keeps_registry_order(history_db, fetch_history):
    composed_status = CLIENT_STATUS_BITS[0] | CLIENT_STATUS_BITS[1]
    row_id = _insert_history_row(
        history_db,
        SNATCHED,
        'client-status-composed-serialization.mkv',
        client_status=composed_status
    )

    rows = json.loads((await fetch_history('My English Title')).body)

    row = next(row for row in rows if row['id'] == row_id)
    expected_statuses = [status for status in status_strings if status.value & composed_status]
    assert row['clientStatus'] == {
        'status': [status.value for status in expected_statuses],
        'string': [status_strings[status] for status in expected_statuses],
    }


@pytest.mark.gen_test
async def test_request_filter_state_is_scoped_by_request(history_db, fetch_history):
    provider_one_row = _insert_history_row(
        history_db,
        DOWNLOADED,
        'provider-one.mkv',
        provider='ProviderOne'
    )
    provider_two_row = _insert_history_row(
        history_db,
        DOWNLOADED,
        'provider-two.mkv',
        provider='ProviderTwo'
    )

    first_request = json.loads((await fetch_history('My English Title', column_filters={'providerId': 'providerone'})).body)
    second_request = json.loads((await fetch_history('My English Title', column_filters={'providerId': 'providertwo'})).body)

    assert {row['id'] for row in first_request} == {provider_one_row}
    assert {row['id'] for row in second_request} == {provider_two_row}


@pytest.mark.gen_test
async def test_compact_mode_groups_episode_by_identity_and_keeps_snatched_downloaded_together(history_db, fetch_history):
    snatched_row = _insert_history_row(
        history_db,
        SNATCHED,
        'compact-s01e01-snatched.mkv',
        quality=Quality.HDTV,
        episode=1
    )
    downloaded_row = _insert_history_row(
        history_db,
        DOWNLOADED,
        'compact-s01e01-downloaded.mkv',
        quality=Quality.HDTV,
        episode=1
    )

    canonical_response = await fetch_history('My English Title', compact=True)
    alias_response = await fetch_history('Romaji Scene Title', compact=True)
    canonical = json.loads(canonical_response.body)
    alias = json.loads(alias_response.body)

    assert len(canonical) == 1
    assert len(alias) == 1
    assert canonical_response.headers['X-Pagination-Count'] == '1'
    assert alias_response.headers['X-Pagination-Count'] == '1'
    assert canonical[0]['rows'][0]['statusName'] in {'Snatched', 'Downloaded'}
    assert {row['statusName'] for row in canonical[0]['rows']} == {'Snatched', 'Downloaded'}
    assert {row['id'] for row in canonical[0]['rows']} == {snatched_row, downloaded_row}
    assert {row['id'] for row in alias[0]['rows']} == {snatched_row, downloaded_row}
    assert canonical[0]['episodeTitle'] == 'My English Title - s01e01'


@pytest.mark.gen_test
@pytest.mark.parametrize('resource_filter', ['My English Title - s01e05', 'Romaji Scene Title - s01e05'])
async def test_rendered_episode_filter_in_compact_mode_targets_exact_episode(history_db, fetch_history, resource_filter):
    target_row = _insert_history_row(history_db, DOWNLOADED, 'compact-ep-05.mkv', episode=5, quality=Quality.HDTV)
    _insert_history_row(history_db, DOWNLOADED, 'compact-ep-06.mkv', episode=6, quality=Quality.HDTV)

    compact_rows = json.loads((await fetch_history(resource_filter, compact=True)).body)

    assert len(compact_rows) == 1
    assert compact_rows[0]['episodeTitle'] == 'My English Title - s01e05'
    assert {row['id'] for row in compact_rows[0]['rows']} == {target_row}


@pytest.mark.gen_test
async def test_detailed_pagination_with_title_filter_uses_total_row_count(history_db, fetch_history):
    inserted = [
        _insert_history_row(history_db, DOWNLOADED, 'detailed-ep-01.mkv', episode=1, date=11),
        _insert_history_row(history_db, DOWNLOADED, 'detailed-ep-02.mkv', episode=2, date=12),
        _insert_history_row(history_db, DOWNLOADED, 'detailed-ep-03.mkv', episode=3, date=13),
        _insert_history_row(history_db, DOWNLOADED, 'detailed-ep-04.mkv', episode=4, date=14),
        _insert_history_row(history_db, DOWNLOADED, 'detailed-ep-05.mkv', episode=5, date=15),
    ]

    first_response = await fetch_history(
        'My English Title',
        page=1,
        limit=2,
        sort=[{'field': 'actionDate', 'type': 'desc'}],
    )
    first_rows = json.loads(first_response.body)

    second_response = await fetch_history(
        'My English Title',
        page=2,
        limit=2,
        sort=[{'field': 'actionDate', 'type': 'desc'}],
    )
    second_rows = json.loads(second_response.body)

    assert first_response.headers['X-Pagination-Count'] == '5'
    assert second_response.headers['X-Pagination-Count'] == '5'
    assert [row['id'] for row in first_rows] == [inserted[4], inserted[3]]
    assert [row['id'] for row in second_rows] == [inserted[2], inserted[1]]
