# coding=utf-8
"""Tests for single-file post-processing."""

import os
from unittest.mock import ANY, Mock

from medusa import app, failed_processor
from medusa.process_tv import ProcessResult

import pytest


@pytest.mark.parametrize('filename,expected', [
    ('RARBG.mp4', False), ('._episode.mkv', False), ('episode.mkv', True),
])
@pytest.mark.parametrize('extracted', [False, True])
def test_nested_media_preserves_filename_exclusions(create_file, monkeypatch, filename, expected, extracted):
    """A nested selection or archive member must retain basename exclusions."""
    selected = create_file('release/nested/' + filename)
    root = os.path.dirname(os.path.dirname(selected))
    relative = os.path.join('nested', filename)
    result = ProcessResult(root)
    if extracted:
        monkeypatch.setattr(result, 'unrar', Mock(return_value=[relative]))
        files = ['release.rar']
    else:
        files = [relative]

    result.prepare_files(root, files)

    assert (relative in result.video_files) is expected
    assert (relative in result.video_in_rar) is (expected and extracted)


@pytest.mark.parametrize('filename,expected', [
    ('RARBG.mp4', False), ('._episode.mkv', False),
    ('episode.mkv', True), ('episode.rar', True),
])
def test_direct_file_preserves_filename_exclusions(create_file, filename, expected):
    """An absolute file path must not bypass exclusions anchored at its name."""
    path = create_file('downloads/' + filename)

    assert ProcessResult(path).should_process(path) is expected


@pytest.mark.parametrize('removed', [False, True])
def test_direct_file_paths_do_not_walk(create_file, monkeypatch, removed):
    """Remember a direct-file selection even after its source has disappeared."""
    path = create_file('downloads/episode.mkv')
    result = ProcessResult(path)
    if removed:
        os.unlink(path)
    walk = Mock(return_value=iter(()))
    monkeypatch.setattr('medusa.process_tv.os.walk', walk)

    assert list(result.paths) == [result.input_path]
    walk.assert_not_called()


@pytest.mark.parametrize('marker,failed', [
    ('_UNPACK_release', False), ('_FAILED_release', True), ('@eaDir', False),
])
def test_direct_file_checks_release_ancestors(create_file, app_config, marker, failed):
    """A nested direct file still respects release state within the download root."""
    path = create_file('downloads/' + marker + '/Season 1/episode.mkv')
    root = os.path.dirname(os.path.dirname(os.path.dirname(path)))
    app_config('TV_DOWNLOAD_DIR', root)
    result = ProcessResult(path)

    assert result.should_process(result.input_path) is False
    assert result.failed is failed


@pytest.mark.parametrize('selection', ['explicit_directory', 'outside_root', 'above_root'])
def test_ancestor_validation_stays_bounded(create_file, create_dir, app_config, selection):
    """Only a direct file's enclosing configured download tree widens validation."""
    if selection == 'above_root':
        path = create_file('_UNPACK_outer/downloads/Season 1/episode.mkv')
        root = os.path.dirname(os.path.dirname(path))
    else:
        path = create_file('downloads/_UNPACK_release/Season 1/episode.mkv')
        root = os.path.dirname(os.path.dirname(os.path.dirname(path)))
    if selection == 'outside_root':
        root = create_dir('elsewhere')
    app_config('TV_DOWNLOAD_DIR', root)
    selected_directory = os.path.dirname(path)
    result = ProcessResult(selected_directory if selection == 'explicit_directory' else path)
    if selection == 'explicit_directory':
        result.resource_name = os.path.basename(path)

    assert result.should_process(result.input_path, path) is True
    assert result.failed is False


@pytest.mark.parametrize('video,extracted,expected', [
    (os.path.join('ShowB', 'episode.mkv'), False, os.path.join('ShowB', 'episode.mkv')),
    (os.path.join('ShowB', 'episode.mkv'), True, 'episode.mkv'),
    ('episode.mkv', False, 'episode.mkv'),
])
def test_history_keeps_selected_file_qualification(create_dir, monkeypatch, video, extracted, expected):
    """Only extracted archive members use basename-only history matching."""
    root = create_dir('downloads')
    result = ProcessResult(root)
    result.video_in_rar = [video] if extracted else []
    history = Mock(return_value=False)
    processor = Mock(_output=[], process=Mock(return_value=True))
    monkeypatch.setattr(result, 'already_postprocessed', history)
    monkeypatch.setattr('medusa.process_tv.post_processor.PostProcessor', Mock(return_value=processor))

    result.process_media(root, [video])

    history.assert_called_once_with(expected)
    processor.process.assert_called_once_with()


@pytest.mark.parametrize('selection', ['file', 'missing_file', 'mapped_file', 'mapped_missing_file', 'archive_member'])
def test_failed_file_uses_original_resolved_source(create_file, tmpdir, monkeypatch, app_config, selection):
    """Real failed handling must not list a file or delete its parent downloads."""
    archive = selection == 'archive_member'
    filename = 'show.s01e01.' + ('rar' if archive else 'mkv')
    path = create_file('downloads/' + filename)
    sibling = create_file('downloads/other.s01e01.mkv')
    root = os.path.dirname(path)
    app_config('TV_DOWNLOAD_DIR', root)
    app_config('USE_FAILED_DOWNLOADS', True)
    app_config('DELETE_FAILED', True)
    original_input = str(tmpdir.join('remote', filename)) if selection.startswith('mapped') else path
    result = ProcessResult(original_input)
    if 'missing' in selection:
        os.unlink(path)
    resource = os.path.join('nested', 'show.s01e01.mkv') if archive else None
    failure_path = root if archive else original_input
    episode = Mock()
    series = Mock(get_episode=Mock(return_value=episode))
    parsed = Mock(episode_numbers=[1], season_number=1, series=series)
    parser = Mock(parse=Mock(return_value=parsed))
    monkeypatch.setattr('medusa.failed_processor.NameParser', Mock(return_value=parser))
    monkeypatch.setattr('medusa.failed_processor.FailedQueueItem', Mock())
    monkeypatch.setattr(app, 'forced_search_queue_scheduler', Mock())
    factory = Mock(side_effect=failed_processor.FailedProcessor)
    monkeypatch.setattr('medusa.process_tv.failed_processor.FailedProcessor', factory)

    result.process_failed(failure_path, resource_name=resource)

    factory.assert_called_once_with(os.path.realpath(path), resource or filename, result.episodes)
    expected_release = (resource or filename).rpartition('.')[0]
    parser.parse.assert_called_once_with(expected_release, use_cache=False)
    app.forced_search_queue_scheduler.action.add_item.assert_called_once_with(ANY)
    assert os.path.isdir(root)
    assert os.path.isfile(sibling)


def test_failed_file_preserves_resource_and_episode_metadata(create_file, monkeypatch, app_config):
    """A supplied release and episode segment retain precedence over filename fallback."""
    path = create_file('downloads/episode.mkv')
    episodes = [Mock()]
    result = ProcessResult(path, episodes=episodes)
    result.resource_name = 'original.release.nzb'
    app_config('USE_FAILED_DOWNLOADS', True)
    app_config('DELETE_FAILED', False)
    processor = Mock(output='', process=Mock(return_value=True))
    factory = Mock(return_value=processor)
    monkeypatch.setattr('medusa.process_tv.failed_processor.FailedProcessor', factory)

    result.process_failed(path)

    factory.assert_called_once_with(os.path.realpath(path), 'original.release.nzb', episodes)
    processor.process.assert_called_once_with()
