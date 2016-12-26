# coding=utf-8
#
# Author: Nic Wolfe <nic@wolfeden.ca>
#
# This file is part of Medusa.
#
# Medusa is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Medusa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Medusa. If not, see <http://www.gnu.org/licenses/>.

import datetime
import os.path
import warnings

from six import iteritems
from .. import common, db, helpers, logger, subtitles
from ..helper.common import dateTimeFormat, episode_num
from ..name_parser.parser import NameParser

MIN_DB_VERSION = 40  # oldest db version we support migrating from
MAX_DB_VERSION = 44

# Used to check when checking for updates
CURRENT_MINOR_DB_VERSION = 3


class MainSanityCheck(db.DBSanityCheck):
    def check(self):
        self.fix_missing_table_indexes()
        self.fix_duplicate_shows()
        self.fix_duplicate_episodes()
        self.fix_orphan_episodes()
        self.fix_unaired_episodes()
        self.fix_tvrage_show_statues()
        self.fix_episode_statuses()
        self.fix_invalid_airdates()
        # self.fix_subtitles_codes()
        self.fix_show_nfo_lang()
        self.convert_tvrage_to_tvdb()
        self.convert_archived_to_compound()
        self.fix_subtitle_reference()
        self.clean_null_indexer_mappings()

    def clean_null_indexer_mappings(self):
        logger.log(u'Checking for null indexer mappings', logger.DEBUG)
        query = "SELECT * from indexer_mapping where mindexer_id = ''"

        sql_results = self.connection.select(query)
        if sql_results:
            logger.log(u"Found {0} null indexer mapping. Deleting...".format(len(sql_results)), logger.DEBUG)
            self.connection.action("DELETE FROM indexer_mapping WHERE mindexer_id = ''")

    def update_old_propers(self):
        logger.log(u'Checking for old propers without proper tags', logger.DEBUG)
        query = "SELECT resource FROM history WHERE (proper_tags is null or proper_tags is '') " + \
                "AND (action LIKE '%2' OR action LIKE '%9') AND " + \
                "(resource LIKE '%REPACK%' or resource LIKE '%PROPER%' or resource LIKE '%REAL%')"
        sql_results = self.connection.select(query)
        if sql_results:
            for sql_result in sql_results:
                proper_release = sql_result['resource']
                logger.log(u"Found old propers without proper tags: {0}".format(proper_release), logger.DEBUG)
                parse_result = NameParser()._parse_string(proper_release)
                if parse_result.proper_tags:
                    proper_tags = '|'.join(parse_result.proper_tags)
                    logger.log(u"Add proper tags '{0}' to '{1}'".format(proper_tags, proper_release), logger.DEBUG)
                    self.connection.action("UPDATE history SET proper_tags = ? WHERE resource = ?",
                                           [proper_tags, proper_release])

    def fix_subtitle_reference(self):
        logger.log(u'Checking for delete episodes with subtitle reference', logger.DEBUG)
        query = "SELECT episode_id, showid, location, subtitles, subtitles_searchcount, subtitles_lastsearch " + \
                "FROM tv_episodes WHERE location = '' AND subtitles is not ''"

        sql_results = self.connection.select(query)
        if sql_results:
            for sql_result in sql_results:
                logger.log(u"Found deleted episode id {0} from show ID {1} with subtitle data. Erasing reference...".format
                           (sql_result['episode_id'], sql_result['showid']), logger.WARNING)
                self.connection.action("UPDATE tv_episodes SET subtitles = '', subtitles_searchcount = 0, subtitles_lastsearch = '' " + \
                                       "WHERE episode_id = %i" % (sql_result['episode_id']))

    def convert_archived_to_compound(self):
        logger.log(u'Checking for archived episodes not qualified', logger.DEBUG)

        query = "SELECT episode_id, showid, e.status, e.location, season, episode, anime " + \
                "FROM tv_episodes e, tv_shows s WHERE e.status = %s AND e.showid = s.indexer_id" % common.ARCHIVED

        sql_results = self.connection.select(query)
        if sql_results:
            logger.log(u"Found %i shows with bare archived status, attempting automatic conversion..." % len(sql_results), logger.WARNING)

        for archivedEp in sql_results:
            fixedStatus = common.Quality.composite_status(common.ARCHIVED, common.Quality.UNKNOWN)
            existing = archivedEp['location'] and os.path.exists(archivedEp['location'])
            if existing:
                quality = common.Quality.name_quality(archivedEp['location'], archivedEp['anime'], extend=False)
                fixedStatus = common.Quality.composite_status(common.ARCHIVED, quality)

            logger.log(u'Changing status from {old_status} to {new_status} for {id}: {ep} at {location} (File {result})'.format
                       (old_status=common.statusStrings[common.ARCHIVED], new_status=common.statusStrings[fixedStatus],
                        id=archivedEp['showid'],
                        ep=episode_num(archivedEp['season'], archivedEp['episode']),
                        location=archivedEp['location'] if archivedEp['location'] else 'unknown location',
                        result=('NOT FOUND', 'EXISTS')[bool(existing)]))

            self.connection.action("UPDATE tv_episodes SET status = %i WHERE episode_id = %i" % (fixedStatus, archivedEp['episode_id']))

    def convert_tvrage_to_tvdb(self):
        logger.log(u"Checking for shows with tvrage id's, since tvrage is gone", logger.DEBUG)
        from ..indexers.indexer_config import INDEXER_TVRAGE
        from ..indexers.indexer_config import INDEXER_TVDBV2

        sql_results = self.connection.select("SELECT indexer_id, show_name, location FROM tv_shows WHERE indexer = %i" % INDEXER_TVRAGE)

        if sql_results:
            logger.log(u"Found %i shows with TVRage ID's, attempting automatic conversion..." % len(sql_results), logger.WARNING)

        for tvrage_show in sql_results:
            logger.log(u"Processing %s at %s" % (tvrage_show['show_name'], tvrage_show['location']))
            mapping = self.connection.select("SELECT mindexer_id FROM indexer_mapping WHERE indexer_id=%i AND indexer=%i AND mindexer=%i" %
                                             (tvrage_show['indexer_id'], INDEXER_TVRAGE, INDEXER_TVDBV2))

            if len(mapping) != 1:
                logger.log(u"Error mapping show from tvrage to tvdb for %s (%s), found %i mapping results. Cannot convert automatically!" %
                           (tvrage_show['show_name'], tvrage_show['location'], len(mapping)), logger.WARNING)
                logger.log(u"Removing the TVRage show and it's episodes from the DB, use 'addExistingShow'", logger.WARNING)
                self.connection.action("DELETE FROM tv_shows WHERE indexer_id = %i AND indexer = %i" % (tvrage_show['indexer_id'], INDEXER_TVRAGE))
                self.connection.action("DELETE FROM tv_episodes WHERE showid = %i" % tvrage_show['indexer_id'])
                continue

            logger.log(u'Checking if there is already a show with id:%i in the show list')
            duplicate = self.connection.select("SELECT show_name, indexer_id, location FROM tv_shows WHERE indexer_id = %i AND indexer = %i" % (mapping[0]['mindexer_id'], INDEXER_TVDBV2))
            if duplicate:
                logger.log(u'Found %s which has the same id as %s, cannot convert automatically so I am pausing %s' %
                           (duplicate[0]['show_name'], tvrage_show['show_name'], duplicate[0]['show_name']), logger.WARNING)
                self.connection.action("UPDATE tv_shows SET paused=1 WHERE indexer=%i AND indexer_id=%i" %
                                       (INDEXER_TVDBV2, duplicate[0]['indexer_id']))

                logger.log(u"Removing %s and it's episodes from the DB" % tvrage_show['show_name'], logger.WARNING)
                self.connection.action("DELETE FROM tv_shows WHERE indexer_id = %i AND indexer = %i" % (tvrage_show['indexer_id'], INDEXER_TVRAGE))
                self.connection.action("DELETE FROM tv_episodes WHERE showid = %i" % tvrage_show['indexer_id'])
                logger.log(u'Manually move the season folders from %s into %s, and delete %s before rescanning %s and unpausing it' %
                           (tvrage_show['location'], duplicate[0]['location'], tvrage_show['location'], duplicate[0]['show_name']), logger.WARNING)
                continue

            logger.log(u'Mapping %s to tvdb id %i' % (tvrage_show['show_name'], mapping[0]['mindexer_id']))

            self.connection.action(
                "UPDATE tv_shows SET indexer=%i, indexer_id=%i WHERE indexer_id=%i" %
                (INDEXER_TVDBV2, mapping[0]['mindexer_id'], tvrage_show['indexer_id'])
            )

            logger.log(u'Relinking episodes to show')
            self.connection.action(
                "UPDATE tv_episodes SET indexer=%i, showid=%i, indexerid=0 WHERE showid=%i" %
                (INDEXER_TVDBV2, mapping[0]['mindexer_id'], tvrage_show['indexer_id'])
            )

            logger.log(u'Please perform a full update on %s' % tvrage_show['show_name'], logger.WARNING)

    def fix_duplicate_shows(self, column='indexer_id'):

        sql_results = self.connection.select(
            "SELECT show_id, " + column + ", COUNT(" + column + ") as count FROM tv_shows GROUP BY " + column + " HAVING count > 1")

        for cur_duplicate in sql_results:

            logger.log(u"Duplicate show detected! " + column + ": " + str(cur_duplicate[column]) + u" count: " + str(
                cur_duplicate["count"]), logger.DEBUG)

            cur_dupe_results = self.connection.select(
                "SELECT show_id, " + column + " FROM tv_shows WHERE " + column + " = ? LIMIT ?",
                [cur_duplicate[column], int(cur_duplicate["count"]) - 1]
            )

            for cur_dupe_id in cur_dupe_results:
                logger.log(
                    u"Deleting duplicate show with " + column + ": " + str(cur_dupe_id[column]) + u" show_id: " + str(
                        cur_dupe_id["show_id"]))
                self.connection.action("DELETE FROM tv_shows WHERE show_id = ?", [cur_dupe_id["show_id"]])

    def fix_duplicate_episodes(self):

        sql_results = self.connection.select(
            "SELECT showid, season, episode, COUNT(showid) as count FROM tv_episodes GROUP BY showid, season, episode HAVING count > 1")

        for cur_duplicate in sql_results:

            logger.log(u"Duplicate episode detected! showid: " + str(cur_duplicate["showid"]) + u" season: " + str(
                cur_duplicate["season"]) + u" episode: " + str(cur_duplicate["episode"]) + u" count: " + str(
                cur_duplicate["count"]), logger.DEBUG)

            cur_dupe_results = self.connection.select(
                "SELECT episode_id FROM tv_episodes WHERE showid = ? AND season = ? and episode = ? ORDER BY episode_id DESC LIMIT ?",
                [cur_duplicate["showid"], cur_duplicate["season"], cur_duplicate["episode"],
                 int(cur_duplicate["count"]) - 1]
            )

            for cur_dupe_id in cur_dupe_results:
                logger.log(u"Deleting duplicate episode with episode_id: " + str(cur_dupe_id["episode_id"]))
                self.connection.action("DELETE FROM tv_episodes WHERE episode_id = ?", [cur_dupe_id["episode_id"]])

    def fix_orphan_episodes(self):

        sql_results = self.connection.select(
            "SELECT episode_id, showid, tv_shows.indexer_id FROM tv_episodes LEFT JOIN tv_shows ON tv_episodes.showid=tv_shows.indexer_id WHERE tv_shows.indexer_id is NULL")

        for cur_orphan in sql_results:
            logger.log(u"Orphan episode detected! episode_id: " + str(cur_orphan["episode_id"]) + " showid: " + str(
                cur_orphan["showid"]), logger.DEBUG)
            logger.log(u"Deleting orphan episode with episode_id: " + str(cur_orphan["episode_id"]))
            self.connection.action("DELETE FROM tv_episodes WHERE episode_id = ?", [cur_orphan["episode_id"]])

    def fix_missing_table_indexes(self):
        if not self.connection.select("PRAGMA index_info('idx_indexer_id')"):
            logger.log(u"Missing idx_indexer_id for TV Shows table detected!, fixing...")
            self.connection.action("CREATE UNIQUE INDEX idx_indexer_id ON tv_shows(indexer_id);")

        if not self.connection.select("PRAGMA index_info('idx_tv_episodes_showid_airdate')"):
            logger.log(u"Missing idx_tv_episodes_showid_airdate for TV Episodes table detected!, fixing...")
            self.connection.action("CREATE INDEX idx_tv_episodes_showid_airdate ON tv_episodes(showid, airdate);")

        if not self.connection.select("PRAGMA index_info('idx_showid')"):
            logger.log(u"Missing idx_showid for TV Episodes table detected!, fixing...")
            self.connection.action("CREATE INDEX idx_showid ON tv_episodes (showid);")

        if not self.connection.select("PRAGMA index_info('idx_status')"):
            logger.log(u"Missing idx_status for TV Episodes table detected!, fixing...")
            self.connection.action("CREATE INDEX idx_status ON tv_episodes (status, season, episode, airdate)")

        if not self.connection.select("PRAGMA index_info('idx_sta_epi_air')"):
            logger.log(u"Missing idx_sta_epi_air for TV Episodes table detected!, fixing...")
            self.connection.action("CREATE INDEX idx_sta_epi_air ON tv_episodes (status, episode, airdate)")

        if not self.connection.select("PRAGMA index_info('idx_sta_epi_sta_air')"):
            logger.log(u"Missing idx_sta_epi_sta_air for TV Episodes table detected!, fixing...")
            self.connection.action("CREATE INDEX idx_sta_epi_sta_air ON tv_episodes (season, episode, status, airdate)")

    def fix_unaired_episodes(self):

        curDate = datetime.date.today()

        sql_results = self.connection.select(
            "SELECT episode_id FROM tv_episodes WHERE (airdate > ? or airdate = 1) AND status in (?,?) AND season > 0",
            [curDate.toordinal(), common.SKIPPED, common.WANTED])

        for cur_unaired in sql_results:
            logger.log(u"Fixing unaired episode status for episode_id: %s" % cur_unaired["episode_id"])
            self.connection.action("UPDATE tv_episodes SET status = ? WHERE episode_id = ?",
                                   [common.UNAIRED, cur_unaired["episode_id"]])

    def fix_tvrage_show_statues(self):
        status_map = {
            'returning series': 'Continuing',
            'canceled/ended': 'Ended',
            'tbd/on the bubble': 'Continuing',
            'in development': 'Continuing',
            'new series': 'Continuing',
            'never aired': 'Ended',
            'final season': 'Continuing',
            'on hiatus': 'Continuing',
            'pilot ordered': 'Continuing',
            'pilot rejected': 'Ended',
            'canceled': 'Ended',
            'ended': 'Ended',
            '': 'Unknown',
        }

        for old_status, new_status in iteritems(status_map):
            self.connection.action("UPDATE tv_shows SET status = ? WHERE LOWER(status) = ?", [new_status, old_status])

    def fix_episode_statuses(self):
        sql_results = self.connection.select("SELECT episode_id, showid FROM tv_episodes WHERE status IS NULL")

        for cur_ep in sql_results:
            logger.log(u"MALFORMED episode status detected! episode_id: " + str(cur_ep["episode_id"]) + " showid: " + str(
                cur_ep["showid"]), logger.DEBUG)
            logger.log(u"Fixing malformed episode status with episode_id: " + str(cur_ep["episode_id"]))
            self.connection.action("UPDATE tv_episodes SET status = ? WHERE episode_id = ?",
                                   [common.UNKNOWN, cur_ep["episode_id"]])

    def fix_invalid_airdates(self):

        sql_results = self.connection.select(
            "SELECT episode_id, showid FROM tv_episodes WHERE airdate >= ? OR airdate < 1",
            [datetime.date.max.toordinal()])

        for bad_airdate in sql_results:
            logger.log(u"Bad episode airdate detected! episode_id: " + str(bad_airdate["episode_id"]) + " showid: " + str(
                bad_airdate["showid"]), logger.DEBUG)
            logger.log(u"Fixing bad episode airdate for episode_id: " + str(bad_airdate["episode_id"]))
            self.connection.action("UPDATE tv_episodes SET airdate = '1' WHERE episode_id = ?", [bad_airdate["episode_id"]])

    def fix_subtitles_codes(self):

        sql_results = self.connection.select(
            "SELECT subtitles, episode_id FROM tv_episodes WHERE subtitles != '' AND subtitles_lastsearch < ?;",
            [datetime.datetime(2015, 7, 15, 17, 20, 44, 326380).strftime(dateTimeFormat)]
        )

        if not sql_results:
            return

        for sql_result in sql_results:
            langs = []

            logger.log(u"Checking subtitle codes for episode_id: %s, codes: %s" %
                       (sql_result['episode_id'], sql_result['subtitles']), logger.DEBUG)

            for subcode in sql_result['subtitles'].split(','):
                if not len(subcode) == 3 or subcode not in subtitles.subtitle_code_filter():
                    logger.log(u"Fixing subtitle codes for episode_id: %s, invalid code: %s" %
                               (sql_result['episode_id'], subcode), logger.DEBUG)
                    continue

                langs.append(subcode)

            self.connection.action("UPDATE tv_episodes SET subtitles = ?, subtitles_lastsearch = ? WHERE episode_id = ?;",
                                   [','.join(langs), datetime.datetime.now().strftime(dateTimeFormat), sql_result['episode_id']])

    def fix_show_nfo_lang(self):
        self.connection.action("UPDATE tv_shows SET lang = '' WHERE lang = 0 or lang = '0'")


