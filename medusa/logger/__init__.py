# coding=utf-8
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
"""Custom Logger."""

from __future__ import unicode_literals

import datetime
import io
import logging
import os
import pkgutil
import re
import sys
from builtins import object
from builtins import range
from collections import OrderedDict
from logging import (
    CRITICAL,
    DEBUG,
    ERROR,
    INFO,
    NullHandler,
    WARNING,
)
from logging.handlers import RotatingFileHandler

import adba

import knowit

from medusa import app
from medusa.init.logconfig import standard_logger

from six import itervalues, string_types, text_type, viewitems
from six.moves import collections_abc
from six.moves.urllib.parse import quote

import subliminal

from tornado.log import access_log, app_log, gen_log

import traktor

# log levels
DB = 5

LOGGING_LEVELS = {
    'ERROR': ERROR,
    'WARNING': WARNING,
    'INFO': INFO,
    'DEBUG': DEBUG,
    'DB': DB,
}

FORMATTER_PATTERN = '%(asctime)s %(levelname)-8s %(threadName)s :: [%(curhash)s] %(message)s'
censored_items = {}
censored = []


def rebuild_censored_list():
    """Rebuild the censored list."""
    # set of censored items
    results = set()
    for value in itervalues(censored_items):
        if not value:
            continue

        if isinstance(value, collections_abc.Iterable) and not isinstance(
                value, (string_types, bytes, bytearray)):
            for item in value:
                if item and item != '0':
                    results.add(item)
        elif value and value != '0':
            results.add(value)

    def quote_unicode(value):
        """Quote a unicode value by encoding it to bytes first."""
        if isinstance(value, text_type):
            return quote(value.encode('utf-8', 'replace'))
        return quote(value)

    # set of censored items and urlencoded counterparts
    results |= {quote_unicode(item) for item in results}
    # convert set items to unicode and typecast to list
    results = list({item.decode('utf-8', 'replace')
                    if not isinstance(item, text_type) else item for item in results})
    # sort the list in order of descending length so that entire item is censored
    # e.g. password and password_1 both get censored instead of getting ********_1
    results.sort(key=len, reverse=True)

    # replace
    censored[:] = results


def list_modules(package):
    """Return all sub-modules for the specified package.

    :param package:
    :type package: module
    :return:
    :rtype: list of str
    """
    return [modname for importer, modname, ispkg in pkgutil.walk_packages(
        path=package.__path__, prefix=package.__name__ + '.', onerror=lambda x: None)]


def get_loggers(package):
    """Return all loggers for package and sub-packages.

    :param package:
    :type package: module
    :return:
    :rtype: list of logging.Logger
    """
    return [standard_logger(modname) for modname in list_modules(package)]


def read_loglines(log_file=None, modification_time=None, start_index=0, max_lines=None, max_traceback_depth=100,
                  predicate=lambda logline: True, formatter=lambda logline: logline):
    """A generator that returns the lines of all consolidated log files in descending order.

    :param log_file:
    :type log_file: str or unicode
    :param modification_time:
    :type modification_time: datetime.datetime
    :param start_index:
    :param max_lines:
    :type max_lines: int
    :param max_traceback_depth:
    :type max_traceback_depth: int
    :param predicate: filter function to accept or not the logline
    :type predicate: function
    :param formatter: function to format the logline
    :type formatter: function
    :return:
    :rtype: collections_abc.Iterable of LogLine
    """
    log_file = log_file or instance.log_file
    log_files = [log_file] + ['{file}.{index}'.format(file=log_file, index=i) for i in range(1, int(app.LOG_NR))]
    traceback_lines = []
    counter = 0
    for f in log_files:
        if not f or not os.path.isfile(f):
            continue

        if modification_time:
            log_mtime = os.path.getmtime(f)
            if log_mtime and datetime.datetime.fromtimestamp(log_mtime) < modification_time:
                continue

        for line in reverse_readlines(f):
            if not line or not line.strip():
                continue

            logline = LogLine.from_line(line)
            if logline:
                if logline.timestamp and modification_time and logline.timestamp < modification_time:
                    return
                if traceback_lines:
                    logline.traceback_lines = list(reversed(traceback_lines))
                    del traceback_lines[:]
                if predicate(logline):
                    counter += 1
                    if counter >= start_index:
                        yield formatter(logline)
                    if max_lines is not None and counter >= max_lines:
                        return

            elif len(traceback_lines) > max_traceback_depth:
                message = traceback_lines[-1]
                logline = LogLine(line, message=message, traceback_lines=list(reversed(traceback_lines[:-1])))
                del traceback_lines[:]
                if predicate(logline):
                    counter += 1
                    if counter >= start_index:
                        yield formatter(logline)
                    if max_lines is not None and counter >= max_lines:
                        return
            else:
                traceback_lines.append(line)

    if traceback_lines:
        message = traceback_lines[-1]
        logline = LogLine(message, message=message, traceback_lines=list(reversed(traceback_lines[:-1])))
        if predicate(logline):
            counter += 1
            if counter >= start_index:
                yield formatter(logline)


