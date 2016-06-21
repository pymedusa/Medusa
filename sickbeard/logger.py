# coding=utf-8
# Author: Nic Wolfe <nic@wolfeden.ca>

# Git: https://github.com/PyMedusa/SickRage.git
#
# This file is part of SickRage.
#
# SickRage is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# SickRage is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with SickRage. If not, see <http://www.gnu.org/licenses/>.

"""
Custom Logger for SickRage
"""

from __future__ import unicode_literals

import io
import locale
import logging
from logging import NullHandler
from logging.handlers import RotatingFileHandler
import os
import pkgutil
import platform
import re
import sys
import traceback

import tornado
import subliminal

from requests.compat import quote
from six import itervalues
from github import Github, InputFileContent  # pylint: disable=import-error

import sickbeard
from sickbeard import classes

import sickrage
from sickrage.helper.encoding import ss, ek
from sickrage.helper.exceptions import ex
from sickrage.helper.common import dateTimeFormat

# pylint: disable=line-too-long

# log levels
CRITICAL = logging.CRITICAL
ERROR = logging.ERROR
WARNING = logging.WARNING
INFO = logging.INFO
DEBUG = logging.DEBUG
DB = 5

LOGGING_LEVELS = {
    'ERROR': ERROR,
    'WARNING': WARNING,
    'INFO': INFO,
    'DEBUG': DEBUG,
    'DB': DB,
}

LEVEL_STEP = INFO - DEBUG

SSL_ERRORS = {
    r'error \[Errno \d+\] _ssl.c:\d+: error:\d+\s*:SSL routines:SSL23_GET_SERVER_HELLO:tlsv1 alert internal error',
    r'error \[SSL: SSLV3_ALERT_HANDSHAKE_FAILURE\] sslv3 alert handshake failure \(_ssl\.c:\d+\)',
}

SSL_ERRORS_WIKI_URL = 'https://git.io/vVaIj'
SSL_ERROR_HELP_MSG = 'See: {0}'.format(SSL_ERRORS_WIKI_URL)

censored_items = {}  # pylint: disable=invalid-name

level_mapping = {
    'subliminal': LEVEL_STEP,
    'subliminal.providers.addic7ed': 2 * LEVEL_STEP,
    'subliminal.providers.itasa': 2 * LEVEL_STEP,
    'subliminal.providers.tvsubtitles': 2 * LEVEL_STEP,
    'subliminal.refiners.omdb': 2 * LEVEL_STEP,
    'subliminal.refiners.metadata': 2 * LEVEL_STEP,
    'subliminal.refiners.tvdb': 2 * LEVEL_STEP,
}


class ContextFilter(logging.Filter):
    """
    This is a filter which injects contextual information into the log, in our case: commit hash
    """

    def filter(self, record):
        cur_commit_hash = sickbeard.CUR_COMMIT_HASH
        record.curhash = cur_commit_hash[:7] if cur_commit_hash and len(cur_commit_hash) > 6 else ''

        fullname = record.name
        basename = fullname.split('.')[0]
        decrease = level_mapping.get(fullname) or level_mapping.get(basename) or 0
        level = max(DEBUG, record.levelno - decrease)
        if record.levelno != level:
            record.levelno = level
            record.levelname = logging.getLevelName(record.levelno)

        # add exception traceback for errors
        if record.levelno == ERROR:
            exc_info = sys.exc_info()
            record.exc_info = exc_info if exc_info != (None, None, None) else None

        return True


class UIViewHandler(logging.Handler):

    def __init__(self):
        super(UIViewHandler, self).__init__(WARNING)

    def emit(self, record):
        # SSL errors might change the record.levelno to WARNING
        message = self.format(record)

        level = record.levelno
        if level not in (WARNING, ERROR):
            return

        if level == WARNING:
            classes.WarningViewer.add(classes.UIError(message))
        elif level == ERROR:
            classes.ErrorViewer.add(classes.UIError(message))