def backupDatabase(version):
    logger.log(u"Backing up database before upgrade")
    if not helpers.backup_versioned_file(db.dbFilename(), version):
        logger.log_error_and_exit(u"Database backup failed, abort upgrading database")
    else:
        logger.log(u"Proceeding with upgrade")


# ======================
# = Main DB Migrations =
# ======================
# Add new migrations at the bottom of the list; subclass the previous migration.

class InitialSchema(db.SchemaUpgrade):
    def test(self):
        return self.hasTable("db_version")

    def execute(self):
        if not self.hasTable("tv_shows") and not self.hasTable("db_version"):
            queries = [
                "CREATE TABLE db_version(db_version INTEGER);",
                "CREATE TABLE history(action NUMERIC, date NUMERIC, showid NUMERIC, season NUMERIC, episode NUMERIC, quality NUMERIC, resource TEXT, provider TEXT, version NUMERIC DEFAULT -1);",
                "CREATE TABLE imdb_info(indexer_id INTEGER PRIMARY KEY, imdb_id TEXT, title TEXT, year NUMERIC, akas TEXT, runtimes NUMERIC, genres TEXT, countries TEXT, country_codes TEXT, certificates TEXT, rating TEXT, votes INTEGER, last_update NUMERIC);",
                "CREATE TABLE info(last_backlog NUMERIC, last_indexer NUMERIC, last_proper_search NUMERIC);",
                "CREATE TABLE scene_numbering(indexer TEXT, indexer_id INTEGER, season INTEGER, episode INTEGER, scene_season INTEGER, scene_episode INTEGER, absolute_number NUMERIC, scene_absolute_number NUMERIC, PRIMARY KEY(indexer_id, season, episode));",
                "CREATE TABLE tv_shows(show_id INTEGER PRIMARY KEY, indexer_id NUMERIC, indexer NUMERIC, show_name TEXT, location TEXT, network TEXT, genre TEXT, classification TEXT, runtime NUMERIC, quality NUMERIC, airs TEXT, status TEXT, flatten_folders NUMERIC, paused NUMERIC, startyear NUMERIC, air_by_date NUMERIC, lang TEXT, subtitles NUMERIC, notify_list TEXT, imdb_id TEXT, last_update_indexer NUMERIC, dvdorder NUMERIC, archive_firstmatch NUMERIC, rls_require_words TEXT, rls_ignore_words TEXT, sports NUMERIC, anime NUMERIC, scene NUMERIC, default_ep_status NUMERIC DEFAULT -1);",
                "CREATE TABLE tv_episodes(episode_id INTEGER PRIMARY KEY, showid NUMERIC, indexerid NUMERIC, indexer TEXT, name TEXT, season NUMERIC, episode NUMERIC, description TEXT, airdate NUMERIC, hasnfo NUMERIC, hastbn NUMERIC, status NUMERIC, location TEXT, file_size NUMERIC, release_name TEXT, subtitles TEXT, subtitles_searchcount NUMERIC, subtitles_lastsearch TIMESTAMP, is_proper NUMERIC, scene_season NUMERIC, scene_episode NUMERIC, absolute_number NUMERIC, scene_absolute_number NUMERIC, version NUMERIC DEFAULT -1, release_group TEXT);",
                "CREATE TABLE blacklist (show_id INTEGER, range TEXT, keyword TEXT);",
                "CREATE TABLE whitelist (show_id INTEGER, range TEXT, keyword TEXT);",
                "CREATE TABLE xem_refresh (indexer TEXT, indexer_id INTEGER PRIMARY KEY, last_refreshed INTEGER);",
                "CREATE TABLE indexer_mapping (indexer_id INTEGER, indexer NUMERIC, mindexer_id INTEGER, mindexer NUMERIC, PRIMARY KEY (indexer_id, indexer));",
                "CREATE UNIQUE INDEX idx_indexer_id ON tv_shows(indexer_id);",
                "CREATE INDEX idx_showid ON tv_episodes(showid);",
                "CREATE INDEX idx_sta_epi_air ON tv_episodes(status, episode, airdate);",
                "CREATE INDEX idx_sta_epi_sta_air ON tv_episodes(season, episode, status, airdate);",
                "CREATE INDEX idx_status ON tv_episodes(status,season,episode,airdate);",
                "CREATE INDEX idx_tv_episodes_showid_airdate ON tv_episodes(showid, airdate);",
                "INSERT INTO db_version(db_version) VALUES (42);"
            ]
            for query in queries:
                self.connection.action(query)

        else:
            cur_db_version = self.checkDBVersion()

            if cur_db_version < MIN_DB_VERSION:
                logger.log_error_and_exit(u"Your database version (" +
                                          str(cur_db_version) + ") is too old to migrate from what this version of the application supports (" +
                                          str(MIN_DB_VERSION) + ").\n" +
                                          "Upgrade using a previous version (tag) build 496 to build 501 of the application first or remove database file to begin fresh."
                                          )

            if cur_db_version > MAX_DB_VERSION:
                logger.log_error_and_exit(u"Your database version (" +
                                          str(cur_db_version) + ") has been incremented past what this version of the application supports (" +
                                          str(MAX_DB_VERSION) + ").\n" +
                                          "If you have used other forks of the application, your database may be unusable due to their modifications."
                                          )


