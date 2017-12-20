# coding=utf-8

from medusa import db
from medusa.common import Quality


# Add new migrations at the bottom of the list
# and subclass the previous migration.
class InitialSchema(db.SchemaUpgrade):
    def test(self):
        return self.hasTable('db_version')

    def execute(self):
        queries = [
            ('CREATE TABLE failed (release TEXT, size NUMERIC, provider TEXT);',),
            ('CREATE TABLE history (date NUMERIC, size NUMERIC, release TEXT, provider TEXT, old_status NUMERIC DEFAULT 0, showid NUMERIC DEFAULT -1, season NUMERIC DEFAULT -1, episode NUMERIC DEFAULT -1);',),
            ('CREATE TABLE db_version (db_version INTEGER);',),
            ('INSERT INTO db_version (db_version) VALUES (1);',),
        ]
        for query in queries:
            if len(query) == 1:
                self.connection.action(query[0])
            else:
                self.connection.action(query[0], query[1:])


class SizeAndProvider(InitialSchema):
    def test(self):
        return self.hasColumn('failed', 'size') and self.hasColumn('failed', 'provider')

    def execute(self):
        self.addColumn('failed', 'size', 'NUMERIC')
        self.addColumn('failed', 'provider', 'TEXT', '')


class History(SizeAndProvider):
    """Snatch history that can't be modified by the user."""

    def test(self):
        return self.hasTable('history')

    def execute(self):
        self.connection.action('CREATE TABLE history (date NUMERIC, ' +
                               'size NUMERIC, release TEXT, provider TEXT);')


class HistoryStatus(History):
    """Store episode status before snatch to revert to if necessary."""

    def test(self):
        return self.hasColumn('history', 'old_status')

    def execute(self):
        self.addColumn('history', 'old_status', 'NUMERIC', Quality.NONE)
        self.addColumn('history', 'showid', 'NUMERIC', '-1')
        self.addColumn('history', 'season', 'NUMERIC', '-1')
        self.addColumn('history', 'episode', 'NUMERIC', '-1')


class AddIndexerIds(HistoryStatus):
    """
    Add the indexer_id to all table's that have a series_id already.

    If the current series_id is named indexer_id or indexerid, use the field `indexer` for now.
    The namings should be renamed to: indexer_id + series_id in a later iteration.
    """

    def test(self):
        """
        Test if the table history already has the indexer_id.
        """
        return self.hasColumn('history', 'indexer_id')

    def execute(self):
        self.addColumn('history', 'indexer_id', 'NUMERIC', -1)
