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
"""Custom Logger."""

from __future__ import unicode_literals

import datetime
import difflib
import io
import logging
import os
import pkgutil
import re
import sys

from inspect import getargspec
from logging import NullHandler
from logging.handlers import RotatingFileHandler

from requests.compat import quote
import sickbeard
from sickbeard import classes
import sickrage
from sickrage.helper.common import dateTimeFormat
from sickrage.helper.encoding import ek
from six import itervalues, text_type
import subliminal
from tornado.log import access_log, app_log, gen_log
import traktor


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

FORMATTER_PATTERN = '%(asctime)s %(levelname)-8s %(threadName)s :: [%(curhash)s] %(message)s'
default_encoding = 'utf-8'
censored_items = {}
censored = []


def rebuild_censored_list():
    """Rebuild the censored list."""
    # set of censored items
    results = {value for value in itervalues(censored_items) if value}
    # set of censored items and urlencoded counterparts
    results = results | {quote(item) for item in results}
    # convert set items to unicode and typecast to list
    results = list({item.decode(default_encoding, 'replace')
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
    return [logging.getLogger(modname) for modname in list_modules(package)]


def read_loglines(log_file=None, traceback_lines=None, modification_time=None, max_lines=None,
                  predicate=lambda logline: True,
                  formatter=lambda logline: logline):
    """A generator that returns the lines of all consolidated log files in descending order.

    :param log_file:
    :type log_file: str or unicode
    :param traceback_lines: mostly used in recursion call.
    :type traceback_lines: list of str
    :param modification_time:
    :type modification_time: datetime.datetime
    :param max_lines:
    :type max_lines: int
    :param predicate: filter function to accept or not the logline
    :type predicate: function
    :param formatter: function to format the logline
    :type formatter: function
    :return:
    :rtype: collections.Iterable of LogLine
    """
    log_file = log_file or _wrapper.instance.log_file
    log_files = [log_file] + ['{file}.{index}'.format(file=log_file, index=i) for i in range(1, int(sickbeard.LOG_NR))]
    traceback_lines = traceback_lines or []
    counter = 0
    for f in log_files:
        if not ek(os.path.isfile, f):
            continue
        if modification_time:
            log_mtime = ek(os.path.getmtime, f)
            if log_mtime and datetime.datetime.fromtimestamp(log_mtime) < modification_time:
                continue

        for line in reverse_readlines(f):
            logline = LogLine.from_line(line)
            if logline:
                if logline.timestamp and modification_time and logline.timestamp < modification_time:
                    return
                if traceback_lines:
                    logline.traceback_lines = list(reversed(traceback_lines))
                    del traceback_lines[:]
                if predicate(logline):
                    counter += 1
                    yield formatter(logline)
                    if max_lines is not None and counter >= max_lines:
                        return

            elif len(traceback_lines) > 200:  # Limiting the maximum traceback depth to 200
                message = '\n'.join(reversed(traceback_lines))
                del traceback_lines[:]
                logline = LogLine(line, message=message)
                if predicate(logline):
                    counter += 1
                    yield formatter(logline)
                    if max_lines is not None and counter >= max_lines:
                        return
            else:
                traceback_lines.append(line)

    if traceback_lines:
        message = '\n'.join(reversed(traceback_lines))
        logline = LogLine(message, message=message)
        if predicate(logline):
            yield formatter(logline)


def reverse_readlines(filename, buf_size=2097152, encoding=default_encoding):
    """A generator that returns the lines of a file in reverse order.

    Thanks to Andomar: http://stackoverflow.com/a/23646049

    :param filename:
    :type filename: str
    :param encoding:
    :type encoding: str
    :param buf_size:
    :return:
    :rtype: collections.Iterable of str
    """
    with io.open(filename, 'r', encoding=encoding) as fh:
        segment = None
        offset = 0
        fh.seek(0, os.SEEK_END)
        file_size = remaining_size = fh.tell()
        while remaining_size > 0:
            offset = min(file_size, offset + buf_size)
            fh.seek(file_size - offset)
            buf = fh.read(min(remaining_size, buf_size))
            remaining_size -= buf_size
            lines = buf.split('\n')
            # the first line of the buffer is probably not a complete line so
            # we'll save it and append it to the last line of the next buffer
            # we read
            if segment is not None:
                # if the previous chunk starts right from the beginning of line
                # do not concact the segment to the last line of new chunk
                # instead, yield the segment first
                if buf[-1] is not '\n':
                    lines[-1] += segment
                else:
                    yield segment
            segment = lines[0]
            for index in range(len(lines) - 1, 0, -1):
                if len(lines[index]):
                    yield lines[index]
        # Don't yield None if the file was empty
        if segment is not None:
            yield segment


def filter_logline(logline, min_level=None, thread_name=None, search_query=None):
    """Return if logline matches the defined filter.

    :param logline:
    :type logline: sickbeard.logger.LogLine
    :param min_level:
    :type min_level: int
    :param thread_name:
    :type thread_name: str or function
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

    return thread_name == logline.thread_name


def get_default_level():
    """Return the default log level to be used based on the user configuration.

    :return: the default log level
    :rtype: int
    """
    return DB if sickbeard.DBDEBUG else DEBUG if sickbeard.DEBUG else INFO


class LogLine(object):
    """Represent a log line."""

    # log regular expression:
    #   2016-08-06 15:58:34 ERROR    DAILYSEARCHER :: [d4ea5af] Exception generated in thread DAILYSEARCHER
    #   2016-08-25 20:12:03 INFO     SEARCHQUEUE-MANUAL-290853 :: [ProviderName] :: [d4ea5af] Performing episode search for Show Name
    log_re = re.compile(r'^(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})\s+'
                        r'(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})(?:,(?P<microsecond>\d{3}))?\s+'
                        r'(?P<level_name>[A-Z]+)\s+(?P<thread_name>.+?)(?:-(?P<thread_id>\d+))?\s+'
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
        return '{extra} {message}'.format(extra=self.extra, message=self.message) if self.extra else self.message

    @property
    def issue_title(self):
        """Return the expected issue title for this logline."""
        result = self.traceback_lines[-1] if self.traceback_lines else self.message
        return result[:1000]

    def is_title_similar_to(self, title):
        """Return wheter the logline title is similar to.

        :param title:
        :type title: str
        :return:
        :rtype: bool
        """
        return difflib.SequenceMatcher(None, self.issue_title, title).ratio() >= 0.9

    def is_loglevel_valid(self, min_level=None):
        """Return true if the log level is valid and supported also taking into consideration min_level if defined.

        :param min_level:
        :type min_level: int
        :return:
        :rtype: bool
        """
        return self.level_name and self.level_name in LOGGING_LEVELS and (
            min_level is None or min_level <= LOGGING_LEVELS[self.level_name])

    def get_context_loglines(self, numberdelta=100, timedelta=datetime.timedelta(seconds=45)):
        """Return the n log lines before current log line or log lines within the timedelta specified.

        :param numberdelta:
        :type numberdelta: int
        :param timedelta:
        :type timedelta: datetime.timedelta
        :return:
        :rtype: list of LogLine
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
            if len(result) >= numberdelta:
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

        cwd = os.getcwd() + '/'
        fmt = '{before}{cwd}<a href="{base_url}/{relativepath}#L{line}">{relativepath}</a>{middle}{line}{after}'
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

            relativepath = filepath[len(cwd):]
            result = fmt.format(cwd=cwd, base_url=base_url, relativepath=relativepath,
                                before=d['before'], line=d['line'], middle=d['middle'], after=d['after'])

            results.append(result)

        results.append('</pre>')
        return '\n'.join(results)

    def __repr__(self):
        """Object representation."""
        return "%s(%r)" % (self.__class__, self.__dict__)

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
        'subliminal.providers.itasa': 2 * level_step,
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
        cur_commit_hash = sickbeard.CUR_COMMIT_HASH
        record.curhash = cur_commit_hash[:7] if cur_commit_hash and len(cur_commit_hash) > 6 else ''

        fullname = record.name
        basename = fullname.split('.')[0]
        decrease = self.level_mapping.get(fullname) or self.level_mapping.get(basename) or 0
        level = max(DEBUG, record.levelno - decrease)
        if record.levelno != level:
            record.levelno = level
            record.levelname = logging.getLevelName(record.levelno)

        # add exception traceback for errors
        if record.levelno == ERROR:
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

    # Needed because Newznab apikey isn't stored as key=value in a section.
    apikey_re = re.compile(r'(?P<before>[&?]r|[&?]apikey|[&?]api_key)(?:=|%3D)([^&]*)(?P<after>[&\w]?)', re.IGNORECASE)

    def __init__(self, fmt=None, datefmt=None, encoding=default_encoding):
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
        privacy_level = sickbeard.common.privacy_levels[sickbeard.PRIVACY_LEVEL]
        if not privacy_level:
            msg = super(CensoredFormatter, self).format(record)
        elif privacy_level == sickbeard.common.privacy_levels['absurd']:
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

            msg = self.apikey_re.sub(r'\g<before>=**********\g<after>', msg)

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
        self.logger = logging.getLogger('sickrage')
        self.loggers = [self.logger]
        self.loggers.extend(get_loggers(sickrage))
        self.loggers.extend(get_loggers(sickbeard))
        self.loggers.extend(get_loggers(subliminal))
        self.loggers.extend([access_log, app_log, gen_log])
        self.loggers.extend(get_loggers(traktor))
        self.log_level = None
        self.log_file = None
        self.file_handler = None
        self.console_handler = None

    def init_logging(self, console_logging):
        """Initialize logging.

        :param console_logging: True if logging to console
        :type console_logging: bool
        """
        logging.addLevelName(DB, 'DB')  # add a new logging level DB
        logging.getLogger().addHandler(NullHandler())  # nullify root logger
        log_filter = ContextFilter()

        # set custom root logger
        for logger in self.loggers:
            logger.addFilter(log_filter)

            if logger is not self.logger:
                logger.root = self.logger
                logger.parent = self.logger
                logger.propagate = False

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
        target_file = ek(os.path.join, sickbeard.LOG_DIR, 'sickrage.log')
        target_size = int(sickbeard.LOG_SIZE * 1024 * 1024)
        target_number = int(sickbeard.LOG_NR)
        if not self.file_handler or self.log_file != target_file or self.file_handler.backupCount != target_number or self.file_handler.maxBytes != target_size:
            file_handler = RotatingFileHandler(target_file, maxBytes=target_size, backupCount=target_number, encoding=default_encoding)
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
            'subliminal': sickbeard.SUBLIMINAL_LOG,
            'tornado': sickbeard.WEB_LOG
        }

        for modname, active in modules_config.items():
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

    @staticmethod
    def shutdown():
        """Shut down the logger."""
        logging.shutdown()

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
            sys.exit(error_msg.encode(sickbeard.SYS_ENCODING, 'xmlcharrefreplace'))
        else:
            sys.exit(1)


class BraceMessage(object):
    """Log Message wrapper that applies new string format style."""

    def __init__(self, fmt, args, kwargs):
        """Constructor.

        :param fmt:
        :type fmt: logging.Formatter
        :param args:
        :param kwargs:
        """
        self.fmt = fmt
        self.args = args
        self.kwargs = kwargs

    def __str__(self):
        """String representation.

        :return:
        :rtype: str
        """
        result = text_type(self.fmt)
        return result.format(*self.args, **self.kwargs) if self.args or self.kwargs else result


class StyleAdapter(logging.LoggerAdapter):
    """Logger Adapter with new string format style."""

    adapter_members = {attr: attr for attr in dir(logging.LoggerAdapter) if not callable(attr) and not attr.startswith('__')}
    adapter_members.update({'warn': 'warning', 'fatal': 'critical'})
    reserved_keywords = getargspec(logging.Logger._log).args[1:]

    def __init__(self, target_logger, extra=None):
        """Constructor.

        :param target_logger:
        :type target_logger: logging.Logger
        :param extra:
        :type extra: dict
        """
        super(StyleAdapter, self).__init__(target_logger, extra)

    def __getattr__(self, name):
        """Wrapper that delegates to the actual logger.

        :param name:
        :type name: str
        :return:
        """
        if name not in self.adapter_members:
            return getattr(self.logger, name)

        return getattr(self, self.adapter_members[name])

    def process(self, msg, kwargs):
        """Enhance default process to use BraceMessage and remove unsupported keyword args for the actual logger method.

        :param msg:
        :param kwargs:
        :return:
        """
        return BraceMessage(msg, (), kwargs), {k: kwargs[k] for k in self.reserved_keywords if k in kwargs}


class Wrapper(object):
    """Wrapper that delegates all calls to the actual Logger instance."""

    instance = Logger()

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


def custom_get_logger(name=None):
    """Custom logging.getLogger function.

    :param name:
    :return:
    """
    return StyleAdapter(standard_logger(name))


def init_logging(console_logging):
    """Shortcut to init logging."""
    _wrapper.instance.init_logging(console_logging)


def reconfigure():
    """Shortcut to reconfigure logging."""
    _wrapper.instance.reconfigure_levels()
    _wrapper.instance.reconfigure_file_handler()


# Keeps the standard logging.getLogger to be used by SylteAdapter
standard_logger = logging.getLogger

# Replaces logging.getLogger with our custom one
logging.getLogger = custom_get_logger

_wrapper = Wrapper(sys.modules[__name__])
_globals = sys.modules[__name__] = _wrapper  # pylint: disable=invalid-name
