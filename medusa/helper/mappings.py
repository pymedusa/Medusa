# coding=utf-8
"""Extended collections."""
from __future__ import unicode_literals


class NonEmptyDict(dict):
    """Dictionary that only accept values that are not none and not empty strings."""

    def __setitem__(self, key, value):
        """Discard None values and empty strings."""
        if key in self or value is not None and value != '':
            super(NonEmptyDict, self).__setitem__(key, value)
