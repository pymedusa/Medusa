# coding=utf-8
"""Module with common helper utils."""
from __future__ import division
from __future__ import unicode_literals

import datetime
import logging
import re
import traceback
from fnmatch import fnmatch

from medusa import app

from six import PY3, text_type


log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

if PY3:
    long = int

dateFormat = '%Y-%m-%d'
dateTimeFormat = '%Y-%m-%d %H:%M:%S'
# Mapping HTTP status codes to official W3C names
http_status_code = {
    300: 'Multiple Choices',
    301: 'Moved Permanently',
    302: 'Found',
    303: 'See Other',
    304: 'Not Modified',
    305: 'Use Proxy',
    306: 'Switch Proxy',
    307: 'Temporary Redirect',
    308: 'Permanent Redirect',
    400: 'Bad Request',
    401: 'Unauthorized',
    402: 'Payment Required',
    403: 'Forbidden',
    404: 'Not Found',
    405: 'Method Not Allowed',
    406: 'Not Acceptable',
    407: 'Proxy Authentication Required',
    408: 'Request Timeout',
    409: 'Conflict',
    410: 'Gone',
    411: 'Length Required',
    412: 'Precondition Failed',
    413: 'Request Entity Too Large',
    414: 'Request-URI Too Long',
    415: 'Unsupported Media Type',
    416: 'Requested Range Not Satisfiable',
    417: 'Expectation Failed',
    418: 'Im a teapot',
    419: 'Authentication Timeout',
    420: 'Enhance Your Calm',
    422: 'Unprocessable Entity',
    423: 'Locked',
    424: 'Failed Dependency',
    426: 'Upgrade Required',
    428: 'Precondition Required',
    429: 'Too Many Requests',
    431: 'Request Header Fields Too Large',
    440: 'Login Timeout',
    444: 'No Response',
    449: 'Retry With',
    450: 'Blocked by Windows Parental Controls',
    451: [
        'Redirect',
        'Unavailable For Legal Reasons',
    ],
    494: 'Request Header Too Large',
    495: 'Cert Error',
    496: 'No Cert',
    497: 'HTTP to HTTPS',
    498: 'Token expired/invalid',
    499: [
        'Client Closed Request',
        'Token required',
    ],
    500: 'Internal Server Error',
    501: 'Not Implemented',
    502: 'Bad Gateway',
    503: 'Service Unavailable',
    504: 'Gateway Timeout',
    505: 'HTTP Version Not Supported',
    506: 'Variant Also Negotiates',
    507: 'Insufficient Storage',
    508: 'Loop Detected',
    509: 'Bandwidth Limit Exceeded',
    510: 'Not Extended',
    511: 'Network Authentication Required',
    520: 'CloudFlare - Web server is returning an unknown error',
    521: 'CloudFlare - Web server is down',
    522: 'CloudFlare - Connection timed out',
    523: 'CloudFlare - Origin is unreachable',
    524: 'CloudFlare - A timeout occurred',
    525: 'CloudFlare - SSL handshake failed',
    526: 'CloudFlare - Invalid SSL certificate',
    598: 'Network read timeout error',
    599: 'Network connect timeout error',
}
media_extensions = [
    '3gp',
    'asf',
    'avi',
    'divx',
    'dvr-ms',
    'f4v',
    'flv',
    'img',
    'iso',
    'm2ts',
    'm4v',
    'mkv',
    'mov',
    'mp4',
    'mpeg',
    'mpg',
    'ogm',
    'ogv',
    'rmvb',
    'strm',
    'tp',
    'ts',
    'vob',
    'webm',
    'wma',
    'wmv',
    'wtv',
]
subtitle_extensions = ['ass', 'idx', 'srt', 'ssa', 'sub', 'mpl', 'smi']
timeFormat = '%A %I:%M %p'


def http_code_description(http_code):
    """
    Get the description of the provided HTTP status code.

    :param http_code: The HTTP status code
    :return: The description of the provided ``http_code``
    """
    description = http_status_code.get(try_int(http_code))

    if isinstance(description, list):
        return '(%s)' % ', '.join(description)

    return description


