# coding=utf-8
"""Exercise persistent cache recovery when a saved DBM backend is unavailable."""
from __future__ import unicode_literals

import dbm
import struct
from datetime import timedelta
from types import SimpleNamespace

from dogpile.cache import region as cache_region
from dogpile.cache.api import NO_VALUE
from dogpile.cache.backends.file import DBMBackend
from dogpile.cache.region import make_region

from medusa import cache

from mock.mock import Mock

import pytest


@pytest.fixture
def unavailable_gnu_cache(tmp_path, monkeypatch):
    """Use the real DBM recognizer with a GNU header and a missing extension."""
    filename = tmp_path / 'application.dbm'
    contents = struct.pack('=l', 0x13579acf) + b'original cache contents'
    filename.write_bytes(contents)
    assert dbm.whichdb(str(filename)) == 'dbm.gnu'
    import_module = cache.importlib.import_module

    def import_without_gnu(name, *args, **kwargs):
        if name == 'dbm.gnu':
            raise ModuleNotFoundError("No module named '_gdbm'")
        return import_module(name, *args, **kwargs)

    monkeypatch.setattr(cache.importlib, 'import_module', import_without_gnu)
    return filename


@pytest.fixture
def configure_region():
    """Keep real cache files confined to each test and release SQLite handles."""
    regions = []

    def configure(filename, expiration_time=timedelta(days=1)):
        region = make_region()
        cache._configure_persistent_cache(region, str(filename), expiration_time)
        regions.append(region)
        return region

    yield configure

    for region in regions:
        if isinstance(region.backend, cache.DiskCacheBackend):
            region.backend.store.close()


def test_missing_gnu_backend_preserves_file_and_recovers_persistently(
        unavailable_gnu_cache, configure_region, monkeypatch, logger, read_loglines):
    """The failing production cache can be replaced without erasing its contents."""
    filename = unavailable_gnu_cache
    original = filename.read_bytes()
    inventory = {'version': 2, 'files': {'episode.mkv': (42, 123456789)}, 'directories': {}}
    monkeypatch.setattr(cache, 'log', logger)

    region = configure_region(filename)

    assert isinstance(region.backend, cache.DiskCacheBackend)
    assert region.get('inventory', ignore_expiration=True) is NO_VALUE
    region.set('inventory', inventory)
    assert region.get('inventory', ignore_expiration=True) == inventory
    assert filename.read_bytes() == original
    region.backend.store.close()

    restarted = configure_region(filename)

    assert restarted.get('inventory', ignore_expiration=True) == inventory
    assert isinstance(restarted.get('inventory')['files']['episode.mkv'], tuple)
    assert filename.read_bytes() == original

    loglines = list(read_loglines)
    assert len(loglines) == 1
    assert loglines[0].level_name == 'INFO'
    assert loglines[0].traceback_lines == []
    assert 'dbm.gnu' in loglines[0].message
    assert str(filename) in loglines[0].message
    assert str(filename) + '.sqlite' in loglines[0].message


def test_failed_fallback_does_not_log_success(unavailable_gnu_cache, configure_region, monkeypatch, logger, read_loglines):
    """A failed SQLite initialization must raise without claiming recovery."""
    monkeypatch.setattr(cache, 'log', logger)
    monkeypatch.setattr(cache, 'DiskCache', Mock(side_effect=PermissionError('fallback directory is read-only')))

    with pytest.raises(PermissionError, match='fallback directory is read-only'):
        configure_region(unavailable_gnu_cache)

    assert list(read_loglines) == []


def test_fallback_stays_authoritative_after_restart(unavailable_gnu_cache, configure_region, monkeypatch):
    """Restoring GNU support must not revive a deleted snapshot from the old file."""
    region = configure_region(unavailable_gnu_cache)
    region.set('deleted-inventory', {'old': True})
    region.set('current-inventory', {'current': True})
    region.delete('deleted-inventory')
    region.backend.store.close()
    forbidden_probe = Mock(side_effect=AssertionError('An established fallback must not reopen the old DBM'))
    monkeypatch.setattr(cache.dbm, 'whichdb', forbidden_probe)

    restarted = configure_region(unavailable_gnu_cache)

    assert restarted.get('deleted-inventory', ignore_expiration=True) is NO_VALUE
    assert restarted.get('current-inventory', ignore_expiration=True) == {'current': True}
    forbidden_probe.assert_not_called()


def test_fallback_preserves_multi_value_and_missing_key_semantics(unavailable_gnu_cache, configure_region):
    """Other shared-cache consumers can batch values and invalidate them normally."""
    region = configure_region(unavailable_gnu_cache)
    region.set_multi({'first': {'name': "Widow's Bay"}, 'second': ('episode', 2)})

    assert region.get_multi(['second', 'missing', 'first']) == [('episode', 2), NO_VALUE, {'name': "Widow's Bay"}]

    region.delete_multi(['first', 'missing'])
    assert region.get('first') is NO_VALUE
    assert region.get('second') == ('episode', 2)
    region.delete('second')
    region.delete('second')
    assert region.get('second') is NO_VALUE