def blocks_r(file_path, size=64 * 1024):
    """
    Yields the data within a file in reverse-ordered blocks of given size.

    This code is part of the flyingcircus package: https://pypi.org/project/flyingcircus/
    The code was adapted for our use case.
    All credits go to the original author.

    Note that:
     - the content of the block is NOT reversed.

    Args:
        file_path (str): The input file path.
        size (int): The block size.

    Yields:
        block (bytes): The data within the blocks.

    """
    with io.open(file_path, 'rb') as file_obj:
        remaining_size = file_obj.seek(0, os.SEEK_END)
        while remaining_size > 0:
            block_size = min(remaining_size, size)
            file_obj.seek(remaining_size - block_size)
            block = file_obj.read(block_size)
            remaining_size -= block_size
            yield block


def reverse_readlines(file_path, skip_empty=True, append_newline=False,
                      block_size=128 * 1024, encoding='utf-8'):
    """
    Flexible function for reversing read lines incrementally.

    This code is part of the flyingcircus package: https://pypi.org/project/flyingcircus/
    The code was adapted for our use case.
    All credits go to the original author.

    Args:
        file_path (str): The input file path.
        skip_empty (bool): Skip empty lines.
        append_newline (bool): Append a new line character at the end of each yielded line.
        block_size (int): The block size.
        encoding (str): The encoding for correct block size computation.

    Yields:
        line (str): The next line.

    """
    newline = '\n'
    empty = ''
    remainder = empty
    block_generator = blocks_r
    for block in block_generator(file_path, size=block_size):
        lines = block.split(b'\n')
        if remainder:
            lines[-1] = lines[-1] + remainder
        remainder = lines[0]
        mask = slice(-1, 0, -1)
        for line in lines[mask]:
            if line or not skip_empty:
                yield line.decode(encoding) + (newline if append_newline else empty)
    if remainder or not skip_empty:
        yield remainder.decode(encoding) + (newline if append_newline else empty)


def filter_logline(logline, min_level=None, thread_name=None, search_query=None):
    """Return if logline matches the defined filter.

    :param logline:
    :type logline: medusa.logger.LogLine
    :param min_level:
    :type min_level: int
    :param thread_name:
    :type thread_name: set, text_type or function
    :param search_query:
    :type search_query: str
    :return:
    :rtype: bool
    """
    if not logline.is_loglevel_valid(min_level=min_level):
        return False

    if search_query:
        search_query = search_query.lower()
        if (not logline.message or search_query not in logline.message.lower()) and (
                not logline.extra or search_query not in logline.extra.lower()):
            return False

    if not thread_name:
        return True

    if callable(thread_name):
        return thread_name(logline.thread_name)

    if isinstance(thread_name, set):
        return logline.thread_name in thread_name

    return thread_name == logline.thread_name


def get_default_level():
    """Return the default log level to be used based on the user configuration.

    :return: the default log level
    :rtype: int
    """
    return DB if app.DBDEBUG else DEBUG if app.DEBUG else INFO


