# coding=utf-8

from __future__ import unicode_literals

import datetime
import logging
import sys
import warnings

from medusa import common, db, subtitles
from medusa.databases import utils
from medusa.helper.common import dateTimeFormat
from medusa.indexers.config import STATUS_MAP
from medusa.logger.adapters.style import BraceAdapter
from medusa.name_parser.parser import NameParser

from six import iteritems

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())

MIN_DB_VERSION = 40  # oldest db version we support migrating from
MAX_DB_VERSION = 44


class MainSanityCheck(db.DBSanityCheck):
    def check(self):
        self.fix_missing_table_indexes()
        self.fix_duplicate_episodes()
        self.fix_orphan_episodes()
        self.fix_unaired_episodes()
        self.fix_indexer_show_statues()
        self.fix_episode_statuses()
        self.fix_invalid_airdates()
        #  self.fix_subtitles_codes()
        self.fix_show_nfo_lang()
        self.fix_subtitle_reference()
        self.clean_null_indexer_mappings()

    def clean_null_indexer_mappings(self):
        log.debug(u'Checking for null indexer mappings')
        query = "SELECT * from indexer_mapping WHERE mindexer_id = ''"

        sql_results = self.connection.select(query)
        if sql_results:
            log.debug(u'Found {0} null indexer mapping. Deleting...',
                      len(sql_results))
            self.connection.action("DELETE FROM indexer_mapping WHERE mindexer_id = ''")

    def update_old_propers(self):
        # This is called once when we create proper_tags columns
        log.debug(u'Checking for old propers without proper tags')
        query = "SELECT resource FROM history WHERE (proper_tags IS NULL OR proper_tags = '') " + \
                "AND (action LIKE '%2' OR action LIKE '%9') AND " + \
                "(resource LIKE '%REPACK%' OR resource LIKE '%PROPER%' OR resource LIKE '%REAL%')"
        sql_results = self.connection.select(query)
        if sql_results:
            for sql_result in sql_results:
                proper_release = sql_result['resource']
                log.debug(u'Found old propers without proper tags: {0}',
                          proper_release)
                parse_result = NameParser()._parse_string(proper_release)
                if parse_result.proper_tags:
                    proper_tags = '|'.join(parse_result.proper_tags)
                    log.debug(u'Add proper tags {0!r} to {1!r}',
                              proper_tags, proper_release)
                    self.connection.action('UPDATE history SET proper_tags = ? WHERE resource = ?',
                                           [proper_tags, proper_release])

    def fix_subtitle_reference(self):
        log.debug(u'Checking for delete episodes with subtitle reference')
        query = 'SELECT episode_id, showid, location, subtitles, subtitles_searchcount, subtitles_lastsearch ' + \
                "FROM tv_episodes WHERE location = '' AND subtitles is not ''"

        sql_results = self.connection.select(query)
        if sql_results:
            for sql_result in sql_results:
                log.warning(u'Found deleted episode id {0} from show ID {1}'
                            u' with subtitle data. Erasing reference...',
                            sql_result['episode_id'], sql_result['showid'])
                self.connection.action("UPDATE tv_episodes SET subtitles = '', "
                                       "subtitles_searchcount = 0, subtitles_lastsearch = '' "
                                       'WHERE episode_id = %i' % (sql_result['episode_id'])
                                       )

    def fix_duplicate_episodes(self):

        sql_results = self.connection.select(
            'SELECT indexer, showid, season, episode, COUNT(showid) as count FROM tv_episodes GROUP BY indexer,'
            ' showid, season, episode HAVING count > 1')

        for cur_duplicate in sql_results:

            log.debug('Duplicate episode detected! showid: {0!s}'
                      ' season: {1!s} episode: {2!s} count: {3!s}',
                      cur_duplicate['showid'], cur_duplicate['season'],
                      cur_duplicate['episode'], cur_duplicate['count'])
            cur_dupe_results = self.connection.select(
                'SELECT episode_id FROM tv_episodes WHERE indexer = ? AND showid = ? AND season = ? and episode = ? ORDER BY episode_id DESC LIMIT ?',
                [cur_duplicate['indexer'], cur_duplicate['showid'], cur_duplicate['season'], cur_duplicate['episode'],
                 int(cur_duplicate['count']) - 1]
            )

            for cur_dupe_id in cur_dupe_results:
                log.info('Deleting duplicate episode with episode_id: {0!s}', cur_dupe_id['episode_id'])
                self.connection.action('DELETE FROM tv_episodes WHERE episode_id = ?', [cur_dupe_id['episode_id']])

    def fix_orphan_episodes(self):

        sql_results = self.connection.select(
            'SELECT episode_id, showid, tv_shows.indexer_id FROM tv_episodes'
            ' LEFT JOIN tv_shows ON tv_episodes.showid=tv_shows.indexer_id'
            ' WHERE tv_shows.indexer_id IS NULL;')

        for cur_orphan in sql_results:
            log.debug(u'Orphan episode detected! episode_id: {0!s}'
                      u' showid: {1!s}', cur_orphan['episode_id'],
                      cur_orphan['showid'])
            log.info(u'Deleting orphan episode with episode_id: {0!s}',
                     cur_orphan['episode_id'])
            self.connection.action('DELETE FROM tv_episodes WHERE episode_id = ?', [cur_orphan['episode_id']])

    def fix_missing_table_indexes(self):
        if not self.connection.select("PRAGMA index_info('idx_tv_episodes_showid_airdate')"):
            log.info(u'Missing idx_tv_episodes_showid_airdate for TV Episodes table detected, fixing...')
            self.connection.action('CREATE INDEX idx_tv_episodes_showid_airdate ON tv_episodes(showid, airdate);')

        if not self.connection.select("PRAGMA index_info('idx_showid')"):
            log.info(u'Missing idx_showid for TV Episodes table detected, fixing...')
            self.connection.action('CREATE INDEX idx_showid ON tv_episodes (showid);')

        if not self.connection.select("PRAGMA index_info('idx_status')"):
            log.info(u'Missing idx_status for TV Episodes table detected, fixing...')
            self.connection.action('CREATE INDEX idx_status ON tv_episodes (status, quality, season, episode, airdate)')

        if not self.connection.select("PRAGMA index_info('idx_sta_epi_air')"):
            log.info(u'Missing idx_sta_epi_air for TV Episodes table detected, fixing...')
            self.connection.action('CREATE INDEX idx_sta_epi_air ON tv_episodes (status, quality, episode, airdate)')

        if not self.connection.select("PRAGMA index_info('idx_sta_epi_sta_air')"):
            log.info(u'Missing idx_sta_epi_sta_air for TV Episodes table detected, fixing...')
            self.connection.action('CREATE INDEX idx_sta_epi_sta_air ON tv_episodes (season, episode, status, quality, airdate)')

    def fix_unaired_episodes(self):

        cur_date = datetime.date.today()

        sql_results = self.connection.select(
            'SELECT episode_id FROM tv_episodes WHERE (airdate > ? OR airdate = 1) AND status in (?, ?) AND season > 0',
            [cur_date.toordinal(), common.SKIPPED, common.WANTED])

        for cur_unaired in sql_results:
            log.info(u'Fixing unaired episode status for episode_id: {0!s}',
                     cur_unaired['episode_id'])
            self.connection.action('UPDATE tv_episodes SET status = ? WHERE episode_id = ?',
                                   [common.UNAIRED, cur_unaired['episode_id']])

    def fix_indexer_show_statues(self):
        for new_status, mappings in iteritems(STATUS_MAP):
            for old_status in mappings:
                self.connection.action('UPDATE tv_shows SET status = ? WHERE LOWER(status) = ?', [new_status, old_status])

    def fix_episode_statuses(self):
        sql_results = self.connection.select('SELECT episode_id, showid FROM tv_episodes WHERE status IS NULL')

        for cur_ep in sql_results:
            log.debug(u'MALFORMED episode status detected! episode_id: {0!s}'
                      u' showid: {1!s}', cur_ep['episode_id'],
                      cur_ep['showid'])
            log.info(u'Fixing malformed episode status with'
                     u' episode_id: {0!s}', cur_ep['episode_id'])
            self.connection.action('UPDATE tv_episodes SET status = ? WHERE episode_id = ?',
                                   [common.UNSET, cur_ep['episode_id']])

    def fix_invalid_airdates(self):

        sql_results = self.connection.select(
            'SELECT episode_id, showid FROM tv_episodes WHERE airdate >= ? OR airdate < 1',
            [datetime.date.max.toordinal()])

        for bad_airdate in sql_results:
            log.debug(u'Bad episode airdate detected! episode_id: {0!s}'
                      u' showid: {1!s}', bad_airdate['episode_id'],
                      bad_airdate['showid'])
            log.info(u'Fixing bad episode airdate for episode_id: {0!s}',
                     bad_airdate['episode_id'])
            self.connection.action("UPDATE tv_episodes SET airdate = '1' WHERE episode_id = ?",
                                   [bad_airdate['episode_id']])

    def fix_subtitles_codes(self):

        sql_results = self.connection.select(
            "SELECT subtitles, episode_id FROM tv_episodes WHERE subtitles != '' AND subtitles_lastsearch < ?;",
            [datetime.datetime(2015, 7, 15, 17, 20, 44, 326380).strftime(dateTimeFormat)]
        )

        if not sql_results:
            return

        for sql_result in sql_results:
            langs = []

            log.debug(u'Checking subtitle codes for episode_id: {0!s},'
                      u' codes: {1!s}', sql_result['episode_id'],
                      sql_result['subtitles'])

            for subcode in sql_result['subtitles'].split(','):
                if not len(subcode) == 3 or subcode not in subtitles.subtitle_code_filter():
                    log.debug(u'Fixing subtitle codes for episode_id: {0!s},'
                              u' invalid code: {1!s}',
                              sql_result['episode_id'], subcode)
                    continue

                langs.append(subcode)

            self.connection.action('UPDATE tv_episodes SET subtitles = ?, subtitles_lastsearch = ? WHERE episode_id = ?;',
                                   [','.join(langs), datetime.datetime.now().strftime(dateTimeFormat), sql_result['episode_id']])

    def fix_show_nfo_lang(self):
        self.connection.action("UPDATE tv_shows SET lang = '' WHERE lang = 0 OR lang = '0';")