def is_sync_file(filename):
    """
    Check if the provided ``filename`` is a sync file, based on its name.

    :param filename: The filename to check
    :return: ``True`` if the ``filename`` is a sync file, ``False`` otherwise
    """
    if isinstance(filename, (str, text_type)):
        extension = filename.rpartition('.')[2].lower()

        return (extension in app.SYNC_FILES or
                filename.startswith('.syncthing') or
                any(fnmatch(filename, match) for match in app.SYNC_FILES))

    return False


def is_torrent_or_nzb_file(filename):
    """
    Check if the provided ``filename`` is a NZB file or a torrent file, based on its extension.

    :param filename: The filename to check
    :return: ``True`` if the ``filename`` is a NZB file or a torrent file, ``False`` otherwise
    """
    if not isinstance(filename, (str, text_type)):
        return False

    return filename.rpartition('.')[2].lower() in ['nzb', 'torrent']


def pretty_file_size(size, use_decimal=False, **kwargs):
    """
    Return a human readable representation of the provided ``size``.

    :param size: The size to convert
    :param use_decimal: use decimal instead of binary prefixes (e.g. kilo = 1000 instead of 1024)

    :keyword units: A list of unit names in ascending order. Default units: ['B', 'KB', 'MB', 'GB', 'TB', 'PB']

    :return: The converted size
    """
    try:
        size = max(float(size), 0.)
    except (ValueError, TypeError):
        size = 0.

    remaining_size = size
    units = kwargs.pop('units', ['B', 'KB', 'MB', 'GB', 'TB', 'PB'])
    block = 1024. if not use_decimal else 1000.
    for unit in units:
        if remaining_size < block:
            return '%3.2f %s' % (remaining_size, unit)
        remaining_size /= block
    return size


def convert_size(size, default=None, use_decimal=False, **kwargs):
    """
    Convert a file size into the number of bytes.

    :param size: to be converted
    :param default: value to return if conversion fails
    :param use_decimal: use decimal instead of binary prefixes (e.g. kilo = 1000 instead of 1024)

    :keyword sep: Separator between size and units, default is space
    :keyword units: A list of (uppercase) unit names in ascending order.
                    Default units: ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    :keyword default_units: Default unit if none is given, default is lowest unit in the scale, e.g. bytes

    :returns: the number of bytes, the default value, or 0
    """
    result = None

    try:
        sep = kwargs.pop('sep', ' ')
        scale = kwargs.pop('units', ['B', 'KB', 'MB', 'GB', 'TB', 'PB'])
        default_units = kwargs.pop('default_units', scale[0])

        if sep:
            size_tuple = size.strip().split(sep)
            scalar, units = size_tuple[0], size_tuple[1:]
            units = units[0].upper() if units else default_units
        else:
            regex_units = re.search(r'([0-9.]+)\s*({scale})'.format(scale='|'.join(scale)), size, re.IGNORECASE)
            units = regex_units.group(2).upper() if regex_units else default_units
            scalar = regex_units.group(1)

        scalar = float(scalar)
        scalar *= (1024 if not use_decimal else 1000) ** scale.index(units)

        result = scalar

    # TODO: Make sure fallback methods obey default units
    except AttributeError:
        result = size if size is not None else default

    except ValueError:
        result = default

    finally:
        try:
            if result != default:
                result = int(result)
                result = max(result, 0)
        except (TypeError, ValueError):
            pass

    return result


def remove_extension(filename):
    """
    Remove the extension of the provided ``filename``.

    The extension is only removed if it is in `medusa.helper.common.media_extensions` or ['nzb', 'torrent'].
    :param filename: The filename from which we want to remove the extension
    :return: The ``filename`` without its extension.
    """
    if isinstance(filename, (str, text_type)) and '.' in filename:
        basename, _, extension = filename.rpartition('.')

        if basename and extension.lower() in ['nzb', 'torrent'] + media_extensions:
            return basename

    return filename


