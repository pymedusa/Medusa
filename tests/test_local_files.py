# coding=utf-8
"""Regression coverage for local-only incremental file reconciliation."""
from __future__ import unicode_literals

import os
import sqlite3
from datetime import date
from types import SimpleNamespace

from dogpile.cache.api import NO_VALUE

from medusa import app
from medusa.common import DOWNLOADED, Quality, SKIPPED, WANTED
from medusa.tv import local_files
from medusa.tv.episode import Episode
from medusa.tv.series import Series

from mock.mock import Mock

import pytest

import requests


@pytest.fixture
def library(tmp_path, monkeypatch):
    """Use real files and SQLite while trapping heavyweight refresh operations."""
    folder = tmp_path / 'Example'
    folder.mkdir()
    connection = sqlite3.connect(':memory:')
    connection.row_factory = sqlite3.Row
    connection.execute(
        'CREATE TABLE tv_episodes ('
        'indexer INTEGER, showid INTEGER, season INTEGER, episode INTEGER, '
        'location TEXT DEFAULT "", file_size INTEGER DEFAULT 0, '
        'status INTEGER, quality INTEGER, absolute_number INTEGER, airdate INTEGER DEFAULT 1, '
        'scene_season INTEGER, scene_episode INTEGER, scene_absolute_number INTEGER, '
        'subtitles TEXT DEFAULT "", subtitles_searchcount INTEGER DEFAULT 0, '
        'subtitles_lastsearch TEXT DEFAULT "", hasnfo INTEGER DEFAULT 0, hastbn INTEGER DEFAULT 0, '
        'release_name TEXT DEFAULT "", release_group TEXT DEFAULT "", '
        'is_proper INTEGER DEFAULT 0, version INTEGER DEFAULT 0, manually_searched INTEGER DEFAULT 0)'
    )
    connection.execute(
        'CREATE TABLE scene_numbering ('
        'indexer INTEGER, indexer_id INTEGER, season INTEGER, episode INTEGER, '
        'scene_season INTEGER, scene_episode INTEGER, scene_absolute_number INTEGER)'
    )
    database = Mock()
    database.select.side_effect = lambda query, args=None: [
        dict(row) for row in connection.execute(query, args or []).fetchall()
    ]

    def commit(queries, *args, **kwargs):
        results = []
        with connection:
            for query, parameters in queries:
                cursor = connection.execute(query, parameters)
                expected_rows = kwargs.get('expected_rowcount')
                if expected_rows is not None and cursor.rowcount != expected_rows:
                    raise local_files.db.StaleRecordError('A local episode changed during reconciliation')
                results.append(cursor.fetchall() if kwargs.get('fetchall') else cursor)
        return results

    database.mass_action.side_effect = commit
    monkeypatch.setattr(local_files.db, 'DBConnection', Mock(return_value=database))

    snapshots = {}
    snapshot_cache = Mock()
    snapshot_cache.get.side_effect = lambda key, **kwargs: snapshots.get(key, NO_VALUE)
    snapshot_cache.set.side_effect = lambda key, value: snapshots.__setitem__(key, value)
    snapshot_cache.delete.side_effect = lambda key: snapshots.pop(key, None)
    monkeypatch.setattr(local_files, 'cache', snapshot_cache)

    series = Mock()
    series.indexer = 1
    series.series_id = series.indexerid = 12
    series.name = 'Example'
    series.location = str(folder)
    series.is_anime = False
    series.is_scene = False
    series.air_by_date = False
    series.episodes = {}
    series.to_json.return_value = {'id': {'slug': 'tvdb12'}}

    parser = Mock(wraps=local_files.default_api.guessit)
    monkeypatch.setattr(local_files.default_api, 'guessit', parser)
    message = Mock()
    monkeypatch.setattr(local_files.ws, 'Message', message)
    monkeypatch.setattr(app, 'SKIP_REMOVED_FILES', False)
    monkeypatch.setattr(app, 'EP_DEFAULT_DELETED_STATUS', SKIPPED)

    forbidden = Mock(side_effect=AssertionError('Local reconciliation reached a full refresh or external request'))
    for method in ('refresh_dir', 'load_episodes_from_dir', 'make_ep_from_file',
                   'update_metadata', 'write_metadata', 'populate_cache'):
        monkeypatch.setattr(Series, method, forbidden)
    monkeypatch.setattr(Episode, '__init__', forbidden)
    monkeypatch.setattr(requests.sessions.Session, 'request', forbidden)

    yield SimpleNamespace(
        folder=folder, series=series, connection=connection, database=database,
        snapshots=snapshots, snapshot_cache=snapshot_cache, parser=parser, message=message,
    )
    connection.close()