# ======================
# = Main DB Migrations =
# ======================
# Add new migrations at the bottom of the list; subclass the previous migration.

class InitialSchema(db.SchemaUpgrade):
    def test(self):
        return self.hasTable('db_version')

    def execute(self):
        if not self.hasTable('tv_shows') and not self.hasTable('db_version'):
            queries = [
                'CREATE TABLE db_version(db_version INTEGER);',
                'CREATE TABLE history(action NUMERIC, date NUMERIC, showid NUMERIC, season NUMERIC, episode NUMERIC, quality NUMERIC, resource TEXT, provider TEXT, version NUMERIC DEFAULT -1);',
                'CREATE TABLE imdb_info(indexer_id INTEGER PRIMARY KEY, imdb_id TEXT, title TEXT, year NUMERIC, akas TEXT, runtimes NUMERIC, genres TEXT, countries TEXT, country_codes TEXT, certificates TEXT, rating TEXT, votes INTEGER, last_update NUMERIC, plot TEXT);',
                'CREATE TABLE info(last_backlog NUMERIC, last_indexer NUMERIC, last_proper_search NUMERIC);',
                'CREATE TABLE scene_numbering(indexer TEXT, indexer_id INTEGER, season INTEGER, episode INTEGER, scene_season INTEGER, scene_episode INTEGER, absolute_number NUMERIC, scene_absolute_number NUMERIC, PRIMARY KEY(indexer_id, season, episode));',
                'CREATE TABLE tv_shows(show_id INTEGER PRIMARY KEY, indexer_id NUMERIC, indexer NUMERIC, show_name TEXT, location TEXT, network TEXT, genre TEXT, classification TEXT, runtime NUMERIC, quality NUMERIC, airs TEXT, status TEXT, flatten_folders NUMERIC, paused NUMERIC, startyear NUMERIC, air_by_date NUMERIC, lang TEXT, subtitles NUMERIC, notify_list TEXT, imdb_id TEXT, last_update_indexer NUMERIC, dvdorder NUMERIC, archive_firstmatch NUMERIC, rls_require_words TEXT, rls_ignore_words TEXT, sports NUMERIC, anime NUMERIC, scene NUMERIC, default_ep_status NUMERIC DEFAULT -1);',
                'CREATE TABLE tv_episodes(episode_id INTEGER PRIMARY KEY, showid NUMERIC, indexerid INTEGER, indexer INTEGER, name TEXT, season NUMERIC, episode NUMERIC, description TEXT, airdate NUMERIC, hasnfo NUMERIC, hastbn NUMERIC, status NUMERIC, location TEXT, file_size NUMERIC, release_name TEXT, subtitles TEXT, subtitles_searchcount NUMERIC, subtitles_lastsearch TIMESTAMP, is_proper NUMERIC, scene_season NUMERIC, scene_episode NUMERIC, absolute_number NUMERIC, scene_absolute_number NUMERIC, version NUMERIC DEFAULT -1, release_group TEXT);',
                'CREATE TABLE blacklist (show_id INTEGER, range TEXT, keyword TEXT);',
                'CREATE TABLE whitelist (show_id INTEGER, range TEXT, keyword TEXT);',
                'CREATE TABLE xem_refresh (indexer TEXT, indexer_id INTEGER PRIMARY KEY, last_refreshed INTEGER);',
                'CREATE TABLE indexer_mapping (indexer_id INTEGER, indexer INTEGER, mindexer_id INTEGER, mindexer INTEGER, PRIMARY KEY (indexer_id, indexer, mindexer));',
                'CREATE UNIQUE INDEX idx_indexer_id ON tv_shows(indexer_id);',
                'CREATE INDEX idx_showid ON tv_episodes(showid);',
                'CREATE INDEX idx_sta_epi_air ON tv_episodes(status, episode, airdate);',
                'CREATE INDEX idx_sta_epi_sta_air ON tv_episodes(season, episode, status, airdate);',
                'CREATE INDEX idx_status ON tv_episodes(status,season,episode,airdate);',
                'CREATE INDEX idx_tv_episodes_showid_airdate ON tv_episodes(showid, airdate);',
                'INSERT INTO db_version(db_version) VALUES (42);'
            ]
            for query in queries:
                self.connection.action(query)

        else:
            cur_db_version = self.checkMajorDBVersion()

            if cur_db_version < MIN_DB_VERSION:
                log.error(
                    u'Your database version ({0!s}) is too old to migrate'
                    u' from what this version of the application'
                    u' supports ({1!s}).\n'
                    u'Upgrade using a previous version (tag) build 496 to'
                    u' build 501 of the application first or remove database'
                    u' file to begin fresh.', cur_db_version, MIN_DB_VERSION,
                )
                sys.exit(1)

            if cur_db_version > MAX_DB_VERSION:
                log.error(
                    u'Your database version ({0!s}) has been incremented past'
                    u' what this version of the application supports'
                    u' ({1!s}).\n'
                    u'If you have used other forks of the application, your'
                    u' database may be unusable due to their modifications.',
                    cur_db_version, MAX_DB_VERSION,
                )


