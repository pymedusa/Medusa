#!/usr/bin/env python2.7
# -*- coding: utf-8 -*
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


"""
Usage: python -m medusa [OPTION]...

Options:
  -h,  --help            Prints this message
  -q,  --quiet           Disables logging to console
       --nolaunch        Suppress launching web browser on startup

  -d,  --daemon          Run as double forked daemon (with --quiet --nolaunch)
                         On Windows and MAC, this option is ignored but still
                         applies --quiet --nolaunch
       --pidfile=[FILE]  Combined with --daemon creates a pid file

  -p,  --port=[PORT]     Override default/configured port to listen on
       --datadir=[PATH]  Override folder (full path) as location for
                         storing database, config file, cache, and log files
                         Default Medusa directory
       --config=[FILE]   Override config filename for loading configuration
                         Default config.ini in Medusa directory or
                         location specified with --datadir
       --noresize        Prevent resizing of the banner/posters even if PIL
                         is installed
"""

from __future__ import print_function, unicode_literals

import datetime
import getopt
import io
import locale
import logging
import os
import random
import re
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time

from configobj import ConfigObj

from six import text_type

from . import (
    app, auto_post_processor, cache, db, event_queue, exception_handler,
    helpers, logger as app_logger, metadata, name_cache, naming, network_timezones, providers,
    scheduler, show_queue, show_updater, subtitles, torrent_checker, trakt_checker, version_checker
)
from .common import SD, SKIPPED, WANTED
from .config import (
    CheckSection, ConfigMigrator, check_setting_bool, check_setting_float,
    check_setting_int, check_setting_str, load_provider_setting, save_provider_setting
)
from .databases import cache_db, failed_db, main_db
from .event_queue import Events
from .providers.generic_provider import GenericProvider
from .providers.nzb.newznab import NewznabProvider
from .providers.torrent.rss.rsstorrent import TorrentRssProvider
from .search.backlog import BacklogSearchScheduler, BacklogSearcher
from .search.daily import DailySearcher
from .search.proper import ProperFinder
from .search.queue import ForcedSearchQueue, SearchQueue, SnatchQueue
from .server.core import AppWebServer
from .system.shutdown import Shutdown
from .tv import Series

logger = logging.getLogger(__name__)