def record_episode(library, episode, location='', size=0, status=DOWNLOADED, **fields):
    """Store one existing episode without invoking application persistence."""
    values = dict(indexer=1, showid=12, season=1, episode=episode, location=str(location),
                  file_size=size, status=status, quality=Quality.SDTV)
    values.update(fields)
    columns = ', '.join(values)
    placeholders = ', '.join('?' for _ in values)
    library.connection.execute('INSERT INTO tv_episodes ({0}) VALUES ({1})'.format(columns, placeholders), list(values.values()))
    library.connection.commit()


def saved_episode(library, number):
    """Read the committed episode state for assertions."""
    return dict(library.connection.execute(
        'SELECT * FROM tv_episodes WHERE indexer = 1 AND showid = 12 AND episode = ?', (number,),
    ).fetchone())


def media_file(library, name='Example.S01E01.mkv', content=b'media'):
    """Create a media file under the show directory."""
    path = library.folder / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def advance_folder_timestamp(directory):
    """Make a directory change observable without depending on clock resolution."""
    metadata = directory.stat()
    os.utime(directory, ns=(metadata.st_atime_ns, metadata.st_mtime_ns + 2000000000))


def test_inventory_collects_media_metadata_recursively(library):
    """Inventory changes in season directories without reading media contents."""
    first = media_file(library, 'Season 01/Example.S01E01.mkv')
    second = media_file(library, 'Season 02/Example.S02E01.mp4', b'other')
    media_file(library, 'Season 01/Example.S01E01.srt', b'subtitle')

    inventory, _, _ = local_files.scan_media_files(str(library.folder))

    assert set(inventory) == {os.path.normcase(os.path.abspath(first)), os.path.normcase(os.path.abspath(second))}
    assert inventory[os.path.normcase(os.path.abspath(first))] == (first.stat().st_size, first.stat().st_mtime_ns)


def test_unchanged_recorded_files_seed_snapshot_without_parsing_or_writes(library):
    """The first local check reuses existing paths and sizes rather than reparsing."""
    path = media_file(library)
    record_episode(library, 1, path, path.stat().st_size)

    assert local_files.reconcile_local_files(library.series) is True
    assert library.snapshots
    library.parser.assert_not_called()
    library.database.mass_action.assert_not_called()
    library.message.assert_not_called()

    assert local_files.reconcile_local_files(library.series) is True
    library.parser.assert_not_called()
    library.database.mass_action.assert_not_called()
    library.message.assert_not_called()


def test_unchanged_multi_episode_path_does_not_trigger_reconciliation(library):
    """Shared media paths are inventory entries rather than repeated episode work."""
    path = media_file(library, 'Example.S01E01E02.mkv')
    for episode in (1, 2):
        record_episode(library, episode, path, path.stat().st_size)

    assert local_files.reconcile_local_files(library.series) is True
    library.parser.assert_not_called()
    library.database.mass_action.assert_not_called()


def test_added_file_updates_only_its_existing_episode(library):
    """An added file is attached to an existing episode without loading a TVEpisode."""
    path = media_file(library, 'Example.S01E02.mkv')
    record_episode(library, 1, status=WANTED)
    record_episode(library, 2, status=WANTED)

    assert local_files.reconcile_local_files(library.series) is True

    assert saved_episode(library, 1)['location'] == ''
    updated = saved_episode(library, 2)
    assert os.path.normcase(updated['location']) == os.path.normcase(str(path))
    assert updated['file_size'] == path.stat().st_size
    assert updated['status'] == DOWNLOADED
    assert library.parser.call_count == 1
    assert library.database.mass_action.call_count == 1
    assert library.message.call_args[0][0] == 'showUpdated'


def test_renamed_file_retains_the_episode_assignment(library):
    """Reconcile the replacement before clearing the old missing file association."""
    old_path = library.folder / 'Example.S01E01.old.mkv'
    replacement = media_file(library, 'Example.S01E01.new.mkv')
    record_episode(library, 1, old_path, replacement.stat().st_size)

    assert local_files.reconcile_local_files(library.series) is True
    assert os.path.normcase(saved_episode(library, 1)['location']) == os.path.normcase(str(replacement))