class AddVersionToTvEpisodes(InitialSchema):
    def test(self):
        return self.checkDBVersion() >= 40

    def execute(self):
        backupDatabase(self.checkDBVersion())

        logger.log(u"Adding column version to tv_episodes and history")
        self.addColumn("tv_episodes", "version", "NUMERIC", "-1")
        self.addColumn("tv_episodes", "release_group", "TEXT", "")
        self.addColumn("history", "version", "NUMERIC", "-1")

        self.incDBVersion()


class AddDefaultEpStatusToTvShows(AddVersionToTvEpisodes):
    def test(self):
        return self.checkDBVersion() >= 41

    def execute(self):
        backupDatabase(self.checkDBVersion())

        logger.log(u"Adding column default_ep_status to tv_shows")
        self.addColumn("tv_shows", "default_ep_status", "NUMERIC", "-1")

        self.incDBVersion()


class AlterTVShowsFieldTypes(AddDefaultEpStatusToTvShows):
    def test(self):
        return self.checkDBVersion() >= 42

    def execute(self):
        backupDatabase(self.checkDBVersion())

        logger.log(u"Converting column indexer and default_ep_status field types to numeric")
        self.connection.action("DROP TABLE IF EXISTS tmp_tv_shows")
        self.connection.action("ALTER TABLE tv_shows RENAME TO tmp_tv_shows")
        self.connection.action("CREATE TABLE tv_shows (show_id INTEGER PRIMARY KEY, indexer_id NUMERIC, indexer NUMERIC, show_name TEXT, location TEXT, network TEXT, genre TEXT, classification TEXT, runtime NUMERIC, quality NUMERIC, airs TEXT, status TEXT, flatten_folders NUMERIC, paused NUMERIC, startyear NUMERIC, air_by_date NUMERIC, lang TEXT, subtitles NUMERIC, notify_list TEXT, imdb_id TEXT, last_update_indexer NUMERIC, dvdorder NUMERIC, archive_firstmatch NUMERIC, rls_require_words TEXT, rls_ignore_words TEXT, sports NUMERIC, anime NUMERIC, scene NUMERIC, default_ep_status NUMERIC)")
        self.connection.action("INSERT INTO tv_shows SELECT * FROM tmp_tv_shows")
        self.connection.action("DROP TABLE tmp_tv_shows")

        self.incDBVersion()


