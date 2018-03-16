# coding=utf-8
"""TV base class."""
from __future__ import unicode_literals

import threading
from builtins import object

from medusa.indexers.config import INDEXER_TVDBV2


class Identifier(object):
    """Base identifier class."""

    def __bool__(self):
        """Magic method."""
        raise NotImplementedError

    def __ne__(self, other):
        """Magic method."""
        return not self == other


class TV(object):
    """Base class for Series and Episode."""

    def __init__(self, indexer, indexerid, ignored_properties):
        """Initialize class.

        :param indexer:
        :type indexer: int
        :param indexerid:
        :type indexerid: int
        :param ignored_properties:
        :type ignored_properties: set(str)
        """
        self.__dirty = True
        self.__ignored_properties = ignored_properties | {'lock'}
        self.indexer = int(indexer)
        self.indexerid = int(indexerid)
        self.lock = threading.Lock()

    @property
    def series_id(self):
        """To make a clear distinction between an indexer and the id for the series. You can now also use series_id."""
        return self.indexerid

    def __setattr__(self, key, value):
        """Set the corresponding attribute and use the dirty flag if the new value is different from the old value.

        :param key:
        :type key: str
        :param value:
        """
        if key == '_location' or (not key.startswith('_') and key not in self.__ignored_properties):
            self.__dirty |= self.__dict__.get(key) != value

        super(TV, self).__setattr__(key, value)

    @property
    def dirty(self):
        """Return the dirty flag.

        :return:
        :rtype: bool
        """
        return self.__dirty

    def reset_dirty(self):
        """Reset the dirty flag."""
        self.__dirty = False

    @property
    def tvdb_id(self):
        """Get the item's tvdb_id."""
        if self.indexerid and self.indexer == INDEXER_TVDBV2:
            return self.indexerid

    def __getstate__(self):
        """Make object serializable."""
        d = dict(self.__dict__)
        del d['lock']
        return d

    def __setstate__(self, d):
        """Un-serialize the object."""
        d['lock'] = threading.Lock()
        self.__dict__.update(d)
