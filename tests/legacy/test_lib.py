# coding=UTF-8
# Author: Dennis Lutter <lad1337@gmail.com>
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

# pylint: disable=line-too-long

"""Create a test database for testing."""

from __future__ import print_function

import os.path
import shutil
import unittest

from configobj import ConfigObj
from medusa import app, config, db, logger, providers, tv_cache
from medusa.databases import cache_db, failed_db, main_db
from medusa.providers.nzb.newznab import NewznabProvider
from medusa.tv import Episode

# =================
#  test globals
# =================
TEST_DIR = os.path.abspath(os.path.dirname(__file__))
TEST_DB_NAME = "application.db"
TEST_CACHE_DB_NAME = "cache.db"
TEST_FAILED_DB_NAME = "failed.db"

SHOW_NAME = u"show name"
SEASON = 4
EPISODE = 2
FILENAME = u"show name - s0" + str(SEASON) + "e0" + str(EPISODE) + ".mkv"
FILE_DIR = os.path.join(TEST_DIR, SHOW_NAME)
FILE_PATH = os.path.join(FILE_DIR, FILENAME)
SHOW_DIR = os.path.join(TEST_DIR, SHOW_NAME + " final")


# =================
#  prepare env functions
# =================
def create_test_log_folder():
    """Create a log folder for test logs."""
    if not os.path.isdir(app.LOG_DIR):
        os.mkdir(app.LOG_DIR)


def create_test_cache_folder():
    """Create a cache folder for caching tests."""
    if not os.path.isdir(app.CACHE_DIR):
        os.mkdir(app.CACHE_DIR)

# call env functions at appropriate time during application var setup

# =================
#  app globals
# =================
app.SYS_ENCODING = 'UTF-8'

app.showList = []
app.QUALITY_DEFAULT = 4  # hdtv
app.FLATTEN_FOLDERS_DEFAULT = 0

app.NAMING_PATTERN = ''
app.NAMING_ABD_PATTERN = ''
app.NAMING_SPORTS_PATTERN = ''
app.NAMING_MULTI_EP = 1


app.PROVIDER_ORDER = ["app_index"]
app.newznabProviderList = NewznabProvider.get_providers_list("'Application Index|http://lolo.medusa.com/|0|5030,5040|0|eponly|0|0|0!!!NZBs.org|"
                                                             "https://nzbs.org/||5030,5040,5060,5070,5090|0|eponly|0|0|0!!!Usenet-Crawler|"
                                                             "https://www.usenet-crawler.com/||5030,5040,5060|0|eponly|0|0|0'")
app.providerList = providers.make_provider_list()

app.PROG_DIR = os.path.abspath(os.path.join(TEST_DIR, '..'))
app.DATA_DIR = TEST_DIR
app.CONFIG_FILE = os.path.join(app.DATA_DIR, "config.ini")
app.CFG = ConfigObj(app.CONFIG_FILE)

app.BRANCH = config.check_setting_str(app.CFG, 'General', 'branch', '')
app.CUR_COMMIT_HASH = config.check_setting_str(app.CFG, 'General', 'cur_commit_hash', '')
app.GIT_USERNAME = config.check_setting_str(app.CFG, 'General', 'git_username', '')
app.GIT_PASSWORD = config.check_setting_str(app.CFG, 'General', 'git_password', '', censor_log='low')

app.LOG_DIR = os.path.join(TEST_DIR, 'Logs')
logger.log_file = os.path.join(app.LOG_DIR, 'test_application.log')
create_test_log_folder()

app.CACHE_DIR = os.path.join(TEST_DIR, 'cache')
create_test_cache_folder()

# pylint: disable=no-member
logger.init_logging(False)


def _fake_specify_ep(self, season, episode):
    """Override contact to TVDB indexer.

    :param self: ...not used
    :param season: Season to search for  ...not used
    :param episode: Episode to search for  ...not used
    """
    pass

# the real one tries to contact TVDB just stop it from getting more info on the ep
Episode._specify_episode = _fake_specify_ep