class AddVersionToTvEpisodes(InitialSchema):
    def test(self):
        return self.checkMajorDBVersion() >= 40

    def execute(self):
        utils.backup_database(self.connection.path, self.checkMajorDBVersion())

        log.info(u'Adding column version to tv_episodes and history')
        self.addColumn('tv_episodes', 'version', 'NUMERIC', '-1')
        self.addColumn('tv_episodes', 'release_group', 'TEXT', '')
        self.addColumn('history', 'version', 'NUMERIC', '-1')

        self.incMajorDBVersion()


class AddDefaultEpStatusToTvShows(AddVersionToTvEpisodes):
    def test(self):
        return self.checkMajorDBVersion() >= 41

    def execute(self):
        utils.backup_database(self.connection.path, self.checkMajorDBVersion())

        log.info(u'Adding column default_ep_status to tv_shows')
        self.addColumn('tv_shows', 'default_ep_status', 'NUMERIC', '-1')

        self.incMajorDBVersion()


class AlterTVShowsFieldTypes(AddDefaultEpStatusToTvShows):
    def test(self):
        return self.checkMajorDBVersion() >= 42

    def execute(self):
        utils.backup_database(self.connection.path, self.checkMajorDBVersion())

        log.info(u'Converting column indexer and default_ep_status field types to numeric')
        self.connection.action('DROP TABLE IF EXISTS tmp_tv_shows')
        self.connection.action('ALTER TABLE tv_shows RENAME TO tmp_tv_shows')
        self.connection.action('CREATE TABLE tv_shows (show_id INTEGER PRIMARY KEY, indexer_id NUMERIC,'
                               ' indexer NUMERIC, show_name TEXT, location TEXT, network TEXT, genre TEXT,'
                               ' classification TEXT, runtime NUMERIC, quality NUMERIC, airs TEXT, status TEXT,'
                               ' flatten_folders NUMERIC, paused NUMERIC, startyear NUMERIC, air_by_date NUMERIC,'
                               ' lang TEXT, subtitles NUMERIC, notify_list TEXT, imdb_id TEXT,'
                               ' last_update_indexer NUMERIC, dvdorder NUMERIC, archive_firstmatch NUMERIC,'
                               ' rls_require_words TEXT, rls_ignore_words TEXT, sports NUMERIC, anime NUMERIC,'
                               ' scene NUMERIC, default_ep_status NUMERIC)')
        self.connection.action('INSERT INTO tv_shows SELECT * FROM tmp_tv_shows')
        self.connection.action('DROP TABLE tmp_tv_shows')

        self.incMajorDBVersion()