class LogLine(object):
    """Represent a log line."""

    # log regular expression:
    #   2016-08-06 15:58:34 ERROR    DAILYSEARCHER :: [d4ea5af] Exception generated in thread DAILYSEARCHER
    #   2016-08-25 20:12:03 INFO     SEARCHQUEUE-MANUAL-290853 :: [ProviderName] :: [d4ea5af] Performing episode search for Show Name
    #   2018-04-14 23:32:37 INFO     Thread_5 :: [6d54662] Broken providers found: [u'']
    log_re = re.compile(r'^(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})\s+'
                        r'(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})(?:,(?P<microsecond>\d{3}))?\s+'
                        r'(?P<level_name>[A-Z]+)\s+(?P<thread_name>.+?)(?:[-_](?P<thread_id>\d+))?\s+'
                        r'(?:::\s+\[(?P<extra>.+?)\]\s+)?::\s+\[(?P<curhash>[a-f0-9]{7})?\]\s+(?P<message>.*)$')

    tracebackline_re = re.compile(r'(?P<before>\s*File ")(?P<file>.+)(?P<middle>", line )(?P<line>\d+)(?P<after>, in .+)')

    def __init__(self, line, message=None, timestamp=None, level_name=None, thread_name=None,
                 thread_id=None, extra=None, curhash=None, traceback_lines=None):
        """Log Line Construtor.

        :param line:
        :type line: str or unicode
        :param message:
        :type message: str or unicode
        :param timestamp:
        :type timestamp: datetime.datetime
        :param level_name:
        :type level_name: str
        :param thread_name:
        :type thread_name: str
        :param thread_id:
        :type thread_id: int
        :param extra:
        :type extra: str
        :param curhash:
        :type curhash: str
        :param traceback_lines:
        :type traceback_lines: list of str
        """
        self.line = line
        self.message = message
        self.timestamp = timestamp
        self.level_name = level_name
        self.thread_name = thread_name
        self.thread_id = thread_id
        self.extra = extra
        self.curhash = curhash
        self.traceback_lines = traceback_lines

    @property
    def key(self):
        """Return the key for this logline.

        Important to not duplicate errors in ui view.
        """
        return '[{extra}] {message}'.format(extra=self.extra, message=self.message) if self.extra else self.message

    @property
    def issue_title(self):
        """Return the expected issue title for this logline."""
        result = None

        if self.traceback_lines:
            # Grab the first viable line from the end of the traceback lines
            offset = 1
            size = len(self.traceback_lines)
            while offset < size:
                # Grab the <-Nth> item from the list (-1, -2, ..., -N)
                line = self.traceback_lines[-offset]

                # Guessit errors have a template and tend to end in three lines that we don't want.
                # The original exception is one line before these lines.
                # --------------------------------------------------------------------
                # Please report at https://github.com/guessit-io/guessit/issues.
                # ====================================================================
                if line.startswith('=' * 20):
                    offset += 3
                    continue

                if line.strip():
                    result = line
                    break

                offset += 1

        # Not found a single viable traceback line, fall back to the log message.
        if not result:
            result = self.message

        return result[:1000]

    def to_json(self):
        """Dict representation."""
        result = OrderedDict([
            ('timestamp', self.timestamp),
            ('level', self.level_name),
            ('commit', self.curhash),
            ('thread', self.thread_name),
            ('message', self.message),
        ])
        if self.thread_id is not None:
            result['threadId'] = self.thread_id
        if self.extra:
            result['extra'] = self.extra
        if self.traceback_lines:
            result['traceback'] = self.traceback_lines

        return result

    def is_loglevel_valid(self, min_level=None):
        """Return true if the log level is valid and supported also taking into consideration min_level if defined.

        :param min_level:
        :type min_level: int
        :return:
        :rtype: bool
        """
        return self.level_name and self.level_name in LOGGING_LEVELS and (
            min_level is None or min_level <= LOGGING_LEVELS[self.level_name])

    def get_context_loglines(self, max_lines=75, timedelta=datetime.timedelta(seconds=45)):
        """Return the n log lines before current log line or log lines within the timedelta specified.

        :param max_lines:
        :type max_lines: int
        :param timedelta:
        :type timedelta: datetime.timedelta
        :return:
        :rtype: iterator of `LogLine`s
        """
        if not self.timestamp:
            raise ValueError('Log line does not have timestamp: {logline}'.format(logline=text_type(self)))

        start_timestamp = self.timestamp - timedelta if timedelta else self.timestamp

        result = []
        found = False
        for logline in read_loglines(modification_time=start_timestamp):
            if not found:
                if logline.timestamp == self.timestamp and logline.message == self.message:
                    found = True
                    result.append(logline)
                continue
            if logline.timestamp < start_timestamp:
                break

            result.append(logline)
            if len(result) >= max_lines:
                break

        return reversed(result)

    @classmethod
    def from_line(cls, line):
        """Create a Log Line from a string line.

        :param line:
        :type line: str
        :return:
        :rtype: LogLine or None
        """
        lines = line.split('\n')
        match = LogLine.log_re.match(lines[0])
        if not match:
            return

        g = match.groupdict()
        return LogLine(line=lines[0], message=g['message'], level_name=g['level_name'], extra=g.get('extra'), curhash=g['curhash'],
                       thread_name=g['thread_name'], thread_id=int(g['thread_id']) if g['thread_id'] else None, traceback_lines=lines[1:],
                       timestamp=datetime.datetime(year=int(g['year']), month=int(g['month']), day=int(g['day']),
                                                   hour=int(g['hour']), minute=int(g['minute']), second=int(g['second'])))

    def format_to_html(self, base_url):
        """Format logline to html."""
        results = ['<pre>', self.line]

        cwd = app.PROG_DIR + os.path.sep
        fmt = '{before}{cwd}<a href="{base_url}/{webpath}#L{line}">{relativepath}</a>{middle}{line}{after}'
        for traceback_line in self.traceback_lines or []:
            if not base_url:
                results.append(traceback_line)
                continue

            match = self.tracebackline_re.match(traceback_line)
            if not match:
                results.append(traceback_line)
                continue

            d = match.groupdict()
            filepath = d['file']
            if not filepath.startswith(cwd):
                results.append(traceback_line)
                continue

            relativepath = webpath = filepath[len(cwd):]
            if '\\' in relativepath:
                webpath = relativepath.replace('\\', '/')

            result = fmt.format(cwd=cwd, base_url=base_url, webpath=webpath, relativepath=relativepath,
                                before=d['before'], line=d['line'], middle=d['middle'], after=d['after'])

            results.append(result)

        results.append('</pre>')
        return '\n'.join(results)

    def __repr__(self):
        """Object representation."""
        return '%s(%r)' % (self.__class__, self.__dict__)

    def __str__(self):
        """String representation."""
        return '\n'.join([self.line] + (self.traceback_lines or []))


