# coding=utf-8
"""Tests for history matching when post-processing a selected file."""
from __future__ import unicode_literals

import os
import sqlite3

from medusa.common import DOWNLOADED, SNATCHED
from medusa.process_tv import MediaFile, PostProcessQueueItem, ProcessResult

from mock.mock import Mock

import pytest


@pytest.fixture
def downloaded_history(monkeypatch):
    """Execute the real history queries against an isolated, in-memory database."""
    connection = sqlite3.connect(':memory:')
    connection.row_factory = sqlite3.Row
    connection.execute(
        'CREATE TABLE history ('
        'showid INTEGER, season INTEGER, episode INTEGER, indexer_id INTEGER, '
        'action INTEGER, resource TEXT, date INTEGER)'
    )
    connection.execute(
        'CREATE TABLE tv_episodes ('
        'indexer INTEGER, showid INTEGER, season INTEGER, episode INTEGER, '
        'status INTEGER, manually_searched INTEGER)'
    )
    database = Mock()
    database.select.side_effect = lambda query, params: connection.execute(query, params).fetchall()
    monkeypatch.setattr('medusa.process_tv.db.DBConnection', Mock(return_value=database))

    def add_download(resource, manually_searched=0):
        connection.execute('INSERT INTO history VALUES (?, ?, ?, ?, ?, ?, ?)',
                           [1, 1, 1, 1, DOWNLOADED, resource, 1])
        connection.execute('INSERT INTO tv_episodes VALUES (?, ?, ?, ?, ?, ?)',
                           [1, 1, 1, 1, SNATCHED, manually_searched])

    yield add_download
    connection.close()


@pytest.mark.parametrize('absolute_resource', [False, True])
@pytest.mark.parametrize('history_folder,force,expected_processed', [
    ('ShowA', False, True),
    ('ShowB', False, False),
    ('ShowB', True, True),
    (None, False, True),
])
def test_selected_nested_file_retains_history_path(
        create_file, create_dir, monkeypatch, app_config, downloaded_history,
        absolute_resource, history_folder, force, expected_processed):
    """An unrelated same-named episode must not suppress a qualified selection."""
    root = create_dir('downloads')
    selected_file = create_file(os.path.join('downloads', 'ShowB', 'episode.mkv'))
    resource_name = selected_file if absolute_resource else os.path.join('ShowB', 'episode.mkv')
    if history_folder:
        downloaded_history(os.path.join(root, history_folder, 'episode.mkv'))
    processor = Mock(_output=[], **{'process.return_value': True})
    processor_class = Mock(return_value=processor)
    monkeypatch.setattr('medusa.process_tv.post_processor.PostProcessor', processor_class)
    app_config('POSTPONE_IF_NO_SUBS', False)
    app_config('POSTPONE_IF_SYNC_FILES', False)
    item = PostProcessQueueItem(
        path=root, resource_name=resource_name, force=force,
        process_method='copy', process_single_resource=True
    )

    result = item.process_path()

    if expected_processed:
        processor_class.assert_called_once_with(os.path.realpath(selected_file), resource_name, 'copy', False)
        processor.process.assert_called_once_with()
    else:
        processor_class.assert_not_called()
        assert 'Skipping already processed file:' in result.output
    assert result.result is True
    assert os.path.isfile(selected_file)


@pytest.mark.parametrize('force', [False, True])
def test_selected_plain_filename_keeps_basename_history_matching(
        create_file, monkeypatch, app_config, downloaded_history, force):
    """Unqualified file selections retain existing history checks and force override."""
    selected_file = create_file(os.path.join('downloads', 'episode.mkv'))
    downloaded_history(os.path.join('library', 'ShowA', 'episode.mkv'))
    processor = Mock(_output=[], **{'process.return_value': True})
    processor_class = Mock(return_value=processor)
    monkeypatch.setattr('medusa.process_tv.post_processor.PostProcessor', processor_class)
    app_config('POSTPONE_IF_NO_SUBS', False)
    app_config('POSTPONE_IF_SYNC_FILES', False)
    item = PostProcessQueueItem(
        path=os.path.dirname(selected_file), resource_name='episode.mkv', force=force,
        process_method='copy', process_single_resource=True
    )

    result = item.process_path()

    if force:
        processor_class.assert_called_once_with(os.path.realpath(selected_file), 'episode.mkv', 'copy', False)
        processor.process.assert_called_once_with()
    else:
        processor_class.assert_not_called()
        assert 'Skipping already processed file:' in result.output
    assert result.result is True
    assert os.path.isfile(selected_file)


