# coding=utf-8
"""Tests for ext.ttl_cache."""
from __future__ import unicode_literals

import gc
import time
import weakref

from medusa.clients.torrent.qbittorrent import QBittorrentAPI

import pytest
import ttl_cache


class CacheValue(object):
    """Simple object that supports weak references in cache tests."""


def test_identical_calls_within_ttl_execute_once():
    calls = []

    @ttl_cache(60.0)
    def cached(value):
        calls.append(value)
        return value

    assert cached(1) == 1
    assert cached(1) == 1
    assert calls == [1]


def test_call_after_expiration_recalculates():
    calls = []

    @ttl_cache(0.05)
    def cached(value):
        calls.append(value)
        return value

    assert cached(1) == 1
    time.sleep(0.1)
    assert cached(1) == 1
    assert calls == [1, 1]


def test_expired_cached_values_are_evicted():
    @ttl_cache(0.05)
    def cached():
        return CacheValue()

    first_ref = weakref.ref(cached())
    time.sleep(0.1)
    cached()
    gc.collect()
    assert first_ref() is None


def test_instance_argument_can_be_garbage_collected_after_expiration():
    calls = [0]

    class CachedClient(object):
        @ttl_cache(0.05)
        def fetch(self):
            calls[0] += 1
            return CacheValue()

    client = CachedClient()
    client_ref = weakref.ref(client)
    client.fetch()
    del client
    gc.collect()
    assert client_ref() is not None

    time.sleep(0.1)
    CachedClient().fetch()
    gc.collect()
    assert client_ref() is None


def test_successive_instances_do_not_grow_cache_indefinitely():
    calls = []

    class CachedClient(object):
        @ttl_cache(0.05)
        def fetch(self):
            calls.append(id(self))
            return CacheValue()

    client_refs = []
    for _ in range(200):
        client = CachedClient()
        client_refs.append(weakref.ref(client))
        client.fetch()
        del client

    time.sleep(0.1)
    CachedClient().fetch()
    gc.collect()
    assert all(client_ref() is None for client_ref in client_refs)


def test_ignore_error_reuses_expired_value_after_repeated_failures():
    """An expired value remains available across repeated refresh failures."""
    attempts = [0]

    @ttl_cache(0.05, ignore_error=True)
    def cached():
        attempts[0] += 1
        if attempts[0] == 1:
            return 'fresh'
        raise RuntimeError('refresh failed')

    assert cached() == 'fresh'
    time.sleep(0.1)
    assert cached() == 'fresh'
    assert attempts[0] == 2
    assert cached() == 'fresh'
    assert attempts[0] == 3


def test_expired_entry_not_retained_without_ignore_error():
    attempts = [0]

    @ttl_cache(0.05, ignore_error=False)
    def cached():
        attempts[0] += 1
        if attempts[0] == 1:
            return CacheValue()
        raise RuntimeError('refresh failed')

    value_ref = weakref.ref(cached())
    time.sleep(0.1)
    with pytest.raises(RuntimeError):
        cached()
    assert attempts[0] == 2
    with pytest.raises(RuntimeError):
        cached()
    assert attempts[0] == 3
    gc.collect()
    assert value_ref() is None


def test_typed_true_keeps_distinct_types():
    calls = []

    @ttl_cache(60.0, typed=True)
    def cached(value):
        calls.append(type(value))
        return value

    assert cached(1) == 1
    assert cached(1.0) == 1.0
    assert calls == [int, float]


def test_qbittorrent_get_torrents_cache_isolated_by_arguments():
    calls = []

    class FakeResponse(object):
        def __init__(self, payload):
            self.payload = payload

        def json(self):
            return self.payload

    class TestQBittorrentAPI(QBittorrentAPI):
        def __init__(self):
            self.name = 'qBittorrent'
            self.host = 'http://localhost'
            self.username = None
            self.password = None
            self.url = self.host
            self.session = type('Session', (), {'cookies': None})()
            self.api = (2, 14, 0)
            self.auth = True
            self.response = None

        def _request(self, method='get', params=None, data=None, files=None, cookies=None):
            calls.append(dict(params or {}))
            self.response = FakeResponse([{'hash': 'abc'}])
            return True

    client = TestQBittorrentAPI()

    assert client._get_torrents() == [{'hash': 'abc'}]
    assert client._get_torrents(filter='downloading') == [{'hash': 'abc'}]
    assert client._get_torrents(category='tv') == [{'hash': 'abc'}]
    assert client._get_torrents(sort='added_on') == [{'hash': 'abc'}]
    assert calls == [
        {},
        {'filter': 'downloading'},
        {'category': 'tv'},
        {'sort': 'added_on'},
    ]

    assert client._get_torrents() == [{'hash': 'abc'}]
    assert len(calls) == 4


def test_qbittorrent_temporary_instances_release_memory():
    client_refs = []
    response_refs = []

    class FakeResponse(object):
        def __init__(self, payload):
            self.payload = payload

        def json(self):
            return self.payload

    class TestQBittorrentAPI(QBittorrentAPI):
        def __init__(self, host):
            self.name = 'qBittorrent'
            self.host = host
            self.username = None
            self.password = None
            self.url = self.host
            self.session = type('Session', (), {'cookies': None})()
            self.api = (2, 14, 0)
            self.auth = True
            self.response = None

        def _request(self, method='get', params=None, data=None, files=None, cookies=None):
            sentinel = CacheValue()
            payload = [{'hash': 'x' * 64, 'name': 'large-response', 'sentinel': sentinel} for _ in range(500)]
            self.response = FakeResponse(payload)
            self._response_sentinel = sentinel
            return True

    TestQBittorrentAPI._get_torrents = ttl_cache(0.05)(TestQBittorrentAPI._get_torrents.__wrapped__)

    for index in range(300):
        client = TestQBittorrentAPI(host='http://localhost-{0}'.format(index))
        client_refs.append(weakref.ref(client))
        response = client._get_torrents()
        response_refs.append(weakref.ref(response[0]['sentinel']))
        del client
        del response

    time.sleep(0.1)
    trigger = TestQBittorrentAPI(host='http://localhost-trigger')
    trigger._get_torrents()
    del trigger
    gc.collect()

    assert all(client_ref() is None for client_ref in client_refs)
    assert all(response_ref() is None for response_ref in response_refs)