class ContextFilter(logging.Filter):
    """This is a filter which injects contextual information into the log, in our case: commit hash."""

    # level step
    level_step = INFO - DEBUG

    # level mapping to decrease library log levels
    level_mapping = {
        'subliminal': level_step,
        'subliminal.providers.addic7ed': 2 * level_step,
        'subliminal.providers.tvsubtitles': 2 * level_step,
        'subliminal.refiners.omdb': 2 * level_step,
        'subliminal.refiners.metadata': 2 * level_step,
        'subliminal.refiners.tvdb': 2 * level_step,
    }

    def filter(self, record):
        """Filter to add commit hash to log record, adjust log level and to add exception traceback for errors.

        :param record:
        :type record: logging.LogRecord
        :return:
        :rtype: bool
        """
        cur_commit_hash = app.CUR_COMMIT_HASH
        record.curhash = cur_commit_hash[:7] if cur_commit_hash and len(cur_commit_hash) > 6 else ''

        fullname = record.name
        basename = fullname.split('.')[0]
        decrease = self.level_mapping.get(fullname) or self.level_mapping.get(basename) or 0
        level = max(DB, record.levelno - decrease)
        if record.levelno != level:
            record.levelno = level
            record.levelname = logging.getLevelName(record.levelno)

        # add exception traceback for errors
        if record.levelno == ERROR and record.exc_info is not False:
            exc_info = sys.exc_info()
            record.exc_info = exc_info if exc_info != (None, None, None) else None

        return True