class AddMinorVersion(AlterTVShowsFieldTypes):
    def test(self):
        return self.checkMajorDBVersion() >= 43 and self.hasColumn('db_version', 'db_minor_version')

    def incMajorDBVersion(self):
        warnings.warn('Deprecated: Use inc_major_version or inc_minor_version instead', DeprecationWarning)

    def inc_major_version(self):
        major_version, minor_version = self.connection.version
        major_version += 1
        minor_version = 0
        self.connection.action('UPDATE db_version SET db_version = ?, db_minor_version = ?;',
                               [major_version, minor_version])
        log.info(u'[MAIN-DB] Updated major version to: {}.{}', *self.connection.version)

        return self.connection.version

    def inc_minor_version(self):
        major_version, minor_version = self.connection.version
        minor_version += 1
        self.connection.action('UPDATE db_version SET db_version = ?, db_minor_version = ?;',
                               [major_version, minor_version])
        log.info(u'[MAIN-DB] Updated minor version to: {}.{}', *self.connection.version)

        return self.connection.version

    def execute(self):
        utils.backup_database(self.connection.path, self.checkMajorDBVersion())

        log.info(u'Add minor version numbers to database')
        self.addColumn('db_version', 'db_minor_version')

        self.inc_major_version()
        self.inc_minor_version()


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
        utils.backup_database(self.connection.path, self.connection.version)

        log.info(u'Test major and minor version updates database')
        self.inc_major_version()
        self.inc_minor_version()


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
        utils.backup_database(self.connection.path, self.connection.version)

        if not self.hasColumn('history', 'proper_tags'):
            log.info(u'Adding column proper_tags to history')
            self.addColumn('history', 'proper_tags', 'TEXT', u'')

        # Call the update old propers once
        MainSanityCheck(self.connection).update_old_propers()
        self.inc_minor_version()


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
        utils.backup_database(self.connection.path, self.connection.version)

        if not self.hasColumn('history', 'manually_searched'):
            log.info(u'Adding column manually_searched to history')
            self.addColumn('history', 'manually_searched', 'NUMERIC', 0)

        if not self.hasColumn('tv_episodes', 'manually_searched'):
            log.info(u'Adding column manually_searched to tv_episodes')
            self.addColumn('tv_episodes', 'manually_searched', 'NUMERIC', 0)

        MainSanityCheck(self.connection).update_old_propers()
        self.inc_minor_version()


class AddInfoHash(AddManualSearched):
    """Adds column info_hash to history table."""

    def test(self):
        """
        Test if the version is at least 44.4
        """
        return self.connection.version >= (44, 4)

    def execute(self):
        utils.backup_database(self.connection.path, self.connection.version)

        log.info(u'Adding column info_hash in history')
        if not self.hasColumn('history', 'info_hash'):
            self.addColumn('history', 'info_hash', 'TEXT', None)

        self.inc_minor_version()


