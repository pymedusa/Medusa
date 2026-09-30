# coding=utf-8
"""Tests for directory-scoped validation and complete release traversal."""
from __future__ import unicode_literals

import os

from medusa.process_tv import PostProcessQueueItem, ProcessResult
from medusa.schedulers.download_handler import ClientStatusEnum

from mock.mock import Mock

import pytest


@pytest.fixture
def directory_processor(monkeypatch, app_config):
    """Keep selection and traversal real without download or library side effects."""
    processor_class = Mock(return_value=Mock(_output=[], **{'process.return_value': True}))
    failure_handler = Mock()
    history_update = Mock()
    monkeypatch.setattr('medusa.process_tv.post_processor.PostProcessor', processor_class)
    monkeypatch.setattr(ProcessResult, 'already_postprocessed', Mock(return_value=False))
    monkeypatch.setattr(ProcessResult, 'process_failed', failure_handler)
    monkeypatch.setattr(ProcessResult, '_clean_up', Mock())
    monkeypatch.setattr(PostProcessQueueItem, 'update_resource', history_update)
    app_config('POSTPONE_IF_SYNC_FILES', False)
    app_config('POSTPONE_IF_NO_SUBS', False)
    app_config('KODI_LIBRARY_CLEAN_PENDING', False)
    app_config('USE_TORRENTS', False)
    return processor_class, failure_handler, history_update


@pytest.mark.parametrize('resource_name', ['release', 'release.nzb'])
@pytest.mark.parametrize('root_episode', [False, True])
@pytest.mark.parametrize('force,is_priority', [(False, False), (True, True)])
def test_named_release_processes_all_nested_episodes(
        create_file, create_dir, directory_processor, resource_name, root_episode, force, is_priority):
    """Root metadata or a root episode must not hide episodes in subdirectories."""
    root = os.path.realpath(create_dir('downloads/release'))
    create_file('downloads/release/release.nfo')
    episodes = [
        create_file('downloads/release/Season 1/show.name.s01e01.mkv'),
        create_file('downloads/release/Season 2/deeper/show.name.s02e01.mkv'),
    ]
    if root_episode:
        episodes.append(create_file('downloads/release/show.name.s01e02.mkv'))
    processor_class, failure_handler, history_update = directory_processor
    item = PostProcessQueueItem(
        path=root, resource_name=resource_name, info_hash='download-id', process_method='copy',
        process_single_resource=True, force=force, is_priority=is_priority
    )

    result = item.process_path()

    processed = [call[0][0] for call in processor_class.call_args_list]
    assert sorted(processed) == sorted(os.path.realpath(episode) for episode in episodes)
    assert all(call[0][1:] == (resource_name, 'copy', is_priority) for call in processor_class.call_args_list)
    assert result.result is True
    assert result.succeeded is True
    assert result.skipped is False
    failure_handler.assert_not_called()
    history_update.assert_called_once()
    assert history_update.call_args[0][0].status == (
        ClientStatusEnum.COMPLETED.value | ClientStatusEnum.POSTPROCESSED.value
    )


@pytest.mark.parametrize('resource_name', [None, 'release', 'release.nzb'])
def test_directory_traversal_excludes_samples_and_ignored_subtrees(
        create_file, create_dir, directory_processor, resource_name):
    """Recursive release processing must not promote samples or ignored media to episodes."""
    root = os.path.realpath(create_dir('downloads/release'))
    episodes = [
        create_file('downloads/release/show.name.s01e01.mkv'),
        create_file('downloads/release/Season 1/show.name.s01e02.mkv'),
    ]
    excluded = [
        create_file(os.path.join('downloads', 'release', folder, 'inner', 'show.name.s01e99.mkv'))
        for folder in ('sample', '@eaDir', '#recycle', '.@__thumb', '.hidden')
    ]
    processor_class, failure_handler, history_update = directory_processor
    item = PostProcessQueueItem(
        path=root, resource_name=resource_name, info_hash='download-id', process_method='copy',
        process_single_resource=True, force=True, is_priority=True
    )

    result = item.process_path()

    processed = [call[0][0] for call in processor_class.call_args_list]
    assert sorted(processed) == sorted(os.path.realpath(episode) for episode in episodes)
    assert all(os.path.isfile(path) for path in excluded)
    assert result.result is True
    assert result.succeeded is True
    failure_handler.assert_not_called()
    history_update.assert_called_once()


