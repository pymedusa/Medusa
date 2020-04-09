# coding=utf-8

from __future__ import unicode_literals

import logging

from medusa import db
from medusa.databases import utils
from medusa.logger.adapters.style import BraceAdapter


log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


# Add new migrations at the bottom of the list
# and subclass the previous migration.
class InitialSchema(db.SchemaUpgrade):
    def test(self):
        return self.hasTable('db_version')

    def execute(self):
        queries = [
            ('CREATE TABLE lastUpdate (provider TEXT, time NUMERIC);',),
            ('CREATE TABLE lastSearch (provider TEXT, time NUMERIC);',),
            ('CREATE TABLE scene_exceptions (exception_id INTEGER PRIMARY KEY, indexer_id INTEGER,'
             ' show_name TEXT, season NUMERIC DEFAULT -1, custom NUMERIC DEFAULT 0);',),
            ('CREATE TABLE scene_names (indexer_id INTEGER, name TEXT);',),
            ('CREATE TABLE network_timezones (network_name TEXT PRIMARY KEY, timezone TEXT);',),
            ('CREATE TABLE scene_exceptions_refresh (list TEXT PRIMARY KEY, last_refreshed INTEGER);',),
            ('CREATE TABLE db_version (db_version INTEGER);',),
            ('INSERT INTO db_version(db_version) VALUES (1);',),
        ]
        for query in queries:
            if len(query) == 1:
                self.connection.action(query[0])
            else:
                self.connection.action(query[0], query[1:])

    def _get_provider_tables(self):
        return self.connection.select(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT IN ('lastUpdate',"
            " 'lastSearch', 'scene_names', 'network_timezones', 'scene_exceptions_refresh',"
            " 'db_version', 'scene_exceptions', 'last_update');")

    def clear_provider_tables(self):
        for provider in self._get_provider_tables():
            self.connection.action("DELETE FROM '{name}';".format(name=provider['name']))

    def drop_provider_tables(self):
        for provider in self._get_provider_tables():
            self.connection.action("DROP TABLE '{name}';".format(name=provider['name']))

    def inc_major_version(self):
        major_version, minor_version = self.connection.version
        major_version += 1
        self.connection.action('UPDATE db_version SET db_version = ?;', [major_version])
        log.info('[CACHE-DB] Updated major version to: {}.{}', *self.connection.version)

        return self.connection.version


class AddSceneExceptions(InitialSchema):
    def test(self):
        return self.hasTable('scene_exceptions')

    def execute(self):
        self.connection.action(
            'CREATE TABLE scene_exceptions (exception_id INTEGER PRIMARY KEY, indexer_id INTEGER, show_name TEXT);')


class AddSceneNameCache(AddSceneExceptions):
    def test(self):
        return self.hasTable('scene_names')

    def execute(self):
        self.connection.action('CREATE TABLE scene_names (indexer_id INTEGER, name TEXT);')


class AddNetworkTimezones(AddSceneNameCache):
    def test(self):
        return self.hasTable('network_timezones')

    def execute(self):
        self.connection.action('CREATE TABLE network_timezones (network_name TEXT PRIMARY KEY, timezone TEXT);')


class AddLastSearch(AddNetworkTimezones):
    def test(self):
        return self.hasTable('lastSearch')

    def execute(self):
        self.connection.action('CREATE TABLE lastSearch (provider TEXT, time NUMERIC);')


class AddSceneExceptionsSeasons(AddLastSearch):
    def test(self):
        return self.hasColumn('scene_exceptions', 'season')

    def execute(self):
        self.addColumn('scene_exceptions', 'season', 'NUMERIC', -1)


class AddSceneExceptionsCustom(AddSceneExceptionsSeasons):  # pylint:disable=too-many-ancestors
    def test(self):
        return self.hasColumn('scene_exceptions', 'custom')

    def execute(self):
        self.addColumn('scene_exceptions', 'custom', 'NUMERIC', 0)


class AddSceneExceptionsRefresh(AddSceneExceptionsCustom):  # pylint:disable=too-many-ancestors
    def test(self):
        return self.hasTable('scene_exceptions_refresh')

    def execute(self):
        self.connection.action(
            'CREATE TABLE scene_exceptions_refresh (list TEXT PRIMARY KEY, last_refreshed INTEGER);')


class ConvertSceneExeptionsToIndexerScheme(AddSceneExceptionsRefresh):  # pylint:disable=too-many-ancestors
    def test(self):
        return self.hasColumn('scene_exceptions', 'indexer_id')

    def execute(self):
        self.connection.action('DROP TABLE IF EXISTS tmp_scene_exceptions;')
        self.connection.action('ALTER TABLE scene_exceptions RENAME TO tmp_scene_exceptions;')
        self.connection.action('CREATE TABLE scene_exceptions (exception_id INTEGER PRIMARY KEY, indexer_id INTEGER,'
                               ' show_name TEXT, season NUMERIC DEFAULT -1, custom NUMERIC DEFAULT 0);')
        self.connection.action('INSERT INTO scene_exceptions SELECT exception_id, tvdb_id as indexer_id, show_name,'
                               ' season, custom FROM tmp_scene_exceptions;')
        self.connection.action('DROP TABLE tmp_scene_exceptions;')


class ConvertSceneNamesToIndexerScheme(AddSceneExceptionsRefresh):  # pylint:disable=too-many-ancestors
    def test(self):
        return self.hasColumn('scene_names', 'indexer_id')

    def execute(self):
        self.connection.action('DROP TABLE IF EXISTS tmp_scene_names;')
        self.connection.action('ALTER TABLE scene_names RENAME TO tmp_scene_names;')
        self.connection.action('CREATE TABLE scene_names (indexer_id INTEGER, name TEXT);')
        self.connection.action('INSERT INTO scene_names SELECT * FROM tmp_scene_names;')
        self.connection.action('DROP TABLE tmp_scene_names;')


class RemoveIndexerUpdateSchema(ConvertSceneNamesToIndexerScheme):  # pylint:disable=too-many-ancestors
    def test(self):
        return not self.hasTable('indexer_update')

    def execute(self):
        self.connection.action('DROP TABLE indexer_update;')


class AddIndexerSceneExceptions(RemoveIndexerUpdateSchema):  # pylint:disable=too-many-ancestors
    def test(self):
        return self.hasColumn('scene_exceptions', 'indexer')

    def execute(self):
        self.connection.action('DROP TABLE IF EXISTS tmp_scene_exceptions;')
        self.connection.action('ALTER TABLE scene_exceptions RENAME TO tmp_scene_exceptions;')
        self.connection.action(
            'CREATE TABLE scene_exceptions (exception_id INTEGER PRIMARY KEY, indexer INTEGER, indexer_id INTEGER, '
            'show_name TEXT, season NUMERIC DEFAULT -1, custom NUMERIC DEFAULT 0);')
        self.connection.action(
            'INSERT INTO scene_exceptions SELECT exception_id, 1, indexer_id, show_name, season,'
            'custom FROM tmp_scene_exceptions;')
        self.connection.action('DROP TABLE tmp_scene_exceptions;')


class AddIndexerIds(AddIndexerSceneExceptions):
    """
    Add the indexer_id to all table's that have a series_id already.

    If the current series_id is named indexer_id or indexerid, use the field `indexer` for now.
    The namings should be renamed to: indexer_id + series_id in a later iteration.

    For example in this case, the table scene_names has used the fieldname `indexer_id` for the series id.
    This is unfortunate, but we can change that later.
    """

    def test(self):
        """Test if the table history already has the indexer_id."""
        return self.hasColumn('scene_names', 'indexer')

    def execute(self):
        # Add the indexer column to the scene_names table.
        self.addColumn('scene_names', 'indexer', 'NUMERIC', -1)

        # clean up null values from the scene_exceptions_table
        self.connection.action("DELETE FROM scene_exceptions WHERE indexer = '' OR indexer IS NULL;")


class ClearProviderTables(AddIndexerIds):
    """Clear provider cache items by deleting their tables."""

    def test(self):
        """Test if the version is at least 2."""
        return self.connection.version >= (2, None)

    def execute(self):
        utils.backup_database(self.connection.path, self.connection.version)

        self.clear_provider_tables()
        self.inc_major_version()


class AddProviderTablesIdentifier(ClearProviderTables):
    """Add new pk field `identifier`."""

    def test(self):
        """Test if the version is at least 3."""
        return self.connection.version >= (3, None)

    def execute(self):
        utils.backup_database(self.connection.path, self.connection.version)

        self.drop_provider_tables()
        self.inc_major_version()


class RemoveSceneExceptionsTable(AddProviderTablesIdentifier):
    """The scene_exceptions table has been moved to main.db."""

    def test(self):
        """Test if the version is at least 4."""
        return self.connection.version >= (4, None)

    def execute(self):
        self.connection.action('DROP TABLE IF EXISTS scene_exceptions;')
        self.inc_major_version()
