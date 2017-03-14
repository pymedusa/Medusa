# coding=utf-8

"""TVShow and TVEpisode classes."""

import datetime
import shutil
import threading

import six

from medusa.indexers.indexer_config import INDEXER_TVDBV2, indexer_id_to_slug, indexer_name_to_id, indexer_id_to_name

import shutil_custom

shutil.copyfile = shutil_custom.copyfile_custom

MILLIS_YEAR_1900 = datetime.datetime(year=1900, month=1, day=1).toordinal()


class TV(object):
    """Base class for Series and Episode."""

    def __init__(self, indexer, indexerid, ignored_properties):
        """Constructor with ignore_properties.

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
        """The item's tvdb_id."""
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


class Indexer(object):

    def __init__(self, identifier):
        self.id = identifier

    @property
    def slug(self):
        return indexer_id_to_name(self.id)

    @classmethod
    def from_slug(cls, slug):
        identifier = indexer_name_to_id(slug)
        if identifier is not None:
            return Indexer(identifier)

    def __bool__(self):
        return self.id is not None

    __nonzero__ = __bool__

    def __repr__(self):
        return '<Indexer [{0}:{1}]>'.format(self.slug, self.id)

    def __str__(self):
        return str(self.slug)

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other):
        if isinstance(other, six.string_types):
            return str(self) == other
        if isinstance(other, int):
            return self.id == other
        if not isinstance(other, Indexer):
            return False
        return self.id == other.id

    def __ne__(self, other):
        return not self == other
