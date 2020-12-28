from collections import OrderedDict
from threading import Lock
import logging

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
            return self.thread_unsafe_get(name)

    def thread_unsafe_get(self, name):
        """Return a cache item from the cache. This function doesn't lock and is therefore not thread safe. """
        if name in self.cache:
            log.debug('Using cache item for {name}', {'name': name})
            return self.cache[name]

    def remove(self, name):
        """Remove a cache item given name."""
        with self.lock:
            del self.cache[name]
            log.debug('Removed cache item for {name}', {'name': name})
