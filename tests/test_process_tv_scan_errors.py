# coding=utf-8
"""Regression tests for independent scan targets and retryable directory errors."""
from __future__ import unicode_literals

import errno
import os

from medusa.process_tv import PostProcessQueueItem, ProcessResult
from medusa.schedulers.download_handler import ClientStatusEnum

from mock.mock import Mock

import pytest


@pytest.fixture
def scan_processor(monkeypatch, app_config):
    """Exercise real selection and cleanup decisions without external side effects."""
    processor_class = Mock(return_value=Mock(_output=[], **{'process.return_value': True}))
    failure_handler = Mock()
    history_update = Mock()
    deletions = [Mock(), Mock(), Mock()]
    monkeypatch.setattr('medusa.process_tv.post_processor.PostProcessor', processor_class)
    monkeypatch.setattr(ProcessResult, 'already_postprocessed', Mock(return_value=False))
    monkeypatch.setattr(ProcessResult, 'process_failed', failure_handler)
    monkeypatch.setattr(PostProcessQueueItem, 'update_resource', history_update)
    monkeypatch.setattr('medusa.process_tv.os.remove', deletions[0])
    monkeypatch.setattr('medusa.process_tv.os.rmdir', deletions[1])
    monkeypatch.setattr('medusa.process_tv.shutil.rmtree', deletions[2])
    app_config('POSTPONE_IF_SYNC_FILES', False)
    app_config('POSTPONE_IF_NO_SUBS', False)
    app_config('KODI_LIBRARY_CLEAN_PENDING', False)
    app_config('USE_TORRENTS', False)
    app_config('USE_FAILED_DOWNLOADS', True)
    app_config('DELETE_FAILED', True)
    app_config('NO_DELETE', False)
    return processor_class, failure_handler, history_update, deletions


@pytest.mark.parametrize('marker', ['_FAILED_release', '_UNDERSIZED_release'])
@pytest.mark.parametrize('root_episode', [False, True])
@pytest.mark.parametrize('nested_marker', [False, True])
def test_broad_scan_keeps_failed_downloads_separate(
        create_file, create_dir, scan_processor, marker, root_episode, nested_marker):
    """One bad download must not reject healthy siblings or fail the scan root."""
    root = os.path.realpath(create_dir('downloads'))
    healthy = create_file('downloads/Good.Show/Season 1/show.name.s01e01.mkv')
    bad_folder = os.path.join('downloads', 'Bad.Show', marker) if nested_marker else os.path.join('downloads', marker)
    rejected = create_file(os.path.join(bad_folder, 'bad.show.s01e01.mkv'))
    expected = [os.path.realpath(healthy)]
    if root_episode:
        expected.append(os.path.realpath(create_file('downloads/root.show.s01e01.mkv')))
    processor_class, failure_handler, history_update, deletions = scan_processor
    item = PostProcessQueueItem(
        path=root, process_method='copy', info_hash='scan-id', process_single_resource=True
    )

    result = item.process_path()

    assert sorted(call[0][0] for call in processor_class.call_args_list) == sorted(expected)
    assert result.failed is False
    assert result.succeeded is True
    assert any(os.path.dirname(rejected) in missed for missed in result.missed_files)
    failure_handler.assert_not_called()
    history_update.assert_called_once()
    assert history_update.call_args[0][0].status == (
        ClientStatusEnum.COMPLETED.value | ClientStatusEnum.POSTPROCESSED.value
    )
    assert os.path.isfile(rejected)
    for deletion in deletions:
        deletion.assert_not_called()


@pytest.mark.parametrize('marker', ['_FAILED_release', '_UNDERSIZED_release'])
@pytest.mark.parametrize('selection', ['direct', 'resource'])
def test_explicit_failed_directory_still_reports_failure(
        create_file, create_dir, scan_processor, marker, selection):
    """Isolating broad scans must not ignore a failed explicitly selected download."""
    root = os.path.realpath(create_dir('downloads'))
    selected = os.path.realpath(create_dir(os.path.join('downloads', marker)))
    create_file(os.path.join('downloads', marker, 'show.name.s01e01.mkv'))
    processor_class, failure_handler, history_update, deletions = scan_processor
    path = selected if selection == 'direct' else root
    item = PostProcessQueueItem(
        path=path, resource_name=None if selection == 'direct' else marker,
        process_method='copy', info_hash='download-id', process_single_resource=True
    )

    result = item.process_path()

    processor_class.assert_not_called()
    assert result.failed is True
    failure_handler.assert_called_once_with(path)
    history_update.assert_called_once()
    assert history_update.call_args[0][0].status == (
        ClientStatusEnum.FAILED.value | ClientStatusEnum.POSTPROCESSED.value
    )
    for deletion in deletions:
        deletion.assert_not_called()