def replace_extension(filename, new_extension):
    """
    Replace the extension of the provided ``filename`` with a new extension.

    :param filename: The filename for which we want to change the extension
    :param new_extension: The new extension to apply on the ``filename``
    :return: The ``filename`` with the new extension
    """
    if isinstance(filename, (str, text_type)) and '.' in filename:
        basename, _, _ = filename.rpartition('.')

        if basename:
            return '%s.%s' % (basename, new_extension)

    return filename


def sanitize_filename(filename):
    """
    Remove specific characters from the provided ``filename``.

    :param filename: The filename to clean
    :return: The cleaned ``filename``
    """
    if isinstance(filename, (str, text_type)):
        # https://stackoverflow.com/a/31976060/7597273
        remove = r''.join((
            r':"<>|?',
            r'™',  # Trade Mark Sign [unicode: \u2122]
            r'\t',  # Tab
            r'\x00-\x1f',  # Null & Control characters
        ))
        remove = r'[' + remove + r']'

        filename = re.sub(r'[\\/\*]', '-', filename)
        filename = re.sub(remove, '', filename)
        # Filenames cannot end in a space or dot on Windows systems
        filename = filename.strip(' .')

        return filename

    return ''


def try_int(candidate, default_value=0):
    """
    Try to convert ``candidate`` to int, or return the ``default_value``.

    :param candidate: The value to convert to int
    :param default_value: The value to return if the conversion fails
    :return: ``candidate`` as int, or ``default_value`` if the conversion fails
    """
    try:
        return int(candidate)
    except (ValueError, TypeError):
        if candidate:
            # Get the current stack trace (excluding the following line)
            stack_trace = traceback.format_stack(limit=10)[:-2]
            log.exception('Casting to int failed.\nStack trace:\n{0}'.format(''.join(stack_trace)))
        return default_value


def episode_num(season=None, episode=None, numbering='standard'):
    """
    Convert season and episode into string.

    :param season: Season number
    :type season: int or None
    :param episode: Episode Number
    :type episode: int or None
    :param numbering: standard or absolute numbering
    :type numbering: str
    :returns: a string in s01e01 format or absolute numbering
    """
    if numbering == 'standard':
        if season is not None and episode:
            return 'S{0:0>2}E{1:0>2}'.format(season, episode)
    elif numbering == 'absolute':
        if not (season and episode) and (season or episode):
            return '{0:0>3}'.format(season or episode)


def enabled_providers(search_type):
    """Return providers based on search type: daily, backlog and manual search."""
    from medusa import providers
    return [x for x in providers.sorted_provider_list(app.RANDOMIZE_PROVIDERS)
            if x.is_active() and x.get_id() not in app.BROKEN_PROVIDERS and
            hasattr(x, 'enable_{}'.format(search_type)) and
            getattr(x, 'enable_{}'.format(search_type))]


def remove_strings(old_string, unwanted_strings):
    """
    Return string removing all unwanted strings on it.

    :param old_string: String that will be cleaned
    :param unwanted_strings: List of unwanted strings

    :returns: the string without the unwanted strings
    """
    if not old_string:
        return

    for item in unwanted_strings:
        old_string = old_string.replace(item, '')
    return old_string


def pretty_date(d):
    """Convert a datetime into relative date."""
    diff = datetime.datetime.now() - d
    s = diff.seconds
    if diff.days > 7 or diff.days < 0:
        return d.strftime('%d %b %y')
    elif diff.days == 1:
        return '1 day ago'
    elif diff.days > 1:
        return '{} days ago'.format(diff.days)
    elif s <= 1:
        return 'just now'
    elif s < 60:
        return '{} seconds ago'.format(s)
    elif s < 120:
        return '1 minute ago'
    elif s < 3600:
        return '{} minutes ago'.format(s // 60)
    elif s < 7200:
        return '1 hour ago'
    else:
        return '{} hours ago'.format(s // 3600)
