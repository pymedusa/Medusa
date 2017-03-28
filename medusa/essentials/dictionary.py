# coding=utf-8
"""Extended dictionaries."""

from collections import OrderedDict


def not_none(x):
    """Return true is x is not none."""
    return x is not None


def not_empty(x):
    """Return true is x is not none and not empty."""
    return x is not None and x != ''


class OrderedPredicateDict(OrderedDict):
    """Ordered dictionary that only accept keys that matches the predicate."""

    def __init__(self, predicate=not_empty, *args, **kwargs):
        """Constructor."""
        super(OrderedPredicateDict, self).__init__(*args, **kwargs)
        self.predicate = predicate

    def __setitem__(self, key, value, dict_setitem=dict.__setitem__):
        """Only accept key if it matches the predicate."""
        if key in self or self.predicate(value):
            super(OrderedPredicateDict, self).__setitem__(key, value, dict_setitem=dict_setitem)