class AddMinorVersion(AlterTVShowsFieldTypes):
    def test(self):
        return self.checkDBVersion() >= 42 and self.hasColumn(b'db_version', b'db_minor_version')

    def incDBVersion(self):
        warnings.warn("Deprecated: Use inc_major_version or inc_minor_version instead", DeprecationWarning)

    def inc_major_version(self):
        major_version, minor_version = self.connection.version
        major_version += 1
        minor_version = 0
        self.connection.action("UPDATE db_version SET db_version = ?, db_minor_version = ?", [major_version, minor_version])
        return self.connection.version

    def inc_minor_version(self):
        major_version, minor_version = self.connection.version
        minor_version += 1
        self.connection.action("UPDATE db_version SET db_version = ?, db_minor_version = ?", [major_version, minor_version])
        return self.connection.version

    def execute(self):
        backupDatabase(self.checkDBVersion())

        logger.log(u"Add minor version numbers to database")
        self.addColumn(b'db_version', b'db_minor_version')

        self.inc_minor_version()

        logger.log(u'Updated to: %d.%d' % self.connection.version)


class TestIncreaseMajorVersion(AddMinorVersion):
    """
    This tests the inc_major_version function

    This is done both to test the new update functionality
    and to maintain version parity with other forks.
    """
    def test(self):
        """
        Test if the version is < 44.0
        """
        return self.connection.version >= (44, 0)

    def execute(self):
        """
        Updates the version until 44.1
        """
        backupDatabase(self.connection.version)

        logger.log(u"Test major and minor version updates database")
        self.inc_major_version()
        self.inc_minor_version()

        logger.log(u'Updated to: %d.%d' % self.connection.version)