class CensoredFormatter(logging.Formatter, object):
    """
    Censor information such as API keys, user names, and passwords from the Log
    """
    def __init__(self, fmt=None, datefmt=None, encoding='utf-8'):
        super(CensoredFormatter, self).__init__(fmt, datefmt)
        self.encoding = encoding

    def format(self, record):
        """
        Strips censored items from string

        :param record: to censor
        """
        privacy_level = sickbeard.common.privacy_levels[sickbeard.PRIVACY_LEVEL]
        if not privacy_level:
            return super(CensoredFormatter, self).format(record)
        elif privacy_level == sickbeard.common.privacy_levels['absurd']:
            return re.sub(r'[\d\w]', '*', super(CensoredFormatter, self).format(record))
        else:
            msg = super(CensoredFormatter, self).format(record)

        if not isinstance(msg, unicode):
            msg = msg.decode(self.encoding, 'replace')  # Convert to unicode

        # Change the SSL error to a warning with a link to information about how to fix it.
        # Check for u'error [SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] sslv3 alert handshake failure (_ssl.c:590)'
        for ssl_error in SSL_ERRORS:
            if re.findall(ssl_error, msg):
                record.levelno = WARNING
                record.levelname = logging.getLevelName(record.levelno)
                msg = super(CensoredFormatter, self).format(record)
                msg = re.sub(ssl_error, SSL_ERROR_HELP_MSG, msg)

        # set of censored items
        censored = {value for value in itervalues(censored_items) if value}
        # set of censored items and urlencoded counterparts
        censored = censored | {quote(item) for item in censored}
        # convert set items to unicode and typecast to list
        censored = list({
            item.decode(self.encoding, 'replace')
            if not isinstance(item, unicode) else item
            for item in censored
        })
        # sort the list in order of descending length so that entire item is censored
        # e.g. password and password_1 both get censored instead of getting ********_1
        censored.sort(key=len, reverse=True)

        for item in censored:
            msg = msg.replace(item, len(item) * '*')

        # Needed because Newznab apikey isn't stored as key=value in a section.
        msg = re.sub(r'([&?]r|[&?]apikey|[&?]api_key)(?:=|%3D)[^&]*([&\w]?)', r'\1=**********\2', msg, re.I)
        return msg


def list_modules(package):
    return [modname for importer, modname, ispkg in pkgutil.walk_packages(
        path=package.__path__, prefix=package.__name__+'.', onerror=lambda x: None)]


def get_loggers(package):
    return [logging.getLogger(modname) for modname in list_modules(package)]


