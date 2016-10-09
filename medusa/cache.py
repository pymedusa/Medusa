# coding=utf-8
"""Cache (dogpile) used by application."""

import os
from datetime import timedelta

from dogpile.cache.backends.file import AbstractFileLock
from dogpile.cache.region import make_region
from dogpile.util.readwrite_lock import ReadWriteMutex


class MutexLock(AbstractFileLock):
    """:class:`MutexLock` is a thread-based rw lock based on :class:`dogpile.core.ReadWriteMutex`."""

    def __init__(self, filename):
        """Constructor.

        :param filename:
        """
        self.mutex = ReadWriteMutex()

    def acquire_read_lock(self, wait):
        """Default acquire_read_lock."""
        ret = self.mutex.acquire_read_lock(wait)
        return wait or ret

    def acquire_write_lock(self, wait):
        """Default acquire_write_lock."""
        ret = self.mutex.acquire_write_lock(wait)
        return wait or ret

    def release_read_lock(self):
        """Default release_read_lock."""
        return self.mutex.release_read_lock()

    def release_write_lock(self):
        """Default release_write_lock."""
        return self.mutex.release_write_lock()

cache = make_region()
memory_cache = make_region()


def configure(cache_dir):
    """Configure caches."""
    # memory cache
    from subliminal.cache import region as subliminal_cache

    memory_cache.configure('dogpile.cache.memory', expiration_time=timedelta(hours=1))

    # subliminal cache
    subliminal_cache.configure('dogpile.cache.dbm',
                               expiration_time=timedelta(days=30),
                               arguments={
                                   'filename': os.path.join(cache_dir, 'subliminal.dbm'),
                                   'lock_factory': MutexLock})

    # application cache
    cache.configure('dogpile.cache.dbm',
                    expiration_time=timedelta(days=1),
                    arguments={'filename': os.path.join(cache_dir, 'application.dbm'),
                               'lock_factory': MutexLock})


def fallback():
    """Memory only configuration. USed for test purposes."""
    from subliminal.cache import region as subliminal_cache

    for region in (cache, memory_cache, subliminal_cache):
        region.configure('dogpile.cache.memory')