class Application(object):
    """Main application module."""

    def __init__(self):
        """Init method."""
        # system event callback for shutdown/restart
        app.events = Events(self.shutdown)

        # daemon constants
        self.run_as_daemon = False
        self.create_pid = False
        self.pid_file = ''

        # web server constants
        self.web_server = None
        self.forced_port = None
        self.no_launch = False

        self.web_host = '0.0.0.0'
        self.start_port = app.WEB_PORT
        self.web_options = {}

        self.log_dir = None
        self.console_logging = True

    @staticmethod
    def clear_cache():
        """Remove the Mako cache directory."""
        try:
            cache_folder = os.path.join(app.CACHE_DIR, 'mako')
            if os.path.isdir(cache_folder):
                shutil.rmtree(cache_folder)
        except Exception as e:
            exception_handler.handle(e, 'Unable to remove the cache/mako directory!')

    @staticmethod
    def help_message():
        """Print help message for commandline options."""
        help_msg = __doc__
        help_msg = help_msg.replace('Medusa directory', app.PROG_DIR)

        return help_msg

    def start(self, args):
        """Start Application."""
        app.instance = self
        signal.signal(signal.SIGINT, self.sig_handler)
        signal.signal(signal.SIGTERM, self.sig_handler)

        # do some preliminary stuff
        app.MY_FULLNAME = os.path.normpath(os.path.abspath(os.path.join(__file__, '..', '..', 'start.py')))
        app.MY_NAME = os.path.basename(app.MY_FULLNAME)
        app.PROG_DIR = os.path.dirname(app.MY_FULLNAME)
        app.DATA_DIR = app.PROG_DIR
        app.MY_ARGS = args

        try:
            locale.setlocale(locale.LC_ALL, '')
            app.SYS_ENCODING = locale.getpreferredencoding()
        except (locale.Error, IOError):
            app.SYS_ENCODING = 'UTF-8'

        # pylint: disable=no-member
        if (not app.SYS_ENCODING or
                app.SYS_ENCODING.lower() in ('ansi_x3.4-1968', 'us-ascii', 'ascii', 'charmap') or
                (sys.platform.startswith('win') and
                    sys.getwindowsversion()[0] >= 6 and
                    text_type(getattr(sys.stdout, 'device', sys.stdout).encoding).lower() in ('cp65001', 'charmap'))):
            app.SYS_ENCODING = 'UTF-8'

        # TODO: Continue working on making this unnecessary, this hack creates all sorts of hellish problems
        if not hasattr(sys, 'setdefaultencoding'):
            reload(sys)

        try:
            # On non-unicode builds this will raise an AttributeError, if encoding type is not valid it throws a LookupError
            sys.setdefaultencoding(app.SYS_ENCODING)  # pylint: disable=no-member
        except (AttributeError, LookupError):
            sys.exit('Sorry, you MUST add the Medusa folder to the PYTHONPATH environment variable or '
                     'find another way to force Python to use {encoding} for string encoding.'.format(encoding=app.SYS_ENCODING))

        self.console_logging = (not hasattr(sys, 'frozen')) or (app.MY_NAME.lower().find('-console') > 0)

        # Rename the main thread
        threading.currentThread().name = 'MAIN'

        try:
            opts, _ = getopt.getopt(
                args, 'hqdp::',
                ['help', 'quiet', 'nolaunch', 'daemon', 'pidfile=', 'port=', 'datadir=', 'config=', 'noresize']
            )
        except getopt.GetoptError:
            sys.exit(self.help_message())

        for option, value in opts:
            # Prints help message
            if option in ('-h', '--help'):
                sys.exit(self.help_message())

            # For now we'll just silence the logging
            if option in ('-q', '--quiet'):
                self.console_logging = False

            # Suppress launching web browser
            # Needed for OSes without default browser assigned
            # Prevent duplicate browser window when restarting in the app
            if option in ('--nolaunch',):
                self.no_launch = True

            # Override default/configured port
            if option in ('-p', '--port'):
                try:
                    self.forced_port = int(value)
                except ValueError:
                    sys.exit('Port: %s is not a number. Exiting.' % value)

            # Run as a double forked daemon
            if option in ('-d', '--daemon'):
                self.run_as_daemon = True
                # When running as daemon disable console_logging and don't start browser
                self.console_logging = False
                self.no_launch = True

                if sys.platform == 'win32' or sys.platform == 'darwin':
                    self.run_as_daemon = False

            # Write a pid file if requested
            if option in ('--pidfile',):
                self.create_pid = True
                self.pid_file = str(value)

                # If the pid file already exists, Medusa may still be running, so exit
                if os.path.exists(self.pid_file):
                    sys.exit('PID file: %s already exists. Exiting.' % self.pid_file)

            # Specify folder to load the config file from
            if option in ('--config',):
                app.CONFIG_FILE = os.path.abspath(value)

            # Specify folder to use as the data directory
            if option in ('--datadir',):
                app.DATA_DIR = os.path.abspath(value)

            # Prevent resizing of the banner/posters even if PIL is installed
            if option in ('--noresize',):
                app.NO_RESIZE = True

        # Keep backwards compatibility
        Application.backwards_compatibility()

        # The pid file is only useful in daemon mode, make sure we can write the file properly
        if self.create_pid:
            if self.run_as_daemon:
                pid_dir = os.path.dirname(self.pid_file)
                if not os.access(pid_dir, os.F_OK):
                    sys.exit('PID dir: %s doesn\'t exist. Exiting.' % pid_dir)
                if not os.access(pid_dir, os.W_OK):
                    sys.exit('PID dir: %s must be writable (write permissions). Exiting.' % pid_dir)

            else:
                if self.console_logging:
                    sys.stdout.write('Not running in daemon mode. PID file creation disabled.\n')

                self.create_pid = False

        # If they don't specify a config file then put it in the data dir
        if not app.CONFIG_FILE:
            app.CONFIG_FILE = os.path.join(app.DATA_DIR, 'config.ini')

        # Make sure that we can create the data dir
        if not os.access(app.DATA_DIR, os.F_OK):
            try:
                os.makedirs(app.DATA_DIR, 0o744)
            except os.error:
                raise SystemExit('Unable to create data directory: %s' % app.DATA_DIR)

        # Make sure we can write to the data dir
        if not os.access(app.DATA_DIR, os.W_OK):
            raise SystemExit('Data directory must be writeable: %s' % app.DATA_DIR)

        # Make sure we can write to the config file
        if not os.access(app.CONFIG_FILE, os.W_OK):
            if os.path.isfile(app.CONFIG_FILE):
                raise SystemExit('Config file must be writeable: %s' % app.CONFIG_FILE)
            elif not os.access(os.path.dirname(app.CONFIG_FILE), os.W_OK):
                raise SystemExit('Config file root dir must be writeable: %s' % os.path.dirname(app.CONFIG_FILE))

        os.chdir(app.DATA_DIR)

        # Check if we need to perform a restore first
        restore_dir = os.path.join(app.DATA_DIR, 'restore')
        if os.path.exists(restore_dir):
            success = self.restore_db(restore_dir, app.DATA_DIR)
            if self.console_logging:
                sys.stdout.write('Restore: restoring DB and config.ini %s!\n' % ('FAILED', 'SUCCESSFUL')[success])

        # Load the config and publish it to the application package
        if self.console_logging and not os.path.isfile(app.CONFIG_FILE):
            sys.stdout.write('Unable to find %s, all settings will be default!\n' % app.CONFIG_FILE)

        app.CFG = ConfigObj(app.CONFIG_FILE)

        # Initialize the config and our threads
        self.initialize(console_logging=self.console_logging)

        if self.run_as_daemon:
            self.daemonize()

        # Get PID
        app.PID = os.getpid()

        # Build from the DB to start with
        self.load_shows_from_db()

        logger.info("Starting Medusa [{branch}] using '{config}'", branch=app.BRANCH, config=app.CONFIG_FILE)

        self.clear_cache()

        if self.forced_port:
            logger.info('Forcing web server to port {port}', port=self.forced_port)
            self.start_port = self.forced_port
        else:
            self.start_port = app.WEB_PORT

        if app.WEB_LOG:
            self.log_dir = app.LOG_DIR
        else:
            self.log_dir = None

        # app.WEB_HOST is available as a configuration value in various
        # places but is not configurable. It is supported here for historic reasons.
        if app.WEB_HOST and app.WEB_HOST != '0.0.0.0':
            self.web_host = app.WEB_HOST
        else:
            self.web_host = '' if app.WEB_IPV6 else '0.0.0.0'

        # web server options
        self.web_options = {
            'port': int(self.start_port),
            'host': self.web_host,
            'data_root': os.path.join(app.PROG_DIR, 'static'),
            'web_root': app.WEB_ROOT,
            'log_dir': self.log_dir,
            'username': app.WEB_USERNAME,
            'password': app.WEB_PASSWORD,
            'enable_https': app.ENABLE_HTTPS,
            'handle_reverse_proxy': app.HANDLE_REVERSE_PROXY,
            'https_cert': os.path.join(app.PROG_DIR, app.HTTPS_CERT),
            'https_key': os.path.join(app.PROG_DIR, app.HTTPS_KEY),
        }

        # start web server
        self.web_server = AppWebServer(self.web_options)
        self.web_server.start()

        # Fire up all our threads
        self.start_threads()

        # Build internal name cache
        name_cache.build_name_cache()

        # Pre-populate network timezones, it isn't thread safe
        network_timezones.update_network_dict()

        # # why???
        # if app.USE_FAILED_DOWNLOADS:
        #     failed_history.trim_history()

        # # Check for metadata indexer updates for shows (Disabled until we use api)
        # app.show_update_scheduler.forceRun()

        # Launch browser
        if app.LAUNCH_BROWSER and not (self.no_launch or self.run_as_daemon):
            Application.launch_browser('https' if app.ENABLE_HTTPS else 'http', self.start_port, app.WEB_ROOT)

        # main loop
        while app.started:
            time.sleep(1)

    def initialize(self, console_logging=True):
        """Initialize global variables and configuration."""
        with app.INIT_LOCK:
            if app.__INITIALIZED__:
                return False

            sections = [
                'General', 'Blackhole', 'Newzbin', 'SABnzbd', 'NZBget', 'KODI', 'PLEX', 'Emby', 'Growl', 'Prowl', 'Twitter',
                'Boxcar2', 'NMJ', 'NMJv2', 'Synology', 'SynologyNotifier', 'pyTivo', 'NMA', 'Pushalot', 'Pushbullet',
                'Subtitles', 'pyTivo',
            ]

            for section in sections:
                CheckSection(app.CFG, section)

            app.PRIVACY_LEVEL = check_setting_str(app.CFG, 'General', 'privacy_level', 'normal')
            # Need to be before any passwords
            app.ENCRYPTION_VERSION = check_setting_int(app.CFG, 'General', 'encryption_version', 0)
            app.ENCRYPTION_SECRET = check_setting_str(app.CFG, 'General', 'encryption_secret', helpers.generate_cookie_secret(), censor_log='low')

            # git login info
            app.GIT_USERNAME = check_setting_str(app.CFG, 'General', 'git_username', '')
            app.GIT_PASSWORD = check_setting_str(app.CFG, 'General', 'git_password', '', censor_log='low')
            app.DEVELOPER = bool(check_setting_int(app.CFG, 'General', 'developer', 0))

            # debugging
            app.DEBUG = bool(check_setting_int(app.CFG, 'General', 'debug', 0))
            app.DBDEBUG = bool(check_setting_int(app.CFG, 'General', 'dbdebug', 0))

            app.DEFAULT_PAGE = check_setting_str(app.CFG, 'General', 'default_page', 'home', valid_values=('home', 'schedule', 'history', 'news', 'IRC'))
            app.SEEDERS_LEECHERS_IN_NOTIFY = check_setting_int(app.CFG, 'General', 'seeders_leechers_in_notify', 1)
            app.ACTUAL_LOG_DIR = check_setting_str(app.CFG, 'General', 'log_dir', 'Logs')
            app.LOG_DIR = os.path.normpath(os.path.join(app.DATA_DIR, app.ACTUAL_LOG_DIR))
            app.LOG_NR = check_setting_int(app.CFG, 'General', 'log_nr', 5)  # Default to 5 backup file (application.log.x)
            app.LOG_SIZE = min(100, check_setting_float(app.CFG, 'General', 'log_size', 10.0))  # Default to max 10MB per logfile

            if not helpers.make_dir(app.LOG_DIR):
                sys.stderr.write('Unable to create log folder {folder}'.format(folder=app.LOG_DIR))
                sys.exit(7)

            # init logging
            app_logger.backwards_compatibility()
            app_logger.init_logging(console_logging=console_logging)

            # git reset on update
            app.GIT_RESET = bool(check_setting_int(app.CFG, 'General', 'git_reset', 1))
            app.GIT_RESET_BRANCHES = check_setting_str(app.CFG, 'General', 'git_reset_branches', app.GIT_RESET_BRANCHES).split(',')
            if app.GIT_RESET_BRANCHES[0] == '':
                app.GIT_RESET_BRANCHES = []

            # current git branch
            app.BRANCH = check_setting_str(app.CFG, 'General', 'branch', '')

            # git_remote
            app.GIT_REMOTE = check_setting_str(app.CFG, 'General', 'git_remote', 'origin')
            app.GIT_REMOTE_URL = check_setting_str(app.CFG, 'General', 'git_remote_url', app.APPLICATION_URL)

            repo_url_re = re.compile(r'(?P<prefix>(?:git@github\.com:)|(?:https://github\.com/))(?P<org>\w+)/(?P<repo>\w+)\.git')
            m = repo_url_re.match(app.GIT_REMOTE_URL)
            if m:
                groups = m.groupdict()
                if groups['org'].lower() != app.GIT_ORG.lower() or groups['repo'].lower() != app.GIT_REPO.lower():
                    app.GIT_REMOTE_URL = groups['prefix'] + app.GIT_ORG + '/' + app.GIT_REPO + '.git'
            else:
                app.GIT_REMOTE_URL = app.APPLICATION_URL

            # current commit hash
            app.CUR_COMMIT_HASH = check_setting_str(app.CFG, 'General', 'cur_commit_hash', '')

            # current commit branch
            app.CUR_COMMIT_BRANCH = check_setting_str(app.CFG, 'General', 'cur_commit_branch', '')
            app.ACTUAL_CACHE_DIR = check_setting_str(app.CFG, 'General', 'cache_dir', 'cache')

            # fix bad configs due to buggy code
            if app.ACTUAL_CACHE_DIR == 'None':
                app.ACTUAL_CACHE_DIR = 'cache'

            # unless they specify, put the cache dir inside the data dir
            if not os.path.isabs(app.ACTUAL_CACHE_DIR):
                app.CACHE_DIR = os.path.join(app.DATA_DIR, app.ACTUAL_CACHE_DIR)
            else:
                app.CACHE_DIR = app.ACTUAL_CACHE_DIR

            if not helpers.make_dir(app.CACHE_DIR):
                logger.error(u'Creating local cache dir failed, using system default')
                app.CACHE_DIR = None

            # Check if we need to perform a restore of the cache folder
            Application.restore_cache_folder(app.CACHE_DIR)
            cache.configure(app.CACHE_DIR)

            app.FANART_BACKGROUND = bool(check_setting_int(app.CFG, 'GUI', 'fanart_background', 1))
            app.FANART_BACKGROUND_OPACITY = check_setting_float(app.CFG, 'GUI', 'fanart_background_opacity', 0.4)

            app.THEME_NAME = check_setting_str(app.CFG, 'GUI', 'theme_name', 'dark')

            app.SOCKET_TIMEOUT = check_setting_int(app.CFG, 'General', 'socket_timeout', 30)
            socket.setdefaulttimeout(app.SOCKET_TIMEOUT)

            try:
                app.WEB_PORT = check_setting_int(app.CFG, 'General', 'web_port', 8081)
            except Exception:
                app.WEB_PORT = 8081

            if not 21 < app.WEB_PORT < 65535:
                app.WEB_PORT = 8081

            app.WEB_HOST = check_setting_str(app.CFG, 'General', 'web_host', '0.0.0.0')
            app.WEB_IPV6 = bool(check_setting_int(app.CFG, 'General', 'web_ipv6', 0))
            app.WEB_ROOT = check_setting_str(app.CFG, 'General', 'web_root', '').rstrip("/")
            app.WEB_LOG = bool(check_setting_int(app.CFG, 'General', 'web_log', 0))
            app.WEB_USERNAME = check_setting_str(app.CFG, 'General', 'web_username', '', censor_log='normal')
            app.WEB_PASSWORD = check_setting_str(app.CFG, 'General', 'web_password', '', censor_log='low')
            app.WEB_COOKIE_SECRET = check_setting_str(app.CFG, 'General', 'web_cookie_secret', helpers.generate_cookie_secret(), censor_log='low')
            if not app.WEB_COOKIE_SECRET:
                app.WEB_COOKIE_SECRET = helpers.generate_cookie_secret()

            app.WEB_USE_GZIP = bool(check_setting_int(app.CFG, 'General', 'web_use_gzip', 1))
            app.SUBLIMINAL_LOG = bool(check_setting_int(app.CFG, 'General', 'subliminal_log', 0))
            app.PRIVACY_LEVEL = check_setting_str(app.CFG, 'General', 'privacy_level', 'normal')
            app.SSL_VERIFY = bool(check_setting_int(app.CFG, 'General', 'ssl_verify', 1))
            app.INDEXER_DEFAULT_LANGUAGE = check_setting_str(app.CFG, 'General', 'indexerDefaultLang', 'en')
            app.EP_DEFAULT_DELETED_STATUS = check_setting_int(app.CFG, 'General', 'ep_default_deleted_status', 6)
            app.LAUNCH_BROWSER = bool(check_setting_int(app.CFG, 'General', 'launch_browser', 1))
            app.DOWNLOAD_URL = check_setting_str(app.CFG, 'General', 'download_url', "")
            app.LOCALHOST_IP = check_setting_str(app.CFG, 'General', 'localhost_ip', '')
            app.CPU_PRESET = check_setting_str(app.CFG, 'General', 'cpu_preset', 'NORMAL')
            app.ANON_REDIRECT = check_setting_str(app.CFG, 'General', 'anon_redirect', 'http://dereferer.org/?')
            app.PROXY_SETTING = check_setting_str(app.CFG, 'General', 'proxy_setting', '')
            app.PROXY_INDEXERS = bool(check_setting_int(app.CFG, 'General', 'proxy_indexers', 1))

            # attempt to help prevent users from breaking links by using a bad url
            if not app.ANON_REDIRECT.endswith('?'):
                app.ANON_REDIRECT = ''

            app.TRASH_REMOVE_SHOW = bool(check_setting_int(app.CFG, 'General', 'trash_remove_show', 0))
            app.TRASH_ROTATE_LOGS = bool(check_setting_int(app.CFG, 'General', 'trash_rotate_logs', 0))
            app.SORT_ARTICLE = bool(check_setting_int(app.CFG, 'General', 'sort_article', 0))
            app.API_KEY = check_setting_str(app.CFG, 'General', 'api_key', '', censor_log='low')
            app.ENABLE_HTTPS = bool(check_setting_int(app.CFG, 'General', 'enable_https', 0))
            app.NOTIFY_ON_LOGIN = bool(check_setting_int(app.CFG, 'General', 'notify_on_login', 0))
            app.HTTPS_CERT = check_setting_str(app.CFG, 'General', 'https_cert', 'server.crt')
            app.HTTPS_KEY = check_setting_str(app.CFG, 'General', 'https_key', 'server.key')
            app.HANDLE_REVERSE_PROXY = bool(check_setting_int(app.CFG, 'General', 'handle_reverse_proxy', 0))
            app.ROOT_DIRS = check_setting_str(app.CFG, 'General', 'root_dirs', '')
            if not re.match(r'\d+\|[^|]+(?:\|[^|]+)*', app.ROOT_DIRS):
                app.ROOT_DIRS = ''

            app.QUALITY_DEFAULT = check_setting_int(app.CFG, 'General', 'quality_default', SD)
            app.STATUS_DEFAULT = check_setting_int(app.CFG, 'General', 'status_default', SKIPPED)
            app.STATUS_DEFAULT_AFTER = check_setting_int(app.CFG, 'General', 'status_default_after', WANTED)
            app.VERSION_NOTIFY = bool(check_setting_int(app.CFG, 'General', 'version_notify', 1))
            app.AUTO_UPDATE = bool(check_setting_int(app.CFG, 'General', 'auto_update', 0))
            app.NOTIFY_ON_UPDATE = bool(check_setting_int(app.CFG, 'General', 'notify_on_update', 1))
            app.FLATTEN_FOLDERS_DEFAULT = bool(check_setting_int(app.CFG, 'General', 'flatten_folders_default', 0))
            app.INDEXER_DEFAULT = check_setting_int(app.CFG, 'General', 'indexer_default', 0)
            app.INDEXER_TIMEOUT = check_setting_int(app.CFG, 'General', 'indexer_timeout', 20)
            app.ANIME_DEFAULT = bool(check_setting_int(app.CFG, 'General', 'anime_default', 0))
            app.SCENE_DEFAULT = bool(check_setting_int(app.CFG, 'General', 'scene_default', 0))
            app.PROVIDER_ORDER = check_setting_str(app.CFG, 'General', 'provider_order', '').split()
            app.NAMING_PATTERN = check_setting_str(app.CFG, 'General', 'naming_pattern', 'Season %0S/%SN - S%0SE%0E - %EN')
            app.NAMING_ABD_PATTERN = check_setting_str(app.CFG, 'General', 'naming_abd_pattern', '%SN - %A.D - %EN')
            app.NAMING_CUSTOM_ABD = bool(check_setting_int(app.CFG, 'General', 'naming_custom_abd', 0))
            app.NAMING_SPORTS_PATTERN = check_setting_str(app.CFG, 'General', 'naming_sports_pattern', '%SN - %A-D - %EN')
            app.NAMING_ANIME_PATTERN = check_setting_str(app.CFG, 'General', 'naming_anime_pattern', 'Season %0S/%SN - S%0SE%0E - %EN')
            app.NAMING_ANIME = check_setting_int(app.CFG, 'General', 'naming_anime', 3)
            app.NAMING_CUSTOM_SPORTS = bool(check_setting_int(app.CFG, 'General', 'naming_custom_sports', 0))
            app.NAMING_CUSTOM_ANIME = bool(check_setting_int(app.CFG, 'General', 'naming_custom_anime', 0))
            app.NAMING_MULTI_EP = check_setting_int(app.CFG, 'General', 'naming_multi_ep', 1)
            app.NAMING_ANIME_MULTI_EP = check_setting_int(app.CFG, 'General', 'naming_anime_multi_ep', 1)
            app.NAMING_FORCE_FOLDERS = naming.check_force_season_folders()
            app.NAMING_STRIP_YEAR = bool(check_setting_int(app.CFG, 'General', 'naming_strip_year', 0))
            app.USE_NZBS = bool(check_setting_int(app.CFG, 'General', 'use_nzbs', 0))
            app.USE_TORRENTS = bool(check_setting_int(app.CFG, 'General', 'use_torrents', 1))

            app.NZB_METHOD = check_setting_str(app.CFG, 'General', 'nzb_method', 'blackhole', valid_values=('blackhole', 'sabnzbd', 'nzbget'))
            app.TORRENT_METHOD = check_setting_str(app.CFG, 'General', 'torrent_method', 'blackhole',
                                                   valid_values=('blackhole', 'utorrent', 'transmission', 'deluge',
                                                                 'deluged', 'download_station', 'rtorrent', 'qbittorrent', 'mlnet'))

            app.DOWNLOAD_PROPERS = bool(check_setting_int(app.CFG, 'General', 'download_propers', 1))
            app.PROPERS_SEARCH_DAYS = max(2, min(8, check_setting_int(app.CFG, 'General', 'propers_search_days', 2)))
            app.REMOVE_FROM_CLIENT = bool(check_setting_int(app.CFG, 'General', 'remove_from_client', 0))
            app.CHECK_PROPERS_INTERVAL = check_setting_str(app.CFG, 'General', 'check_propers_interval', 'daily',
                                                           valid_values=('15m', '45m', '90m', '4h', 'daily'))
            app.RANDOMIZE_PROVIDERS = bool(check_setting_int(app.CFG, 'General', 'randomize_providers', 0))
            app.ALLOW_HIGH_PRIORITY = bool(check_setting_int(app.CFG, 'General', 'allow_high_priority', 1))
            app.SKIP_REMOVED_FILES = bool(check_setting_int(app.CFG, 'General', 'skip_removed_files', 0))
            app.ALLOWED_EXTENSIONS = check_setting_str(app.CFG, 'General', 'allowed_extensions', app.ALLOWED_EXTENSIONS)
            app.USENET_RETENTION = check_setting_int(app.CFG, 'General', 'usenet_retention', 500)
            app.CACHE_TRIMMING = bool(check_setting_int(app.CFG, 'General', 'cache_trimming', 0))
            app.MAX_CACHE_AGE = check_setting_int(app.CFG, 'General', 'max_cache_age', 30)
            app.AUTOPOSTPROCESSOR_FREQUENCY = max(app.MIN_AUTOPOSTPROCESSOR_FREQUENCY,
                                                  check_setting_int(app.CFG, 'General', 'autopostprocessor_frequency',
                                                                    app.DEFAULT_AUTOPOSTPROCESSOR_FREQUENCY))

            app.TORRENT_CHECKER_FREQUENCY = max(app.MIN_TORRENT_CHECKER_FREQUENCY,
                                                check_setting_int(app.CFG, 'General', 'torrent_checker_frequency',
                                                                  app.DEFAULT_TORRENT_CHECKER_FREQUENCY))
            app.DAILYSEARCH_FREQUENCY = max(app.MIN_DAILYSEARCH_FREQUENCY,
                                            check_setting_int(app.CFG, 'General', 'dailysearch_frequency', app.DEFAULT_DAILYSEARCH_FREQUENCY))
            app.MIN_BACKLOG_FREQUENCY = Application.get_backlog_cycle_time()
            app.BACKLOG_FREQUENCY = max(app.MIN_BACKLOG_FREQUENCY, check_setting_int(app.CFG, 'General', 'backlog_frequency', app.DEFAULT_BACKLOG_FREQUENCY))
            app.UPDATE_FREQUENCY = max(app.MIN_UPDATE_FREQUENCY, check_setting_int(app.CFG, 'General', 'update_frequency', app.DEFAULT_UPDATE_FREQUENCY))
            app.SHOWUPDATE_HOUR = max(0, min(23, check_setting_int(app.CFG, 'General', 'showupdate_hour', app.DEFAULT_SHOWUPDATE_HOUR)))

            app.BACKLOG_DAYS = check_setting_int(app.CFG, 'General', 'backlog_days', 7)

            app.NEWS_LAST_READ = check_setting_str(app.CFG, 'General', 'news_last_read', '1970-01-01')
            app.NEWS_LATEST = app.NEWS_LAST_READ

            app.BROKEN_PROVIDERS = check_setting_str(app.CFG, 'General', 'broken_providers',
                                                     helpers.get_broken_providers() or app.BROKEN_PROVIDERS)

            app.NZB_DIR = check_setting_str(app.CFG, 'Blackhole', 'nzb_dir', '')
            app.TORRENT_DIR = check_setting_str(app.CFG, 'Blackhole', 'torrent_dir', '')

            app.TV_DOWNLOAD_DIR = check_setting_str(app.CFG, 'General', 'tv_download_dir', '')
            app.PROCESS_AUTOMATICALLY = bool(check_setting_int(app.CFG, 'General', 'process_automatically', 0))
            app.NO_DELETE = bool(check_setting_int(app.CFG, 'General', 'no_delete', 0))
            app.UNPACK = bool(check_setting_int(app.CFG, 'General', 'unpack', 0))
            app.RENAME_EPISODES = bool(check_setting_int(app.CFG, 'General', 'rename_episodes', 1))
            app.AIRDATE_EPISODES = bool(check_setting_int(app.CFG, 'General', 'airdate_episodes', 0))
            app.FILE_TIMESTAMP_TIMEZONE = check_setting_str(app.CFG, 'General', 'file_timestamp_timezone', 'network')
            app.KEEP_PROCESSED_DIR = bool(check_setting_int(app.CFG, 'General', 'keep_processed_dir', 1))
            app.PROCESS_METHOD = check_setting_str(app.CFG, 'General', 'process_method', 'copy' if app.KEEP_PROCESSED_DIR else 'move')
            app.DELRARCONTENTS = bool(check_setting_int(app.CFG, 'General', 'del_rar_contents', 0))
            app.MOVE_ASSOCIATED_FILES = bool(check_setting_int(app.CFG, 'General', 'move_associated_files', 0))
            app.POSTPONE_IF_SYNC_FILES = bool(check_setting_int(app.CFG, 'General', 'postpone_if_sync_files', 1))
            app.POSTPONE_IF_NO_SUBS = bool(check_setting_int(app.CFG, 'General', 'postpone_if_no_subs', 0))
            app.SYNC_FILES = check_setting_str(app.CFG, 'General', 'sync_files', app.SYNC_FILES)
            app.NFO_RENAME = bool(check_setting_int(app.CFG, 'General', 'nfo_rename', 1))
            app.CREATE_MISSING_SHOW_DIRS = bool(check_setting_int(app.CFG, 'General', 'create_missing_show_dirs', 0))
            app.ADD_SHOWS_WO_DIR = bool(check_setting_int(app.CFG, 'General', 'add_shows_wo_dir', 0))

            app.NZBS = bool(check_setting_int(app.CFG, 'NZBs', 'nzbs', 0))
            app.NZBS_UID = check_setting_str(app.CFG, 'NZBs', 'nzbs_uid', '', censor_log='normal')
            app.NZBS_HASH = check_setting_str(app.CFG, 'NZBs', 'nzbs_hash', '', censor_log='low')

            app.NEWZBIN = bool(check_setting_int(app.CFG, 'Newzbin', 'newzbin', 0))
            app.NEWZBIN_USERNAME = check_setting_str(app.CFG, 'Newzbin', 'newzbin_username', '', censor_log='normal')
            app.NEWZBIN_PASSWORD = check_setting_str(app.CFG, 'Newzbin', 'newzbin_password', '', censor_log='low')

            app.SAB_USERNAME = check_setting_str(app.CFG, 'SABnzbd', 'sab_username', '', censor_log='normal')
            app.SAB_PASSWORD = check_setting_str(app.CFG, 'SABnzbd', 'sab_password', '', censor_log='low')
            app.SAB_APIKEY = check_setting_str(app.CFG, 'SABnzbd', 'sab_apikey', '', censor_log='low')
            app.SAB_CATEGORY = check_setting_str(app.CFG, 'SABnzbd', 'sab_category', 'tv')
            app.SAB_CATEGORY_BACKLOG = check_setting_str(app.CFG, 'SABnzbd', 'sab_category_backlog', app.SAB_CATEGORY)
            app.SAB_CATEGORY_ANIME = check_setting_str(app.CFG, 'SABnzbd', 'sab_category_anime', 'anime')
            app.SAB_CATEGORY_ANIME_BACKLOG = check_setting_str(app.CFG, 'SABnzbd', 'sab_category_anime_backlog', app.SAB_CATEGORY_ANIME)
            app.SAB_HOST = check_setting_str(app.CFG, 'SABnzbd', 'sab_host', '', censor_log='high')
            app.SAB_FORCED = bool(check_setting_int(app.CFG, 'SABnzbd', 'sab_forced', 0))

            app.NZBGET_USERNAME = check_setting_str(app.CFG, 'NZBget', 'nzbget_username', 'nzbget', censor_log='normal')
            app.NZBGET_PASSWORD = check_setting_str(app.CFG, 'NZBget', 'nzbget_password', 'tegbzn6789', censor_log='low')
            app.NZBGET_CATEGORY = check_setting_str(app.CFG, 'NZBget', 'nzbget_category', 'tv')
            app.NZBGET_CATEGORY_BACKLOG = check_setting_str(app.CFG, 'NZBget', 'nzbget_category_backlog', app.NZBGET_CATEGORY)
            app.NZBGET_CATEGORY_ANIME = check_setting_str(app.CFG, 'NZBget', 'nzbget_category_anime', 'anime')
            app.NZBGET_CATEGORY_ANIME_BACKLOG = check_setting_str(app.CFG, 'NZBget', 'nzbget_category_anime_backlog', app.NZBGET_CATEGORY_ANIME)
            app.NZBGET_HOST = check_setting_str(app.CFG, 'NZBget', 'nzbget_host', '', censor_log='high')
            app.NZBGET_USE_HTTPS = bool(check_setting_int(app.CFG, 'NZBget', 'nzbget_use_https', 0))
            app.NZBGET_PRIORITY = check_setting_int(app.CFG, 'NZBget', 'nzbget_priority', 100)

            app.TORRENT_USERNAME = check_setting_str(app.CFG, 'TORRENT', 'torrent_username', '', censor_log='normal')
            app.TORRENT_PASSWORD = check_setting_str(app.CFG, 'TORRENT', 'torrent_password', '', censor_log='low')
            app.TORRENT_HOST = check_setting_str(app.CFG, 'TORRENT', 'torrent_host', '', censor_log='high')
            app.TORRENT_PATH = check_setting_str(app.CFG, 'TORRENT', 'torrent_path', '')
            app.TORRENT_SEED_TIME = check_setting_int(app.CFG, 'TORRENT', 'torrent_seed_time', 0)
            app.TORRENT_PAUSED = bool(check_setting_int(app.CFG, 'TORRENT', 'torrent_paused', 0))
            app.TORRENT_HIGH_BANDWIDTH = bool(check_setting_int(app.CFG, 'TORRENT', 'torrent_high_bandwidth', 0))
            app.TORRENT_LABEL = check_setting_str(app.CFG, 'TORRENT', 'torrent_label', '')
            app.TORRENT_LABEL_ANIME = check_setting_str(app.CFG, 'TORRENT', 'torrent_label_anime', '')
            app.TORRENT_VERIFY_CERT = bool(check_setting_int(app.CFG, 'TORRENT', 'torrent_verify_cert', 0))
            app.TORRENT_RPCURL = check_setting_str(app.CFG, 'TORRENT', 'torrent_rpcurl', 'transmission')
            app.TORRENT_AUTH_TYPE = check_setting_str(app.CFG, 'TORRENT', 'torrent_auth_type', '')

            app.USE_KODI = bool(check_setting_int(app.CFG, 'KODI', 'use_kodi', 0))
            app.KODI_ALWAYS_ON = bool(check_setting_int(app.CFG, 'KODI', 'kodi_always_on', 1))
            app.KODI_NOTIFY_ONSNATCH = bool(check_setting_int(app.CFG, 'KODI', 'kodi_notify_onsnatch', 0))
            app.KODI_NOTIFY_ONDOWNLOAD = bool(check_setting_int(app.CFG, 'KODI', 'kodi_notify_ondownload', 0))
            app.KODI_NOTIFY_ONSUBTITLEDOWNLOAD = bool(check_setting_int(app.CFG, 'KODI', 'kodi_notify_onsubtitledownload', 0))
            app.KODI_UPDATE_LIBRARY = bool(check_setting_int(app.CFG, 'KODI', 'kodi_update_library', 0))
            app.KODI_UPDATE_FULL = bool(check_setting_int(app.CFG, 'KODI', 'kodi_update_full', 0))
            app.KODI_UPDATE_ONLYFIRST = bool(check_setting_int(app.CFG, 'KODI', 'kodi_update_onlyfirst', 0))
            app.KODI_HOST = check_setting_str(app.CFG, 'KODI', 'kodi_host', '', censor_log='high')
            app.KODI_USERNAME = check_setting_str(app.CFG, 'KODI', 'kodi_username', '', censor_log='normal')
            app.KODI_PASSWORD = check_setting_str(app.CFG, 'KODI', 'kodi_password', '', censor_log='low')
            app.KODI_CLEAN_LIBRARY = bool(check_setting_int(app.CFG, 'KODI', 'kodi_clean_library', 0))

            app.USE_PLEX_SERVER = bool(check_setting_int(app.CFG, 'Plex', 'use_plex_server', 0))
            app.PLEX_NOTIFY_ONSNATCH = bool(check_setting_int(app.CFG, 'Plex', 'plex_notify_onsnatch', 0))
            app.PLEX_NOTIFY_ONDOWNLOAD = bool(check_setting_int(app.CFG, 'Plex', 'plex_notify_ondownload', 0))
            app.PLEX_NOTIFY_ONSUBTITLEDOWNLOAD = bool(check_setting_int(app.CFG, 'Plex', 'plex_notify_onsubtitledownload', 0))
            app.PLEX_UPDATE_LIBRARY = bool(check_setting_int(app.CFG, 'Plex', 'plex_update_library', 0))
            app.PLEX_SERVER_HOST = check_setting_str(app.CFG, 'Plex', 'plex_server_host', '', censor_log='high')
            app.PLEX_SERVER_TOKEN = check_setting_str(app.CFG, 'Plex', 'plex_server_token', '', censor_log='high')
            app.PLEX_CLIENT_HOST = check_setting_str(app.CFG, 'Plex', 'plex_client_host', '', censor_log='high')
            app.PLEX_SERVER_USERNAME = check_setting_str(app.CFG, 'Plex', 'plex_server_username', '', censor_log='normal')
            app.PLEX_SERVER_PASSWORD = check_setting_str(app.CFG, 'Plex', 'plex_server_password', '', censor_log='low')
            app.USE_PLEX_CLIENT = bool(check_setting_int(app.CFG, 'Plex', 'use_plex_client', 0))
            app.PLEX_CLIENT_USERNAME = check_setting_str(app.CFG, 'Plex', 'plex_client_username', '', censor_log='normal')
            app.PLEX_CLIENT_PASSWORD = check_setting_str(app.CFG, 'Plex', 'plex_client_password', '', censor_log='low')
            app.PLEX_SERVER_HTTPS = bool(check_setting_int(app.CFG, 'Plex', 'plex_server_https', 0))

            app.USE_EMBY = bool(check_setting_int(app.CFG, 'Emby', 'use_emby', 0))
            app.EMBY_HOST = check_setting_str(app.CFG, 'Emby', 'emby_host', '', censor_log='high')
            app.EMBY_APIKEY = check_setting_str(app.CFG, 'Emby', 'emby_apikey', '', censor_log='low')

            app.USE_GROWL = bool(check_setting_int(app.CFG, 'Growl', 'use_growl', 0))
            app.GROWL_NOTIFY_ONSNATCH = bool(check_setting_int(app.CFG, 'Growl', 'growl_notify_onsnatch', 0))
            app.GROWL_NOTIFY_ONDOWNLOAD = bool(check_setting_int(app.CFG, 'Growl', 'growl_notify_ondownload', 0))
            app.GROWL_NOTIFY_ONSUBTITLEDOWNLOAD = bool(check_setting_int(app.CFG, 'Growl', 'growl_notify_onsubtitledownload', 0))
            app.GROWL_HOST = check_setting_str(app.CFG, 'Growl', 'growl_host', '')
            app.GROWL_PASSWORD = check_setting_str(app.CFG, 'Growl', 'growl_password', '', censor_log='low')

            app.USE_FREEMOBILE = bool(check_setting_int(app.CFG, 'FreeMobile', 'use_freemobile', 0))
            app.FREEMOBILE_NOTIFY_ONSNATCH = bool(check_setting_int(app.CFG, 'FreeMobile', 'freemobile_notify_onsnatch', 0))
            app.FREEMOBILE_NOTIFY_ONDOWNLOAD = bool(check_setting_int(app.CFG, 'FreeMobile', 'freemobile_notify_ondownload', 0))
            app.FREEMOBILE_NOTIFY_ONSUBTITLEDOWNLOAD = bool(check_setting_int(app.CFG, 'FreeMobile', 'freemobile_notify_onsubtitledownload', 0))
            app.FREEMOBILE_ID = check_setting_str(app.CFG, 'FreeMobile', 'freemobile_id', '', censor_log='normal')
            app.FREEMOBILE_APIKEY = check_setting_str(app.CFG, 'FreeMobile', 'freemobile_apikey', '', censor_log='low')

            app.USE_TELEGRAM = bool(check_setting_int(app.CFG, 'Telegram', 'use_telegram', 0))
            app.TELEGRAM_NOTIFY_ONSNATCH = bool(check_setting_int(app.CFG, 'Telegram', 'telegram_notify_onsnatch', 0))
            app.TELEGRAM_NOTIFY_ONDOWNLOAD = bool(check_setting_int(app.CFG, 'Telegram', 'telegram_notify_ondownload', 0))
            app.TELEGRAM_NOTIFY_ONSUBTITLEDOWNLOAD = bool(check_setting_int(app.CFG, 'Telegram', 'telegram_notify_onsubtitledownload', 0))
            app.TELEGRAM_ID = check_setting_str(app.CFG, 'Telegram', 'telegram_id', '', censor_log='normal')
            app.TELEGRAM_APIKEY = check_setting_str(app.CFG, 'Telegram', 'telegram_apikey', '', censor_log='low')

            app.USE_PROWL = bool(check_setting_int(app.CFG, 'Prowl', 'use_prowl', 0))
            app.PROWL_NOTIFY_ONSNATCH = bool(check_setting_int(app.CFG, 'Prowl', 'prowl_notify_onsnatch', 0))
            app.PROWL_NOTIFY_ONDOWNLOAD = bool(check_setting_int(app.CFG, 'Prowl', 'prowl_notify_ondownload', 0))
            app.PROWL_NOTIFY_ONSUBTITLEDOWNLOAD = bool(check_setting_int(app.CFG, 'Prowl', 'prowl_notify_onsubtitledownload', 0))
            app.PROWL_API = check_setting_str(app.CFG, 'Prowl', 'prowl_api', '', censor_log='low')
            app.PROWL_PRIORITY = check_setting_str(app.CFG, 'Prowl', 'prowl_priority', "0")
            app.PROWL_MESSAGE_TITLE = check_setting_str(app.CFG, 'Prowl', 'prowl_message_title', "Medusa")

            app.USE_TWITTER = bool(check_setting_int(app.CFG, 'Twitter', 'use_twitter', 0))
            app.TWITTER_NOTIFY_ONSNATCH = bool(check_setting_int(app.CFG, 'Twitter', 'twitter_notify_onsnatch', 0))
            app.TWITTER_NOTIFY_ONDOWNLOAD = bool(check_setting_int(app.CFG, 'Twitter', 'twitter_notify_ondownload', 0))
            app.TWITTER_NOTIFY_ONSUBTITLEDOWNLOAD = bool(check_setting_int(app.CFG, 'Twitter', 'twitter_notify_onsubtitledownload', 0))
            app.TWITTER_USERNAME = check_setting_str(app.CFG, 'Twitter', 'twitter_username', '', censor_log='normal')
            app.TWITTER_PASSWORD = check_setting_str(app.CFG, 'Twitter', 'twitter_password', '', censor_log='low')
            app.TWITTER_PREFIX = check_setting_str(app.CFG, 'Twitter', 'twitter_prefix', app.GIT_REPO)
            app.TWITTER_DMTO = check_setting_str(app.CFG, 'Twitter', 'twitter_dmto', '')
            app.TWITTER_USEDM = bool(check_setting_int(app.CFG, 'Twitter', 'twitter_usedm', 0))

            app.USE_BOXCAR2 = bool(check_setting_int(app.CFG, 'Boxcar2', 'use_boxcar2', 0))
            app.BOXCAR2_NOTIFY_ONSNATCH = bool(check_setting_int(app.CFG, 'Boxcar2', 'boxcar2_notify_onsnatch', 0))
            app.BOXCAR2_NOTIFY_ONDOWNLOAD = bool(check_setting_int(app.CFG, 'Boxcar2', 'boxcar2_notify_ondownload', 0))
            app.BOXCAR2_NOTIFY_ONSUBTITLEDOWNLOAD = bool(check_setting_int(app.CFG, 'Boxcar2', 'boxcar2_notify_onsubtitledownload', 0))
            app.BOXCAR2_ACCESSTOKEN = check_setting_str(app.CFG, 'Boxcar2', 'boxcar2_accesstoken', '', censor_log='low')

            app.USE_PUSHOVER = bool(check_setting_int(app.CFG, 'Pushover', 'use_pushover', 0))
            app.PUSHOVER_NOTIFY_ONSNATCH = bool(check_setting_int(app.CFG, 'Pushover', 'pushover_notify_onsnatch', 0))
            app.PUSHOVER_NOTIFY_ONDOWNLOAD = bool(check_setting_int(app.CFG, 'Pushover', 'pushover_notify_ondownload', 0))
            app.PUSHOVER_NOTIFY_ONSUBTITLEDOWNLOAD = bool(check_setting_int(app.CFG, 'Pushover', 'pushover_notify_onsubtitledownload', 0))
            app.PUSHOVER_USERKEY = check_setting_str(app.CFG, 'Pushover', 'pushover_userkey', '', censor_log='normal')
            app.PUSHOVER_APIKEY = check_setting_str(app.CFG, 'Pushover', 'pushover_apikey', '', censor_log='low')
            app.PUSHOVER_DEVICE = check_setting_str(app.CFG, 'Pushover', 'pushover_device', '')
            app.PUSHOVER_SOUND = check_setting_str(app.CFG, 'Pushover', 'pushover_sound', 'pushover')

            app.USE_LIBNOTIFY = bool(check_setting_int(app.CFG, 'Libnotify', 'use_libnotify', 0))
            app.LIBNOTIFY_NOTIFY_ONSNATCH = bool(check_setting_int(app.CFG, 'Libnotify', 'libnotify_notify_onsnatch', 0))
            app.LIBNOTIFY_NOTIFY_ONDOWNLOAD = bool(check_setting_int(app.CFG, 'Libnotify', 'libnotify_notify_ondownload', 0))
            app.LIBNOTIFY_NOTIFY_ONSUBTITLEDOWNLOAD = bool(check_setting_int(app.CFG, 'Libnotify', 'libnotify_notify_onsubtitledownload', 0))

            app.USE_NMJ = bool(check_setting_int(app.CFG, 'NMJ', 'use_nmj', 0))
            app.NMJ_HOST = check_setting_str(app.CFG, 'NMJ', 'nmj_host', '')
            app.NMJ_DATABASE = check_setting_str(app.CFG, 'NMJ', 'nmj_database', '')
            app.NMJ_MOUNT = check_setting_str(app.CFG, 'NMJ', 'nmj_mount', '')

            app.USE_NMJv2 = bool(check_setting_int(app.CFG, 'NMJv2', 'use_nmjv2', 0))
            app.NMJv2_HOST = check_setting_str(app.CFG, 'NMJv2', 'nmjv2_host', '')
            app.NMJv2_DATABASE = check_setting_str(app.CFG, 'NMJv2', 'nmjv2_database', '')
            app.NMJv2_DBLOC = check_setting_str(app.CFG, 'NMJv2', 'nmjv2_dbloc', '')

            app.USE_SYNOINDEX = bool(check_setting_int(app.CFG, 'Synology', 'use_synoindex', 0))

            app.USE_SYNOLOGYNOTIFIER = bool(check_setting_int(app.CFG, 'SynologyNotifier', 'use_synologynotifier', 0))
            app.SYNOLOGYNOTIFIER_NOTIFY_ONSNATCH = bool(check_setting_int(app.CFG, 'SynologyNotifier', 'synologynotifier_notify_onsnatch', 0))
            app.SYNOLOGYNOTIFIER_NOTIFY_ONDOWNLOAD = bool(check_setting_int(app.CFG, 'SynologyNotifier', 'synologynotifier_notify_ondownload', 0))
            app.SYNOLOGYNOTIFIER_NOTIFY_ONSUBTITLEDOWNLOAD = bool(
                check_setting_int(app.CFG, 'SynologyNotifier', 'synologynotifier_notify_onsubtitledownload', 0))

            app.USE_TRAKT = bool(check_setting_int(app.CFG, 'Trakt', 'use_trakt', 0))
            app.TRAKT_USERNAME = check_setting_str(app.CFG, 'Trakt', 'trakt_username', '', censor_log='normal')
            app.TRAKT_ACCESS_TOKEN = check_setting_str(app.CFG, 'Trakt', 'trakt_access_token', '', censor_log='low')
            app.TRAKT_REFRESH_TOKEN = check_setting_str(app.CFG, 'Trakt', 'trakt_refresh_token', '', censor_log='low')
            app.TRAKT_REMOVE_WATCHLIST = bool(check_setting_int(app.CFG, 'Trakt', 'trakt_remove_watchlist', 0))
            app.TRAKT_REMOVE_SERIESLIST = bool(check_setting_int(app.CFG, 'Trakt', 'trakt_remove_serieslist', 0))

            # Check if user has legacy setting and store value in new setting
            if check_setting_int(app.CFG, 'Trakt', 'trakt_remove_show_from_sickrage', None) is not None:
                app.TRAKT_REMOVE_SHOW_FROM_APPLICATION = bool(check_setting_int(app.CFG, 'Trakt', 'trakt_remove_show_from_sickrage', 0))
            else:
                app.TRAKT_REMOVE_SHOW_FROM_APPLICATION = bool(check_setting_int(app.CFG, 'Trakt', 'trakt_remove_show_from_application', 0))

            app.TRAKT_SYNC_WATCHLIST = bool(check_setting_int(app.CFG, 'Trakt', 'trakt_sync_watchlist', 0))
            app.TRAKT_METHOD_ADD = check_setting_int(app.CFG, 'Trakt', 'trakt_method_add', 0)
            app.TRAKT_START_PAUSED = bool(check_setting_int(app.CFG, 'Trakt', 'trakt_start_paused', 0))
            app.TRAKT_USE_RECOMMENDED = bool(check_setting_int(app.CFG, 'Trakt', 'trakt_use_recommended', 0))
            app.TRAKT_SYNC = bool(check_setting_int(app.CFG, 'Trakt', 'trakt_sync', 0))
            app.TRAKT_SYNC_REMOVE = bool(check_setting_int(app.CFG, 'Trakt', 'trakt_sync_remove', 0))
            app.TRAKT_DEFAULT_INDEXER = check_setting_int(app.CFG, 'Trakt', 'trakt_default_indexer', 1)
            app.TRAKT_TIMEOUT = check_setting_int(app.CFG, 'Trakt', 'trakt_timeout', 30)
            app.TRAKT_BLACKLIST_NAME = check_setting_str(app.CFG, 'Trakt', 'trakt_blacklist_name', '')

            app.USE_PYTIVO = bool(check_setting_int(app.CFG, 'pyTivo', 'use_pytivo', 0))
            app.PYTIVO_NOTIFY_ONSNATCH = bool(check_setting_int(app.CFG, 'pyTivo', 'pytivo_notify_onsnatch', 0))
            app.PYTIVO_NOTIFY_ONDOWNLOAD = bool(check_setting_int(app.CFG, 'pyTivo', 'pytivo_notify_ondownload', 0))
            app.PYTIVO_NOTIFY_ONSUBTITLEDOWNLOAD = bool(check_setting_int(app.CFG, 'pyTivo', 'pytivo_notify_onsubtitledownload', 0))
            app.PYTIVO_UPDATE_LIBRARY = bool(check_setting_int(app.CFG, 'pyTivo', 'pyTivo_update_library', 0))
            app.PYTIVO_HOST = check_setting_str(app.CFG, 'pyTivo', 'pytivo_host', '')
            app.PYTIVO_SHARE_NAME = check_setting_str(app.CFG, 'pyTivo', 'pytivo_share_name', '')
            app.PYTIVO_TIVO_NAME = check_setting_str(app.CFG, 'pyTivo', 'pytivo_tivo_name', '')

            app.USE_NMA = bool(check_setting_int(app.CFG, 'NMA', 'use_nma', 0))
            app.NMA_NOTIFY_ONSNATCH = bool(check_setting_int(app.CFG, 'NMA', 'nma_notify_onsnatch', 0))
            app.NMA_NOTIFY_ONDOWNLOAD = bool(check_setting_int(app.CFG, 'NMA', 'nma_notify_ondownload', 0))
            app.NMA_NOTIFY_ONSUBTITLEDOWNLOAD = bool(check_setting_int(app.CFG, 'NMA', 'nma_notify_onsubtitledownload', 0))
            app.NMA_API = check_setting_str(app.CFG, 'NMA', 'nma_api', '', censor_log='low')
            app.NMA_PRIORITY = check_setting_str(app.CFG, 'NMA', 'nma_priority', "0")

            app.USE_PUSHALOT = bool(check_setting_int(app.CFG, 'Pushalot', 'use_pushalot', 0))
            app.PUSHALOT_NOTIFY_ONSNATCH = bool(check_setting_int(app.CFG, 'Pushalot', 'pushalot_notify_onsnatch', 0))
            app.PUSHALOT_NOTIFY_ONDOWNLOAD = bool(check_setting_int(app.CFG, 'Pushalot', 'pushalot_notify_ondownload', 0))
            app.PUSHALOT_NOTIFY_ONSUBTITLEDOWNLOAD = bool(check_setting_int(app.CFG, 'Pushalot', 'pushalot_notify_onsubtitledownload', 0))
            app.PUSHALOT_AUTHORIZATIONTOKEN = check_setting_str(app.CFG, 'Pushalot', 'pushalot_authorizationtoken', '', censor_log='low')

            app.USE_PUSHBULLET = bool(check_setting_int(app.CFG, 'Pushbullet', 'use_pushbullet', 0))
            app.PUSHBULLET_NOTIFY_ONSNATCH = bool(check_setting_int(app.CFG, 'Pushbullet', 'pushbullet_notify_onsnatch', 0))
            app.PUSHBULLET_NOTIFY_ONDOWNLOAD = bool(check_setting_int(app.CFG, 'Pushbullet', 'pushbullet_notify_ondownload', 0))
            app.PUSHBULLET_NOTIFY_ONSUBTITLEDOWNLOAD = bool(check_setting_int(app.CFG, 'Pushbullet', 'pushbullet_notify_onsubtitledownload', 0))
            app.PUSHBULLET_API = check_setting_str(app.CFG, 'Pushbullet', 'pushbullet_api', '', censor_log='low')
            app.PUSHBULLET_DEVICE = check_setting_str(app.CFG, 'Pushbullet', 'pushbullet_device', '')

            app.USE_EMAIL = bool(check_setting_int(app.CFG, 'Email', 'use_email', 0))
            app.EMAIL_NOTIFY_ONSNATCH = bool(check_setting_int(app.CFG, 'Email', 'email_notify_onsnatch', 0))
            app.EMAIL_NOTIFY_ONDOWNLOAD = bool(check_setting_int(app.CFG, 'Email', 'email_notify_ondownload', 0))
            app.EMAIL_NOTIFY_ONSUBTITLEDOWNLOAD = bool(check_setting_int(app.CFG, 'Email', 'email_notify_onsubtitledownload', 0))
            app.EMAIL_HOST = check_setting_str(app.CFG, 'Email', 'email_host', '')
            app.EMAIL_PORT = check_setting_int(app.CFG, 'Email', 'email_port', 25)
            app.EMAIL_TLS = bool(check_setting_int(app.CFG, 'Email', 'email_tls', 0))
            app.EMAIL_USER = check_setting_str(app.CFG, 'Email', 'email_user', '', censor_log='normal')
            app.EMAIL_PASSWORD = check_setting_str(app.CFG, 'Email', 'email_password', '', censor_log='low')
            app.EMAIL_FROM = check_setting_str(app.CFG, 'Email', 'email_from', '')
            app.EMAIL_LIST = check_setting_str(app.CFG, 'Email', 'email_list', '')
            app.EMAIL_SUBJECT = check_setting_str(app.CFG, 'Email', 'email_subject', '')

            app.USE_SUBTITLES = bool(check_setting_int(app.CFG, 'Subtitles', 'use_subtitles', 0))
            app.SUBTITLES_ERASE_CACHE = bool(check_setting_int(app.CFG, 'Subtitles', 'subtitles_erase_cache', 0))
            app.SUBTITLES_LANGUAGES = check_setting_str(app.CFG, 'Subtitles', 'subtitles_languages', '').split(',')
            if app.SUBTITLES_LANGUAGES[0] == '':
                app.SUBTITLES_LANGUAGES = []
            app.SUBTITLES_DIR = check_setting_str(app.CFG, 'Subtitles', 'subtitles_dir', '')
            app.SUBTITLES_SERVICES_LIST = check_setting_str(app.CFG, 'Subtitles', 'SUBTITLES_SERVICES_LIST', '').split(',')
            app.SUBTITLES_SERVICES_ENABLED = [int(x) for x in check_setting_str(app.CFG, 'Subtitles', 'SUBTITLES_SERVICES_ENABLED', '').split('|') if x]
            app.SUBTITLES_DEFAULT = bool(check_setting_int(app.CFG, 'Subtitles', 'subtitles_default', 0))
            app.SUBTITLES_HISTORY = bool(check_setting_int(app.CFG, 'Subtitles', 'subtitles_history', 0))
            app.SUBTITLES_PERFECT_MATCH = bool(check_setting_int(app.CFG, 'Subtitles', 'subtitles_perfect_match', 1))
            app.IGNORE_EMBEDDED_SUBS = bool(check_setting_int(app.CFG, 'Subtitles', 'embedded_subtitles_all', 0))
            app.SUBTITLES_STOP_AT_FIRST = bool(check_setting_int(app.CFG, 'Subtitles', 'subtitles_stop_at_first', 0))
            app.ACCEPT_UNKNOWN_EMBEDDED_SUBS = bool(check_setting_int(app.CFG, 'Subtitles', 'embedded_subtitles_unknown_lang', 0))
            app.SUBTITLES_HEARING_IMPAIRED = bool(check_setting_int(app.CFG, 'Subtitles', 'subtitles_hearing_impaired', 0))
            app.SUBTITLES_FINDER_FREQUENCY = check_setting_int(app.CFG, 'Subtitles', 'subtitles_finder_frequency', 1)
            app.SUBTITLES_MULTI = bool(check_setting_int(app.CFG, 'Subtitles', 'subtitles_multi', 1))
            app.SUBTITLES_KEEP_ONLY_WANTED = bool(check_setting_int(app.CFG, 'Subtitles', 'subtitles_keep_only_wanted', 0))
            app.SUBTITLES_EXTRA_SCRIPTS = [x.strip() for x in check_setting_str(app.CFG, 'Subtitles', 'subtitles_extra_scripts', '').split('|') if x.strip()]
            app.SUBTITLES_PRE_SCRIPTS = [x.strip() for x in check_setting_str(app.CFG, 'Subtitles', 'subtitles_pre_scripts', '').split('|') if x.strip()]

            app.ADDIC7ED_USER = check_setting_str(app.CFG, 'Subtitles', 'addic7ed_username', '', censor_log='normal')
            app.ADDIC7ED_PASS = check_setting_str(app.CFG, 'Subtitles', 'addic7ed_password', '', censor_log='low')

            app.ITASA_USER = check_setting_str(app.CFG, 'Subtitles', 'itasa_username', '', censor_log='normal')
            app.ITASA_PASS = check_setting_str(app.CFG, 'Subtitles', 'itasa_password', '', censor_log='low')

            app.LEGENDASTV_USER = check_setting_str(app.CFG, 'Subtitles', 'legendastv_username', '', censor_log='normal')
            app.LEGENDASTV_PASS = check_setting_str(app.CFG, 'Subtitles', 'legendastv_password', '', censor_log='low')

            app.OPENSUBTITLES_USER = check_setting_str(app.CFG, 'Subtitles', 'opensubtitles_username', '', censor_log='normal')
            app.OPENSUBTITLES_PASS = check_setting_str(app.CFG, 'Subtitles', 'opensubtitles_password', '', censor_log='low')

            app.USE_FAILED_DOWNLOADS = bool(check_setting_int(app.CFG, 'FailedDownloads', 'use_failed_downloads', 0))
            app.DELETE_FAILED = bool(check_setting_int(app.CFG, 'FailedDownloads', 'delete_failed', 0))

            app.GIT_PATH = check_setting_str(app.CFG, 'General', 'git_path', '')

            app.IGNORE_WORDS = check_setting_str(app.CFG, 'General', 'ignore_words', app.IGNORE_WORDS)
            app.PREFERRED_WORDS = check_setting_str(app.CFG, 'General', 'preferred_words', app.PREFERRED_WORDS)
            app.UNDESIRED_WORDS = check_setting_str(app.CFG, 'General', 'undesired_words', app.UNDESIRED_WORDS)
            app.TRACKERS_LIST = check_setting_str(app.CFG, 'General', 'trackers_list', app.TRACKERS_LIST)
            app.REQUIRE_WORDS = check_setting_str(app.CFG, 'General', 'require_words', app.REQUIRE_WORDS)
            app.IGNORED_SUBS_LIST = check_setting_str(app.CFG, 'General', 'ignored_subs_list', app.IGNORED_SUBS_LIST)
            app.IGNORE_UND_SUBS = bool(check_setting_int(app.CFG, 'General', 'ignore_und_subs', app.IGNORE_UND_SUBS))

            app.CALENDAR_UNPROTECTED = bool(check_setting_int(app.CFG, 'General', 'calendar_unprotected', 0))
            app.CALENDAR_ICONS = bool(check_setting_int(app.CFG, 'General', 'calendar_icons', 0))

            app.NO_RESTART = bool(check_setting_int(app.CFG, 'General', 'no_restart', 0))

            app.EXTRA_SCRIPTS = [x.strip() for x in check_setting_str(app.CFG, 'General', 'extra_scripts', '').split('|') if
                                 x.strip()]

            app.USE_LISTVIEW = bool(check_setting_int(app.CFG, 'General', 'use_listview', 0))

            app.ANIMESUPPORT = False
            app.USE_ANIDB = bool(check_setting_int(app.CFG, 'ANIDB', 'use_anidb', 0))
            app.ANIDB_USERNAME = check_setting_str(app.CFG, 'ANIDB', 'anidb_username', '', censor_log='normal')
            app.ANIDB_PASSWORD = check_setting_str(app.CFG, 'ANIDB', 'anidb_password', '', censor_log='low')
            app.ANIDB_USE_MYLIST = bool(check_setting_int(app.CFG, 'ANIDB', 'anidb_use_mylist', 0))
            app.ANIME_SPLIT_HOME = bool(check_setting_int(app.CFG, 'ANIME', 'anime_split_home', 0))

            app.METADATA_KODI = check_setting_str(app.CFG, 'General', 'metadata_kodi', '0|0|0|0|0|0|0|0|0|0')
            app.METADATA_KODI_12PLUS = check_setting_str(app.CFG, 'General', 'metadata_kodi_12plus', '0|0|0|0|0|0|0|0|0|0')
            app.METADATA_MEDIABROWSER = check_setting_str(app.CFG, 'General', 'metadata_mediabrowser', '0|0|0|0|0|0|0|0|0|0')
            app.METADATA_PS3 = check_setting_str(app.CFG, 'General', 'metadata_ps3', '0|0|0|0|0|0|0|0|0|0')
            app.METADATA_WDTV = check_setting_str(app.CFG, 'General', 'metadata_wdtv', '0|0|0|0|0|0|0|0|0|0')
            app.METADATA_TIVO = check_setting_str(app.CFG, 'General', 'metadata_tivo', '0|0|0|0|0|0|0|0|0|0')
            app.METADATA_MEDE8ER = check_setting_str(app.CFG, 'General', 'metadata_mede8er', '0|0|0|0|0|0|0|0|0|0')

            app.HOME_LAYOUT = check_setting_str(app.CFG, 'GUI', 'home_layout', 'poster')
            app.HISTORY_LAYOUT = check_setting_str(app.CFG, 'GUI', 'history_layout', 'detailed')
            app.HISTORY_LIMIT = check_setting_str(app.CFG, 'GUI', 'history_limit', '100')
            app.DISPLAY_SHOW_SPECIALS = bool(check_setting_int(app.CFG, 'GUI', 'display_show_specials', 1))
            app.COMING_EPS_LAYOUT = check_setting_str(app.CFG, 'GUI', 'coming_eps_layout', 'banner')
            app.COMING_EPS_DISPLAY_PAUSED = bool(check_setting_int(app.CFG, 'GUI', 'coming_eps_display_paused', 0))
            app.COMING_EPS_SORT = check_setting_str(app.CFG, 'GUI', 'coming_eps_sort', 'date')
            app.COMING_EPS_MISSED_RANGE = check_setting_int(app.CFG, 'GUI', 'coming_eps_missed_range', 7)
            app.FUZZY_DATING = bool(check_setting_int(app.CFG, 'GUI', 'fuzzy_dating', 0))
            app.TRIM_ZERO = bool(check_setting_int(app.CFG, 'GUI', 'trim_zero', 0))
            app.DATE_PRESET = check_setting_str(app.CFG, 'GUI', 'date_preset', '%x')
            app.TIME_PRESET_W_SECONDS = check_setting_str(app.CFG, 'GUI', 'time_preset', '%I:%M:%S %p')
            app.TIME_PRESET = app.TIME_PRESET_W_SECONDS.replace(u":%S", u"")
            app.TIMEZONE_DISPLAY = check_setting_str(app.CFG, 'GUI', 'timezone_display', 'local')
            app.POSTER_SORTBY = check_setting_str(app.CFG, 'GUI', 'poster_sortby', 'name')
            app.POSTER_SORTDIR = check_setting_int(app.CFG, 'GUI', 'poster_sortdir', 1)
            app.DISPLAY_ALL_SEASONS = bool(check_setting_int(app.CFG, 'General', 'display_all_seasons', 1))
            app.RECENTLY_DELETED = set()
            app.RELEASES_IN_PP = []
            app.GIT_REMOTE_BRANCHES = []
            app.KODI_LIBRARY_CLEAN_PENDING = False

            # reconfigure the logger
            app_logger.reconfigure()

            # initialize static configuration
            try:
                import pwd
                app.OS_USER = pwd.getpwuid(os.getuid()).pw_name
            except ImportError:
                try:
                    import getpass
                    app.OS_USER = getpass.getuser()
                except StandardError:
                    pass

            try:
                app.LOCALE = locale.getdefaultlocale()
            except StandardError:
                app.LOCALE = None, None

            try:
                import ssl
                app.OPENSSL_VERSION = ssl.OPENSSL_VERSION
            except StandardError:
                pass

            if app.VERSION_NOTIFY:
                updater = version_checker.CheckVersion().updater
                if updater:
                    app.APP_VERSION = updater.get_cur_version()

            app.MAJOR_DB_VERSION, app.MINOR_DB_VERSION = db.DBConnection().checkDBVersion()

            # initialize NZB and TORRENT providers
            app.providerList = providers.make_provider_list()

            app.NEWZNAB_DATA = check_setting_str(app.CFG, 'Newznab', 'newznab_data', '')
            app.newznabProviderList = NewznabProvider.get_providers_list(app.NEWZNAB_DATA)

            app.TORRENTRSS_DATA = check_setting_str(app.CFG, 'TorrentRss', 'torrentrss_data', '')
            app.torrentRssProviderList = TorrentRssProvider.get_providers_list(app.TORRENTRSS_DATA)

            all_providers = providers.sorted_provider_list()

            # dynamically load provider settings
            for provider in all_providers:
                # use check_setting_bool to see if the provider is enabled instead of load_provider_settings
                # since the attr name does not match the default provider option style of '{provider}_{attribute}'
                provider.enabled = check_setting_bool(app.CFG, provider.get_id().upper(), provider.get_id(), 0)

                load_provider_setting(app.CFG, provider, 'string', 'username', '', censor_log='normal')
                load_provider_setting(app.CFG, provider, 'string', 'api_key', '', censor_log='low')
                load_provider_setting(app.CFG, provider, 'string', 'search_mode', 'eponly')
                load_provider_setting(app.CFG, provider, 'bool', 'search_fallback', 0)
                load_provider_setting(app.CFG, provider, 'bool', 'enable_daily', 1)
                load_provider_setting(app.CFG, provider, 'bool', 'enable_backlog', provider.supports_backlog)
                load_provider_setting(app.CFG, provider, 'bool', 'enable_manualsearch', 1)

                if provider.provider_type == GenericProvider.TORRENT:
                    load_provider_setting(app.CFG, provider, 'string', 'custom_url', '', censor_log='low')
                    load_provider_setting(app.CFG, provider, 'string', 'hash', '', censor_log='low')
                    load_provider_setting(app.CFG, provider, 'string', 'digest', '', censor_log='low')
                    load_provider_setting(app.CFG, provider, 'string', 'password', '', censor_log='low')
                    load_provider_setting(app.CFG, provider, 'string', 'passkey', '', censor_log='low')
                    load_provider_setting(app.CFG, provider, 'string', 'pin', '', censor_log='low')
                    load_provider_setting(app.CFG, provider, 'string', 'sorting', 'seeders')
                    load_provider_setting(app.CFG, provider, 'string', 'options', '')
                    load_provider_setting(app.CFG, provider, 'string', 'ratio', '')
                    load_provider_setting(app.CFG, provider, 'bool', 'confirmed', 1)
                    load_provider_setting(app.CFG, provider, 'bool', 'ranked', 1)
                    load_provider_setting(app.CFG, provider, 'bool', 'engrelease', 0)
                    load_provider_setting(app.CFG, provider, 'bool', 'onlyspasearch', 0)
                    load_provider_setting(app.CFG, provider, 'int', 'minseed', 1)
                    load_provider_setting(app.CFG, provider, 'int', 'minleech', 0)
                    load_provider_setting(app.CFG, provider, 'bool', 'freeleech', 0)
                    load_provider_setting(app.CFG, provider, 'int', 'cat', 0)
                    load_provider_setting(app.CFG, provider, 'bool', 'subtitle', 0)
                    if provider.enable_cookies:
                        load_provider_setting(app.CFG, provider, 'string', 'cookies', '', censor_log='low')

            if not os.path.isfile(app.CONFIG_FILE):
                logger.debug(u"Unable to find '{config}', all settings will be default!", config=app.CONFIG_FILE)
                self.save_config()

            if app.SUBTITLES_ERASE_CACHE:
                try:
                    for cache_file in ['application.dbm', 'subliminal.dbm']:
                        file_path = os.path.join(app.CACHE_DIR, cache_file)
                        if os.path.isfile(file_path):
                            logger.info(u"Removing subtitles cache file: {cache_file}", cache_file=file_path)
                            os.remove(file_path)
                except OSError as e:
                    logger.warning(u"Unable to remove subtitles cache files. Error: {error}", error=e)
                # Disable flag to erase cache
                app.SUBTITLES_ERASE_CACHE = 0

            # initialize the main SB database
            main_db_con = db.DBConnection()
            db.upgradeDatabase(main_db_con, main_db.InitialSchema)

            # initialize the cache database
            cache_db_con = db.DBConnection('cache.db')
            db.upgradeDatabase(cache_db_con, cache_db.InitialSchema)

            # Performs a vacuum on cache.db
            logger.debug(u'Performing a vacuum on the CACHE database')
            cache_db_con.action('VACUUM')

            # initialize the failed downloads database
            failed_db_con = db.DBConnection('failed.db')
            db.upgradeDatabase(failed_db_con, failed_db.InitialSchema)

            # fix up any db problems
            main_db_con = db.DBConnection()
            db.sanityCheckDatabase(main_db_con, main_db.MainSanityCheck)

            # migrate the config if it needs it
            migrator = ConfigMigrator(app.CFG)
            migrator.migrate_config()

            # initialize metadata_providers
            app.metadata_provider_dict = metadata.get_metadata_generator_dict()
            for cur_metadata_tuple in [(app.METADATA_KODI, metadata.kodi),
                                       (app.METADATA_KODI_12PLUS, metadata.kodi_12plus),
                                       (app.METADATA_MEDIABROWSER, metadata.media_browser),
                                       (app.METADATA_PS3, metadata.ps3),
                                       (app.METADATA_WDTV, metadata.wdtv),
                                       (app.METADATA_TIVO, metadata.tivo),
                                       (app.METADATA_MEDE8ER, metadata.mede8er)]:
                (cur_metadata_config, cur_metadata_class) = cur_metadata_tuple
                tmp_provider = cur_metadata_class.metadata_class()
                tmp_provider.set_config(cur_metadata_config)
                app.metadata_provider_dict[tmp_provider.name] = tmp_provider

            # initialize schedulers
            # updaters
            app.version_check_scheduler = scheduler.Scheduler(version_checker.CheckVersion(),
                                                              cycleTime=datetime.timedelta(hours=app.UPDATE_FREQUENCY),
                                                              threadName="CHECKVERSION", silent=False)

            app.show_queue_scheduler = scheduler.Scheduler(show_queue.ShowQueue(),
                                                           cycleTime=datetime.timedelta(seconds=3),
                                                           threadName="SHOWQUEUE")

            app.show_update_scheduler = scheduler.Scheduler(show_updater.ShowUpdater(),
                                                            cycleTime=datetime.timedelta(hours=1),
                                                            threadName="SHOWUPDATER",
                                                            start_time=datetime.time(hour=app.SHOWUPDATE_HOUR,
                                                                                     minute=random.randint(0, 59)))

            # snatcher used for manual search, manual picked results
            app.manual_snatch_scheduler = scheduler.Scheduler(SnatchQueue(),
                                                              cycleTime=datetime.timedelta(seconds=3),
                                                              threadName="MANUALSNATCHQUEUE")
            # searchers
            app.search_queue_scheduler = scheduler.Scheduler(SearchQueue(),
                                                             cycleTime=datetime.timedelta(seconds=3),
                                                             threadName="SEARCHQUEUE")

            app.forced_search_queue_scheduler = scheduler.Scheduler(ForcedSearchQueue(),
                                                                    cycleTime=datetime.timedelta(seconds=3),
                                                                    threadName="FORCEDSEARCHQUEUE")

            # TODO: update_interval should take last daily/backlog times into account!
            update_interval = datetime.timedelta(minutes=app.DAILYSEARCH_FREQUENCY)
            app.daily_search_scheduler = scheduler.Scheduler(DailySearcher(),
                                                             cycleTime=update_interval,
                                                             threadName="DAILYSEARCHER",
                                                             run_delay=update_interval)

            update_interval = datetime.timedelta(minutes=app.BACKLOG_FREQUENCY)
            app.backlog_search_scheduler = BacklogSearchScheduler(BacklogSearcher(),
                                                                  cycleTime=update_interval,
                                                                  threadName="BACKLOG",
                                                                  run_delay=update_interval)

            search_intervals = {'15m': 15, '45m': 45, '90m': 90, '4h': 4 * 60, 'daily': 24 * 60}
            if app.CHECK_PROPERS_INTERVAL in search_intervals:
                update_interval = datetime.timedelta(minutes=search_intervals[app.CHECK_PROPERS_INTERVAL])
                run_at = None
            else:
                update_interval = datetime.timedelta(hours=1)
                run_at = datetime.time(hour=1)  # 1 AM

            app.proper_finder_scheduler = scheduler.Scheduler(ProperFinder(),
                                                              cycleTime=update_interval,
                                                              threadName="FINDPROPERS",
                                                              start_time=run_at,
                                                              run_delay=update_interval)

            # processors
            update_interval = datetime.timedelta(minutes=app.AUTOPOSTPROCESSOR_FREQUENCY)
            app.auto_post_processor_scheduler = scheduler.Scheduler(auto_post_processor.PostProcessor(),
                                                                    cycleTime=update_interval,
                                                                    threadName="POSTPROCESSOR",
                                                                    silent=not app.PROCESS_AUTOMATICALLY,
                                                                    run_delay=update_interval)
            update_interval = datetime.timedelta(minutes=5)
            app.trakt_checker_scheduler = scheduler.Scheduler(trakt_checker.TraktChecker(),
                                                              cycleTime=datetime.timedelta(hours=1),
                                                              threadName="TRAKTCHECKER",
                                                              run_delay=update_interval,
                                                              silent=not app.USE_TRAKT)

            update_interval = datetime.timedelta(hours=app.SUBTITLES_FINDER_FREQUENCY)
            app.subtitles_finder_scheduler = scheduler.Scheduler(subtitles.SubtitlesFinder(),
                                                                 cycleTime=update_interval,
                                                                 threadName="FINDSUBTITLES",
                                                                 run_delay=update_interval,
                                                                 silent=not app.USE_SUBTITLES)

            update_interval = datetime.timedelta(minutes=app.TORRENT_CHECKER_FREQUENCY)
            app.torrent_checker_scheduler = scheduler.Scheduler(torrent_checker.TorrentChecker(),
                                                                cycleTime=update_interval,
                                                                threadName="TORRENTCHECKER",
                                                                run_delay=update_interval)

            app.__INITIALIZED__ = True
            return True

    @staticmethod
    def get_backlog_cycle_time():
        """Return backlog cycle frequency."""
        cycletime = app.DAILYSEARCH_FREQUENCY * 2 + 7
        return max([cycletime, 720])

    @staticmethod
    def restore_cache_folder(cache_folder):
        """Restore cache folder.

        :param cache_folder:
        :type cache_folder: string
        """
        restore_folder = os.path.join(app.DATA_DIR, 'restore')
        if not os.path.exists(restore_folder) or not os.path.exists(os.path.join(restore_folder, 'cache')):
            return

        try:
            def restore_cache(src_folder, dest_folder):
                def path_leaf(path):
                    head, tail = os.path.split(path)
                    return tail or os.path.basename(head)

                try:
                    if os.path.isdir(dest_folder):
                        bak_filename = '{0}-{1}'.format(path_leaf(dest_folder), datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
                        shutil.move(dest_folder, os.path.join(os.path.dirname(dest_folder), bak_filename))

                    shutil.move(src_folder, dest_folder)
                    logger.log(u"Restore: restoring cache successful", logger.INFO)
                except OSError as e:
                    logger.log(u"Restore: restoring cache failed: {0!r}".format(e), logger.ERROR)

            restore_cache(os.path.join(restore_folder, 'cache'), cache_folder)
        finally:
            helpers.remove_folder(restore_folder)
            for name in ('mako', 'sessions', 'indexers', 'rss'):
                folder_path = os.path.join(cache_folder, name)
                helpers.remove_folder(folder_path)

    @staticmethod
    def start_threads():
        """Start application threads."""
        with app.INIT_LOCK:
            if not app.__INITIALIZED__:
                return

            # start system events queue
            app.events.start()

            # start the daily search scheduler
            app.daily_search_scheduler.enable = True
            app.daily_search_scheduler.start()

            # start the backlog scheduler
            app.backlog_search_scheduler.enable = True
            app.backlog_search_scheduler.start()

            # start the show updater
            app.show_update_scheduler.enable = True
            app.show_update_scheduler.start()

            # start the version checker
            app.version_check_scheduler.enable = True
            app.version_check_scheduler.start()

            # start the queue checker
            app.show_queue_scheduler.enable = True
            app.show_queue_scheduler.start()

            # start the search queue checker
            app.search_queue_scheduler.enable = True
            app.search_queue_scheduler.start()

            # start the forced search queue checker
            app.forced_search_queue_scheduler.enable = True
            app.forced_search_queue_scheduler.start()

            # start the search queue checker
            app.manual_snatch_scheduler.enable = True
            app.manual_snatch_scheduler.start()

            # start the proper finder
            if app.DOWNLOAD_PROPERS:
                app.proper_finder_scheduler.silent = False
                app.proper_finder_scheduler.enable = True
            else:
                app.proper_finder_scheduler.enable = False
                app.proper_finder_scheduler.silent = True
            app.proper_finder_scheduler.start()

            # start the post processor
            if app.PROCESS_AUTOMATICALLY:
                app.auto_post_processor_scheduler.silent = False
                app.auto_post_processor_scheduler.enable = True
            else:
                app.auto_post_processor_scheduler.enable = False
                app.auto_post_processor_scheduler.silent = True
            app.auto_post_processor_scheduler.start()

            # start the subtitles finder
            if app.USE_SUBTITLES:
                app.subtitles_finder_scheduler.silent = False
                app.subtitles_finder_scheduler.enable = True
            else:
                app.subtitles_finder_scheduler.enable = False
                app.subtitles_finder_scheduler.silent = True
            app.subtitles_finder_scheduler.start()

            # start the trakt checker
            if app.USE_TRAKT:
                app.trakt_checker_scheduler.silent = False
                app.trakt_checker_scheduler.enable = True
            else:
                app.trakt_checker_scheduler.enable = False
                app.trakt_checker_scheduler.silent = True
            app.trakt_checker_scheduler.start()

            if app.USE_TORRENTS and app.REMOVE_FROM_CLIENT:
                app.torrent_checker_scheduler.enable = True
            app.torrent_checker_scheduler.silent = False
            app.torrent_checker_scheduler.start()

            app.started = True

    @staticmethod
    def halt():
        """Halt the system."""
        with app.INIT_LOCK:
            if not app.__INITIALIZED__:
                return

            logger.info(u'Aborting all threads')

            threads = [
                app.daily_search_scheduler,
                app.backlog_search_scheduler,
                app.show_update_scheduler,
                app.version_check_scheduler,
                app.show_queue_scheduler,
                app.search_queue_scheduler,
                app.forced_search_queue_scheduler,
                app.manual_snatch_scheduler,
                app.auto_post_processor_scheduler,
                app.trakt_checker_scheduler,
                app.proper_finder_scheduler,
                app.subtitles_finder_scheduler,
                app.torrent_checker_scheduler,
                app.events
            ]

            # set them all to stop at the same time
            for t in threads:
                t.stop.set()

            for t in threads:
                logger.info(u'Waiting for the {thread} thread to exit', thread=t.name)
                try:
                    t.join(10)
                except Exception:
                    pass

            if app.ADBA_CONNECTION:
                app.ADBA_CONNECTION.logout()
                logger.info(u'Waiting for the ANIDB CONNECTION thread to exit')
                try:
                    app.ADBA_CONNECTION.join(10)
                except Exception:
                    pass

            app.__INITIALIZED__ = False
            app.started = False

    def save_all(self):
        """Save all information to database and config file."""
        # write all shows
        logger.info(u'Saving all shows to the database')
        for show in app.showList:
            show.save_to_db()

        # save config
        logger.info(u'Saving config file to disk')
        self.save_config()

    @staticmethod
    def save_config():
        """Save configuration."""
        new_config = ConfigObj(encoding='UTF-8', default_encoding='UTF-8')
        new_config.filename = app.CONFIG_FILE

        # For passwords you must include the word `password` in the item_name
        # and add `helpers.encrypt(ITEM_NAME, ENCRYPTION_VERSION)` in save_config()
        new_config['General'] = {}
        new_config['General']['git_username'] = app.GIT_USERNAME
        new_config['General']['git_password'] = helpers.encrypt(app.GIT_PASSWORD, app.ENCRYPTION_VERSION)
        new_config['General']['git_reset'] = int(app.GIT_RESET)
        new_config['General']['git_reset_branches'] = ','.join(app.GIT_RESET_BRANCHES)
        new_config['General']['branch'] = app.BRANCH
        new_config['General']['git_remote'] = app.GIT_REMOTE
        new_config['General']['git_remote_url'] = app.GIT_REMOTE_URL
        new_config['General']['cur_commit_hash'] = app.CUR_COMMIT_HASH
        new_config['General']['cur_commit_branch'] = app.CUR_COMMIT_BRANCH
        new_config['General']['config_version'] = app.CONFIG_VERSION
        new_config['General']['encryption_version'] = int(app.ENCRYPTION_VERSION)
        new_config['General']['encryption_secret'] = app.ENCRYPTION_SECRET
        new_config['General']['log_dir'] = app.ACTUAL_LOG_DIR if app.ACTUAL_LOG_DIR else 'Logs'
        new_config['General']['log_nr'] = int(app.LOG_NR)
        new_config['General']['log_size'] = float(app.LOG_SIZE)
        new_config['General']['socket_timeout'] = app.SOCKET_TIMEOUT
        new_config['General']['web_port'] = app.WEB_PORT
        new_config['General']['web_host'] = app.WEB_HOST
        new_config['General']['web_ipv6'] = int(app.WEB_IPV6)
        new_config['General']['web_log'] = int(app.WEB_LOG)
        new_config['General']['web_root'] = app.WEB_ROOT
        new_config['General']['web_username'] = app.WEB_USERNAME
        new_config['General']['web_password'] = helpers.encrypt(app.WEB_PASSWORD, app.ENCRYPTION_VERSION)
        new_config['General']['web_cookie_secret'] = app.WEB_COOKIE_SECRET
        new_config['General']['web_use_gzip'] = int(app.WEB_USE_GZIP)
        new_config['General']['subliminal_log'] = int(app.SUBLIMINAL_LOG)
        new_config['General']['privacy_level'] = app.PRIVACY_LEVEL
        new_config['General']['ssl_verify'] = int(app.SSL_VERIFY)
        new_config['General']['download_url'] = app.DOWNLOAD_URL
        new_config['General']['localhost_ip'] = app.LOCALHOST_IP
        new_config['General']['cpu_preset'] = app.CPU_PRESET
        new_config['General']['anon_redirect'] = app.ANON_REDIRECT
        new_config['General']['api_key'] = app.API_KEY
        new_config['General']['debug'] = int(app.DEBUG)
        new_config['General']['dbdebug'] = int(app.DBDEBUG)
        new_config['General']['default_page'] = app.DEFAULT_PAGE
        new_config['General']['seeders_leechers_in_notify'] = int(app.SEEDERS_LEECHERS_IN_NOTIFY)
        new_config['General']['enable_https'] = int(app.ENABLE_HTTPS)
        new_config['General']['notify_on_login'] = int(app.NOTIFY_ON_LOGIN)
        new_config['General']['https_cert'] = app.HTTPS_CERT
        new_config['General']['https_key'] = app.HTTPS_KEY
        new_config['General']['handle_reverse_proxy'] = int(app.HANDLE_REVERSE_PROXY)
        new_config['General']['use_nzbs'] = int(app.USE_NZBS)
        new_config['General']['use_torrents'] = int(app.USE_TORRENTS)
        new_config['General']['nzb_method'] = app.NZB_METHOD
        new_config['General']['torrent_method'] = app.TORRENT_METHOD
        new_config['General']['usenet_retention'] = int(app.USENET_RETENTION)
        new_config['General']['cache_trimming'] = int(app.CACHE_TRIMMING)
        new_config['General']['max_cache_age'] = int(app.MAX_CACHE_AGE)
        new_config['General']['autopostprocessor_frequency'] = int(app.AUTOPOSTPROCESSOR_FREQUENCY)
        new_config['General']['torrent_checker_frequency'] = int(app.TORRENT_CHECKER_FREQUENCY)
        new_config['General']['dailysearch_frequency'] = int(app.DAILYSEARCH_FREQUENCY)
        new_config['General']['backlog_frequency'] = int(app.BACKLOG_FREQUENCY)
        new_config['General']['update_frequency'] = int(app.UPDATE_FREQUENCY)
        new_config['General']['showupdate_hour'] = int(app.SHOWUPDATE_HOUR)
        new_config['General']['download_propers'] = int(app.DOWNLOAD_PROPERS)
        new_config['General']['propers_search_days'] = int(app.PROPERS_SEARCH_DAYS)
        new_config['General']['remove_from_client'] = int(app.REMOVE_FROM_CLIENT)
        new_config['General']['randomize_providers'] = int(app.RANDOMIZE_PROVIDERS)
        new_config['General']['check_propers_interval'] = app.CHECK_PROPERS_INTERVAL
        new_config['General']['allow_high_priority'] = int(app.ALLOW_HIGH_PRIORITY)
        new_config['General']['skip_removed_files'] = int(app.SKIP_REMOVED_FILES)
        new_config['General']['allowed_extensions'] = app.ALLOWED_EXTENSIONS
        new_config['General']['quality_default'] = int(app.QUALITY_DEFAULT)
        new_config['General']['status_default'] = int(app.STATUS_DEFAULT)
        new_config['General']['status_default_after'] = int(app.STATUS_DEFAULT_AFTER)
        new_config['General']['flatten_folders_default'] = int(app.FLATTEN_FOLDERS_DEFAULT)
        new_config['General']['indexer_default'] = int(app.INDEXER_DEFAULT)
        new_config['General']['indexer_timeout'] = int(app.INDEXER_TIMEOUT)
        new_config['General']['anime_default'] = int(app.ANIME_DEFAULT)
        new_config['General']['scene_default'] = int(app.SCENE_DEFAULT)
        new_config['General']['provider_order'] = ' '.join(app.PROVIDER_ORDER)
        new_config['General']['version_notify'] = int(app.VERSION_NOTIFY)
        new_config['General']['auto_update'] = int(app.AUTO_UPDATE)
        new_config['General']['notify_on_update'] = int(app.NOTIFY_ON_UPDATE)
        new_config['General']['naming_strip_year'] = int(app.NAMING_STRIP_YEAR)
        new_config['General']['naming_pattern'] = app.NAMING_PATTERN
        new_config['General']['naming_custom_abd'] = int(app.NAMING_CUSTOM_ABD)
        new_config['General']['naming_abd_pattern'] = app.NAMING_ABD_PATTERN
        new_config['General']['naming_custom_sports'] = int(app.NAMING_CUSTOM_SPORTS)
        new_config['General']['naming_sports_pattern'] = app.NAMING_SPORTS_PATTERN
        new_config['General']['naming_custom_anime'] = int(app.NAMING_CUSTOM_ANIME)
        new_config['General']['naming_anime_pattern'] = app.NAMING_ANIME_PATTERN
        new_config['General']['naming_multi_ep'] = int(app.NAMING_MULTI_EP)
        new_config['General']['naming_anime_multi_ep'] = int(app.NAMING_ANIME_MULTI_EP)
        new_config['General']['naming_anime'] = int(app.NAMING_ANIME)
        new_config['General']['indexerDefaultLang'] = app.INDEXER_DEFAULT_LANGUAGE
        new_config['General']['ep_default_deleted_status'] = int(app.EP_DEFAULT_DELETED_STATUS)
        new_config['General']['launch_browser'] = int(app.LAUNCH_BROWSER)
        new_config['General']['trash_remove_show'] = int(app.TRASH_REMOVE_SHOW)
        new_config['General']['trash_rotate_logs'] = int(app.TRASH_ROTATE_LOGS)
        new_config['General']['sort_article'] = int(app.SORT_ARTICLE)
        new_config['General']['proxy_setting'] = app.PROXY_SETTING
        new_config['General']['proxy_indexers'] = int(app.PROXY_INDEXERS)

        new_config['General']['use_listview'] = int(app.USE_LISTVIEW)
        new_config['General']['metadata_kodi'] = app.METADATA_KODI
        new_config['General']['metadata_kodi_12plus'] = app.METADATA_KODI_12PLUS
        new_config['General']['metadata_mediabrowser'] = app.METADATA_MEDIABROWSER
        new_config['General']['metadata_ps3'] = app.METADATA_PS3
        new_config['General']['metadata_wdtv'] = app.METADATA_WDTV
        new_config['General']['metadata_tivo'] = app.METADATA_TIVO
        new_config['General']['metadata_mede8er'] = app.METADATA_MEDE8ER

        new_config['General']['backlog_days'] = int(app.BACKLOG_DAYS)

        new_config['General']['cache_dir'] = app.ACTUAL_CACHE_DIR if app.ACTUAL_CACHE_DIR else 'cache'
        new_config['General']['root_dirs'] = app.ROOT_DIRS if app.ROOT_DIRS else ''
        new_config['General']['tv_download_dir'] = app.TV_DOWNLOAD_DIR
        new_config['General']['keep_processed_dir'] = int(app.KEEP_PROCESSED_DIR)
        new_config['General']['process_method'] = app.PROCESS_METHOD
        new_config['General']['del_rar_contents'] = int(app.DELRARCONTENTS)
        new_config['General']['move_associated_files'] = int(app.MOVE_ASSOCIATED_FILES)
        new_config['General']['sync_files'] = app.SYNC_FILES
        new_config['General']['postpone_if_sync_files'] = int(app.POSTPONE_IF_SYNC_FILES)
        new_config['General']['postpone_if_no_subs'] = int(app.POSTPONE_IF_NO_SUBS)
        new_config['General']['nfo_rename'] = int(app.NFO_RENAME)
        new_config['General']['process_automatically'] = int(app.PROCESS_AUTOMATICALLY)
        new_config['General']['no_delete'] = int(app.NO_DELETE)
        new_config['General']['unpack'] = int(app.UNPACK)
        new_config['General']['rename_episodes'] = int(app.RENAME_EPISODES)
        new_config['General']['airdate_episodes'] = int(app.AIRDATE_EPISODES)
        new_config['General']['file_timestamp_timezone'] = app.FILE_TIMESTAMP_TIMEZONE
        new_config['General']['create_missing_show_dirs'] = int(app.CREATE_MISSING_SHOW_DIRS)
        new_config['General']['add_shows_wo_dir'] = int(app.ADD_SHOWS_WO_DIR)

        new_config['General']['extra_scripts'] = '|'.join(app.EXTRA_SCRIPTS)
        new_config['General']['git_path'] = app.GIT_PATH
        new_config['General']['ignore_words'] = app.IGNORE_WORDS
        new_config['General']['preferred_words'] = app.PREFERRED_WORDS
        new_config['General']['undesired_words'] = app.UNDESIRED_WORDS
        new_config['General']['trackers_list'] = app.TRACKERS_LIST
        new_config['General']['require_words'] = app.REQUIRE_WORDS
        new_config['General']['ignored_subs_list'] = app.IGNORED_SUBS_LIST
        new_config['General']['ignore_und_subs'] = app.IGNORE_UND_SUBS
        new_config['General']['calendar_unprotected'] = int(app.CALENDAR_UNPROTECTED)
        new_config['General']['calendar_icons'] = int(app.CALENDAR_ICONS)
        new_config['General']['no_restart'] = int(app.NO_RESTART)
        new_config['General']['developer'] = int(app.DEVELOPER)
        new_config['General']['display_all_seasons'] = int(app.DISPLAY_ALL_SEASONS)
        new_config['General']['news_last_read'] = app.NEWS_LAST_READ
        new_config['General']['broken_providers'] = helpers.get_broken_providers() or app.BROKEN_PROVIDERS

        new_config['Blackhole'] = {}
        new_config['Blackhole']['nzb_dir'] = app.NZB_DIR
        new_config['Blackhole']['torrent_dir'] = app.TORRENT_DIR

        # dynamically save provider settings
        all_providers = providers.sorted_provider_list()
        for provider in all_providers:
            name = provider.get_id()
            section = name.upper()

            new_config[section] = {}
            new_config[section][name] = int(provider.enabled)

            attributes = {
                'all': [
                    'api_key', 'username',
                    'search_mode', 'search_fallback',
                    'enable_daily', 'enable_backlog', 'enable_manualsearch',
                ],
                'encrypted': [
                    'password',
                ],
                GenericProvider.TORRENT: [
                    'custom_url', 'digest', 'hash', 'passkey', 'pin', 'confirmed', 'ranked', 'engrelease', 'onlyspasearch',
                    'sorting', 'ratio', 'minseed', 'minleech', 'options', 'freelech', 'cat', 'subtitle', 'cookies',
                ],
                GenericProvider.NZB: [
                ],
            }

            for attr in attributes['all']:
                save_provider_setting(new_config, provider, attr)

            for attr in attributes['encrypted']:
                # encrypt the attribute value first before storing
                encrypted_attribute = helpers.encrypt(getattr(provider, attr, ''), app.ENCRYPTION_VERSION)
                save_provider_setting(new_config, provider, attr, value=encrypted_attribute)

            for provider_type in [GenericProvider.NZB, GenericProvider.TORRENT]:
                if provider_type == provider.provider_type:
                    for attr in attributes[provider_type]:
                        save_provider_setting(new_config, provider, attr)

        new_config['NZBs'] = {}
        new_config['NZBs']['nzbs'] = int(app.NZBS)
        new_config['NZBs']['nzbs_uid'] = app.NZBS_UID
        new_config['NZBs']['nzbs_hash'] = app.NZBS_HASH

        new_config['Newzbin'] = {}
        new_config['Newzbin']['newzbin'] = int(app.NEWZBIN)
        new_config['Newzbin']['newzbin_username'] = app.NEWZBIN_USERNAME
        new_config['Newzbin']['newzbin_password'] = helpers.encrypt(app.NEWZBIN_PASSWORD, app.ENCRYPTION_VERSION)

        new_config['SABnzbd'] = {}
        new_config['SABnzbd']['sab_username'] = app.SAB_USERNAME
        new_config['SABnzbd']['sab_password'] = helpers.encrypt(app.SAB_PASSWORD, app.ENCRYPTION_VERSION)
        new_config['SABnzbd']['sab_apikey'] = app.SAB_APIKEY
        new_config['SABnzbd']['sab_category'] = app.SAB_CATEGORY
        new_config['SABnzbd']['sab_category_backlog'] = app.SAB_CATEGORY_BACKLOG
        new_config['SABnzbd']['sab_category_anime'] = app.SAB_CATEGORY_ANIME
        new_config['SABnzbd']['sab_category_anime_backlog'] = app.SAB_CATEGORY_ANIME_BACKLOG
        new_config['SABnzbd']['sab_host'] = app.SAB_HOST
        new_config['SABnzbd']['sab_forced'] = int(app.SAB_FORCED)

        new_config['NZBget'] = {}

        new_config['NZBget']['nzbget_username'] = app.NZBGET_USERNAME
        new_config['NZBget']['nzbget_password'] = helpers.encrypt(app.NZBGET_PASSWORD, app.ENCRYPTION_VERSION)
        new_config['NZBget']['nzbget_category'] = app.NZBGET_CATEGORY
        new_config['NZBget']['nzbget_category_backlog'] = app.NZBGET_CATEGORY_BACKLOG
        new_config['NZBget']['nzbget_category_anime'] = app.NZBGET_CATEGORY_ANIME
        new_config['NZBget']['nzbget_category_anime_backlog'] = app.NZBGET_CATEGORY_ANIME_BACKLOG
        new_config['NZBget']['nzbget_host'] = app.NZBGET_HOST
        new_config['NZBget']['nzbget_use_https'] = int(app.NZBGET_USE_HTTPS)
        new_config['NZBget']['nzbget_priority'] = app.NZBGET_PRIORITY

        new_config['TORRENT'] = {}
        new_config['TORRENT']['torrent_username'] = app.TORRENT_USERNAME
        new_config['TORRENT']['torrent_password'] = helpers.encrypt(app.TORRENT_PASSWORD, app.ENCRYPTION_VERSION)
        new_config['TORRENT']['torrent_host'] = app.TORRENT_HOST
        new_config['TORRENT']['torrent_path'] = app.TORRENT_PATH
        new_config['TORRENT']['torrent_seed_time'] = int(app.TORRENT_SEED_TIME)
        new_config['TORRENT']['torrent_paused'] = int(app.TORRENT_PAUSED)
        new_config['TORRENT']['torrent_high_bandwidth'] = int(app.TORRENT_HIGH_BANDWIDTH)
        new_config['TORRENT']['torrent_label'] = app.TORRENT_LABEL
        new_config['TORRENT']['torrent_label_anime'] = app.TORRENT_LABEL_ANIME
        new_config['TORRENT']['torrent_verify_cert'] = int(app.TORRENT_VERIFY_CERT)
        new_config['TORRENT']['torrent_rpcurl'] = app.TORRENT_RPCURL
        new_config['TORRENT']['torrent_auth_type'] = app.TORRENT_AUTH_TYPE

        new_config['KODI'] = {}
        new_config['KODI']['use_kodi'] = int(app.USE_KODI)
        new_config['KODI']['kodi_always_on'] = int(app.KODI_ALWAYS_ON)
        new_config['KODI']['kodi_notify_onsnatch'] = int(app.KODI_NOTIFY_ONSNATCH)
        new_config['KODI']['kodi_notify_ondownload'] = int(app.KODI_NOTIFY_ONDOWNLOAD)
        new_config['KODI']['kodi_notify_onsubtitledownload'] = int(app.KODI_NOTIFY_ONSUBTITLEDOWNLOAD)
        new_config['KODI']['kodi_update_library'] = int(app.KODI_UPDATE_LIBRARY)
        new_config['KODI']['kodi_update_full'] = int(app.KODI_UPDATE_FULL)
        new_config['KODI']['kodi_update_onlyfirst'] = int(app.KODI_UPDATE_ONLYFIRST)
        new_config['KODI']['kodi_host'] = app.KODI_HOST
        new_config['KODI']['kodi_username'] = app.KODI_USERNAME
        new_config['KODI']['kodi_password'] = helpers.encrypt(app.KODI_PASSWORD, app.ENCRYPTION_VERSION)
        new_config['KODI']['kodi_clean_library'] = int(app.KODI_CLEAN_LIBRARY)

        new_config['Plex'] = {}
        new_config['Plex']['use_plex_server'] = int(app.USE_PLEX_SERVER)
        new_config['Plex']['plex_notify_onsnatch'] = int(app.PLEX_NOTIFY_ONSNATCH)
        new_config['Plex']['plex_notify_ondownload'] = int(app.PLEX_NOTIFY_ONDOWNLOAD)
        new_config['Plex']['plex_notify_onsubtitledownload'] = int(app.PLEX_NOTIFY_ONSUBTITLEDOWNLOAD)
        new_config['Plex']['plex_update_library'] = int(app.PLEX_UPDATE_LIBRARY)
        new_config['Plex']['plex_server_host'] = app.PLEX_SERVER_HOST
        new_config['Plex']['plex_server_token'] = app.PLEX_SERVER_TOKEN
        new_config['Plex']['plex_client_host'] = app.PLEX_CLIENT_HOST
        new_config['Plex']['plex_server_username'] = app.PLEX_SERVER_USERNAME
        new_config['Plex']['plex_server_password'] = helpers.encrypt(app.PLEX_SERVER_PASSWORD, app.ENCRYPTION_VERSION)

        new_config['Plex']['use_plex_client'] = int(app.USE_PLEX_CLIENT)
        new_config['Plex']['plex_client_username'] = app.PLEX_CLIENT_USERNAME
        new_config['Plex']['plex_client_password'] = helpers.encrypt(app.PLEX_CLIENT_PASSWORD, app.ENCRYPTION_VERSION)
        new_config['Plex']['plex_server_https'] = int(app.PLEX_SERVER_HTTPS)

        new_config['Emby'] = {}
        new_config['Emby']['use_emby'] = int(app.USE_EMBY)
        new_config['Emby']['emby_host'] = app.EMBY_HOST
        new_config['Emby']['emby_apikey'] = app.EMBY_APIKEY

        new_config['Growl'] = {}
        new_config['Growl']['use_growl'] = int(app.USE_GROWL)
        new_config['Growl']['growl_notify_onsnatch'] = int(app.GROWL_NOTIFY_ONSNATCH)
        new_config['Growl']['growl_notify_ondownload'] = int(app.GROWL_NOTIFY_ONDOWNLOAD)
        new_config['Growl']['growl_notify_onsubtitledownload'] = int(app.GROWL_NOTIFY_ONSUBTITLEDOWNLOAD)
        new_config['Growl']['growl_host'] = app.GROWL_HOST
        new_config['Growl']['growl_password'] = helpers.encrypt(app.GROWL_PASSWORD, app.ENCRYPTION_VERSION)

        new_config['FreeMobile'] = {}
        new_config['FreeMobile']['use_freemobile'] = int(app.USE_FREEMOBILE)
        new_config['FreeMobile']['freemobile_notify_onsnatch'] = int(app.FREEMOBILE_NOTIFY_ONSNATCH)
        new_config['FreeMobile']['freemobile_notify_ondownload'] = int(app.FREEMOBILE_NOTIFY_ONDOWNLOAD)
        new_config['FreeMobile']['freemobile_notify_onsubtitledownload'] = int(app.FREEMOBILE_NOTIFY_ONSUBTITLEDOWNLOAD)
        new_config['FreeMobile']['freemobile_id'] = app.FREEMOBILE_ID
        new_config['FreeMobile']['freemobile_apikey'] = app.FREEMOBILE_APIKEY

        new_config['Telegram'] = {}
        new_config['Telegram']['use_telegram'] = int(app.USE_TELEGRAM)
        new_config['Telegram']['telegram_notify_onsnatch'] = int(app.TELEGRAM_NOTIFY_ONSNATCH)
        new_config['Telegram']['telegram_notify_ondownload'] = int(app.TELEGRAM_NOTIFY_ONDOWNLOAD)
        new_config['Telegram']['telegram_notify_onsubtitledownload'] = int(app.TELEGRAM_NOTIFY_ONSUBTITLEDOWNLOAD)
        new_config['Telegram']['telegram_id'] = app.TELEGRAM_ID
        new_config['Telegram']['telegram_apikey'] = app.TELEGRAM_APIKEY

        new_config['Prowl'] = {}
        new_config['Prowl']['use_prowl'] = int(app.USE_PROWL)
        new_config['Prowl']['prowl_notify_onsnatch'] = int(app.PROWL_NOTIFY_ONSNATCH)
        new_config['Prowl']['prowl_notify_ondownload'] = int(app.PROWL_NOTIFY_ONDOWNLOAD)
        new_config['Prowl']['prowl_notify_onsubtitledownload'] = int(app.PROWL_NOTIFY_ONSUBTITLEDOWNLOAD)
        new_config['Prowl']['prowl_api'] = app.PROWL_API
        new_config['Prowl']['prowl_priority'] = app.PROWL_PRIORITY
        new_config['Prowl']['prowl_message_title'] = app.PROWL_MESSAGE_TITLE

        new_config['Twitter'] = {}
        new_config['Twitter']['use_twitter'] = int(app.USE_TWITTER)
        new_config['Twitter']['twitter_notify_onsnatch'] = int(app.TWITTER_NOTIFY_ONSNATCH)
        new_config['Twitter']['twitter_notify_ondownload'] = int(app.TWITTER_NOTIFY_ONDOWNLOAD)
        new_config['Twitter']['twitter_notify_onsubtitledownload'] = int(app.TWITTER_NOTIFY_ONSUBTITLEDOWNLOAD)
        new_config['Twitter']['twitter_username'] = app.TWITTER_USERNAME
        new_config['Twitter']['twitter_password'] = helpers.encrypt(app.TWITTER_PASSWORD, app.ENCRYPTION_VERSION)
        new_config['Twitter']['twitter_prefix'] = app.TWITTER_PREFIX
        new_config['Twitter']['twitter_dmto'] = app.TWITTER_DMTO
        new_config['Twitter']['twitter_usedm'] = int(app.TWITTER_USEDM)

        new_config['Boxcar2'] = {}
        new_config['Boxcar2']['use_boxcar2'] = int(app.USE_BOXCAR2)
        new_config['Boxcar2']['boxcar2_notify_onsnatch'] = int(app.BOXCAR2_NOTIFY_ONSNATCH)
        new_config['Boxcar2']['boxcar2_notify_ondownload'] = int(app.BOXCAR2_NOTIFY_ONDOWNLOAD)
        new_config['Boxcar2']['boxcar2_notify_onsubtitledownload'] = int(app.BOXCAR2_NOTIFY_ONSUBTITLEDOWNLOAD)
        new_config['Boxcar2']['boxcar2_accesstoken'] = app.BOXCAR2_ACCESSTOKEN

        new_config['Pushover'] = {}
        new_config['Pushover']['use_pushover'] = int(app.USE_PUSHOVER)
        new_config['Pushover']['pushover_notify_onsnatch'] = int(app.PUSHOVER_NOTIFY_ONSNATCH)
        new_config['Pushover']['pushover_notify_ondownload'] = int(app.PUSHOVER_NOTIFY_ONDOWNLOAD)
        new_config['Pushover']['pushover_notify_onsubtitledownload'] = int(app.PUSHOVER_NOTIFY_ONSUBTITLEDOWNLOAD)
        new_config['Pushover']['pushover_userkey'] = app.PUSHOVER_USERKEY
        new_config['Pushover']['pushover_apikey'] = app.PUSHOVER_APIKEY
        new_config['Pushover']['pushover_device'] = app.PUSHOVER_DEVICE
        new_config['Pushover']['pushover_sound'] = app.PUSHOVER_SOUND

        new_config['Libnotify'] = {}
        new_config['Libnotify']['use_libnotify'] = int(app.USE_LIBNOTIFY)
        new_config['Libnotify']['libnotify_notify_onsnatch'] = int(app.LIBNOTIFY_NOTIFY_ONSNATCH)
        new_config['Libnotify']['libnotify_notify_ondownload'] = int(app.LIBNOTIFY_NOTIFY_ONDOWNLOAD)
        new_config['Libnotify']['libnotify_notify_onsubtitledownload'] = int(app.LIBNOTIFY_NOTIFY_ONSUBTITLEDOWNLOAD)

        new_config['NMJ'] = {}
        new_config['NMJ']['use_nmj'] = int(app.USE_NMJ)
        new_config['NMJ']['nmj_host'] = app.NMJ_HOST
        new_config['NMJ']['nmj_database'] = app.NMJ_DATABASE
        new_config['NMJ']['nmj_mount'] = app.NMJ_MOUNT

        new_config['NMJv2'] = {}
        new_config['NMJv2']['use_nmjv2'] = int(app.USE_NMJv2)
        new_config['NMJv2']['nmjv2_host'] = app.NMJv2_HOST
        new_config['NMJv2']['nmjv2_database'] = app.NMJv2_DATABASE
        new_config['NMJv2']['nmjv2_dbloc'] = app.NMJv2_DBLOC

        new_config['Synology'] = {}
        new_config['Synology']['use_synoindex'] = int(app.USE_SYNOINDEX)

        new_config['SynologyNotifier'] = {}
        new_config['SynologyNotifier']['use_synologynotifier'] = int(app.USE_SYNOLOGYNOTIFIER)
        new_config['SynologyNotifier']['synologynotifier_notify_onsnatch'] = int(app.SYNOLOGYNOTIFIER_NOTIFY_ONSNATCH)
        new_config['SynologyNotifier']['synologynotifier_notify_ondownload'] = int(app.SYNOLOGYNOTIFIER_NOTIFY_ONDOWNLOAD)
        new_config['SynologyNotifier']['synologynotifier_notify_onsubtitledownload'] = int(
            app.SYNOLOGYNOTIFIER_NOTIFY_ONSUBTITLEDOWNLOAD)

        new_config['Trakt'] = {}
        new_config['Trakt']['use_trakt'] = int(app.USE_TRAKT)
        new_config['Trakt']['trakt_username'] = app.TRAKT_USERNAME
        new_config['Trakt']['trakt_access_token'] = app.TRAKT_ACCESS_TOKEN
        new_config['Trakt']['trakt_refresh_token'] = app.TRAKT_REFRESH_TOKEN
        new_config['Trakt']['trakt_remove_watchlist'] = int(app.TRAKT_REMOVE_WATCHLIST)
        new_config['Trakt']['trakt_remove_serieslist'] = int(app.TRAKT_REMOVE_SERIESLIST)
        new_config['Trakt']['trakt_remove_show_from_application'] = int(app.TRAKT_REMOVE_SHOW_FROM_APPLICATION)
        new_config['Trakt']['trakt_sync_watchlist'] = int(app.TRAKT_SYNC_WATCHLIST)
        new_config['Trakt']['trakt_method_add'] = int(app.TRAKT_METHOD_ADD)
        new_config['Trakt']['trakt_start_paused'] = int(app.TRAKT_START_PAUSED)
        new_config['Trakt']['trakt_use_recommended'] = int(app.TRAKT_USE_RECOMMENDED)
        new_config['Trakt']['trakt_sync'] = int(app.TRAKT_SYNC)
        new_config['Trakt']['trakt_sync_remove'] = int(app.TRAKT_SYNC_REMOVE)
        new_config['Trakt']['trakt_default_indexer'] = int(app.TRAKT_DEFAULT_INDEXER)
        new_config['Trakt']['trakt_timeout'] = int(app.TRAKT_TIMEOUT)
        new_config['Trakt']['trakt_blacklist_name'] = app.TRAKT_BLACKLIST_NAME

        new_config['pyTivo'] = {}
        new_config['pyTivo']['use_pytivo'] = int(app.USE_PYTIVO)
        new_config['pyTivo']['pytivo_notify_onsnatch'] = int(app.PYTIVO_NOTIFY_ONSNATCH)
        new_config['pyTivo']['pytivo_notify_ondownload'] = int(app.PYTIVO_NOTIFY_ONDOWNLOAD)
        new_config['pyTivo']['pytivo_notify_onsubtitledownload'] = int(app.PYTIVO_NOTIFY_ONSUBTITLEDOWNLOAD)
        new_config['pyTivo']['pyTivo_update_library'] = int(app.PYTIVO_UPDATE_LIBRARY)
        new_config['pyTivo']['pytivo_host'] = app.PYTIVO_HOST
        new_config['pyTivo']['pytivo_share_name'] = app.PYTIVO_SHARE_NAME
        new_config['pyTivo']['pytivo_tivo_name'] = app.PYTIVO_TIVO_NAME

        new_config['NMA'] = {}
        new_config['NMA']['use_nma'] = int(app.USE_NMA)
        new_config['NMA']['nma_notify_onsnatch'] = int(app.NMA_NOTIFY_ONSNATCH)
        new_config['NMA']['nma_notify_ondownload'] = int(app.NMA_NOTIFY_ONDOWNLOAD)
        new_config['NMA']['nma_notify_onsubtitledownload'] = int(app.NMA_NOTIFY_ONSUBTITLEDOWNLOAD)
        new_config['NMA']['nma_api'] = app.NMA_API
        new_config['NMA']['nma_priority'] = app.NMA_PRIORITY

        new_config['Pushalot'] = {}
        new_config['Pushalot']['use_pushalot'] = int(app.USE_PUSHALOT)
        new_config['Pushalot']['pushalot_notify_onsnatch'] = int(app.PUSHALOT_NOTIFY_ONSNATCH)
        new_config['Pushalot']['pushalot_notify_ondownload'] = int(app.PUSHALOT_NOTIFY_ONDOWNLOAD)
        new_config['Pushalot']['pushalot_notify_onsubtitledownload'] = int(app.PUSHALOT_NOTIFY_ONSUBTITLEDOWNLOAD)
        new_config['Pushalot']['pushalot_authorizationtoken'] = app.PUSHALOT_AUTHORIZATIONTOKEN

        new_config['Pushbullet'] = {}
        new_config['Pushbullet']['use_pushbullet'] = int(app.USE_PUSHBULLET)
        new_config['Pushbullet']['pushbullet_notify_onsnatch'] = int(app.PUSHBULLET_NOTIFY_ONSNATCH)
        new_config['Pushbullet']['pushbullet_notify_ondownload'] = int(app.PUSHBULLET_NOTIFY_ONDOWNLOAD)
        new_config['Pushbullet']['pushbullet_notify_onsubtitledownload'] = int(app.PUSHBULLET_NOTIFY_ONSUBTITLEDOWNLOAD)
        new_config['Pushbullet']['pushbullet_api'] = app.PUSHBULLET_API
        new_config['Pushbullet']['pushbullet_device'] = app.PUSHBULLET_DEVICE

        new_config['Email'] = {}
        new_config['Email']['use_email'] = int(app.USE_EMAIL)
        new_config['Email']['email_notify_onsnatch'] = int(app.EMAIL_NOTIFY_ONSNATCH)
        new_config['Email']['email_notify_ondownload'] = int(app.EMAIL_NOTIFY_ONDOWNLOAD)
        new_config['Email']['email_notify_onsubtitledownload'] = int(app.EMAIL_NOTIFY_ONSUBTITLEDOWNLOAD)
        new_config['Email']['email_host'] = app.EMAIL_HOST
        new_config['Email']['email_port'] = int(app.EMAIL_PORT)
        new_config['Email']['email_tls'] = int(app.EMAIL_TLS)
        new_config['Email']['email_user'] = app.EMAIL_USER
        new_config['Email']['email_password'] = helpers.encrypt(app.EMAIL_PASSWORD, app.ENCRYPTION_VERSION)
        new_config['Email']['email_from'] = app.EMAIL_FROM
        new_config['Email']['email_list'] = app.EMAIL_LIST
        new_config['Email']['email_subject'] = app.EMAIL_SUBJECT

        new_config['Newznab'] = {}
        new_config['Newznab']['newznab_data'] = app.NEWZNAB_DATA

        new_config['TorrentRss'] = {}
        new_config['TorrentRss']['torrentrss_data'] = '!!!'.join([x.config_string() for x in app.torrentRssProviderList])

        new_config['GUI'] = {}
        new_config['GUI']['theme_name'] = app.THEME_NAME
        new_config['GUI']['fanart_background'] = app.FANART_BACKGROUND
        new_config['GUI']['fanart_background_opacity'] = app.FANART_BACKGROUND_OPACITY
        new_config['GUI']['home_layout'] = app.HOME_LAYOUT
        new_config['GUI']['history_layout'] = app.HISTORY_LAYOUT
        new_config['GUI']['history_limit'] = app.HISTORY_LIMIT
        new_config['GUI']['display_show_specials'] = int(app.DISPLAY_SHOW_SPECIALS)
        new_config['GUI']['coming_eps_layout'] = app.COMING_EPS_LAYOUT
        new_config['GUI']['coming_eps_display_paused'] = int(app.COMING_EPS_DISPLAY_PAUSED)
        new_config['GUI']['coming_eps_sort'] = app.COMING_EPS_SORT
        new_config['GUI']['coming_eps_missed_range'] = int(app.COMING_EPS_MISSED_RANGE)
        new_config['GUI']['fuzzy_dating'] = int(app.FUZZY_DATING)
        new_config['GUI']['trim_zero'] = int(app.TRIM_ZERO)
        new_config['GUI']['date_preset'] = app.DATE_PRESET
        new_config['GUI']['time_preset'] = app.TIME_PRESET_W_SECONDS
        new_config['GUI']['timezone_display'] = app.TIMEZONE_DISPLAY
        new_config['GUI']['poster_sortby'] = app.POSTER_SORTBY
        new_config['GUI']['poster_sortdir'] = app.POSTER_SORTDIR

        new_config['Subtitles'] = {}
        new_config['Subtitles']['use_subtitles'] = int(app.USE_SUBTITLES)
        new_config['Subtitles']['subtitles_erase_cache'] = int(app.SUBTITLES_ERASE_CACHE)
        new_config['Subtitles']['subtitles_languages'] = ','.join(app.SUBTITLES_LANGUAGES)
        new_config['Subtitles']['SUBTITLES_SERVICES_LIST'] = ','.join(app.SUBTITLES_SERVICES_LIST)
        new_config['Subtitles']['SUBTITLES_SERVICES_ENABLED'] = '|'.join([str(x) for x in app.SUBTITLES_SERVICES_ENABLED])
        new_config['Subtitles']['subtitles_dir'] = app.SUBTITLES_DIR
        new_config['Subtitles']['subtitles_default'] = int(app.SUBTITLES_DEFAULT)
        new_config['Subtitles']['subtitles_history'] = int(app.SUBTITLES_HISTORY)
        new_config['Subtitles']['subtitles_perfect_match'] = int(app.SUBTITLES_PERFECT_MATCH)
        new_config['Subtitles']['embedded_subtitles_all'] = int(app.IGNORE_EMBEDDED_SUBS)
        new_config['Subtitles']['subtitles_stop_at_first'] = int(app.SUBTITLES_STOP_AT_FIRST)
        new_config['Subtitles']['embedded_subtitles_unknown_lang'] = int(app.ACCEPT_UNKNOWN_EMBEDDED_SUBS)
        new_config['Subtitles']['subtitles_hearing_impaired'] = int(app.SUBTITLES_HEARING_IMPAIRED)
        new_config['Subtitles']['subtitles_finder_frequency'] = int(app.SUBTITLES_FINDER_FREQUENCY)
        new_config['Subtitles']['subtitles_multi'] = int(app.SUBTITLES_MULTI)
        new_config['Subtitles']['subtitles_extra_scripts'] = '|'.join(app.SUBTITLES_EXTRA_SCRIPTS)
        new_config['Subtitles']['subtitles_pre_scripts'] = '|'.join(app.SUBTITLES_PRE_SCRIPTS)
        new_config['Subtitles']['subtitles_keep_only_wanted'] = int(app.SUBTITLES_KEEP_ONLY_WANTED)
        new_config['Subtitles']['addic7ed_username'] = app.ADDIC7ED_USER
        new_config['Subtitles']['addic7ed_password'] = helpers.encrypt(app.ADDIC7ED_PASS, app.ENCRYPTION_VERSION)

        new_config['Subtitles']['itasa_username'] = app.ITASA_USER
        new_config['Subtitles']['itasa_password'] = helpers.encrypt(app.ITASA_PASS, app.ENCRYPTION_VERSION)

        new_config['Subtitles']['legendastv_username'] = app.LEGENDASTV_USER
        new_config['Subtitles']['legendastv_password'] = helpers.encrypt(app.LEGENDASTV_PASS, app.ENCRYPTION_VERSION)

        new_config['Subtitles']['opensubtitles_username'] = app.OPENSUBTITLES_USER
        new_config['Subtitles']['opensubtitles_password'] = helpers.encrypt(app.OPENSUBTITLES_PASS, app.ENCRYPTION_VERSION)

        new_config['FailedDownloads'] = {}
        new_config['FailedDownloads']['use_failed_downloads'] = int(app.USE_FAILED_DOWNLOADS)
        new_config['FailedDownloads']['delete_failed'] = int(app.DELETE_FAILED)

        new_config['ANIDB'] = {}
        new_config['ANIDB']['use_anidb'] = int(app.USE_ANIDB)
        new_config['ANIDB']['anidb_username'] = app.ANIDB_USERNAME
        new_config['ANIDB']['anidb_password'] = helpers.encrypt(app.ANIDB_PASSWORD, app.ENCRYPTION_VERSION)
        new_config['ANIDB']['anidb_use_mylist'] = int(app.ANIDB_USE_MYLIST)

        new_config['ANIME'] = {}
        new_config['ANIME']['anime_split_home'] = int(app.ANIME_SPLIT_HOME)

        new_config.write()

    @staticmethod
    def launch_browser(protocol='http', start_port=None, web_root='/'):
        """Launch web browser."""
        try:
            import webbrowser
        except ImportError:
            logger.warning(u'Unable to load the webbrowser module, cannot launch the browser.')
            return

        if not start_port:
            start_port = app.WEB_PORT

        browser_url = '%s://localhost:%d%s/home/' % (protocol, start_port, web_root)

        try:
            webbrowser.open(browser_url, 2, 1)
        except Exception:
            try:
                webbrowser.open(browser_url, 1, 1)
            except Exception:
                logger.error(u'Unable to launch a browser')

    @staticmethod
    def sig_handler(signum=None, frame=None):
        """Signal handler function."""
        if not isinstance(signum, type(None)):
            logger.info(u'Signal {number} caught, saving and exiting...', number=signum)
            Shutdown.stop(app.PID)

    @staticmethod
    def backwards_compatibility():
        """Rename old files and folders to the expected ones."""
        if os.path.isdir(app.DATA_DIR):
            cwd = os.getcwd() if os.path.isabs(app.DATA_DIR) else ''
            backup_re = re.compile(r'[^\d]+(?P<suffix>-\d{14}\.zip)')
            for filename in os.listdir(app.DATA_DIR):
                # Rename database file
                if filename.startswith(app.LEGACY_DB) and not any(f.startswith(app.APPLICATION_DB) for f in os.listdir(app.DATA_DIR)):
                    new_file = os.path.join(cwd, app.DATA_DIR, app.APPLICATION_DB + filename[len(app.LEGACY_DB):])
                    os.rename(os.path.join(cwd, app.DATA_DIR, filename), new_file)
                    continue

                # Rename old backups
                match = backup_re.match(filename)
                if match:
                    new_file = os.path.join(cwd, app.DATA_DIR, app.BACKUP_FILENAME_PREFIX + match.group('suffix'))
                    os.rename(os.path.join(cwd, app.DATA_DIR, filename), new_file)
                    continue

    def daemonize(self):
        """Fork off as a daemon."""
        # pylint: disable=protected-access
        # An object is accessed for a non-existent member.
        # Access to a protected member of a client class
        # Make a non-session-leader child process
        try:
            pid = os.fork()  # @UndefinedVariable - only available in UNIX
            if pid != 0:
                os._exit(0)
        except OSError as error:
            sys.stderr.write('fork #1 failed: {error_num}: {error_message}\n'.format
                             (error_num=error.errno, error_message=error.strerror))
            sys.exit(1)

        os.setsid()  # @UndefinedVariable - only available in UNIX

        # https://github.com/SickRage/sickrage-issues/issues/2969
        # http://www.microhowto.info/howto/cause_a_process_to_become_a_daemon_in_c.html#idp23920
        # https://www.safaribooksonline.com/library/view/python-cookbook/0596001673/ch06s08.html
        # Previous code simply set the umask to whatever it was because it was ANDing instead of OR-ing
        # Daemons traditionally run with umask 0 anyways and this should not have repercussions
        os.umask(0)

        # Make the child a session-leader by detaching from the terminal
        try:
            pid = os.fork()  # @UndefinedVariable - only available in UNIX
            if pid != 0:
                os._exit(0)
        except OSError as error:
            sys.stderr.write('fork #2 failed: Error {error_num}: {error_message}\n'.format
                             (error_num=error.errno, error_message=error.strerror))
            sys.exit(1)

        # Write pid
        if self.create_pid:
            pid = os.getpid()
            logger.info('Writing PID: {pid} to {filename}', pid=pid, filename=self.pid_file)

            try:
                with io.open(self.pid_file, 'w') as f_pid:
                    f_pid.write('%s\n' % pid)
            except EnvironmentError as error:
                logger.error('Unable to write PID file: {filename} Error {error_num}: {error_message}',
                             filename=self.pid_file, error_num=error.errno, error_message=error.strerror)
                sys.exit('Unable to write PID file')

        # Redirect all output
        sys.stdout.flush()
        sys.stderr.flush()

        devnull = getattr(os, 'devnull', '/dev/null')
        stdin = file(devnull)
        stdout = file(devnull, 'a+')
        stderr = file(devnull, 'a+')

        os.dup2(stdin.fileno(), getattr(sys.stdin, 'device', sys.stdin).fileno())
        os.dup2(stdout.fileno(), getattr(sys.stdout, 'device', sys.stdout).fileno())
        os.dup2(stderr.fileno(), getattr(sys.stderr, 'device', sys.stderr).fileno())

    def stop_webserver(self):
        """Stop web server."""
        if not self.web_server:
            return

        try:
            logger.info('Shutting down Tornado')
            self.web_server.shutDown()
            self.web_server.join(10)
        except Exception as error:
            exception_handler.handle(error)

    @staticmethod
    def restart():
        """Restart application."""
        install_type = app.version_check_scheduler.action.install_type

        popen_list = []

        if install_type in ('git', 'source'):
            popen_list = [sys.executable, app.MY_FULLNAME]
        elif install_type == 'win':
            logger.error('You are using a binary Windows build of Medusa. Please switch to using git.')

        if popen_list and not app.NO_RESTART:
            popen_list += app.MY_ARGS
            if '--nolaunch' not in popen_list:
                popen_list += ['--nolaunch']
            logger.info('Restarting Medusa with {options}', options=popen_list)
            # shutdown the logger to make sure it's released the logfile BEFORE it restarts SR.
            logging.shutdown()
            print(popen_list)
            subprocess.Popen(popen_list, cwd=os.getcwd())

    @staticmethod
    def remove_pid_file(pid_file):
        """Remove pid file.

        :param pid_file: to remove
        :return:
        """
        try:
            if os.path.exists(pid_file):
                os.remove(pid_file)
        except EnvironmentError:
            return False

        return True

    @staticmethod
    def load_shows_from_db():
        """Populate the showList with shows from the database."""
        logger.debug('Loading initial show list')

        main_db_con = db.DBConnection()
        sql_results = main_db_con.select('SELECT indexer, indexer_id, location FROM tv_shows;')

        app.showList = []
        for sql_show in sql_results:
            try:
                cur_show = Series(sql_show[b'indexer'], sql_show[b'indexer_id'])
                cur_show.next_episode()
                app.showList.append(cur_show)
            except Exception as error:
                exception_handler.handle(error, 'There was an error creating the show in {location}',
                                         location=sql_show[b'location'])

    @staticmethod
    def restore_db(src_dir, dst_dir):
        """Restore the Database from a backup.

        :param src_dir: Directory containing backup
        :param dst_dir: Directory to restore to
        :return:
        """
        try:
            files_list = [app.APPLICATION_DB, app.CONFIG_INI, app.FAILED_DB, app.CACHE_DB]

            for filename in files_list:
                src_file = os.path.join(src_dir, filename)
                dst_file = os.path.join(dst_dir, filename)
                bak_file = os.path.join(dst_dir, '%s.bak-%s' % (filename, datetime.datetime.now().strftime('%Y%m%d_%H%M%S')))
                if os.path.isfile(dst_file):
                    shutil.move(dst_file, bak_file)
                shutil.move(src_file, dst_file)
            return True
        except Exception as error:
            exception_handler.handle(error)
            return False

    def shutdown(self, event):
        """Shut down Application.

        :param event: Type of shutdown event, used to see if restart required
        """
        try:
            if not app.started:
                return

            self.halt()  # stop all tasks
            self.save_all()  # save all shows to DB

            # shutdown web server
            self.stop_webserver()

            self.clear_cache()  # Clean cache

            # if run as daemon delete the pid file
            if self.run_as_daemon and self.create_pid:
                self.remove_pid_file(self.pid_file)
        finally:
            if event == event_queue.Events.SystemEvent.RESTART:
                self.restart()

            # Make sure the logger has stopped, just in case
            logging.shutdown()
            os._exit(0)  # TODO: Remove in another PR. There's no need for this one.


def main():
    """Application entry point."""
    # start application
    application = Application()
    application.start(sys.argv[1:])


if __name__ == '__main__':
    main()