class CensoredFormatter(logging.Formatter, object):
    """Censor information such as API keys, user names, and passwords from the Log."""

    ssl_errors = {
        re.compile(r'error \[Errno \d+\] _ssl.c:\d+: error:\d+\s*:SSL routines:SSL23_GET_SERVER_HELLO:tlsv1 alert internal error'),
        re.compile(r'error \[SSL: SSLV3_ALERT_HANDSHAKE_FAILURE\] sslv3 alert handshake failure \(_ssl\.c:\d+\)')
    }

    absurd_re = re.compile(r'[\d\w]')

    def __init__(self, fmt=None, datefmt=None, encoding='utf-8'):
        """Constructor."""
        super(CensoredFormatter, self).__init__(fmt, datefmt)
        self.encoding = encoding

    def format(self, record):
        """Strip censored items from string.

        :param record: to censor
        :type record: logging.LogRecord
        :return:
        :rtype: str
        """
        from medusa import classes, common
        privacy_level = common.privacy_levels[app.PRIVACY_LEVEL]
        if not privacy_level:
            msg = super(CensoredFormatter, self).format(record)
        elif privacy_level == common.privacy_levels['absurd']:
            msg = self.absurd_re.sub('*', super(CensoredFormatter, self).format(record))
        else:
            msg = super(CensoredFormatter, self).format(record)
            if not isinstance(msg, text_type):
                msg = msg.decode(self.encoding, 'replace')  # Convert to unicode

            # Change the SSL error to a warning with a link to information about how to fix it.
            # Check for u'error [SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] sslv3 alert handshake failure (_ssl.c:590)'
            for ssl_error in self.ssl_errors:
                if ssl_error.findall(msg):
                    record.levelno = WARNING
                    record.levelname = logging.getLevelName(record.levelno)
                    msg = super(CensoredFormatter, self).format(record)
                    msg = ssl_error.sub('See: https://git.io/vVaIj', msg)

            for item in censored:
                msg = msg.replace(item, '**********')  # must not give any hint about the length

        level = record.levelno
        if level in (WARNING, ERROR):
            logline = LogLine.from_line(msg)
            if level == WARNING:
                classes.WarningViewer.add(logline)
            elif level == ERROR:
                classes.ErrorViewer.add(logline)

        return msg