def test_modified_shared_file_updates_all_of_its_episode_sizes(library):
    """One changed file must keep all episode rows sharing that file consistent."""
    path = media_file(library, 'Example.S01E01E02.mkv')
    for episode in (1, 2):
        record_episode(library, episode, path, path.stat().st_size)
    assert local_files.reconcile_local_files(library.series) is True

    path.write_bytes(b'larger replacement media')
    advance_folder_timestamp(path.parent)
    assert local_files.reconcile_local_files(library.series) is True

    assert saved_episode(library, 1)['file_size'] == path.stat().st_size
    assert saved_episode(library, 2)['file_size'] == path.stat().st_size


def test_changed_folder_refreshes_same_size_file_fingerprint(library):
    """Enumerating a changed folder refreshes the fingerprints of its direct files."""
    path = media_file(library)
    record_episode(library, 1, path, path.stat().st_size)
    assert local_files.reconcile_local_files(library.series) is True
    old_stat = path.stat()

    path.write_bytes(b'other')
    os.utime(path, ns=(old_stat.st_atime_ns, old_stat.st_mtime_ns + 2000000000))
    advance_folder_timestamp(path.parent)
    assert local_files.reconcile_local_files(library.series) is True

    snapshot = next(iter(library.snapshots.values()))
    normalized = os.path.normcase(os.path.abspath(path))
    assert snapshot['files'][normalized] == (path.stat().st_size, path.stat().st_mtime_ns)


@pytest.mark.parametrize('skip_removed', [False, True])
def test_missing_file_respects_removal_policy_without_deleting_sidecars(library, monkeypatch, skip_removed):
    """Only confirmed missing associations change; subtitle and metadata files remain."""
    survivor = media_file(library, 'Example.S01E02.mkv')
    missing = library.folder / 'Example.S01E01.mkv'
    sidecar = media_file(library, 'Example.S01E01.srt', b'keep subtitle')
    record_episode(library, 1, missing, 5)
    record_episode(library, 2, survivor, survivor.stat().st_size)
    monkeypatch.setattr(app, 'SKIP_REMOVED_FILES', skip_removed)

    assert local_files.reconcile_local_files(library.series) is True

    row = saved_episode(library, 1)
    if skip_removed:
        assert row['location'] == str(missing)
        assert row['file_size'] == 5
        assert row['status'] == DOWNLOADED
    else:
        assert row['location'] == ''
        assert row['file_size'] == 0
        assert row['status'] == SKIPPED
    assert sidecar.read_bytes() == b'keep subtitle'
    library.parser.assert_not_called()


def test_unresolved_file_does_not_create_episode_or_call_external_services(library):
    """Unknown numbering stays unresolved rather than causing an indexer lookup."""
    media_file(library, 'Example.S99E99.mkv')
    record_episode(library, 1, status=WANTED)

    assert local_files.reconcile_local_files(library.series) is True
    assert saved_episode(library, 1)['location'] == ''
    assert library.connection.execute('SELECT COUNT(*) FROM tv_episodes').fetchone()[0] == 1
    library.database.mass_action.assert_not_called()


def test_unreadable_subdirectory_preserves_all_episode_records(library, monkeypatch):
    """An incomplete inventory is unknown and must never become a deletion list."""
    path = media_file(library, 'Season 01/Example.S01E01.mkv')
    record_episode(library, 1, path, path.stat().st_size)
    before = saved_episode(library, 1)
    real_scandir = os.scandir

    def scandir(directory):
        if os.path.normcase(str(directory)) == os.path.normcase(str(path.parent)):
            raise PermissionError('unreadable season')
        return real_scandir(directory)

    monkeypatch.setattr(local_files.os, 'scandir', scandir)

    assert local_files.reconcile_local_files(library.series) is False
    assert saved_episode(library, 1) == before
    library.database.mass_action.assert_not_called()
    library.snapshot_cache.set.assert_not_called()
    library.message.assert_not_called()


