# coding=utf-8
"""Regression tests separating download failure from successful failure handling."""
from __future__ import unicode_literals

import os

from medusa import app
from medusa.helper.exceptions import EpisodePostProcessingFailedException, FailedPostProcessingFailedException
from medusa.process_tv import PostProcessQueueItem, ProcessResult
from medusa.schedulers.download_handler import ClientStatusEnum

from mock.mock import Mock

import pytest


@pytest.mark.parametrize('single_resource', [False, True])
@pytest.mark.parametrize('media_raises', [False, True])
@pytest.mark.parametrize('failure_outcome', ['success', 'false', 'exception'])
@pytest.mark.parametrize('delete_failed', [False, True])
def test_failed_download_handling_preserves_failure_status(
        create_file, monkeypatch, single_resource, media_raises, failure_outcome, delete_failed):
    """Successful retry handling is not successful media processing, but can still clean up."""
    path = create_file('downloads/release/show.name.s01e01.mkv')
    directory = os.path.dirname(path)
    resource = os.path.basename(path)
    processor = Mock(_output=[], **{'process.return_value': False})
    if media_raises:
        processor.process.side_effect = EpisodePostProcessingFailedException('media processing failed')
    failed_processor = Mock(output='', **{'process.return_value': failure_outcome == 'success'})
    if failure_outcome == 'exception':
        failed_processor.process.side_effect = FailedPostProcessingFailedException('failure handling failed')
    failed_processor_class = Mock(return_value=failed_processor)
    delete_folder = Mock(return_value=True)
    history_update = Mock()
    monkeypatch.setattr(app, 'USE_FAILED_DOWNLOADS', True)
    monkeypatch.setattr(app, 'DELETE_FAILED', delete_failed)
    monkeypatch.setattr(app, 'POSTPONE_IF_SYNC_FILES', False)
    monkeypatch.setattr(app, 'POSTPONE_IF_NO_SUBS', False)
    monkeypatch.setattr('medusa.process_tv.post_processor.PostProcessor', Mock(return_value=processor))
    monkeypatch.setattr('medusa.process_tv.failed_processor.FailedProcessor', failed_processor_class)
    monkeypatch.setattr(ProcessResult, 'already_postprocessed', Mock(return_value=False))
    monkeypatch.setattr(ProcessResult, 'delete_folder', delete_folder)
    monkeypatch.setattr(PostProcessQueueItem, 'update_resource', history_update)
    item = PostProcessQueueItem(
        path=directory, resource_name=resource, info_hash='test-hash',
        process_method='copy', process_single_resource=single_resource
    )

    result = item.process_path()

    processor.process.assert_called_once_with()
    failed_processor_class.assert_called_once_with(os.path.realpath(directory), resource, [])
    failed_processor.process.assert_called_once_with()
    assert result.result is False
    assert result.succeeded is False
    assert result.skipped is False
    assert item.success is False
    history_update.assert_called_once()
    assert history_update.call_args[0][0].status == ClientStatusEnum.FAILED.value | ClientStatusEnum.POSTPROCESSED.value
    if delete_failed and failure_outcome == 'success':
        delete_folder.assert_called_once_with(os.path.realpath(directory), check_empty=False)
    else:
        delete_folder.assert_not_called()
    if failure_outcome == 'success':
        assert 'Failed Download Processing succeeded:' in result.output
    else:
        assert 'Failed Download Processing failed:' in result.output