class AddPlot(AddInfoHash):
    """Adds column plot to imdb_info table."""

    def test(self):
        """
        Test if the version is at least 44.5
        """
        return self.connection.version >= (44, 5)

    def execute(self):
        utils.backup_database(self.connection.path, self.connection.version)

        log.info(u'Adding column plot in imdb_info')
        if not self.hasColumn('imdb_info', 'plot'):
            self.addColumn('imdb_info', 'plot', 'TEXT', None)

        log.info(u'Adding column plot in tv_show')
        if not self.hasColumn('tv_shows', 'plot'):
            self.addColumn('tv_shows', 'plot', 'TEXT', None)

        self.inc_minor_version()


class AddResourceSize(AddPlot):
    """Adds column size to history table."""

    def test(self):
        """
        Test if the version is at least 44.6
        """
        return self.connection.version >= (44, 6)

    def execute(self):
        utils.backup_database(self.connection.path, self.connection.version)

        log.info(u'Adding column size in history')
        if not self.hasColumn('history', 'size'):
            self.addColumn('history', 'size', 'NUMERIC', -1)

        self.inc_minor_version()


class AddPKIndexerMapping(AddResourceSize):
    """Add PK to mindexer column in indexer_mapping table."""

    def test(self):
        """Test if the version is at least 44.7"""
        return self.connection.version >= (44, 7)

    def execute(self):
        utils.backup_database(self.connection.path, self.connection.version)

        log.info(u'Adding PK to mindexer column in indexer_mapping table')
        self.connection.action('DROP TABLE IF EXISTS new_indexer_mapping;')
        self.connection.action('CREATE TABLE IF NOT EXISTS new_indexer_mapping'
                               '(indexer_id INTEGER, indexer INTEGER, mindexer_id INTEGER, mindexer INTEGER,'
                               'PRIMARY KEY (indexer_id, indexer, mindexer));')
        self.connection.action('INSERT INTO new_indexer_mapping SELECT * FROM indexer_mapping;')
        self.connection.action('DROP TABLE IF EXISTS indexer_mapping;')
        self.connection.action('ALTER TABLE new_indexer_mapping RENAME TO indexer_mapping;')
        self.connection.action('DROP TABLE IF EXISTS new_indexer_mapping;')

        self.inc_minor_version()


class AddIndexerInteger(AddPKIndexerMapping):
    """Make indexer as INTEGER in tv_episodes table."""

    def test(self):
        """Test if the version is at least 44.8"""
        return self.connection.version >= (44, 8)

    def execute(self):
        utils.backup_database(self.connection.path, self.connection.version)

        log.info(u'Make indexer and indexer_id as INTEGER in tv_episodes table')
        self.connection.action('DROP TABLE IF EXISTS new_tv_episodes;')
        self.connection.action(
            'CREATE TABLE new_tv_episodes '
            '(episode_id INTEGER PRIMARY KEY, showid NUMERIC, indexerid INTEGER, indexer INTEGER, name TEXT, '
            'season NUMERIC, episode NUMERIC, description TEXT, airdate NUMERIC, hasnfo NUMERIC, hastbn NUMERIC, '
            'status NUMERIC, location TEXT, file_size NUMERIC, release_name TEXT, subtitles TEXT, '
            'subtitles_searchcount NUMERIC, subtitles_lastsearch TIMESTAMP, is_proper NUMERIC, '
            'scene_season NUMERIC, scene_episode NUMERIC, absolute_number NUMERIC, scene_absolute_number NUMERIC, '
            'version NUMERIC DEFAULT -1, release_group TEXT, manually_searched NUMERIC);')
        self.connection.action('INSERT INTO new_tv_episodes SELECT * FROM tv_episodes;')
        self.connection.action('DROP TABLE IF EXISTS tv_episodes;')
        self.connection.action('ALTER TABLE new_tv_episodes RENAME TO tv_episodes;')
        self.connection.action('DROP TABLE IF EXISTS new_tv_episodoes;')

        self.inc_minor_version()