# =================
#  test classes
# =================
class AppTestDBCase(unittest.TestCase):
    """Superclass for testing the database."""

    def setUp(self):
        app.showList = []
        setup_test_db()
        setup_test_episode_file()
        setup_test_show_dir()

    def tearDown(self):
        app.showList = []
        teardown_test_db()
        teardown_test_episode_file()
        teardown_test_show_dir()


class TestDBConnection(db.DBConnection, object):
    """Test connecting to the database."""

    def __init__(self, db_file_name=TEST_DB_NAME):
        db_file_name = os.path.join(TEST_DIR, db_file_name)
        super(TestDBConnection, self).__init__(db_file_name)


class TestCacheDBConnection(TestDBConnection, object):
    """Test connecting to the cache database."""

    def __init__(self, provider_name):
        # pylint: disable=non-parent-init-called
        db.DBConnection.__init__(self, os.path.join(TEST_DIR, TEST_CACHE_DB_NAME))

        # Create the table if it's not already there
        try:
            if not self.hasTable(provider_name):
                sql = "CREATE TABLE [" + provider_name + \
                      "] (name TEXT, season NUMERIC, episodes TEXT, indexerid NUMERIC, url TEXT, time NUMERIC, quality TEXT, release_group TEXT)"
                self.connection.execute(sql)
                self.connection.commit()
        # pylint: disable=broad-except
        # Catching too general exception
        except Exception as error:
            if str(error) != "table [" + provider_name + "] already exists":
                raise

            # add version column to table if missing
            if not self.hasColumn(provider_name, 'version'):
                self.addColumn(provider_name, 'version', "NUMERIC", "-1")

        # Create the table if it's not already there
        try:
            sql = "CREATE TABLE lastUpdate (provider TEXT, time NUMERIC);"
            self.connection.execute(sql)
            self.connection.commit()
        # pylint: disable=broad-except
        # Catching too general exception
        except Exception as error:
            if str(error) != "table lastUpdate already exists":
                raise

# this will override the normal db connection
db.DBConnection = TestDBConnection
tv_cache.CacheDBConnection = TestCacheDBConnection


# =================
#  test functions
# =================
def setup_test_db():
    """Set up the test databases."""
    # Upgrade the db to the latest version.
    # upgrading the db
    db.upgradeDatabase(db.DBConnection(), main_db.InitialSchema)

    # fix up any db problems
    db.sanityCheckDatabase(db.DBConnection(), main_db.MainSanityCheck)

    # and for cache.db too
    db.upgradeDatabase(db.DBConnection('cache.db'), cache_db.InitialSchema)

    # and for failed.db too
    db.upgradeDatabase(db.DBConnection('failed.db'), failed_db.InitialSchema)


def teardown_test_db():
    """Tear down the test database."""
    from medusa.db import db_cons
    for connection in db_cons:
        db_cons[connection].commit()
    #     db_cons[connection].close()
    #
    # for current_db in [ TEST_DB_NAME, TEST_CACHE_DB_NAME, TEST_FAILED_DB_NAME ]:
    #    file_name = os.path.join(TEST_DIR, current_db)
    #    if os.path.exists(file_name):
    #        try:
    #            os.remove(file_name)
    #        except Exception as e:
    #            print('ERROR: Failed to remove ' + file_name)
    #            print(exception(e))


def setup_test_episode_file():
    """Create a test episode directory with a test episode in it."""
    if not os.path.exists(FILE_DIR):
        os.makedirs(FILE_DIR)

    try:
        with open(FILE_PATH, 'wb') as ep_file:
            ep_file.write("foo bar")
            ep_file.flush()
    # pylint: disable=broad-except
    # Catching too general exception
    except Exception:
        print("Unable to set up test episode")
        raise


def teardown_test_episode_file():
    """Remove the test episode."""
    if os.path.exists(FILE_DIR):
        shutil.rmtree(FILE_DIR)


def setup_test_show_dir():
    """Create a test show directory."""
    if not os.path.exists(SHOW_DIR):
        os.makedirs(SHOW_DIR)


def teardown_test_show_dir():
    """Remove the test show."""
    if os.path.exists(SHOW_DIR):
        shutil.rmtree(SHOW_DIR)
