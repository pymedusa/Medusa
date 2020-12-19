# -*- coding: utf-8 -*-
import re
import six
import unicodedata
from datetime import datetime

__author__ = 'Jon Nappi'
__all__ = ['slugify', 'airs_date', 'now', 'timestamp', 'extract_ids',
           'unicode_safe']


def slugify(value):
    """Converts to lowercase, removes non-word characters (alphanumerics and
    underscores) and converts spaces to hyphens. Also strips leading and
    trailing whitespace.

    Adapted from django.utils.text.slugify
    """
    if six.PY2 and isinstance(value, str):
        value = unicode(value, 'utf-8')  # NOQA
    nfkd_form = unicodedata.normalize('NFKD', value)
    decoded = nfkd_form.encode('ascii', 'ignore').decode('utf-8')
    value = re.sub(r'[^\w\s-]', ' ', decoded).strip().lower()
    return re.sub(r'[-\s]+', '-', value)


def airs_date(airs_at):
    """convert a timestamp of the form '2015-02-01T05:30:00.000-08:00Z' to a
    python datetime object (with time zone information removed)
    """
    if airs_at is None:
        return None
    parsed = airs_at.split('-')[:-1]
    if len(parsed) == 2:
        return datetime.strptime(airs_at[:-1], '%Y-%m-%dT%H:%M:%S.000')
    return datetime.strptime('-'.join(parsed), '%Y-%m-%dT%H:%M:%S.000')


def now():
    """Get the current day in the format expected by each :class:`Calendar`"""
    meow = datetime.now()
    year = meow.year
    month = meow.month if meow.month >= 10 else '0{}'.format(meow.month)
    day = meow.day if meow.day >= 10 else '0{}'.format(meow.day)
    return '{}-{}-{}'.format(year, month, day)


def timestamp(date_object):
    """Generate a trakt formatted timestamp from the given date object"""
    fmt = '%Y-%m-%d:T%H:%M:%S.000Z'
    return date_object.strftime(fmt)


def extract_ids(id_dict):
    """Extract the inner `ids` dict out of trakt JSON responses and insert them
    into the containing `dict`. Then return the input `dict`
    """
    id_dict.update(id_dict.pop('ids', {}))
    return id_dict


def unicode_safe(s):
    if six.PY3:
        return s
    return s.encode('ascii', 'ignore').decode('ascii')