@pytest.mark.parametrize('resource', [None, ''])
@pytest.mark.parametrize('media_raises', [False, True])
@pytest.mark.parametrize('delete_failed', [False, True])
@pytest.mark.parametrize('single_resource', [False, True])
def test_direct_file_failure_uses_filename_without_deleting_siblings(
        create_file, monkeypatch, resource, media_raises, delete_failed, single_resource):
    """File-only requests can queue replacement downloads without scanning or deleting their parent."""
    path = create_file('downloads/show.name.s01e01.mkv')
    sibling = create_file('downloads/another.show.s01e01.mkv')
    processor = Mock(_output=[], **{'process.return_value': False})
    if media_raises:
        processor.process.side_effect = EpisodePostProcessingFailedException('media processing failed')
    episode = Mock(episode=1)
    series = episode.series
    series.get_episode.return_value = episode
    parse_result = Mock(series=series, season_number=1, episode_numbers=[1])
    parser = Mock(**{'parse.return_value': parse_result})
    queue_item_class = Mock()
    scheduler = Mock()
    history_update = Mock()
    original_delete_folder = ProcessResult.delete_folder

    def delete_selected_file(folder, **kwargs):
        assert folder == path
        return original_delete_folder(folder, **kwargs)

    delete_folder = Mock(side_effect=delete_selected_file)
    monkeypatch.setattr(app, 'USE_FAILED_DOWNLOADS', True)
    monkeypatch.setattr(app, 'DELETE_FAILED', delete_failed)
    monkeypatch.setattr(app, 'POSTPONE_IF_SYNC_FILES', False)
    monkeypatch.setattr(app, 'POSTPONE_IF_NO_SUBS', False)
    monkeypatch.setattr(app, 'forced_search_queue_scheduler', scheduler)
    monkeypatch.setattr('medusa.process_tv.post_processor.PostProcessor', Mock(return_value=processor))
    monkeypatch.setattr('medusa.failed_processor.NameParser', Mock(return_value=parser))
    monkeypatch.setattr('medusa.failed_processor.FailedQueueItem', queue_item_class)
    monkeypatch.setattr(ProcessResult, 'already_postprocessed', Mock(return_value=False))
    monkeypatch.setattr(ProcessResult, 'delete_folder', delete_folder)
    monkeypatch.setattr(PostProcessQueueItem, 'update_resource', history_update)
    item = PostProcessQueueItem(
        path=path, resource_name=resource, info_hash='test-hash',
        process_method='copy', process_single_resource=single_resource, delete_on=False
    )

    result = item.process_path()

    processor.process.assert_called_once_with()
    parser.parse.assert_called_once_with('show.name.s01e01', use_cache=False)
    series.get_episode.assert_called_once_with(1, 1)
    queue_item_class.assert_called_once_with(series, [episode])
    scheduler.action.add_item.assert_called_once_with(queue_item_class.return_value)
    assert result.result is False
    assert result.succeeded is False
    assert item.success is False
    history_update.assert_called_once()
    assert history_update.call_args[0][0].status == ClientStatusEnum.FAILED.value | ClientStatusEnum.POSTPROCESSED.value
    assert os.path.isfile(path)
    assert os.path.isfile(sibling)
    assert sorted(os.listdir(os.path.dirname(path))) == ['another.show.s01e01.mkv', 'show.name.s01e01.mkv']
    if delete_failed:
        delete_folder.assert_called_once_with(path, check_empty=False)
    else:
        delete_folder.assert_not_called()


@pytest.mark.parametrize('single_resource', [False, True])
def test_direct_archive_failure_keeps_cleanup_scoped_to_selected_archive(
        create_file, monkeypatch, single_resource):
    """Failed extracted media must not expose the archive's parent to recursive deletion."""
    archive = create_file('downloads/show.name.s01e01.rar')
    video = create_file('downloads/show.name.s01e01.mkv')
    sibling = create_file('downloads/another.show.s01e01.mkv')
    processor = Mock(_output=[], **{'process.return_value': False})
    failed_processor = Mock(output='', **{'process.return_value': True})
    failed_processor_class = Mock(return_value=failed_processor)
    original_delete_folder = ProcessResult.delete_folder

    def delete_selected_archive(folder, **kwargs):
        assert folder == archive
        return original_delete_folder(folder, **kwargs)

    delete_folder = Mock(side_effect=delete_selected_archive)
    monkeypatch.setattr(app, 'USE_FAILED_DOWNLOADS', True)
    monkeypatch.setattr(app, 'DELETE_FAILED', True)
    monkeypatch.setattr(app, 'UNPACK', True)
    monkeypatch.setattr(app, 'DELRARCONTENTS', False)
    monkeypatch.setattr(app, 'POSTPONE_IF_SYNC_FILES', False)
    monkeypatch.setattr(app, 'POSTPONE_IF_NO_SUBS', False)
    monkeypatch.setattr('medusa.process_tv.post_processor.PostProcessor', Mock(return_value=processor))
    monkeypatch.setattr('medusa.process_tv.failed_processor.FailedProcessor', failed_processor_class)
    monkeypatch.setattr(ProcessResult, 'already_postprocessed', Mock(return_value=False))
    monkeypatch.setattr(ProcessResult, 'unrar', Mock(return_value=[os.path.basename(video)]))
    monkeypatch.setattr(ProcessResult, 'delete_folder', delete_folder)
    history_update = Mock()
    monkeypatch.setattr(PostProcessQueueItem, 'update_resource', history_update)
    item = PostProcessQueueItem(
        path=archive, info_hash='test-hash', process_method='copy',
        process_single_resource=single_resource, delete_on=False
    )

    result = item.process_path()

    processor.process.assert_called_once_with()
    resource_name = os.path.basename(archive if single_resource else video)
    failed_processor_class.assert_called_once_with(archive, resource_name, [])
    failed_processor.process.assert_called_once_with()
    delete_folder.assert_called_once_with(archive, check_empty=False)
    assert result.result is False
    assert result.succeeded is False
    assert item.success is False
    history_update.assert_called_once()
    assert history_update.call_args[0][0].status == ClientStatusEnum.FAILED.value | ClientStatusEnum.POSTPROCESSED.value
    assert all(os.path.isfile(path) for path in (archive, video, sibling))