class AddIndexerIds(AddIndexerInteger):
    """
    Add the indexer_id to all table's that have a series_id already.

    If the current series_id is named indexer_id or indexerid, use the field `indexer` for now.
    The namings should be renamed to: indexer_id + series_id in a later iteration.
    """

    def test(self):
        """
        Test if the version is at least 44.9
        """
        return self.connection.version >= (44, 9)

    def execute(self):
        utils.backup_database(self.connection.path, self.connection.version)

        log.info(u'Adding column indexer_id in history')
        if not self.hasColumn('history', 'indexer_id'):
            self.addColumn('history', 'indexer_id', 'NUMERIC', None)

        log.info(u'Adding column indexer_id in blacklist')
        if not self.hasColumn('blacklist', 'indexer_id'):
            self.addColumn('blacklist', 'indexer_id', 'NUMERIC', None)

        log.info(u'Adding column indexer_id in whitelist')
        if not self.hasColumn('whitelist', 'indexer_id'):
            self.addColumn('whitelist', 'indexer_id', 'NUMERIC', None)

        log.info(u'Adding column indexer in imdb_info')
        if not self.hasColumn('imdb_info', 'indexer'):
            self.addColumn('imdb_info', 'indexer', 'NUMERIC', None)

        log.info(u'Dropping the unique index on idx_indexer_id')
        self.connection.action('DROP INDEX IF EXISTS idx_indexer_id')

        # Add the column imdb_info_id with PK
        self.connection.action('DROP TABLE IF EXISTS tmp_imdb_info')
        self.connection.action('ALTER TABLE imdb_info RENAME TO tmp_imdb_info')
        self.connection.action(
            'CREATE TABLE imdb_info(imdb_info_id INTEGER PRIMARY KEY, indexer NUMERIC, indexer_id INTEGER, imdb_id TEXT, '
            'title TEXT, year NUMERIC, akas TEXT, runtimes NUMERIC, genres TEXT, countries TEXT, country_codes TEXT, '
            'certificates TEXT, rating TEXT, votes INTEGER, last_update NUMERIC, plot TEXT)'
        )
        self.connection.action('INSERT INTO imdb_info (indexer, indexer_id, imdb_id, title, year, akas, runtimes, '
                               'genres, countries, country_codes, certificates, rating, votes, last_update, plot) '
                               'SELECT indexer, indexer_id, imdb_id, title, year, akas, runtimes, '
                               'genres, countries, country_codes, certificates, rating, votes, last_update, plot FROM tmp_imdb_info')
        self.connection.action('DROP TABLE tmp_imdb_info')

        # recreate the xem_refresh table, without the primary key on indexer_id. Add the column xem_refresh_id.
        log.info(u'Dropping the primary key on the table xem_refresh')

        self.connection.action('DROP TABLE IF EXISTS tmp_xem_refresh')
        self.connection.action('ALTER TABLE xem_refresh RENAME TO tmp_xem_refresh')
        self.connection.action(
            'CREATE TABLE xem_refresh (xem_refresh_id INTEGER PRIMARY KEY, indexer INTEGER, indexer_id INTEGER, last_refreshed INTEGER)'
        )
        self.connection.action('INSERT INTO xem_refresh (indexer, indexer_id, last_refreshed) '
                               'SELECT CAST(indexer AS INTEGER), indexer_id, last_refreshed FROM tmp_xem_refresh')
        self.connection.action('DROP TABLE tmp_xem_refresh')

        series_dict = {}

        def create_series_dict():
            """Create a dict with series[indexer]: series_id."""
            if not series_dict:

                # get all the shows. Might need them.
                all_series = self.connection.select('SELECT indexer, indexer_id FROM tv_shows')

                # check for double
                for series in all_series:
                    if series['indexer_id'] not in series_dict:
                        series_dict[series['indexer_id']] = series['indexer']
                    else:
                        log.warning(u'Found a duplicate series id for indexer_id: {0} and indexer: {1}',
                                    series['indexer_id'], series['indexer'])

        # Check if it's required for the main.db tables.
        for migration_config in (('blacklist', 'show_id', 'indexer_id'),
                                 ('whitelist', 'show_id', 'indexer_id'),
                                 ('history', 'showid', 'indexer_id'),
                                 ('imdb_info', 'indexer_id', 'indexer')):

            log.info(
                u'Updating indexer field on table {0}. Using the series id to match with field {1}',
                migration_config[0], migration_config[1]
            )

            query = 'SELECT {config[1]} FROM {config[0]} WHERE {config[2]} IS NULL'.format(config=migration_config)
            results = self.connection.select(query)
            if not results:
                continue

            create_series_dict()

            # Updating all rows, using the series id.
            for series_id in series_dict:
                # Update the value in the db.
                # Get the indexer (tvdb, tmdb, tvmaze etc, for this series_id).
                indexer_id = series_dict.get(series_id)
                if not indexer_id:
                    continue

                self.connection.action(
                    'UPDATE {config[0]} SET {config[2]} = ? WHERE {config[1]} = ?'.format(config=migration_config),
                    [indexer_id, series_id])

        self.inc_minor_version()

        # Flag the image migration.
        from medusa import app
        app.MIGRATE_IMAGES = True


