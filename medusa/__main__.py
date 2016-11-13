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
import re
import shutil
import signal
import subprocess
import sys
import threading
import time

from configobj import ConfigObj
import medusa as app
from six import text_type

from . import db, exception_handler, failed_history, name_cache, network_timezones
from .event_queue import Events
from .server.core import AppWebServer
from .tv import TVShow


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
        signal.signal(signal.SIGINT, app.sig_handler)
        signal.signal(signal.SIGTERM, app.sig_handler)

        # do some preliminary stuff
        app.MY_FULLNAME = os.path.normpath(os.path.abspath(os.path.join(__file__, '..')))
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
        app.initialize(consoleLogging=self.console_logging)

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
        app.start()

        # Build internal name cache
        name_cache.buildNameCache()

        # Pre-populate network timezones, it isn't thread safe
        network_timezones.update_network_dict()

        # sure, why not?
        if app.USE_FAILED_DOWNLOADS:
            failed_history.trimHistory()

        # # Check for metadata indexer updates for shows (Disabled until we use api)
        # app.showUpdateScheduler.forceRun()

        # Launch browser
        if app.LAUNCH_BROWSER and not (self.no_launch or self.run_as_daemon):
            app.launchBrowser('https' if app.ENABLE_HTTPS else 'http', self.start_port, app.WEB_ROOT)

        # main loop
        while True:
            time.sleep(1)

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
                cur_show = TVShow(sql_show[b'indexer'], sql_show[b'indexer_id'])
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
        if app.started:
            app.halt()  # stop all tasks
            app.saveAll()  # save all shows to DB

            # shutdown web server
            if self.web_server:
                logger.info('Shutting down Tornado')
                self.web_server.shutDown()

                try:
                    self.web_server.join(10)
                except Exception as error:
                    exception_handler.handle(error)

            self.clear_cache()  # Clean cache

            # if run as daemon delete the pid file
            if self.run_as_daemon and self.create_pid:
                self.remove_pid_file(self.pid_file)

            if event == app.event_queue.Events.SystemEvent.RESTART:
                install_type = app.versionCheckScheduler.action.install_type

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
                    subprocess.Popen(popen_list, cwd=os.getcwd())

        # Make sure the logger has stopped, just in case
        logging.shutdown()
        os._exit(0)  # pylint: disable=protected-access


def main():
    """Application entry point."""
    # start application
    application = Application()
    application.start(sys.argv[1:])


if __name__ == '__main__':
    main()
