# coding=utf-8
"""Tests for search templates persistence and cleanup behavior."""

from __future__ import unicode_literals

import sqlite3
from types import SimpleNamespace
import os

from medusa import app
import medusa.search_templates as search_templates_module

import pytest


class SQLiteDBConnection(object):
    """Minimal DBConnection test double for SearchTemplates.

    Some legacy tests globally replace `medusa.db.DBConnection` with a custom class.
    SearchTemplates relies on a DBConnection-compatible API, so we patch it with this
    lightweight implementation to keep these tests isolated.
    """

    def __init__(self, filename=None, suffix=None, row_type='dict'):
        self.filename = filename or app.APPLICATION_DB
        self.suffix = suffix
        self.row_type = row_type
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row

    @property
    def path(self):
        filename = self.filename
        if self.suffix:
            filename = '{0}.{1}'.format(filename, self.suffix)
        return os.path.join(app.DATA_DIR, filename)

    def action(self, query, args=None, fetchall=False, fetchone=False):
        cur = self.connection.cursor()
        cur.execute(query, args or [])
        result = None
        if fetchall:
            result = [dict(row) for row in cur.fetchall()]
        elif fetchone:
            row = cur.fetchone()
            result = dict(row) if row else None
        self.connection.commit()
        return result

    def select(self, query, args=None):
        return self.action(query, args, fetchall=True) or []

    def upsert(self, tableName, valueDict, keyDict):
        def gen_params(my_dict):
            return [key + ' = ?' for key in my_dict]

        changes_before = self.connection.total_changes
        query = 'UPDATE [{0}] SET {1} WHERE {2}'.format(
            tableName,
            ', '.join(gen_params(valueDict)),
            ' AND '.join(gen_params(keyDict)),
        )
        self.action(query, list(valueDict.values()) + list(keyDict.values()))

        if self.connection.total_changes == changes_before:
            cols = list(valueDict) + list(keyDict)
            query = 'INSERT INTO [{0}] ({1}) VALUES ({2})'.format(
                tableName,
                ', '.join(cols),
                ', '.join(['?'] * len(cols)),
            )
            self.action(query, list(valueDict.values()) + list(keyDict.values()))


def _create_search_templates_db(db_path):
    con = sqlite3.connect(str(db_path))
    try:
        con.execute(
            'CREATE TABLE scene_exceptions '
            '(exception_id INTEGER PRIMARY KEY, indexer INTEGER, series_id INTEGER, title TEXT, '
            'season NUMERIC DEFAULT -1, custom NUMERIC DEFAULT 0);'
        )
        con.execute(
            'CREATE TABLE search_templates ('
            '`search_template_id` INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, '
            '`template` TEXT, '
            '`title` TEXT, '
            '`indexer` INTEGER, '
            '`series_id` INTEGER, '
            '`season` INTEGER, '
            '`enabled` INTEGER DEFAULT 1, '
            '`default` INTEGER DEFAULT 1, '
            '`season_search` INTEGER DEFAULT 0'
            ');'
        )
        con.commit()
    finally:
        con.close()


@pytest.fixture
def show_with_db(tmp_path, monkeypatch):
    monkeypatch.setattr(app, 'DATA_DIR', str(tmp_path))
    monkeypatch.setattr(app, 'APPLICATION_DB', 'test_main.db')
    monkeypatch.setattr(search_templates_module.db, 'DBConnection', SQLiteDBConnection)

    db_path = tmp_path / app.APPLICATION_DB
    _create_search_templates_db(db_path)

    # Keep this as a lightweight object (no Series.aliases property access / DB coupling).
    return SimpleNamespace(
        indexer=1,
        series_id=1,
        name='Show Name',
        aliases=[],
        air_by_date=0,
        sports=0,
        anime=0,
        is_scene=False,
    )


def test_custom_template_persists_after_update(show_with_db):
    st = search_templates_module.SearchTemplates(show_with_db)
    st.update([{
        'template': '%SN S%0SE%0E',
        'title': 'My Custom',
        'season': -1,
        'enabled': 1,
        'default': 0,
        'seasonSearch': 0,
    }])

    st2 = search_templates_module.SearchTemplates(show_with_db)
    st2.read_from_db()

    assert any(t.title == 'My Custom' and not t.default for t in st2.templates)


def test_custom_template_survives_clean(show_with_db):
    st = search_templates_module.SearchTemplates(show_with_db)
    st.main_db_con.action(
        'INSERT INTO search_templates (template, title, indexer, series_id, season, enabled, `default`, season_search) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        ['%SN S%0SE%0E', 'Orphan Custom', show_with_db.indexer, show_with_db.series_id, -1, 1, 0, 0]
    )

    st.read_from_db()
    assert any(t.title == 'Orphan Custom' and not t.default for t in st.templates)


def test_default_template_without_scene_exception_is_removed(show_with_db):
    st = search_templates_module.SearchTemplates(show_with_db)
    st.main_db_con.action(
        'INSERT INTO search_templates (template, title, indexer, series_id, season, enabled, `default`, season_search) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        ['%SN S%0SE%0E', 'Old Default', show_with_db.indexer, show_with_db.series_id, -1, 1, 1, 0]
    )

    st.read_from_db()
    assert all(t.title != 'Old Default' for t in st.templates)

    remaining = st.main_db_con.select(
        'SELECT * FROM search_templates WHERE indexer = ? AND series_id = ? AND title = ?',
        [show_with_db.indexer, show_with_db.series_id, 'Old Default']
    )
    assert remaining == []


def test_custom_template_without_scene_exception_is_preserved(show_with_db):
    st = search_templates_module.SearchTemplates(show_with_db)
    st.main_db_con.action(
        'INSERT INTO search_templates (template, title, indexer, series_id, season, enabled, `default`, season_search) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        ['%SN S%0SE%0E', 'Orphan Custom 2', show_with_db.indexer, show_with_db.series_id, -1, 1, 0, 0]
    )

    st.read_from_db()

    remaining = st.main_db_con.select(
        'SELECT * FROM search_templates WHERE indexer = ? AND series_id = ? AND title = ?',
        [show_with_db.indexer, show_with_db.series_id, 'Orphan Custom 2']
    )
    assert len(remaining) == 1


def test_custom_template_survives_generate_refresh_flow(show_with_db):
    st = search_templates_module.SearchTemplates(show_with_db)
    st.main_db_con.action(
        'INSERT INTO search_templates (template, title, indexer, series_id, season, enabled, `default`, season_search) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        ['%SN S%0SE%0E', 'Custom Persistent', show_with_db.indexer, show_with_db.series_id, -1, 1, 0, 0]
    )

    st2 = search_templates_module.SearchTemplates(show_with_db)
    st2.generate()

    assert any(t.title == 'Custom Persistent' and not t.default for t in st2.templates)


def test_series_search_templates_defensive_init(tvshow, monkeypatch):
    class DummySearchTemplates(object):
        def read_from_db(self):
            return None

    def init():
        tvshow._search_templates = DummySearchTemplates()

    monkeypatch.setattr(tvshow, 'init_search_templates', init)
    tvshow._search_templates = None

    assert isinstance(tvshow.search_templates, DummySearchTemplates)