@pytest.mark.parametrize('resource_name', [None, 'release', 'release.nzb'])
def test_explicit_download_failure_is_not_reset_by_scanning(
        create_file, create_dir, scan_processor, resource_name):
    """The client-supplied failed flag remains authoritative for the whole request."""
    root = os.path.realpath(create_dir('downloads/release'))
    create_file('downloads/release/show.name.s01e01.mkv')
    create_file('downloads/release/Season 1/show.name.s01e02.mkv')
    processor_class, failure_handler, history_update, deletions = scan_processor
    item = PostProcessQueueItem(
        path=root, resource_name=resource_name, failed=True,
        process_method='copy', info_hash='download-id', process_single_resource=True
    )

    result = item.process_path()

    processor_class.assert_not_called()
    assert result.failed is True
    failure_handler.assert_called_once_with(root)
    history_update.assert_called_once()
    assert history_update.call_args[0][0].status == (
        ClientStatusEnum.FAILED.value | ClientStatusEnum.POSTPROCESSED.value
    )
    for deletion in deletions:
        deletion.assert_not_called()


def _deny_scan(monkeypatch, blocked, should_deny):
    """Keep real directory walking and inject a platform-independent access failure."""
    original_scandir = os.scandir
    blocked = os.path.normcase(os.path.abspath(blocked))
    failures = []

    def scandir(path):
        if os.path.normcase(os.path.abspath(path)) == blocked and should_deny():
            failures.append(path)
            raise PermissionError(errno.EACCES, 'Directory access denied by test', path)
        return original_scandir(path)

    monkeypatch.setattr('medusa.process_tv.os.scandir', scandir)
    return failures


def _assert_retryable_scan_error(result, blocked, failures, scan_processor):
    """Require an incomplete listing to remain retryable without failure handling."""
    _, failure_handler, history_update, deletions = scan_processor
    assert failures
    assert result.postpone_any is True
    assert result.failed is False
    assert blocked in result.output
    assert 'Directory access denied by test' in result.output
    assert any(blocked in missed for missed in result.missed_files)
    failure_handler.assert_not_called()
    history_update.assert_not_called()
    for deletion in deletions:
        deletion.assert_not_called()


@pytest.mark.parametrize('resource_name', ['release', 'release.nzb'])
@pytest.mark.parametrize('phase', ['validation', 'processing'])
@pytest.mark.parametrize('root_episode', [False, True])
def test_named_release_retries_unreadable_subdirectory(
        create_file, create_dir, monkeypatch, scan_processor, resource_name, phase, root_episode):
    """Failures during either walk must prevent completion and normal cleanup."""
    root = os.path.realpath(create_dir('downloads/release'))
    blocked = os.path.realpath(create_dir('downloads/release/Season 1'))
    hidden_episode = create_file('downloads/release/Season 1/show.name.s01e02.mkv')
    metadata = create_file('downloads/release/readme.txt')
    if root_episode:
        create_file('downloads/release/show.name.s01e01.mkv')
    processor_class, _, _, _ = scan_processor
    original_get_files = ProcessResult._get_files
    walking_files = []

    def get_files(process_result, target):
        walking_files.append(True)
        try:
            yield from original_get_files(process_result, target)
        finally:
            walking_files.pop()

    monkeypatch.setattr(ProcessResult, '_get_files', get_files)
    failures = _deny_scan(monkeypatch, blocked, lambda: phase == 'validation' or bool(walking_files))
    item = PostProcessQueueItem(
        path=root, resource_name=resource_name, process_method='move',
        info_hash='download-id', process_single_resource=True
    )

    result = item.process_path()

    _assert_retryable_scan_error(result, blocked, failures, scan_processor)
    if phase == 'validation':
        processor_class.assert_not_called()
    assert all(call[0][0] != hidden_episode for call in processor_class.call_args_list)
    assert os.path.isfile(hidden_episode)
    assert os.path.isfile(metadata)