class Logger(object):
    """Custom Logger."""

    def __init__(self):
        """Default Constructor."""
        self.logger = standard_logger('medusa')
        self.loggers = [self.logger]
        self.log_level = None
        self.log_file = None
        self.file_handler = None
        self.console_handler = None

    def init_logging(self, console_logging):
        """Initialize logging.

        :param console_logging: True if logging to console
        :type console_logging: bool
        """
        import medusa
        from medusa.helper.common import dateTimeFormat
        self.loggers.extend(get_loggers(medusa))
        self.loggers.extend(get_loggers(subliminal))
        self.loggers.extend([access_log, app_log, gen_log])
        self.loggers.extend(get_loggers(traktor))
        self.loggers.extend(get_loggers(knowit))
        self.loggers.extend(get_loggers(adba))

        logging.addLevelName(DB, 'DB')  # add a new logging level DB
        logging.getLogger().addHandler(NullHandler())  # nullify root logger
        log_filter = ContextFilter()

        # set custom root logger
        for logger in self.loggers:
            logger.propagate = False
            logger.addFilter(log_filter)

            if logger is not self.logger:
                logger.root = self.logger
                logger.parent = self.logger

        # console log handler
        if console_logging:
            console = logging.StreamHandler()
            console.setFormatter(CensoredFormatter(FORMATTER_PATTERN, dateTimeFormat))

            for logger in self.loggers:
                logger.addHandler(console)
            self.console_handler = console

        self.reconfigure_levels()
        self.reconfigure_file_handler()

    def reconfigure_file_handler(self):
        """Reconfigure rotating file handler."""
        from medusa.helper.common import dateTimeFormat
        target_file = os.path.join(app.LOG_DIR, app.LOG_FILENAME)
        target_size = int(app.LOG_SIZE * 1024 * 1024)
        target_number = int(app.LOG_NR)
        if not self.file_handler or self.log_file != target_file or self.file_handler.backupCount != target_number or self.file_handler.maxBytes != target_size:
            file_handler = RotatingFileHandler(target_file, maxBytes=target_size, backupCount=target_number, encoding='utf-8')
            file_handler.setFormatter(CensoredFormatter(FORMATTER_PATTERN, dateTimeFormat))
            file_handler.setLevel(self.log_level)

            for logger in self.loggers:
                if self.file_handler:
                    logger.removeHandler(self.file_handler)
                    self.file_handler.close()
                logger.addHandler(file_handler)

            self.log_file = target_file
            self.file_handler = file_handler

    def reconfigure_levels(self):
        """Adjust the log levels for some modules."""
        self.log_level = get_default_level()
        mapping = dict()

        modules_config = {
            'subliminal': app.SUBLIMINAL_LOG,
            'tornado': app.WEB_LOG
        }

        for modname, active in viewitems(modules_config):
            if not active:
                mapping.update({modname: CRITICAL})

        for logger in self.loggers:
            fullname = logger.name
            basename = fullname.split('.')[0]
            level = mapping.get(fullname) or mapping.get(basename) or self.log_level
            logger.setLevel(level)

        for handler in (self.console_handler, self.file_handler):
            if handler:
                handler.setLevel(self.log_level)

    def log(self, msg, level=INFO, *args, **kwargs):
        """Create log entry.

        :param msg: to log
        :param level: of log, e.g. DEBUG, INFO, etc.
        :type level: int
        :param args: to pass to logger
        :param kwargs: to pass to logger
        """
        self.logger.log(level, msg, *args, **kwargs)

    def log_error_and_exit(self, error_msg, *args, **kwargs):
        """Create and error log entry and exit application.

        :param error_msg: to log
        :param args: to pass to logger
        :param kwargs: to pass to logger
        """
        self.log(error_msg, ERROR, *args, **kwargs)

        if not self.console_handler:
            sys.exit(error_msg.encode(app.SYS_ENCODING, 'xmlcharrefreplace'))
        else:
            sys.exit(1)


class Wrapper(object):
    """Wrapper that delegates all calls to the actual Logger instance."""

    def __init__(self, wrapped):
        """Constructor with the actual module instance.

        :param wrapped:
        """
        self.wrapped = wrapped

    def __getattr__(self, name):
        """Delegate to the wrapped module instance or to Logger instance.

        :param name:
        :type name: str
        :return:
        """
        try:
            return getattr(self.wrapped, name)
        except AttributeError:
            return getattr(self.instance, name)


def log(*args, **kwargs):
    """To avoid IDE warnings everywhere.

    :param args:
    :param kwargs:
    """
    _globals.instance.log(*args, **kwargs)


def init_logging(console_logging):
    """Shortcut to init logging."""
    instance.init_logging(console_logging)


def reconfigure():
    """Shortcut to reconfigure logging."""
    instance.reconfigure_levels()
    instance.reconfigure_file_handler()


def log_error_and_exit(error_msg, *args, **kwargs):
    """Shortcut to log_error_and_exit."""
    instance.log_error_and_exit(error_msg, *args, **kwargs)


def backwards_compatibility():
    """Keep backwards compatibility renaming old log files."""
    log_re = re.compile(r'\w+\.log(?P<suffix>\.\d+)?')
    cwd = os.getcwd() if os.path.isabs(app.DATA_DIR) else ''
    for filename in os.listdir(app.LOG_DIR):
        # Rename log files
        match = log_re.match(filename)
        if match:
            new_file = os.path.join(cwd, app.LOG_DIR, app.LOG_FILENAME + (match.group('suffix') or ''))
            if not any(f.startswith(os.path.basename(filename)) for f in os.listdir(app.LOG_DIR)):
                os.rename(os.path.join(cwd, app.LOG_DIR, filename), new_file)
            continue


instance = Logger()
_globals = sys.modules[__name__] = Wrapper(sys.modules[__name__])  # pylint: disable=invalid-name