def test_missing_show_directory_preserves_episode_records(library):
    """Unavailable storage does not erase the last successful inventory."""
    missing = library.folder / 'Example.S01E01.mkv'
    record_episode(library, 1, missing, 5)
    library.folder.rmdir()

    assert local_files.reconcile_local_files(library.series) is False
    assert saved_episode(library, 1)['location'] == str(missing)
    library.database.mass_action.assert_not_called()
    library.snapshot_cache.set.assert_not_called()


def test_empty_mountpoint_does_not_erase_every_recorded_file(library):
    """An empty accessible mountpoint is not evidence that all media was deleted."""
    missing = library.folder / 'Example.S01E01.mkv'
    record_episode(library, 1, missing, 5)

    assert local_files.reconcile_local_files(library.series) is False
    assert saved_episode(library, 1)['location'] == str(missing)
    library.database.mass_action.assert_not_called()


@pytest.mark.parametrize('failure', ['exception', 'not_committed'])
def test_failed_commit_preserves_snapshot_and_sends_no_update(library, failure):
    """Do not hide unfinished reconciliation behind an advanced filesystem snapshot."""
    path = media_file(library)
    record_episode(library, 1, path, path.stat().st_size)
    assert local_files.reconcile_local_files(library.series) is True
    previous = dict(next(iter(library.snapshots.values()))['files'])
    library.snapshot_cache.set.reset_mock()
    library.message.reset_mock()
    path.write_bytes(b'larger replacement media')
    advance_folder_timestamp(path.parent)

    if failure == 'exception':
        library.database.mass_action.side_effect = sqlite3.OperationalError('write failed')
        with pytest.raises(sqlite3.OperationalError):
            local_files.reconcile_local_files(library.series)
    else:
        library.database.mass_action.side_effect = lambda queries, **kwargs: []
        assert local_files.reconcile_local_files(library.series) is False

    assert next(iter(library.snapshots.values()))['files'] == previous
    library.snapshot_cache.set.assert_not_called()
    library.message.assert_not_called()


def test_anime_absolute_numbers_match_only_saved_episode_records(library):
    """Anime files can attach locally without retrieving scene or indexer data."""
    library.series.is_anime = True
    path = media_file(library, '[Group] Example - 012 [720p].mkv')
    record_episode(library, 1, status=WANTED, absolute_number=12)

    assert local_files.reconcile_local_files(library.series) is True
    assert os.path.normcase(saved_episode(library, 1)['location']) == os.path.normcase(str(path))


def test_scene_numbers_use_saved_custom_mapping(library):
    """An existing local scene mapping works without forcing XEM refresh."""
    library.series.is_scene = True
    path = media_file(library, 'Example.S02E07.mkv')
    record_episode(library, 1, status=WANTED)
    library.connection.execute('INSERT INTO scene_numbering VALUES (1, 12, 1, 1, 2, 7, NULL)')
    library.connection.commit()

    assert local_files.reconcile_local_files(library.series) is True
    assert os.path.normcase(saved_episode(library, 1)['location']) == os.path.normcase(str(path))


def test_airdate_filename_matches_a_saved_episode_without_indexer_lookup(library):
    """Local airdate records provide sufficient information to attach a new file."""
    library.series.air_by_date = True
    path = media_file(library, 'Example.2024.01.23.mkv')
    record_episode(library, 1, status=WANTED, airdate=date(2024, 1, 23).toordinal())

    assert local_files.reconcile_local_files(library.series) is True
    assert os.path.normcase(saved_episode(library, 1)['location']) == os.path.normcase(str(path))


def test_multiple_candidate_files_do_not_choose_an_arbitrary_replacement(library):
    """Duplicate releases for one unassigned episode require manual resolution."""
    media_file(library, 'Example.S01E01.720p.mkv')
    media_file(library, 'Example.S01E01.1080p.mkv')
    record_episode(library, 1, status=WANTED)

    assert local_files.reconcile_local_files(library.series) is True
    assert saved_episode(library, 1)['location'] == ''
    library.database.mass_action.assert_not_called()


