# coding=utf-8

from __future__ import unicode_literals

import logging

from medusa import db
from medusa.common import Quality
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
            ('CREATE TABLE failed (release TEXT, size NUMERIC, provider TEXT);',),
            ('CREATE TABLE history (date NUMERIC, size NUMERIC, release TEXT, provider TEXT,'
             ' old_status NUMERIC DEFAULT 0, showid NUMERIC DEFAULT -1, season NUMERIC DEFAULT -1,'
             ' episode NUMERIC DEFAULT -1);',),
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
        return self.hasColumn('history', 'old_status') and self.hasColumn('history', 'showid')

    def execute(self):
        self.addColumn('history', 'old_status', 'NUMERIC', Quality.NA)
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
        """Test if the table history already has the indexer_id."""
        return self.hasColumn('history', 'indexer_id')

    def execute(self):
        self.addColumn('history', 'indexer_id', 'NUMERIC', None)

        # get all the shows. Might need them.
        main_db_con = db.DBConnection()
        all_series = main_db_con.select('SELECT indexer, indexer_id FROM tv_shows')

        series_dict = {}
        # check for double
        for series in all_series:
            if series[b'indexer_id'] not in series_dict:
                series_dict[series[b'indexer_id']] = series[b'indexer']

        query = 'SELECT showid FROM history WHERE indexer_id is null'
        results = self.connection.select(query)
        if not results:
            return

        log.info(u'Starting to update the history table in the failed.db database')

        # Updating all rows, using the series id.
        for series_id in series_dict:
            # Update the value in the db.
            # Get the indexer (tvdb, tmdb, tvmaze etc, for this series_id).
            indexer_id = series_dict.get(series_id)
            if not indexer_id:
                continue

            self.connection.action(
                'UPDATE history SET indexer_id = ? WHERE showid = ?', [indexer_id, series_id]
            )

class UpdateHistoryTableQuality(AddIndexerIds):
    """
    Add the quality field and separate
    """
    def test(self):
        """Test if the table history already has the column quality."""
        return self.hasColumn('history', 'quality')

    def execute(self):
        """
        Add columns status and quality.

        Translate composite status/quality from old_status to the new fields.
        """
        log.info(u'Transforming old_status (composite) to separated fields status + quality.')
        self.connection.action('DROP TABLE IF EXISTS new_history;')

        self.connection.action('CREATE TABLE new_history (date NUMERIC, size NUMERIC, release TEXT, provider TEXT, '
                               'status NUMERIC DEFAULT -1, quality NUMERIC DEFAULT 0, showid NUMERIC DEFAULT -1, '
                               'season NUMERIC DEFAULT -1, episode NUMERIC DEFAULT -1, indexer_id NUMERIC)')

        self.connection.action('INSERT INTO new_history (date, size, release, provider, '
                               'status, quality, showid, season, episode, indexer_id) '
                               'SELECT date, size, release, provider, '
                               'old_status, -1, showid, season, episode, indexer_id '
                               'FROM history;')
        self.connection.action('DROP TABLE IF EXISTS history;')
        self.connection.action('ALTER TABLE new_history RENAME TO history;')
        self.connection.action('DROP TABLE IF EXISTS new_history;')

        sql_results = self.connection.select('SELECT status FROM history GROUP BY status')
        for result in sql_results:
            split = Quality.split_composite_status(result[b'status'])
            self.connection.action('UPDATE history SET status = ?, quality = ? WHERE status = ?',
                                   [split.status, split.quality, result[b'status']])