class AddSeparatedStatusQualityFields(AddIndexerIds):
    """Add new separated status and quality fields."""

    def test(self):
        """Test if the version is at least 44.10"""
        return self.connection.version >= (44, 10)

    def execute(self):
        utils.backup_database(self.connection.path, self.connection.version)

        log.info(u'Adding new quality field in the tv_episodes table')
        self.connection.action('DROP TABLE IF EXISTS tmp_tv_episodes;')
        self.connection.action('ALTER TABLE tv_episodes RENAME TO tmp_tv_episodes;')

        self.connection.action(
            'CREATE TABLE IF NOT EXISTS tv_episodes '
            '(episode_id INTEGER PRIMARY KEY, showid NUMERIC, indexerid INTEGER, indexer INTEGER, '
            'name TEXT, season NUMERIC, episode NUMERIC, description TEXT, airdate NUMERIC, hasnfo NUMERIC, '
            'hastbn NUMERIC, status NUMERIC, quality NUMERIC, location TEXT, file_size NUMERIC, release_name TEXT, '
            'subtitles TEXT, subtitles_searchcount NUMERIC, subtitles_lastsearch TIMESTAMP, '
            'is_proper NUMERIC, scene_season NUMERIC, scene_episode NUMERIC, absolute_number NUMERIC, '
            'scene_absolute_number NUMERIC, version NUMERIC DEFAULT -1, release_group TEXT, manually_searched NUMERIC);'
        )

        # Re-insert old values, setting the new quality column to the invalid value of -1
        self.connection.action(
            'INSERT INTO tv_episodes '
            '(showid, indexerid, indexer, name, season, episode, description, airdate, hasnfo, '
            'hastbn, status, quality, location, file_size, release_name, subtitles, subtitles_searchcount, '
            'subtitles_lastsearch, is_proper, scene_season, scene_episode, absolute_number, scene_absolute_number, '
            'version, release_group, manually_searched) '
            'SELECT showid, indexerid, indexer, '
            'name, season, episode, description, airdate, hasnfo, '
            'hastbn, status, -1 AS quality, location, file_size, release_name, '
            'subtitles, subtitles_searchcount, subtitles_lastsearch, '
            'is_proper, scene_season, scene_episode, absolute_number, '
            'scene_absolute_number, version, release_group, manually_searched '
            'FROM tmp_tv_episodes;'
        )

        # We have all that we need, drop the old table
        for index in ['idx_sta_epi_air', 'idx_sta_epi_sta_air', 'idx_status']:
            log.info(u'Dropping the index on {0}', index)
            self.connection.action('DROP INDEX IF EXISTS {index};'.format(index=index))
        self.connection.action('DROP TABLE IF EXISTS tmp_tv_episodes;')

        log.info(u'Splitting the composite status into status and quality')
        sql_results = self.connection.select('SELECT status from tv_episodes GROUP BY status;')
        for episode in sql_results:
            composite_status = episode['status']
            status, quality = utils.split_composite_status(composite_status)
            self.connection.action('UPDATE tv_episodes SET status = ?, quality = ? WHERE status = ?;',
                                   [status, quality, composite_status])

        # Update `history` table: Remove the quality value from `action`
        log.info(u'Removing the quality from the action field, as this is a composite status')
        sql_results = self.connection.select('SELECT action FROM history GROUP BY action;')
        for item in sql_results:
            composite_action = item['action']
            status, quality = utils.split_composite_status(composite_action)
            self.connection.action('UPDATE history SET action = ? WHERE action = ?;',
                                   [status, composite_action])

        self.inc_minor_version()


class ShiftQualities(AddSeparatedStatusQualityFields):
    """Shift all qualities one place to the left."""

    def test(self):
        """Test if the version is at least 44.11"""
        return self.connection.version >= (44, 11)

    def execute(self):
        utils.backup_database(self.connection.path, self.connection.version)

        self.shift_tv_qualities()
        self.shift_episode_qualities()
        self.shift_history_qualities()
        self.inc_minor_version()

    def shift_tv_qualities(self):
        """
        Shift all qualities << 1.

        This makes it possible to set UNKNOWN as 1, making it the lowest quality.
        """
        log.info('Shift qualities in tv_shows one place to the left.')
        sql_results = self.connection.select('SELECT quality FROM tv_shows GROUP BY quality ORDER BY quality DESC;')
        for result in sql_results:
            quality = result['quality']
            new_quality = quality << 1

            # UNKNOWN quality value is 65536 (1 << 16) instead of 32768 (1 << 15) after the shift
            # Qualities in the tv_shows table have the combined values of allowed and preferred qualities.
            # Preferred quality couldn't contain UNKNOWN
            if new_quality & 65536 > 0:  # If contains UNKNOWN allowed quality
                new_quality -= 65536  # Remove it
                new_quality |= common.Quality.UNKNOWN  # Then re-add it using the correct value

            self.connection.action(
                'UPDATE tv_shows SET quality = ? WHERE quality = ?;',
                [new_quality, quality]
            )

    def shift_episode_qualities(self):
        """
        Shift all qualities << 1.

        This makes it possible to set UNKNOWN as 1, making it the lowest quality.
        """
        log.info('Shift qualities in tv_episodes one place to the left.')
        sql_results = self.connection.select('SELECT quality FROM tv_episodes WHERE quality != 0 GROUP BY quality'
                                             ' ORDER BY quality DESC;')
        for result in sql_results:
            quality = result['quality']
            new_quality = quality << 1

            if quality == 32768:  # Old UNKNOWN quality (1 << 15)
                new_quality = common.Quality.UNKNOWN
            else:
                new_quality = quality << 1

            self.connection.action(
                'UPDATE tv_episodes SET quality = ? WHERE quality = ?;',
                [new_quality, quality]
            )

    def shift_history_qualities(self):
        """
        Shift all qualities << 1.

        This makes it possible to set UNKNOWN as 1, making it the lowest quality.
        """
        log.info('Shift qualities in history one place to the left.')
        sql_results = self.connection.select('SELECT quality FROM history GROUP BY quality ORDER BY quality DESC;')
        for result in sql_results:
            quality = result['quality']

            if quality == 32768:  # Old UNKNOWN quality (1 << 15)
                new_quality = common.Quality.UNKNOWN
            else:
                new_quality = quality << 1

            self.connection.action(
                'UPDATE history SET quality = ? WHERE quality = ?;',
                [new_quality, quality]
            )