def test_stale_episode_record_does_not_advance_inventory_or_overwrite_new_location(library):
    """A postprocessor can change an episode between reading and writing the scan."""
    path = media_file(library)
    record_episode(library, 1, path, path.stat().st_size)
    assert local_files.reconcile_local_files(library.series) is True
    previous = dict(next(iter(library.snapshots.values()))['files'])
    library.snapshot_cache.set.reset_mock()
    library.message.reset_mock()
    path.write_bytes(b'larger replacement media')
    advance_folder_timestamp(path.parent)
    original_commit = library.database.mass_action.side_effect
    replacement = str(library.folder / 'postprocessed.mkv')

    def concurrent_write(queries, **kwargs):
        library.connection.execute('UPDATE tv_episodes SET location = ? WHERE episode = 1', (replacement,))
        library.connection.commit()
        return original_commit(queries, **kwargs)

    library.database.mass_action.side_effect = concurrent_write

    assert local_files.reconcile_local_files(library.series) is False
    assert saved_episode(library, 1)['location'] == replacement
    assert next(iter(library.snapshots.values()))['files'] == previous
    library.snapshot_cache.set.assert_not_called()
    library.message.assert_not_called()


def test_overlapping_multi_episode_files_remain_wholly_unassigned(library):
    """An ambiguous episode must not leave part of a multi-episode file attached."""
    media_file(library, 'Example.S01E01E02.mkv')
    media_file(library, 'Example.S01E02.1080p.mkv')
    record_episode(library, 1, status=WANTED)
    record_episode(library, 2, status=WANTED)

    assert local_files.reconcile_local_files(library.series) is True
    assert saved_episode(library, 1)['location'] == ''
    assert saved_episode(library, 2)['location'] == ''
    library.database.mass_action.assert_not_called()


@pytest.mark.parametrize('old_format', [False, True])
@pytest.mark.parametrize('changed_directory', ['root', 'season'])
def test_changed_storage_identity_preserves_records(library, monkeypatch, changed_directory, old_format):
    """A changed show or season mount is not treated as ordinary file deletion."""
    path = media_file(library, 'Season 01/Example.S01E01.mkv')
    record_episode(library, 1, path, path.stat().st_size)
    assert local_files.reconcile_local_files(library.series) is True
    key = next(iter(library.snapshots))
    if old_format:
        snapshot = library.snapshots[key]
        library.snapshots[key] = {
            'identity': snapshot['identity'],
            'files': snapshot['files'],
            'directories': {directory: entry['fingerprint'][:2] for directory, entry in snapshot['directories'].items()},
        }
    previous = dict(library.snapshots[key])
    library.snapshot_cache.set.reset_mock()
    library.message.reset_mock()
    directory = library.folder if changed_directory == 'root' else path.parent
    directory_key = os.path.normcase(os.path.abspath(directory))
    real_stat = os.stat

    def stat(file_path, *args, **kwargs):
        metadata = real_stat(file_path, *args, **kwargs)
        if os.path.normcase(os.path.abspath(file_path)) == directory_key:
            return SimpleNamespace(st_dev=metadata.st_dev + 1, st_ino=metadata.st_ino,
                                   st_mtime_ns=metadata.st_mtime_ns, st_ctime_ns=metadata.st_ctime_ns)
        return metadata

    monkeypatch.setattr(local_files.os, 'stat', stat)

    assert local_files.reconcile_local_files(library.series) is False
    assert saved_episode(library, 1)['location'] == str(path)
    assert next(iter(library.snapshots.values())) == previous
    library.database.mass_action.assert_not_called()
    library.snapshot_cache.set.assert_not_called()
    library.message.assert_not_called()


def test_file_changed_during_inventory_defers_the_pass(library, monkeypatch):
    """An actively changing file is retried rather than committing an obsolete size."""
    path = media_file(library)
    record_episode(library, 1, path, path.stat().st_size)
    assert local_files.reconcile_local_files(library.series) is True
    previous = dict(next(iter(library.snapshots.values()))['files'])
    library.snapshot_cache.set.reset_mock()
    path.write_bytes(b'new media')
    advance_folder_timestamp(path.parent)
    scan = local_files.scan_media_files

    def changing_inventory(root, previous=None):
        inventory = scan(root, previous)
        path.write_bytes(b'longer media that is still being copied')
        return inventory

    monkeypatch.setattr(local_files, 'scan_media_files', changing_inventory)

    assert local_files.reconcile_local_files(library.series) is False
    assert saved_episode(library, 1)['file_size'] == 5
    assert next(iter(library.snapshots.values()))['files'] == previous
    library.database.mass_action.assert_not_called()
    library.snapshot_cache.set.assert_not_called()