def test_fallback_keeps_expired_inventory_available_when_requested(unavailable_gnu_cache, configure_region, monkeypatch):
    """Dogpile expiration must not physically remove restartable file inventories."""
    region = configure_region(unavailable_gnu_cache, expiration_time=1)
    region.set('inventory', {'file': (42, 123)})
    future = cache_region.time.time() + 60
    monkeypatch.setattr(cache_region, 'time', SimpleNamespace(time=lambda: future))

    assert region.get('inventory') is NO_VALUE
    assert region.get('inventory', ignore_expiration=True) == {'file': (42, 123)}


def test_readable_dbm_keeps_existing_backend_and_values(tmp_path, configure_region):
    """Normal installations continue using their existing persistent DBM cache."""
    filename = tmp_path / 'application.dbm'
    region = configure_region(filename)
    region.set('existing', {'value': 42})

    restarted = configure_region(filename)

    assert isinstance(restarted.backend, DBMBackend)
    assert restarted.get('existing') == {'value': 42}
    assert not (tmp_path / 'application.dbm.sqlite').exists()


def test_dbm_permission_error_is_not_hidden_by_fallback(tmp_path, configure_region, monkeypatch):
    """Permissions need an actionable failure rather than silently abandoning a cache."""
    filename = tmp_path / 'application.dbm'
    monkeypatch.setattr(cache.dbm, 'open', Mock(side_effect=PermissionError('cache permission denied')))

    with pytest.raises(PermissionError, match='cache permission denied'):
        configure_region(filename)

    assert not (tmp_path / 'application.dbm.sqlite').exists()


def test_unknown_dbm_format_remains_an_explicit_error(tmp_path, configure_region):
    """Unrecognized data must not be mistaken for a missing optional Python module."""
    filename = tmp_path / 'application.dbm'
    original = b'not a recognized cache format'
    filename.write_bytes(original)

    region = configure_region(filename)
    with pytest.raises(dbm.error):
        region.get('inventory')

    assert filename.read_bytes() == original
    assert not (tmp_path / 'application.dbm.sqlite').exists()


def test_all_persistent_regions_recover_and_can_be_reconfigured(unavailable_gnu_cache, monkeypatch):
    """Public startup configures application, subtitles, recommendations, and anime caches."""
    from subliminal import cache as subtitle_cache

    directory = unavailable_gnu_cache.parent
    contents = unavailable_gnu_cache.read_bytes()
    regions = []
    for attribute, filename in (
        ('cache', 'application.dbm'),
        ('recommended_series_cache', 'recommended.dbm'),
        ('anidb_cache', 'anidb.dbm'),
    ):
        (directory / filename).write_bytes(contents)
        region = make_region()
        monkeypatch.setattr(cache, attribute, region)
        regions.append(region)

    (directory / 'subliminal.dbm').write_bytes(contents)
    subtitles = make_region()
    monkeypatch.setattr(subtitle_cache, 'region', subtitles)
    regions.append(subtitles)
    monkeypatch.setattr(cache, 'memory_cache', make_region())
    opened_stores = []

    try:
        cache.configure(str(directory))
        for region in regions:
            assert isinstance(region.backend, cache.DiskCacheBackend)
            opened_stores.append(region.backend.store)
            region.set('retained', {'value': 42})
        cache.memory_cache.set('transient', 'memory only')

        cache.configure(str(directory), replace=True)

        for region in regions:
            opened_stores.append(region.backend.store)
            assert region.get('retained') == {'value': 42}
        assert cache.memory_cache.get('transient') is NO_VALUE
        assert cache.cache.expiration_time == 86400
        assert subtitles.expiration_time == 30 * 86400
        assert cache.recommended_series_cache.expiration_time == 7 * 86400
        assert cache.anidb_cache.expiration_time == 3 * 86400
    finally:
        for store in opened_stores:
            store.close()


def test_explicit_cache_clear_remains_effective_after_recovery(unavailable_gnu_cache, configure_region):
    """The cache-clear setting must not leave fallback values behind or revive old DBM entries."""
    filename = unavailable_gnu_cache
    original = filename.read_bytes()
    region = configure_region(filename)
    region.set('inventory', {'files': ('episode.mkv',)})
    region.backend.store.close()

    cache.clear_fallback_cache(str(filename))
    restarted = configure_region(filename)

    assert restarted.get('inventory', ignore_expiration=True) is NO_VALUE
    assert isinstance(restarted.backend, cache.DiskCacheBackend)
    assert filename.read_bytes() == original


def test_clearing_absent_fallback_does_not_create_one(tmp_path):
    """Ordinary cache clearing should not switch a healthy installation to SQLite."""
    cache.clear_fallback_cache(str(tmp_path / 'application.dbm'))

    assert list(tmp_path.iterdir()) == []