class AddEpisodeWatchedField(ShiftQualities):
    """Add episode watched field."""

    def test(self):
        """Test if the version is at least 44.12"""
        return self.connection.version >= (44, 12)

    def execute(self):
        utils.backup_database(self.connection.path, self.connection.version)

        log.info(u'Adding new watched field in the tv_episodes table')
        self.connection.action('DROP TABLE IF EXISTS tmp_tv_episodes;')
        self.connection.action('ALTER TABLE tv_episodes RENAME TO tmp_tv_episodes;')

        self.connection.action(
            'CREATE TABLE IF NOT EXISTS tv_episodes '
            '(episode_id INTEGER PRIMARY KEY, showid NUMERIC, indexerid INTEGER, indexer INTEGER, '
            'name TEXT, season NUMERIC, episode NUMERIC, description TEXT, airdate NUMERIC, hasnfo NUMERIC, '
            'hastbn NUMERIC, status NUMERIC, quality NUMERIC, location TEXT, file_size NUMERIC, release_name TEXT, '
            'subtitles TEXT, subtitles_searchcount NUMERIC, subtitles_lastsearch TIMESTAMP, '
            'is_proper NUMERIC, scene_season NUMERIC, scene_episode NUMERIC, absolute_number NUMERIC, '
            'scene_absolute_number NUMERIC, version NUMERIC DEFAULT -1, release_group TEXT, '
            'manually_searched NUMERIC, watched NUMERIC);'
        )

        # Re-insert old values, setting the new column 'watched' to the default value 0.
        self.connection.action(
            'INSERT INTO tv_episodes '
            '(showid, indexerid, indexer, name, season, episode, description, airdate, hasnfo, '
            'hastbn, status, quality, location, file_size, release_name, subtitles, subtitles_searchcount, '
            'subtitles_lastsearch, is_proper, scene_season, scene_episode, absolute_number, scene_absolute_number, '
            'version, release_group, manually_searched, watched) '
            'SELECT showid, indexerid, indexer, '
            'name, season, episode, description, airdate, hasnfo, '
            'hastbn, status, quality, location, file_size, release_name, '
            'subtitles, subtitles_searchcount, subtitles_lastsearch, '
            'is_proper, scene_season, scene_episode, absolute_number, '
            'scene_absolute_number, version, release_group, manually_searched, 0 AS watched '
            'FROM tmp_tv_episodes;'
        )

        self.connection.action('DROP TABLE tmp_tv_episodes;')
        self.inc_minor_version()


class AddTvshowStartSearchOffset(AddEpisodeWatchedField):
    """Add tv_show airdate_offset field."""

    def test(self):
        """Test if the version is at least 44.13"""
        return self.connection.version >= (44, 13)

    def execute(self):
        utils.backup_database(self.connection.path, self.connection.version)

        log.info(u'Adding new airdate_offset field in the tv_shows table')
        if not self.hasColumn('tv_shows', 'airdate_offset'):
            self.addColumn('tv_shows', 'airdate_offset', 'NUMERIC', 0)

        self.inc_minor_version()


class AddReleaseIgnoreRequireExcludeOptions(AddTvshowStartSearchOffset):
    """Add release ignore and require exclude option flags."""

    def test(self):
        """Test if the version is at least 44.14"""
        return self.connection.version >= (44, 14)

    def execute(self):
        utils.backup_database(self.connection.path, self.connection.version)

        log.info(u'Adding release ignore and require exclude option flags to the tv_shows table')
        if not self.hasColumn('tv_shows', 'rls_require_exclude'):
            self.addColumn('tv_shows', 'rls_require_exclude', 'NUMERIC', 0)
        if not self.hasColumn('tv_shows', 'rls_ignore_exclude'):
            self.addColumn('tv_shows', 'rls_ignore_exclude', 'NUMERIC', 0)

        self.inc_minor_version()


class MoveSceneExceptions(AddReleaseIgnoreRequireExcludeOptions):
    """Create a new table scene_exceptions in main.db, as part of the process to move it from cache to main."""

    def test(self):
        """
        Test if the version is at least 44.15
        """
        return self.connection.version >= (44, 15)

    def execute(self):
        utils.backup_database(self.connection.path, self.connection.version)

        log.info('Creating a new table scene_exceptions in the main.db database.')

        self.connection.action(
            'CREATE TABLE scene_exceptions '
            '(exception_id INTEGER PRIMARY KEY, indexer INTEGER, series_id INTEGER, title TEXT, '
            'season NUMERIC DEFAULT -1, custom NUMERIC DEFAULT 0);'
        )

        self.inc_minor_version()


class AddShowLists(MoveSceneExceptions):
    """Add show_lists field to tv_shows."""

    def test(self):
        """Test if the version is at least 44.16."""
        return self.connection.version >= (44, 16)

    def execute(self):
        utils.backup_database(self.connection.path, self.connection.version)

        log.info(u'Addin show_lists field to tv_shows.')
        if not self.hasColumn('tv_shows', 'show_lists'):
            self.addColumn('tv_shows', 'show_lists', 'text', 'series')

            # Shows that are not flagged as anime, put in the anime list
            self.connection.action("update tv_shows set show_lists = 'series' where anime = 0")

            # Shows that are flagged as anime, put in the anime list
            self.connection.action("update tv_shows set show_lists = 'anime' where anime = 1")

        self.inc_minor_version()


class AddCustomLogs(AddShowLists):
    """Create a new table custom_logs in main.db."""

    def test(self):
        """Test if the version is at least 44.17."""
        return self.connection.version >= (44, 17)

    def execute(self):
        utils.backup_database(self.connection.path, self.connection.version)

        log.info('Creating a new table custom_logs in the main.db database.')

        self.connection.action(
            'CREATE TABLE custom_logs '
            '(log_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, '
            'identifier TEXT NOT NULL, '
            'level INTEGER NOT NULL DEFAULT 0);'
        )

        self.inc_minor_version()