@pytest.mark.parametrize('sibling_name', ['_FAILED_other', '_UNPACK_other', '_unpack_other'])
@pytest.mark.parametrize('selection', ['relative', 'absolute'])
@pytest.mark.parametrize('nested', [False, True])
def test_selected_directory_ignores_unrelated_downloads(
        create_file, create_dir, directory_processor, sibling_name, selection, nested):
    """Validation and traversal stay inside the requested release rather than its siblings."""
    root = os.path.realpath(create_dir('downloads'))
    relative = os.path.join('group', 'Good.Show') if nested else 'Good.Show'
    selected = os.path.realpath(create_dir(os.path.join('downloads', relative)))
    episode = create_file(os.path.join('downloads', relative, 'Season 1', 'show.name.s01e01.mkv'))
    sibling = create_file(os.path.join('downloads', sibling_name, 'other.show.s01e01.mkv'))
    create_file('downloads/unrelated.mkv')
    resource_name = selected if selection == 'absolute' else relative
    processor_class, failure_handler, history_update = directory_processor
    item = PostProcessQueueItem(
        path=root, resource_name=resource_name, info_hash='download-id', process_method='copy',
        process_single_resource=True
    )

    result = item.process_path()

    processor_class.assert_called_once_with(os.path.realpath(episode), resource_name, 'copy', False)
    failure_handler.assert_not_called()
    assert result.result is True
    assert result.failed is False
    assert result.succeeded is True
    assert os.path.isfile(sibling)
    history_update.assert_called_once()


@pytest.mark.parametrize('folder_name,failed', [
    ('_FAILED_release', True), ('_UNDERSIZED_release', True),
    ('_UNPACK_release', False), ('_unpack_release', False),
    ('@eaDir', False), ('#recycle', False), ('.@__thumb', False), ('.hidden', False),
])
@pytest.mark.parametrize('selection', ['relative', 'absolute'])
@pytest.mark.parametrize('intermediate', [False, True])
def test_selected_directory_respects_its_own_and_ancestor_state(
        create_file, create_dir, directory_processor, folder_name, failed, selection, intermediate):
    """Selecting a nested directory must not bypass ignored, staging or failed ancestors."""
    root = os.path.realpath(create_dir('downloads'))
    relative = os.path.join(folder_name, 'Good.Show') if intermediate else folder_name
    selected = os.path.realpath(create_dir(os.path.join('downloads', relative)))
    episode = create_file(os.path.join('downloads', relative, 'show.name.s01e01.mkv'))
    # Valid unrelated media must not allow an excluded selection through validation.
    create_file('downloads/unrelated.mkv')
    resource_name = selected if selection == 'absolute' else relative
    processor_class, failure_handler, history_update = directory_processor
    item = PostProcessQueueItem(
        path=root, resource_name=resource_name, info_hash='download-id', process_method='copy',
        process_single_resource=True
    )

    result = item.process_path()

    processor_class.assert_not_called()
    assert result.result is False
    assert result.failed is failed
    assert os.path.isfile(episode)
    if failed:
        failure_handler.assert_called_once_with(root)
        history_update.assert_called_once()
        assert history_update.call_args[0][0].status == (
            ClientStatusEnum.FAILED.value | ClientStatusEnum.POSTPROCESSED.value
        )
    else:
        postponed = folder_name.startswith(('_UNPACK_', '_unpack'))
        assert result.postpone_any is postponed
        assert result.skipped is not postponed
        failure_handler.assert_not_called()
        history_update.assert_not_called()


@pytest.mark.parametrize('resource_name', ['release', 'release.nzb'])
@pytest.mark.parametrize('folder_name,failed', [
    ('_FAILED_release', True), ('_UNDERSIZED_release', True),
    ('_UNPACK_release', False), ('_unpack_release', False),
])
def test_named_release_validates_deep_markers_before_processing_root_media(
        create_file, create_dir, directory_processor, resource_name, folder_name, failed):
    """A root episode must not bypass validation of the rest of a selected release."""
    root = os.path.realpath(create_dir('downloads/release'))
    create_file('downloads/release/show.name.s01e01.mkv')
    episode = create_file(os.path.join(
        'downloads', 'release', 'Season 1', folder_name, 'show.name.s01e02.mkv'
    ))
    processor_class, failure_handler, history_update = directory_processor
    item = PostProcessQueueItem(
        path=root, resource_name=resource_name, info_hash='download-id', process_method='copy',
        process_single_resource=True, force=True, is_priority=True
    )

    result = item.process_path()

    processor_class.assert_not_called()
    assert result.result is False
    assert result.failed is failed
    assert os.path.isfile(episode)
    if failed:
        failure_handler.assert_called_once_with(root)
        history_update.assert_called_once()
        assert history_update.call_args[0][0].status == (
            ClientStatusEnum.FAILED.value | ClientStatusEnum.POSTPROCESSED.value
        )
    else:
        assert result.postpone_any is True
        assert result.skipped is False
        failure_handler.assert_not_called()
        history_update.assert_not_called()


