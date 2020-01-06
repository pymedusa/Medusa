# coding=utf-8

"""General utility functions."""
from __future__ import unicode_literals

from builtins import str
from datetime import datetime

from dateutil import tz

from six import string_types, viewitems
from six.moves.collections_abc import Iterable


def generate(it):
    """
    Generate items from an iterable.

    :param it: an iterable
    :return: items from an iterable
        If the iterable is a string yield the entire string
        If the item is not iterable, yield the item
    """
    if isinstance(it, Iterable) and not isinstance(it, string_types):
        for item in it:
            yield item
    else:
        yield it


def gen_values_by_key(it, key):
    """Generate values by key."""
    return (item[key] for item in it)


def split_and_strip(value, sep=','):
    """Split a value based on the passed separator, and remove whitespace for each individual value."""
    return [_.strip() for _ in value.split(sep) if value != ''] if isinstance(value, string_types) else value


def safe_get(dct, keys, default=''):
    """
    Iterate over a dict with a tuple of keys to get the last value.

    :param dct: a dictionary
    :param keys: a tuple of keys
    :param default: default value to return in case of error
    :return: value from the last key in the tuple or default
    """
    for key in keys:
        try:
            dct = dct[key]
        except KeyError:
            return default
    return dct


def truth_to_bool(value):
    """
    Convert a representation of truth to a boolean.

    :param value: str, int or None
    :return: boolean value, either True or False
    """
    return bool(strtobool(str(value))) if value else False


def strtobool(val):
    """
    Convert a string representation of truth to true (1) or false (0).

    Ported from: https://is.gd/FSeBX8
    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if
    'val' is anything else.
    """
    val = val.lower()
    if val in ('y', 'yes', 't', 'true', 'on', '1'):
        return 1
    elif val in ('n', 'no', 'f', 'false', 'off', '0'):
        return 0
    else:
        raise ValueError('invalid truth value %r' % (val,))


def to_timestamp(dt):
    """
    Return POSIX timestamp corresponding to the datetime instance.

    :param dt: datetime (possibly aware)
    :return: seconds since epoch as float
    """
    epoch = datetime(1970, 1, 1, tzinfo=tz.gettz('UTC'))
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        dt_utc = dt.replace(tzinfo=tz.gettz('UTC'))
    else:
        dt_utc = dt.astimezone(tz.gettz('UTC'))

    return (dt_utc - epoch).total_seconds()


def to_camel_case(snake_str):
    """Convert a snake formatted string to camel case."""
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


def dict_to_array(values, key, value):
    """
    Convert a dict to an array with dicts.

    Use the paramaters key and value to describe the key/value property in the new array.

    For example. values: {a: b, c: d}, with key="my_key_prop" and value="my_value_prop".
    Will result in: [{"my_key_prop": a, "my_value_prop": b}, {"my_key_prop": c, "my_value_prop": d}, ...etc].

    :param values: Dict with single key/value mappings.
    :param key: Name for the key property.
    :param value: Name for the value property.
    :return: An array of dicts.
    """
    return [{key: k, value: v} for k, v in viewitems(values)]


def timedelta_in_milliseconds(td):
    """
    Return the value of the timedelta object in milliseconds.

    :param td: timedelta
    :type td: timedelta
    :return: the value of the timedelta in milliseconds
    :rtype: int
    """
    if not td:
        return 0

    return int(td.total_seconds() * 1000)


def int_default(value, default=0):
    """Cast value to integer or default if None."""
    if value is not None:
        return int(value)
    return default
