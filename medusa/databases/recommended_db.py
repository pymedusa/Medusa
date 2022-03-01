# coding=utf-8
"""Recommended.db cache module."""
from __future__ import unicode_literals

import logging

from medusa import db
from medusa.logger.adapters.style import BraceAdapter


log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class RecommendedSanityCheck(db.DBSanityCheck):
    """Sanity check class."""

    def check(self):
        """Check functions."""
        self.remove_imdb_tt()

    def remove_imdb_tt(self):
        """Remove tt from imdb id's."""
        log.debug(u'Remove shows added with an incorrect imdb id.')
        self.connection.action("DELETE FROM shows WHERE source = 10 AND series_id like '%tt%'")


# Add new migrations at the bottom of the list
# and subclass the previous migration.
class InitialSchema(db.SchemaUpgrade):
    """Recommended shows db class."""

    def test(self):
        """Test method."""
        return self.hasTable('db_version')

    def execute(self):
        """Create initial tables."""
        queries = [
            ("""CREATE TABLE shows (
                `recommended_show_id`	INTEGER PRIMARY KEY AUTOINCREMENT,
                `source`	INTEGER NOT NULL,
                `series_id`	INTEGER NOT NULL,
                `mapped_indexer`	INTEGER,
                `mapped_series_id`	INTEGER,
                `title`	TEXT NOT NULL,
                `rating`	NUMERIC,
                `votes`	INTEGER,
                `is_anime`	INTEGER DEFAULT 0,
                `image_href`	TEXT,
                `image_src`	TEXT,
                `subcat` TEXT,
                `added` DATETIME,
                `genres` TEXT,
                `plot` TEXT
            )""",),
            ('CREATE TABLE db_version (db_version INTEGER);',),
            ('INSERT INTO db_version(db_version) VALUES (1);',),
        ]
        for query in queries:
            if len(query) == 1:
                self.connection.action(query[0])
            else:
                self.connection.action(query[0], query[1:])

    def inc_major_version(self):
        """Increment major version of the db."""
        major_version, _ = self.connection.version
        major_version += 1
        self.connection.action('UPDATE db_version SET db_version = ?;', [major_version])
        log.info('[CACHE-DB] Updated major version to: {}.{}', *self.connection.version)

        return self.connection.version