@pytest.mark.parametrize('resource_name', ['release', 'release.nzb'])
@pytest.mark.parametrize('sync_directory', ['', os.path.join('Season 2', 'deeper')])
def test_named_release_checks_all_sync_markers_before_processing(
        create_file, create_dir, directory_processor, app_config, resource_name, sync_directory):
    """A syncing release is postponed before processing either root or nested episodes."""
    root = os.path.realpath(create_dir('downloads/release'))
    create_file('downloads/release/show.name.s01e01.mkv')
    create_file('downloads/release/Season 1/show.name.s01e02.mkv')
    sync_file = create_file(os.path.join(
        'downloads', 'release', sync_directory, '.syncthing.show.name.s02e01.mkv.tmp'
    ))
    app_config('POSTPONE_IF_SYNC_FILES', True)
    processor_class, failure_handler, history_update = directory_processor
    item = PostProcessQueueItem(
        path=root, resource_name=resource_name, info_hash='download-id', process_method='copy',
        process_single_resource=True, force=True, is_priority=True
    )

    result = item.process_path()

    processor_class.assert_not_called()
    failure_handler.assert_not_called()
    history_update.assert_not_called()
    assert result.postpone_processing is True
    assert result.postpone_any is True
    assert result.failed is False
    assert os.path.isfile(sync_file)


@pytest.mark.parametrize('resource_name', ['release', 'release.nzb'])
@pytest.mark.parametrize('ignored_folder', ['@eaDir', '.hidden'])
@pytest.mark.parametrize('marker', ['failed', 'sync'])
def test_named_release_validation_ignores_markers_in_excluded_subtrees(
        create_file, create_dir, directory_processor, app_config, resource_name, ignored_folder, marker):
    """Ignored folders cannot fail or postpone an otherwise valid selected release."""
    root = os.path.realpath(create_dir('downloads/release'))
    episodes = [
        create_file('downloads/release/show.name.s01e01.mkv'),
        create_file('downloads/release/Season 1/show.name.s01e02.mkv'),
    ]
    ignored_root = os.path.join('downloads', 'release', ignored_folder)
    if marker == 'failed':
        create_file(os.path.join(ignored_root, '_FAILED_release', 'show.name.s01e99.mkv'))
    else:
        create_file(os.path.join(ignored_root, '.syncthing.show.name.s01e99.mkv.tmp'))
    app_config('POSTPONE_IF_SYNC_FILES', True)
    processor_class, failure_handler, history_update = directory_processor
    item = PostProcessQueueItem(
        path=root, resource_name=resource_name, info_hash='download-id', process_method='copy',
        process_single_resource=True
    )

    result = item.process_path()

    processed = [call[0][0] for call in processor_class.call_args_list]
    assert sorted(processed) == sorted(os.path.realpath(episode) for episode in episodes)
    assert result.result is True
    assert result.failed is False
    assert result.postpone_any is False
    failure_handler.assert_not_called()
    history_update.assert_called_once()


@pytest.mark.parametrize('resource_name', ['missing.mkv', 'Missing.Show'])
@pytest.mark.parametrize('sibling_name', ['_FAILED_other', '_UNDERSIZED_other'])
def test_missing_selection_does_not_validate_unrelated_failed_downloads(
        create_file, create_dir, directory_processor, resource_name, sibling_name):
    """A vanished requested resource must not redirect validation to unrelated downloads."""
    root = os.path.realpath(create_dir('downloads'))
    sibling = create_file(os.path.join('downloads', sibling_name, 'other.show.s01e01.mkv'))
    processor_class, failure_handler, history_update = directory_processor
    item = PostProcessQueueItem(
        path=root, resource_name=resource_name, info_hash='download-id', process_method='copy',
        process_single_resource=True
    )

    result = item.process_path()

    processor_class.assert_not_called()
    failure_handler.assert_not_called()
    history_update.assert_not_called()
    assert result.result is False
    assert result.skipped is True
    assert result.failed is False
    assert os.path.isfile(sibling)
