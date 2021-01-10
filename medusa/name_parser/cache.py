# coding=utf-8

"""A thread-safe cache with a max size."""

import logging
from collections import OrderedDict
from threading import Lock

from medusa.logger.adapters.style import BraceAdapter

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class BaseCache(object):
    """Base cache."""

    def __init__(self, max_size=1000):
        """Initialize the cache with a maximum size."""
        self.cache = OrderedDict()
        self.max_size = max_size
        self.lock = Lock()

    def add(self, name, value):
        """Add a cache item to the cache.

        :param name:
        :type name: str
        :param value:
        :type value: object
        """
        with self.lock:
            while len(self.cache) >= self.max_size:
                self.cache.popitem(last=False)
            self.cache[name] = value

    def get(self, name):
        """Return a cache item from the cache.

        :param name:
        :type name: str
        :return:
        :rtype: object
        """
        with self.lock:
            if name in self.cache:
                log.debug('Using cache item for {name}', {'name': name})
                return self.cache[name]

    def remove(self, name):
        """Remove a cache item given name."""
        with self.lock:
            del self.cache[name]
            log.debug('Removed cache item for {name}', {'name': name})

    def clear(self):
        """Removes all items from the cache."""
        with self.lock:
            self.cache.clear()
