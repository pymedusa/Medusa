# coding=utf-8
"""Cache (dogpile) used by application."""
from __future__ import unicode_literals

import dbm
import importlib
import logging
import os
from datetime import timedelta

from diskcache import Cache as DiskCache

from dogpile.cache import register_backend
from dogpile.cache.api import CacheBackend, NO_VALUE
from dogpile.cache.backends.file import AbstractFileLock
from dogpile.cache.region import make_region
from dogpile.util.readwrite_lock import ReadWriteMutex


log = logging.getLogger(__name__)


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
recommended_series_cache = make_region()
# Some of the show titles that are used as keys, contain unicode encoded characters. We need to encode them to
# bytestrings to be able to use them as keys in dogpile.
anidb_cache = make_region()


class DiskCacheBackend(CacheBackend):
    """Persist Dogpile values in SQLite when an existing DBM format cannot be loaded.

    Dogpile owns expiration, including ignore_expiration for file inventories.
    Disable eviction and culling to retain the existing DBM retention behavior.
    Reads do not update usage statistics or last-access timestamps.
    """

    def __init__(self, arguments):
        self.store = DiskCache(arguments['directory'], eviction_policy='none', cull_limit=0)

    def get(self, key):
        """Return a cached value or Dogpile's missing-value sentinel."""
        return self.store.get(key, default=NO_VALUE)

    def get_multi(self, keys):
        """Preserve key order and missing values in a batch read."""
        return [self.get(key) for key in keys]

    def set(self, key, value):
        """Store the value and its Dogpile expiration metadata."""
        self.store.set(key, value)

    def set_multi(self, mapping):
        """Commit a batch of values in one transaction."""
        with self.store.transact():
            for key, value in mapping.items():
                self.store.set(key, value)

    def delete(self, key):
        """Discard a value if present."""
        self.store.delete(key)

    def delete_multi(self, keys):
        """Discard a batch of values in one transaction."""
        with self.store.transact():
            for key in keys:
                self.store.delete(key)


register_backend('medusa.cache.diskcache', 'medusa.cache', 'DiskCacheBackend')


def _configure_persistent_cache(region, filename, expiration_time, replace=False):
    """Keep readable DBM caches, preserving incompatible files beside a durable fallback.

    Once the fallback exists, it remains authoritative across restarts even if
    the original DBM module becomes available again. Switching back could revive
    entries deleted from the fallback. Other storage errors must remain visible.
    """
    sqlite_directory = filename + '.sqlite'
    use_sqlite = os.path.isdir(sqlite_directory)
    unavailable_backend = None

    if not use_sqlite:
        backend = dbm.whichdb(filename)
        if backend:
            try:
                importlib.import_module(backend)
            except ImportError:
                use_sqlite = True
                unavailable_backend = backend

    if use_sqlite:
        region.configure('medusa.cache.diskcache', expiration_time=expiration_time,
                         replace_existing_backend=replace, arguments={'directory': sqlite_directory})

        if unavailable_backend is not None:
            log.info('Cache %s uses unavailable backend %s; preserving it and using persistent cache %s.',
                     filename, unavailable_backend, sqlite_directory)
        return

    region.configure('dogpile.cache.dbm', expiration_time=expiration_time,
                     replace_existing_backend=replace,
                     arguments={'filename': filename, 'lock_factory': MutexLock})


def clear_fallback_cache(filename):
    """Clear a recovered cache while retaining the directory that selects its backend."""
    sqlite_directory = filename + '.sqlite'
    if os.path.isdir(sqlite_directory):
        with DiskCache(sqlite_directory) as store:
            removed = store.clear()
        log.info('Cleared persistent fallback cache %s (%s entries).', sqlite_directory, removed)


def configure(cache_dir, replace=False):
    """Configure persistent caches with recovery for unavailable DBM modules."""
    from subliminal.cache import region as subliminal_cache

    memory_cache.configure('dogpile.cache.memory', expiration_time=timedelta(hours=1),
                           replace_existing_backend=replace)

    caches = (
        (subliminal_cache, 'subliminal.dbm', timedelta(days=30)),
        (cache, 'application.dbm', timedelta(days=1)),
        (recommended_series_cache, 'recommended.dbm', timedelta(days=7)),
        (anidb_cache, 'anidb.dbm', timedelta(days=3)),
    )
    for region, name, expiration_time in caches:
        _configure_persistent_cache(region, os.path.join(cache_dir, name), expiration_time, replace)


def fallback():
    """Memory only configuration. Used for test purposes."""
    from subliminal.cache import region as subliminal_cache
    for region in (cache, memory_cache, subliminal_cache):
        region.configure('dogpile.cache.memory')
