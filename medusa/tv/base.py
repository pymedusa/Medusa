"""TVShow and TVEpisode classes."""

import datetime
import shutil
import threading
import shutil_custom

from medusa import (
    app,
)
from medusa.indexers.indexer_config import INDEXER_TVDBV2

try:
    import xml.etree.cElementTree as ETree
except ImportError:
    import xml.etree.ElementTree as ETree

try:
    from send2trash import send2trash
except ImportError:
    app.TRASH_REMOVE_SHOW = 0


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