def test_multi_episode_conflict_rolls_back_every_file_update(library):
    """A stale second episode cannot leave the first half of a shared file updated."""
    path = media_file(library, 'Example.S01E01E02.mkv')
    for episode in (1, 2):
        record_episode(library, episode, path, path.stat().st_size)
    assert local_files.reconcile_local_files(library.series) is True
    previous = dict(next(iter(library.snapshots.values()))['files'])
    library.snapshot_cache.set.reset_mock()
    library.message.reset_mock()
    path.write_bytes(b'larger replacement media')
    advance_folder_timestamp(path.parent)
    original_commit = library.database.mass_action.side_effect
    replacement = str(library.folder / 'postprocessed.mkv')

    def concurrent_write(queries, **kwargs):
        library.connection.execute('UPDATE tv_episodes SET location = ? WHERE episode = 2', (replacement,))
        library.connection.commit()
        return original_commit(queries, **kwargs)

    library.database.mass_action.side_effect = concurrent_write

    assert local_files.reconcile_local_files(library.series) is False
    assert saved_episode(library, 1)['location'] == str(path)
    assert saved_episode(library, 1)['file_size'] == 5
    assert saved_episode(library, 2)['location'] == replacement
    assert saved_episode(library, 2)['file_size'] == 5
    assert next(iter(library.snapshots.values()))['files'] == previous
    library.snapshot_cache.set.assert_not_called()
    library.message.assert_not_called()


def test_dirty_cached_episode_defers_file_reconciliation(library):
    """A pending in-memory episode edit must survive until its owner saves it."""
    path = media_file(library)
    record_episode(library, 1, path, path.stat().st_size)
    assert local_files.reconcile_local_files(library.series) is True
    previous = dict(next(iter(library.snapshots.values()))['files'])
    library.snapshot_cache.set.reset_mock()
    pending_episode = Mock(dirty=True)
    library.series.episodes = {1: {1: pending_episode}}
    path.write_bytes(b'larger replacement media')
    advance_folder_timestamp(path.parent)

    assert local_files.reconcile_local_files(library.series) is False
    assert saved_episode(library, 1)['file_size'] == 5
    assert library.series.episodes[1][1] is pending_episode
    assert next(iter(library.snapshots.values()))['files'] == previous
    library.database.mass_action.assert_not_called()
    library.snapshot_cache.set.assert_not_called()
    library.message.assert_not_called()


def test_explicit_refresh_invalidates_only_its_show_inventory(library):
    """A completed manual refresh can establish a fresh local-check baseline."""
    path = media_file(library)
    record_episode(library, 1, path, path.stat().st_size)
    assert local_files.reconcile_local_files(library.series) is True
    key = next(iter(library.snapshots))
    library.snapshots['another-show'] = {'files': {}}

    local_files.invalidate_local_file_inventory(library.series)

    assert key not in library.snapshots
    assert library.snapshots['another-show'] == {'files': {}}
    library.snapshot_cache.delete.assert_called_once_with(key)
    assert local_files.reconcile_local_files(library.series) is True
    assert key in library.snapshots
    library.database.mass_action.assert_not_called()
    library.parser.assert_not_called()


def test_warm_unchanged_folders_do_not_enumerate_or_stat_files(library, monkeypatch):
    """A warm check reads folder metadata only, including empty nested folders."""
    paths = [media_file(library, 'Season 01/Example.S01E01.mkv'),
             media_file(library, 'Season 02/Example.S02E01.mkv')]
    (library.folder / 'Season 03' / 'Empty').mkdir(parents=True)
    for episode, path in enumerate(paths, 1):
        record_episode(library, episode, path, path.stat().st_size)
    assert local_files.reconcile_local_files(library.series) is True
    library.database.reset_mock()
    library.snapshot_cache.set.reset_mock()
    library.message.reset_mock()
    files = {local_files.normalized_path(path) for path in paths}
    real_stat = os.stat

    def stat(path, *args, **kwargs):
        assert local_files.normalized_path(path) not in files, 'Unchanged media was statted'
        return real_stat(path, *args, **kwargs)

    forbidden_scandir = Mock(side_effect=AssertionError('Unchanged folder was enumerated'))
    monkeypatch.setattr(local_files.os, 'stat', stat)
    monkeypatch.setattr(local_files.os, 'scandir', forbidden_scandir)

    assert local_files.reconcile_local_files(library.series) is True
    library.database.select.assert_not_called()
    library.database.mass_action.assert_not_called()
    library.parser.assert_not_called()
    library.snapshot_cache.set.assert_not_called()
    library.message.assert_not_called()