class Logger(object):  # pylint: disable=too-many-instance-attributes
    """
    Logger to create log entries
    """
    def __init__(self):
        self.logger = logging.getLogger('sickrage')

        self.loggers = [self.logger]
        self.loggers.extend(get_loggers(sickrage))
        self.loggers.extend(get_loggers(sickbeard))
        self.loggers.extend(get_loggers(subliminal))
        self.loggers.extend(get_loggers(tornado))

        self.console_logging = False
        self.file_logging = False
        self.debug_logging = False
        self.database_logging = False
        self.log_file = None

        self.submitter_running = False

    def init_logging(self, console_logging=False, file_logging=False, debug_logging=False, database_logging=False):
        """
        Initialize logging

        :param console_logging: True if logging to console
        :param file_logging: True if logging to file
        :param debug_logging: True if debug logging is enabled
        :param database_logging: True if logging database access
        """
        self.log_file = self.log_file or ek(os.path.join, sickbeard.LOG_DIR, 'sickrage.log')
        self.debug_logging = debug_logging
        self.console_logging = console_logging
        self.file_logging = file_logging
        self.database_logging = database_logging

        logging.addLevelName(DB, 'DB')  # add a new logging level DB
        logging.getLogger().addHandler(NullHandler())  # nullify root logger

        log_filter = ContextFilter()
        view_log_pattern = '%(threadName)s :: [%(curhash)s] %(message)s'
        console_log_pattern = '%(asctime)s %(levelname)s::%(threadName)s :: [%(curhash)s] %(message)s'
        file_log_pattern = '%(asctime)s %(levelname)-8s %(threadName)s :: [%(curhash)s] %(message)s'

        ui_handler = UIViewHandler()
        ui_handler.setLevel(INFO)
        ui_handler.setFormatter(CensoredFormatter(view_log_pattern))

        # set custom root logger
        for logger in self.loggers:
            logger.addFilter(log_filter)
            logger.addHandler(ui_handler)

            if logger is not self.logger:
                logger.root = self.logger
                logger.parent = self.logger
                logger.propagate = False

        log_level = self.get_default_level()

        # set minimum logging level allowed for loggers
        for logger in self.loggers:
            logger.setLevel(log_level)

        # console log handler
        if self.console_logging:
            console = logging.StreamHandler()
            console.setFormatter(CensoredFormatter(console_log_pattern, '%H:%M:%S'))
            console.setLevel(log_level)

            for logger in self.loggers:
                logger.addHandler(console)

        # rotating log file handler
        if self.file_logging:

            rfh = RotatingFileHandler(
                self.log_file, maxBytes=int(sickbeard.LOG_SIZE * 1048576), backupCount=sickbeard.LOG_NR,
                encoding='utf-8')
            rfh.setFormatter(CensoredFormatter(file_log_pattern, dateTimeFormat))
            rfh.setLevel(log_level)

            for logger in self.loggers:
                logger.addHandler(rfh)

    # TODO: Read the user configuration instead of using the initial config
    def get_default_level(self):
        """Returns the default log level to be used based on the initial user configuration.
        :return: the default log level
        :rtype: int
        """
        return DB if self.database_logging else DEBUG if self.debug_logging else INFO

    def reconfigure_levels(self):
        """Reconfigures the log levels. Right now, only subliminal module is affected"""
        default_level = self.get_default_level()
        mapping = dict()

        if not sickbeard.SUBLIMINAL_LOG:
            modname = 'subliminal'
            mapping.update({modname: CRITICAL})

        for logger in self.loggers:
            fullname = logger.name
            basename = fullname.split('.')[0]
            level = mapping.get(fullname) or mapping.get(basename) or default_level
            logger.setLevel(level)

    @staticmethod
    def shutdown():
        """
        Shut down the logger
        """
        logging.shutdown()

    def log(self, msg, level=INFO, *args, **kwargs):
        """
        Create log entry

        :param msg: to log
        :param level: of log, e.g. DEBUG, INFO, etc.
        :param args: to pass to logger
        :param kwargs: to pass to logger
        """
        self.logger.log(level, msg, *args, **kwargs)

    def log_error_and_exit(self, error_msg, *args, **kwargs):
        self.log(error_msg, ERROR, *args, **kwargs)

        if not self.console_logging:
            sys.exit(error_msg.encode(sickbeard.SYS_ENCODING, 'xmlcharrefreplace'))
        else:
            sys.exit(1)

    def submit_errors(self):  # pylint: disable=too-many-branches,too-many-locals

        submitter_result = ''
        issue_id = None

        if not (sickbeard.GIT_USERNAME and sickbeard.GIT_PASSWORD and sickbeard.DEBUG and len(classes.ErrorViewer.errors) > 0):
            submitter_result = 'Please set your GitHub username and password in the config and enable debug. Unable to submit issue ticket to GitHub!'
            return submitter_result, issue_id

        try:
            from sickbeard.versionChecker import CheckVersion
            checkversion = CheckVersion()
            checkversion.check_for_new_version()
            commits_behind = checkversion.updater.get_num_commits_behind()
        except Exception:  # pylint: disable=broad-except
            submitter_result = 'Could not check if your SickRage is updated, unable to submit issue ticket to GitHub!'
            return submitter_result, issue_id

        if commits_behind is None or commits_behind > 0:
            submitter_result = 'Please update SickRage, unable to submit issue ticket to GitHub with an outdated version!'
            return submitter_result, issue_id

        if self.submitter_running:
            submitter_result = 'Issue submitter is running, please wait for it to complete'
            return submitter_result, issue_id

        self.submitter_running = True

        gh_org = sickbeard.GIT_ORG
        gh_repo = sickbeard.GIT_REPO

        git = Github(login_or_token=sickbeard.GIT_USERNAME, password=sickbeard.GIT_PASSWORD, user_agent='SickRage')

        try:
            # read log file
            log_data = None

            if ek(os.path.isfile, self.log_file):
                with io.open(self.log_file, encoding='utf-8') as log_f:
                    log_data = log_f.readlines()

            for i in range(1, int(sickbeard.LOG_NR)):
                f_name = '%s.%i' % (self.log_file, i)
                if ek(os.path.isfile, f_name) and (len(log_data) <= 500):
                    with io.open(f_name, encoding='utf-8') as log_f:
                        log_data += log_f.readlines()

            log_data = [line for line in reversed(log_data)]

            # parse and submit errors to issue tracker
            for cur_error in sorted(classes.ErrorViewer.errors, key=lambda error: error.time, reverse=True)[:500]:
                try:
                    title_error = ss(str(cur_error.title))
                    if not title_error or title_error == 'None':
                        # Match: SEARCHQUEUE-FORCEDSEARCH-262407 :: [HDTorrents] :: [ea015c6] Error1
                        # Match: MAIN :: [ea015c6] Error1
                        # We only need Error title
                        title_error = re.match(r'^(?:.*)(?:\[[\w]{7}\]\s*)(.*)$', ss(cur_error.message)).group(1)

                    if len(title_error) > 1000:
                        title_error = title_error[0:1000]

                except Exception as err_msg:  # pylint: disable=broad-except
                    self.log('Unable to get error title : %s' % ex(err_msg), ERROR)
                    continue

                gist = None
                regex = r'^(%s)\s*([A-Z]+)\s*(.*)\s*::\s*(\[[\w]{7}\])\s*(.*)$' % cur_error.time
                for i, data in enumerate(log_data):
                    match = re.match(regex, data)
                    if match:
                        level = match.group(2)
                        if LOGGING_LEVELS[level] == ERROR:
                            paste_data = ''.join(log_data[i:i + 50])
                            if paste_data:
                                gist = git.get_user().create_gist(False, {'sickrage.log': InputFileContent(paste_data)})
                            break
                    else:
                        gist = 'No ERROR found'

                try:
                    locale_name = locale.getdefaultlocale()[1]
                except Exception:  # pylint: disable=broad-except
                    locale_name = 'unknown'

                if gist and gist != 'No ERROR found':
                    log_link = 'Link to Log: %s' % gist.html_url
                else:
                    log_link = 'No Log available with ERRORS:'

                msg = [
                    '### INFO',
                    'Python Version: **%s**' % sys.version[:120].replace('\n', ''),
                    'Operating System: **%s**' % platform.platform(),
                    'Locale: %s' % locale_name,
                    'Branch: **%s**' % sickbeard.BRANCH,
                    'Commit: PyMedusa/SickRage@%s' % sickbeard.CUR_COMMIT_HASH,
                    log_link,
                    '### ERROR',
                    '```',
                    cur_error.message,
                    '```',
                    '---',
                    '_STAFF NOTIFIED_: @pymedusa/support @pymedusa/moderators',
                ]

                message = '\n'.join(msg)
                title_error = '[APP SUBMITTED]: %s' % title_error
                reports = git.get_organization(gh_org).get_repo(gh_repo).get_issues(state='all')

                def is_ascii_error(title):
                    # [APP SUBMITTED]: 'ascii' codec can't encode characters in position 00-00: ordinal not in range(128)
                    # [APP SUBMITTED]: 'charmap' codec can't decode byte 0x00 in position 00: character maps to <undefined>
                    return re.search(r'.* codec can\'t .*code .* in position .*:', title) is not None

                def is_malformed_error(title):
                    # [APP SUBMITTED]: not well-formed (invalid token): line 0, column 0
                    return re.search(r'.* not well-formed \(invalid token\): line .* column .*', title) is not None

                ascii_error = is_ascii_error(title_error)
                malformed_error = is_malformed_error(title_error)

                issue_found = False
                for report in reports:
                    if title_error.rsplit(' :: ')[-1] in report.title or \
                        (malformed_error and is_malformed_error(report.title)) or \
                            (ascii_error and is_ascii_error(report.title)):

                        issue_id = report.number
                        if not report.raw_data['locked']:
                            if report.create_comment(message):
                                submitter_result = 'Commented on existing issue #%s successfully!' % issue_id
                            else:
                                submitter_result = 'Failed to comment on found issue #%s!' % issue_id
                        else:
                            submitter_result = 'Issue #%s is locked, check GitHub to find info about the error.' % issue_id

                        issue_found = True
                        break

                if not issue_found:
                    issue = git.get_organization(gh_org).get_repo(gh_repo).create_issue(title_error, message)
                    if issue:
                        issue_id = issue.number
                        submitter_result = 'Your issue ticket #%s was submitted successfully!' % issue_id
                    else:
                        submitter_result = 'Failed to create a new issue!'

                if issue_id and cur_error in classes.ErrorViewer.errors:
                    # clear error from error list
                    classes.ErrorViewer.errors.remove(cur_error)
        except Exception:  # pylint: disable=broad-except
            self.log(traceback.format_exc(), ERROR)
            submitter_result = 'Exception generated in issue submitter, please check the log'
            issue_id = None
        finally:
            self.submitter_running = False

        return submitter_result, issue_id


# pylint: disable=too-few-public-methods
class Wrapper(object):
    instance = Logger()

    def __init__(self, wrapped):
        self.wrapped = wrapped

    def __getattr__(self, name):
        try:
            return getattr(self.wrapped, name)
        except AttributeError:
            return getattr(self.instance, name)


_globals = sys.modules[__name__] = Wrapper(sys.modules[__name__])  # pylint: disable=invalid-name