@pytest.mark.parametrize('root_episode', [False, True])
def test_broad_scan_retries_unreadable_child(
        create_file, create_dir, monkeypatch, scan_processor, root_episode):
    """Unrelated readable media may process without completing the incomplete scan."""
    root = os.path.realpath(create_dir('downloads'))
    blocked = os.path.realpath(create_dir('downloads/Unreadable.Show'))
    inaccessible = create_file('downloads/Unreadable.Show/show.name.s01e01.mkv')
    healthy = create_file('downloads/Good.Show/show.name.s01e01.mkv')
    expected = [os.path.realpath(healthy)]
    if root_episode:
        expected.append(os.path.realpath(create_file('downloads/root.show.s01e01.mkv')))
    processor_class, _, _, _ = scan_processor
    failures = _deny_scan(monkeypatch, blocked, lambda: True)
    item = PostProcessQueueItem(
        path=root, process_method='copy', info_hash='scan-id', process_single_resource=True
    )

    result = item.process_path()

    _assert_retryable_scan_error(result, blocked, failures, scan_processor)
    assert sorted(call[0][0] for call in processor_class.call_args_list) == sorted(expected)
    assert os.path.isfile(inaccessible)


def test_broad_scan_discovery_error_after_root_processing_is_retryable(
        create_file, create_dir, monkeypatch, scan_processor):
    """A later failure listing root children must retain the pending history status."""
    root = os.path.realpath(create_dir('downloads'))
    episode = create_file('downloads/root.show.s01e01.mkv')
    inaccessible = create_file('downloads/Child.Show/show.name.s01e01.mkv')
    processor_class, _, _, _ = scan_processor
    failures = _deny_scan(monkeypatch, root, lambda: processor_class.return_value.process.called)
    item = PostProcessQueueItem(
        path=root, process_method='copy', info_hash='scan-id', process_single_resource=True
    )

    result = item.process_path()

    _assert_retryable_scan_error(result, root, failures, scan_processor)
    processor_class.assert_called_once_with(os.path.realpath(episode), None, 'copy', False)
    assert os.path.isfile(inaccessible)


@pytest.mark.parametrize('resource_name', [None, 'release', 'release.nzb'])
@pytest.mark.parametrize('ignored_folder', ['@eaDir', '.hidden'])
@pytest.mark.parametrize('nested_error', [False, True])
def test_unreadable_ignored_subtree_does_not_postpone_healthy_media(
        create_file, create_dir, monkeypatch, scan_processor, resource_name, ignored_folder, nested_error):
    """Access failures in excluded folders must not abort otherwise complete walks."""
    root = os.path.realpath(create_dir('downloads/release'))
    episodes = [
        create_file('downloads/release/show.name.s01e01.mkv'),
        create_file('downloads/release/Season 1/show.name.s01e02.mkv'),
    ]
    ignored = os.path.join('downloads', 'release', 'Season 1', ignored_folder)
    ignored_episode = create_file(os.path.join(ignored, 'deeper', 'show.name.s01e99.mkv'))
    blocked = os.path.realpath(create_dir(os.path.join(ignored, 'deeper') if nested_error else ignored))
    failures = _deny_scan(monkeypatch, blocked, lambda: True)
    processor_class, failure_handler, history_update, deletions = scan_processor
    item = PostProcessQueueItem(
        path=root, resource_name=resource_name, process_method='copy',
        info_hash='download-id', process_single_resource=True
    )

    result = item.process_path()

    assert failures
    assert sorted(call[0][0] for call in processor_class.call_args_list) == sorted(episodes)
    assert result.result is True
    assert result.failed is False
    assert result.postpone_any is False
    failure_handler.assert_not_called()
    history_update.assert_called_once()
    assert history_update.call_args[0][0].status == (
        ClientStatusEnum.COMPLETED.value | ClientStatusEnum.POSTPROCESSED.value
    )
    assert os.path.isfile(ignored_episode)
    for deletion in deletions:
        deletion.assert_not_called()