def test_changed_season_leaves_unchanged_sibling_files_unchecked(library, monkeypatch):
    """One season's additions must not enumerate another season or the show root."""
    first = media_file(library, 'Season 01/Example.S01E01.mkv')
    second = media_file(library, 'Season 02/Example.S02E01.mkv')
    record_episode(library, 1, first, first.stat().st_size)
    record_episode(library, 2, second, second.stat().st_size, season=2)
    record_episode(library, 3, status=WANTED)
    assert local_files.reconcile_local_files(library.series) is True
    addition = media_file(library, 'Season 01/Example.S01E03.mkv')
    advance_folder_timestamp(addition.parent)
    real_scandir = os.scandir
    enumerated = []

    def scandir(directory):
        normalized = local_files.normalized_path(directory)
        assert normalized == local_files.normalized_path(first.parent)
        enumerated.append(normalized)
        return real_scandir(directory)

    monkeypatch.setattr(local_files.os, 'scandir', scandir)

    assert local_files.reconcile_local_files(library.series) is True
    assert enumerated == [local_files.normalized_path(first.parent)]
    assert os.path.normcase(saved_episode(library, 3)['location']) == os.path.normcase(str(addition))
    assert library.parser.call_count == 1


def test_new_file_in_cached_empty_nested_folder_is_found(library):
    """A nested folder's timestamp is checked even when all its ancestors are unchanged."""
    empty = library.folder / 'Season 01' / 'Nested'
    empty.mkdir(parents=True)
    record_episode(library, 1, status=WANTED)
    assert local_files.reconcile_local_files(library.series) is True
    ancestor_fingerprints = {
        path: local_files._directory_fingerprint(str(path))
        for path in (library.folder, empty.parent)
    }
    addition = media_file(library, 'Season 01/Nested/Example.S01E01.mkv')
    advance_folder_timestamp(empty)

    assert local_files.reconcile_local_files(library.series) is True
    assert os.path.normcase(saved_episode(library, 1)['location']) == os.path.normcase(str(addition))
    for ancestor, fingerprint in ancestor_fingerprints.items():
        assert local_files._directory_fingerprint(str(ancestor)) == fingerprint


@pytest.mark.parametrize('operation', ['delete', 'rename'])
def test_file_removal_or_rename_after_baseline_updates_local_records(library, operation):
    """Cached inventories still discover changes to directory entries."""
    path = media_file(library, 'Season 01/Example.S01E01.old.mkv')
    survivor = media_file(library, 'Season 01/Example.S01E02.mkv')
    record_episode(library, 1, path, path.stat().st_size)
    record_episode(library, 2, survivor, survivor.stat().st_size)
    assert local_files.reconcile_local_files(library.series) is True

    if operation == 'delete':
        path.unlink()
        expected_location = ''
    else:
        destination = path.with_name('Example.S01E01.new.mkv')
        path.rename(destination)
        expected_location = str(destination)
    advance_folder_timestamp(path.parent)

    assert local_files.reconcile_local_files(library.series) is True
    assert os.path.normcase(saved_episode(library, 1)['location']) == os.path.normcase(expected_location)
    assert saved_episode(library, 2)['location'] == str(survivor)


def test_old_snapshot_format_is_rebuilt_once_without_episode_writes(library, monkeypatch):
    """Upgrade the persisted inventory without interpreting old identity tuples as folder entries."""
    path = media_file(library, 'Season 01/Example.S01E01.mkv')
    record_episode(library, 1, path, path.stat().st_size)
    assert local_files.reconcile_local_files(library.series) is True
    key = next(iter(library.snapshots))
    old_snapshot = library.snapshots[key]
    library.snapshots[key] = {
        'identity': old_snapshot['identity'],
        'files': old_snapshot['files'],
        'directories': {directory: entry['fingerprint'][:2] for directory, entry in old_snapshot['directories'].items()},
    }
    enumerator = Mock(wraps=os.scandir)
    monkeypatch.setattr(local_files.os, 'scandir', enumerator)

    assert local_files.reconcile_local_files(library.series) is True
    assert enumerator.call_count == 2
    assert library.snapshots[key]['version'] == 2
    library.database.mass_action.assert_not_called()
    library.parser.assert_not_called()

    enumerator.reset_mock()
    assert local_files.reconcile_local_files(library.series) is True
    enumerator.assert_not_called()


