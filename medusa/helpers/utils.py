# coding=utf-8

"""General utility functions."""

from collections import Iterable

from six import string_types


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


def split_and_strip(value, sep=','):
    """Split a value based on the passed separator, and remove whitespace for each individual value."""
    return [_.strip() for _ in value.split(sep) if value != ''] if isinstance(value, string_types) else value
