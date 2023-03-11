# -*- coding: utf-8 -*-
import re
import unicodedata
from datetime import datetime, timezone

__author__ = 'Jon Nappi'
__all__ = ['slugify', 'airs_date', 'now', 'timestamp', 'extract_ids']


def slugify(value):
    """Converts to lowercase, removes non-word characters (alphanumerics and
    underscores) and converts spaces to hyphens. Also strips leading and
    trailing whitespace.

    Adapted from django.utils.text.slugify
    """
    value = unicodedata.normalize('NFKD', value)
    # special case, "ascii" encode would just remove it
    value = value.replace("’", '-')
    value = value.encode('ascii', 'ignore').decode('utf-8')
    value = value.lower()
    value = re.sub(r'[^\w\s-]', ' ', value)
    value = re.sub(r'[-\s]+', '-', value)
    value = value.strip('-')

    return value


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
    meow = datetime.now(tz=timezone.utc)
    return meow.strftime("%Y-%m-%d")


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