@pytest.mark.parametrize('resource_name', [None, 'Release.rar'])
def test_nested_archive_member_keeps_basename_history_matching(
        create_file, create_dir, monkeypatch, downloaded_history, resource_name):
    """Extracted member paths must still match basename-only download history."""
    root = create_dir('downloads')
    video = os.path.join('nested', 'episode.mkv')
    selected_file = create_file(os.path.join('downloads', video))
    downloaded_history('episode.mkv')
    processor_class = Mock()
    monkeypatch.setattr('medusa.process_tv.post_processor.PostProcessor', processor_class)
    result = ProcessResult(root, process_method='copy', process_single_resource=True)
    result.resource_name = resource_name

    result.process_media(root, [MediaFile(video, os.path.basename(video))])

    processor_class.assert_not_called()
    assert 'Skipping already processed file:' in result.output
    assert os.path.isfile(selected_file)


@pytest.mark.parametrize('video_file,history_resource', [
    ('A_B.S01E01.mkv', 'AXB.S01E01.mkv'),
    ('A%B.S01E01.mkv', 'Along.titleB.S01E01.mkv'),
    ('A%B.S01E01.mkv', 'AB.S01E01.mkv'),
    ('A!_B.S01E01.mkv', 'A!XB.S01E01.mkv'),
    ('A!%B.S01E01.mkv', 'A!long.titleB.S01E01.mkv'),
    (r'Show_Name\episode.mkv', r'ShowXName\episode.mkv'),
])
def test_history_filename_wildcards_do_not_match_other_downloads(
        create_dir, downloaded_history, video_file, history_resource):
    """SQL wildcard characters in filenames must be matched literally."""
    downloaded_history(history_resource)
    result = ProcessResult(create_dir('downloads'), process_method='copy')

    assert not result.already_postprocessed(video_file)


@pytest.mark.parametrize('video_file', [
    'A_B.S01E01.mkv',
    'A%B.S01E01.mkv',
    'A!B.S01E01.mkv',
    'A!_%B.S01E01.mkv',
    'A!!B.S01E01.mkv',
    r'Show_Name\episode!100%.mkv',
])
@pytest.mark.parametrize('history_prefix', ['', 'library/'])
def test_history_literal_filename_matches_with_optional_path_prefix(
        create_dir, downloaded_history, video_file, history_prefix):
    """Escaping the requested filename must retain suffix-based history checks."""
    downloaded_history(history_prefix + video_file)
    result = ProcessResult(create_dir('downloads'), process_method='copy')

    assert result.already_postprocessed(video_file) is True


@pytest.mark.parametrize('video_file', ['A_B.S01E01.mkv', 'A!100%.S01E01.mkv'])
def test_literal_history_match_allows_manually_searched_episode(
        create_dir, downloaded_history, video_file):
    """A manual re-search must still override an exact literal history match."""
    downloaded_history('library/' + video_file, manually_searched=1)
    result = ProcessResult(create_dir('downloads'), process_method='copy')

    assert not result.already_postprocessed(video_file)


@pytest.mark.parametrize('video_file,history_resource', [
    ('House.S01E01.mkv', 'Full.House.S01E01.mkv'),
    ('House.S01E01.mkv', 'library/Full.House.S01E01.mkv'),
    ('House.S01E01.mkv', r'library\Full.House.S01E01.mkv'),
    ('Show/episode.mkv', 'OtherShow/episode.mkv'),
    ('Show/episode.mkv', 'library/OtherShow/episode.mkv'),
    (r'Show\episode.mkv', r'library\OtherShow\episode.mkv'),
    ('A!_%B.S01E01.mkv', 'OtherA!_%B.S01E01.mkv'),
])
def test_history_match_requires_a_filename_or_directory_boundary(
        create_dir, downloaded_history, video_file, history_resource):
    """A matching suffix inside another filename or folder is not the same resource."""
    downloaded_history(history_resource)
    result = ProcessResult(create_dir('downloads'), process_method='copy')

    assert not result.already_postprocessed(video_file)


@pytest.mark.parametrize('history_prefix', ['', 'library/', 'library\\'])
@pytest.mark.parametrize('video_file', [
    'House.S01E01.mkv',
    'Show/episode.mkv',
    r'Show\episode.mkv',
    'A!_%B.S01E01.mkv',
])
def test_history_boundary_match_accepts_exact_or_path_qualified_names(
        create_dir, downloaded_history, history_prefix, video_file):
    """Both path separators may introduce a complete literal requested suffix."""
    downloaded_history(history_prefix + video_file)
    result = ProcessResult(create_dir('downloads'), process_method='copy')

    assert result.already_postprocessed(video_file) is True


@pytest.mark.parametrize('history_prefix', ['', 'library/', 'library\\'])
def test_history_boundary_match_preserves_manual_research_override(
        create_dir, downloaded_history, history_prefix):
    """A boundary match must still allow an explicitly re-snatched literal filename."""
    video_file = 'A!_%B.S01E01.mkv'
    downloaded_history(history_prefix + video_file, manually_searched=1)
    result = ProcessResult(create_dir('downloads'), process_method='copy')

    assert not result.already_postprocessed(video_file)
