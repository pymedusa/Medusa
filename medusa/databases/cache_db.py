# coding=utf-8

from medusa import db


# Add new migrations at the bottom of the list
# and subclass the previous migration.
class InitialSchema(db.SchemaUpgrade):
    def test(self):
        return self.hasTable("db_version")

    def execute(self):
        queries = [
            ("CREATE TABLE lastUpdate (provider TEXT, time NUMERIC);",),
            ("CREATE TABLE lastSearch (provider TEXT, time NUMERIC);",),
            ("CREATE TABLE scene_exceptions (exception_id INTEGER PRIMARY KEY, indexer_id INTEGER, show_name TEXT, season NUMERIC DEFAULT -1, custom NUMERIC DEFAULT 0);",),
            ("CREATE TABLE scene_names (indexer_id INTEGER, name TEXT);",),
            ("CREATE TABLE network_timezones (network_name TEXT PRIMARY KEY, timezone TEXT);",),
            ("CREATE TABLE scene_exceptions_refresh (list TEXT PRIMARY KEY, last_refreshed INTEGER);",),
            ("CREATE TABLE db_version (db_version INTEGER);",),
            ("INSERT INTO db_version(db_version) VALUES (1);",),
        ]
        for query in queries:
            if len(query) == 1:
                self.connection.action(query[0])
            else:
                self.connection.action(query[0], query[1:])


class AddSceneExceptions(InitialSchema):
    def test(self):
        return self.hasTable("scene_exceptions")

    def execute(self):
        self.connection.action(
            "CREATE TABLE scene_exceptions (exception_id INTEGER PRIMARY KEY, indexer_id INTEGER, show_name TEXT);")


class AddSceneNameCache(AddSceneExceptions):
    def test(self):
        return self.hasTable("scene_names")

    def execute(self):
        self.connection.action("CREATE TABLE scene_names (indexer_id INTEGER, name TEXT);")


class AddNetworkTimezones(AddSceneNameCache):
    def test(self):
        return self.hasTable("network_timezones")

    def execute(self):
        self.connection.action("CREATE TABLE network_timezones (network_name TEXT PRIMARY KEY, timezone TEXT);")


class AddLastSearch(AddNetworkTimezones):
    def test(self):
        return self.hasTable("lastSearch")

    def execute(self):
        self.connection.action("CREATE TABLE lastSearch (provider TEXT, time NUMERIC);")


class AddSceneExceptionsSeasons(AddLastSearch):
    def test(self):
        return self.hasColumn("scene_exceptions", "season")

    def execute(self):
        self.addColumn("scene_exceptions", "season", "NUMERIC", -1)


class AddSceneExceptionsCustom(AddSceneExceptionsSeasons):  # pylint:disable=too-many-ancestors
    def test(self):
        return self.hasColumn("scene_exceptions", "custom")

    def execute(self):
        self.addColumn("scene_exceptions", "custom", "NUMERIC", 0)


class AddSceneExceptionsRefresh(AddSceneExceptionsCustom):  # pylint:disable=too-many-ancestors
    def test(self):
        return self.hasTable("scene_exceptions_refresh")

    def execute(self):
        self.connection.action(
            "CREATE TABLE scene_exceptions_refresh (list TEXT PRIMARY KEY, last_refreshed INTEGER);")


class ConvertSceneExeptionsToIndexerScheme(AddSceneExceptionsRefresh):  # pylint:disable=too-many-ancestors
    def test(self):
        return self.hasColumn("scene_exceptions", "indexer_id")

    def execute(self):
        self.connection.action("DROP TABLE IF EXISTS tmp_scene_exceptions;")
        self.connection.action("ALTER TABLE scene_exceptions RENAME TO tmp_scene_exceptions;")
        self.connection.action("CREATE TABLE scene_exceptions (exception_id INTEGER PRIMARY KEY, indexer_id INTEGER, show_name TEXT, season NUMERIC DEFAULT -1, custom NUMERIC DEFAULT 0);")
        self.connection.action("INSERT INTO scene_exceptions SELECT exception_id, tvdb_id as indexer_id, show_name, season, custom FROM tmp_scene_exceptions;")
        self.connection.action("DROP TABLE tmp_scene_exceptions;")


class ConvertSceneNamesToIndexerScheme(AddSceneExceptionsRefresh):  # pylint:disable=too-many-ancestors
    def test(self):
        return self.hasColumn("scene_names", "indexer_id")

    def execute(self):
        self.connection.action("DROP TABLE IF EXISTS tmp_scene_names;")
        self.connection.action("ALTER TABLE scene_names RENAME TO tmp_scene_names;")
        self.connection.action("CREATE TABLE scene_names (indexer_id INTEGER, name TEXT);")
        self.connection.action("INSERT INTO scene_names SELECT * FROM tmp_scene_names;")
        self.connection.action("DROP TABLE tmp_scene_names;")


class RemoveIndexerUpdateSchema(ConvertSceneNamesToIndexerScheme):  # pylint:disable=too-many-ancestors
    def test(self):
        return not self.hasTable("indexer_update")

    def execute(self):
        self.connection.action("DROP TABLE indexer_update;")


class AddIndexerSceneExceptions(RemoveIndexerUpdateSchema):  # pylint:disable=too-many-ancestors
    def test(self):
        return self.hasColumn("scene_exceptions", "indexer")

    def execute(self):
        self.connection.action("DROP TABLE IF EXISTS tmp_scene_exceptions;")
        self.connection.action("ALTER TABLE scene_exceptions RENAME TO tmp_scene_exceptions;")
        self.connection.action(
            "CREATE TABLE scene_exceptions (exception_id INTEGER PRIMARY KEY, indexer INTEGER, indexer_id INTEGER, "
            "show_name TEXT, season NUMERIC DEFAULT -1, custom NUMERIC DEFAULT 0);")
        self.connection.action(
            "INSERT INTO scene_exceptions SELECT exception_id, 1, indexer_id, show_name, season,"
            "custom FROM tmp_scene_exceptions;")
        self.connection.action("DROP TABLE tmp_scene_exceptions;")


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
        self.connection.action("DELETE FROM scene_exceptions WHERE indexer = '' or indexer is null;")
