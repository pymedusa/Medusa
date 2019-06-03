# coding=utf-8
"""Cache (dogpile) used by application."""
from __future__ import unicode_literals

import os
import msgpack
from datetime import timedelta, date
from dateutil.parser import parse


from six import binary_type
from dogpile.cache.backends.file import AbstractFileLock
from dogpile.cache.proxy import ProxyBackend
from dogpile.cache.api import NO_VALUE, CachedValue
from dogpile.cache.region import make_region
from dogpile.util.readwrite_lock import ReadWriteMutex

from knowit.properties import Language, Quantity
from pint.quantity import _Quantity
import babelfish


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
episode_metadata = make_region()


class _EncodedProxy(ProxyBackend):
    """base class for building value-mangling proxies"""

    def value_decode(self, value):
        raise NotImplementedError("override me")

    def value_encode(self, value):
        raise NotImplementedError("override me")

    def set(self, k, v):
        v = self.value_encode(v)
        self.proxied.set(k, v)

    def get(self, key):
        v = self.proxied.get(key)
        return self.value_decode(v)

    def set_multi(self, mapping):
        """encode to a new dict to preserve unencoded values in-place when
           called by `get_or_create_multi`
           """
        mapping_set = {}
        for (k, v) in mapping.iteritems():
            mapping_set[k] = self.value_encode(v)
        return self.proxied.set_multi(mapping_set)

    def get_multi(self, keys):
        results = self.proxied.get_multi(keys)
        translated = []
        for record in results:
            try:
                translated.append(self.value_decode(record))
            except Exception as e:
                raise
        return translated


class KludgedExtType(msgpack.ExtType):
    """
    This is an ExtType that doesn't care for rules.
    """
    def __new__(cls, code, data):
        return super(msgpack.ExtType, cls).__new__(cls, code, data)


def knowit_encode(obj):
    """MsgPack object hook for encoding datetimes."""
    if isinstance(obj, date):
        obj = {
            b'__datetime__': True,
            b'value': obj.isoformat()
        }
    if isinstance(obj, timedelta):
        obj = {
            b'__timedelta__': True,
            b'value': obj.total_seconds()
        }
    if isinstance(obj, _Quantity):
        obj = {
            b'__quantity__': True,
            b'units': binary_type(obj.units),
            b'magnitude': obj.magnitude,
        }
    if isinstance(obj, babelfish.Language):
        obj = {
            b'__language__': True,
            b'alpha3': obj.alpha3,
            b'country': obj.country,
            b'script': obj.script
        }
    return obj


def knowit_decode(obj):
    """MsgPack object hook for decoding knowit Properties."""

    new_obj = obj
    if isinstance(obj, dict):
        if b'__datetime__' in obj:
            new_obj = parse(obj['value'])
        if b'__timedelta__' in obj:
            new_obj = timedelta(seconds=obj['value'])
        if b'__quantity__' in obj:
            pass
            new_obj = Quantity(obj['units'], obj['magnitude'])
        if b'__language__' in obj:
            pass
            new_obj = Language('language', description='video language')
    return new_obj


class MsgpackProxy(_EncodedProxy):
    """custom decode/encode for value mangling"""

    def value_decode(self, payload):
        if not payload or payload is NO_VALUE:
            return NO_VALUE
        # you probably want to specify a custom decoder via `object_hook`
        v = msgpack.unpackb(payload, object_hook=knowit_decode, encoding="utf-8")
        return CachedValue(*v)

    def value_encode(self, payload):
        # you probably want to specify a custom encoder via `default`
        v = msgpack.packb(payload, default=knowit_encode, use_bin_type=True)
        return v


def configure(cache_dir, replace=False):
    """Configure caches."""
    # memory cache
    from subliminal.cache import region as subliminal_cache

    memory_cache.configure('dogpile.cache.memory', expiration_time=timedelta(hours=1))

    # subliminal cache
    subliminal_cache.configure('dogpile.cache.dbm', replace_existing_backend=replace,
                               expiration_time=timedelta(days=30),
                               arguments={
                                   'filename': os.path.join(cache_dir, 'subliminal.dbm'),
                                   'lock_factory': MutexLock})

    # application cache
    cache.configure('dogpile.cache.dbm', replace_existing_backend=replace,
                    expiration_time=timedelta(days=1),
                    arguments={'filename': os.path.join(cache_dir, 'application.dbm'),
                               'lock_factory': MutexLock})

    # recommended series cache
    recommended_series_cache.configure('dogpile.cache.dbm', replace_existing_backend=replace,
                                       expiration_time=timedelta(days=7),
                                       arguments={'filename': os.path.join(cache_dir, 'recommended.dbm'),
                                                  'lock_factory': MutexLock})

    # anidb (adba) series cache
    anidb_cache.configure('dogpile.cache.dbm', replace_existing_backend=replace,
                          expiration_time=timedelta(days=3),
                          arguments={'filename': os.path.join(cache_dir, 'anidb.dbm'),
                                     'lock_factory': MutexLock})

    # epsisode parsing (knowit / guessit) cache
    episode_metadata.configure(
        'dogpile.cache.dbm',
        expiration_time=timedelta(days=365),
        arguments={'filename': os.path.join(cache_dir, 'episodes.dbm'), 'lock_factory': MutexLock},
        wrap=[MsgpackProxy]
    )


def fallback():
    """Memory only configuration. Used for test purposes."""
    from subliminal.cache import region as subliminal_cache
    for region in (cache, memory_cache, subliminal_cache):
        region.configure('dogpile.cache.memory')