@pytest.mark.parametrize('known_episodes', [False, True])
def test_direct_file_failure_preserves_explicit_release_and_episode_metadata(
        create_file, monkeypatch, known_episodes):
    """A filename fallback must not replace supplied release names or require parsing known episodes."""
    path = create_file('downloads/show.name.s01e01.mkv')
    episode = Mock(episode=1)
    episode.series.get_episode.return_value = episode
    parser = Mock(**{'parse.return_value': Mock(
        series=episode.series, season_number=1, episode_numbers=[1]
    )})
    queue_item_class = Mock()
    scheduler = Mock()
    monkeypatch.setattr(app, 'USE_FAILED_DOWNLOADS', True)
    monkeypatch.setattr(app, 'DELETE_FAILED', False)
    monkeypatch.setattr(app, 'forced_search_queue_scheduler', scheduler)
    monkeypatch.setattr('medusa.failed_processor.NameParser', Mock(return_value=parser))
    monkeypatch.setattr('medusa.failed_processor.FailedQueueItem', queue_item_class)
    result = ProcessResult(path, 'copy', episodes=[episode] if known_episodes else [])
    if not known_episodes:
        result.resource_name = 'original.release.s01e01.nzb'

    result.process_failed(path)

    if known_episodes:
        parser.parse.assert_not_called()
    else:
        parser.parse.assert_called_once_with('original.release.s01e01', use_cache=False)
    queue_item_class.assert_called_once_with(episode.series, [episode])
    scheduler.action.add_item.assert_called_once_with(queue_item_class.return_value)


@pytest.mark.parametrize('single_resource', [False, True])
def test_direct_file_failure_remembers_file_scope_after_source_moves(
        create_file, monkeypatch, single_resource):
    """Moving the source before a failure cannot turn a file request into directory cleanup."""
    path = create_file('downloads/show.name.s01e01.mkv')
    sibling = create_file('downloads/another.show.s01e01.mkv')
    moved_path = path + '.moved'

    def move_then_fail():
        os.rename(path, moved_path)
        return False

    processor = Mock(_output=[], **{'process.side_effect': move_then_fail})
    failed_processor = Mock(output='', **{'process.return_value': True})
    failed_processor_class = Mock(return_value=failed_processor)
    original_delete_folder = ProcessResult.delete_folder

    def delete_selected_file(folder, **kwargs):
        assert folder == path
        return original_delete_folder(folder, **kwargs)

    delete_folder = Mock(side_effect=delete_selected_file)
    monkeypatch.setattr(app, 'USE_FAILED_DOWNLOADS', True)
    monkeypatch.setattr(app, 'DELETE_FAILED', True)
    monkeypatch.setattr(app, 'POSTPONE_IF_SYNC_FILES', False)
    monkeypatch.setattr(app, 'POSTPONE_IF_NO_SUBS', False)
    monkeypatch.setattr('medusa.process_tv.post_processor.PostProcessor', Mock(return_value=processor))
    monkeypatch.setattr('medusa.process_tv.failed_processor.FailedProcessor', failed_processor_class)
    monkeypatch.setattr(ProcessResult, 'already_postprocessed', Mock(return_value=False))
    monkeypatch.setattr(ProcessResult, 'delete_folder', delete_folder)
    item = PostProcessQueueItem(
        path=path, process_method='move', process_single_resource=single_resource, delete_on=False
    )
    # Only inspect failed-download cleanup, not the separate successful-processing cleanup policy.
    monkeypatch.setattr(ProcessResult, '_clean_up', Mock())

    result = item.process_path()

    processor.process.assert_called_once_with()
    failed_processor_class.assert_called_once_with(path, os.path.basename(path), [])
    failed_processor.process.assert_called_once_with()
    delete_folder.assert_called_once_with(path, check_empty=False)
    assert result.result is False
    assert result.succeeded is False
    assert not os.path.exists(path)
    assert os.path.isfile(moved_path)
    assert os.path.isfile(sibling)