def test_in_place_file_change_waits_for_explicit_inventory_invalidation(library):
    """Folder gating deliberately does not detect writes inside an unchanged directory."""
    path = media_file(library)
    record_episode(library, 1, path, path.stat().st_size)
    assert local_files.reconcile_local_files(library.series) is True
    key = next(iter(library.snapshots))
    previous = library.snapshots[key]
    folder_fingerprint = local_files._directory_fingerprint(str(path.parent))
    path.write_bytes(b'larger replacement media')
    assert local_files._directory_fingerprint(str(path.parent)) == folder_fingerprint
    library.database.reset_mock()
    library.snapshot_cache.set.reset_mock()

    assert local_files.reconcile_local_files(library.series) is True
    assert saved_episode(library, 1)['file_size'] == 5
    assert library.snapshots[key] is previous
    library.database.select.assert_not_called()
    library.database.mass_action.assert_not_called()
    library.snapshot_cache.set.assert_not_called()

    local_files.invalidate_local_file_inventory(library.series)
    assert local_files.reconcile_local_files(library.series) is True
    assert saved_episode(library, 1)['file_size'] == path.stat().st_size


def test_cached_file_size_does_not_overwrite_newer_postprocessing_record(library):
    """A changed sibling cannot cause stale cached file metadata to undo a saved import."""
    first = media_file(library, 'Season 01/Example.S01E01.mkv')
    second = media_file(library, 'Season 02/Example.S02E01.mkv')
    record_episode(library, 1, first, first.stat().st_size)
    record_episode(library, 2, second, second.stat().st_size, season=2)
    assert local_files.reconcile_local_files(library.series) is True
    first.write_bytes(b'new imported media')
    library.connection.execute('UPDATE tv_episodes SET file_size = ? WHERE episode = 1', (first.stat().st_size,))
    library.connection.commit()
    advance_folder_timestamp(second.parent)
    library.database.mass_action.reset_mock()

    assert local_files.reconcile_local_files(library.series) is True
    assert saved_episode(library, 1)['file_size'] == first.stat().st_size
    library.database.mass_action.assert_not_called()


def test_disappeared_recorded_season_preserves_previous_inventory(library):
    """A missing season folder is still treated as unavailable storage after caching."""
    first = media_file(library, 'Season 01/Example.S01E01.mkv')
    second = media_file(library, 'Season 02/Example.S02E01.mkv')
    record_episode(library, 1, first, first.stat().st_size)
    record_episode(library, 2, second, second.stat().st_size, season=2)
    assert local_files.reconcile_local_files(library.series) is True
    key = next(iter(library.snapshots))
    previous = library.snapshots[key]
    first.unlink()
    first.parent.rmdir()
    advance_folder_timestamp(library.folder)
    library.database.mass_action.reset_mock()
    library.snapshot_cache.set.reset_mock()

    assert local_files.reconcile_local_files(library.series) is False
    assert saved_episode(library, 1)['location'] == str(first)
    assert library.snapshots[key] is previous
    library.database.mass_action.assert_not_called()
    library.snapshot_cache.set.assert_not_called()


def test_directory_timestamp_race_does_not_accept_a_partial_baseline(library, monkeypatch):
    """A directory changing during enumeration must be retried even without episode writes."""
    path = media_file(library)
    record_episode(library, 1, path, path.stat().st_size)
    assert local_files.reconcile_local_files(library.series) is True
    key = next(iter(library.snapshots))
    previous = library.snapshots[key]
    advance_folder_timestamp(path.parent)
    library.snapshot_cache.set.reset_mock()
    library.database.mass_action.reset_mock()
    read_directory = local_files._read_media_directory

    def changing_directory(directory):
        result = read_directory(directory)
        advance_folder_timestamp(path.parent)
        return result

    monkeypatch.setattr(local_files, '_read_media_directory', changing_directory)

    assert local_files.reconcile_local_files(library.series) is False
    assert saved_episode(library, 1)['file_size'] == path.stat().st_size
    assert library.snapshots[key] is previous
    library.database.mass_action.assert_not_called()
    library.snapshot_cache.set.assert_not_called()