class AddProperTags(TestIncreaseMajorVersion):
    """Adds column proper_tags to history table."""

    def test(self):
        """
        Test if the version is < 44.2
        """
        return self.connection.version >= (44, 2)

    def execute(self):
        """
        Updates the version until 44.2 and adds proper_tags column
        """
        backupDatabase(self.connection.version)

        if not self.hasColumn('history', 'proper_tags'):
            logger.log(u'Adding column proper_tags to history')
            self.addColumn('history', 'proper_tags', 'TEXT', u'')

        MainSanityCheck(self.connection).update_old_propers()
        self.inc_minor_version()

        logger.log(u'Updated to: %d.%d' % self.connection.version)


class AddManualSearched(AddProperTags):
    """Adds columns manually_searched to history and tv_episodes table."""

    def test(self):
        """
        Test if the version is < 44.3
        """
        return self.connection.version >= (44, 3)

    def execute(self):
        """
        Updates the version until 44.3 and adds manually_searched columns
        """
        backupDatabase(self.connection.version)

        if not self.hasColumn('history', 'manually_searched'):
            logger.log(u'Adding column manually_searched to history')
            self.addColumn('history', 'manually_searched', 'NUMERIC', 0)

        if not self.hasColumn('tv_episodes', 'manually_searched'):
            logger.log(u'Adding column manually_searched to tv_episodes')
            self.addColumn('tv_episodes', 'manually_searched', 'NUMERIC', 0)

        MainSanityCheck(self.connection).update_old_propers()
        self.inc_minor_version()

        logger.log(u'Updated to: %d.%d' % self.connection.version)
