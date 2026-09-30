# coding=utf-8
"""Failed download handling for remote file paths mapped to local downloads."""
from __future__ import unicode_literals

import os

from medusa import app, failed_processor
from medusa.helper.exceptions import EpisodePostProcessingFailedException
from medusa.process_tv import PostProcessQueueItem, ProcessResult
from medusa.schedulers.download_handler import ClientStatusEnum

from mock.mock import Mock

import pytest


@pytest.fixture
def mapped_file_failure(create_file, tmpdir, monkeypatch):
    """Use real path mapping and failure parsing without queueing an actual download."""
    local_path = create_file('downloads/show.name.s01e01.mkv')
    sibling = create_file('downloads/another.show.s01e01.mkv')
    remote_path = str(tmpdir.join('remote', os.path.basename(local_path)))
    episode = Mock(episode=1)
    episode.series.get_episode.return_value = episode
    parser = Mock(**{'parse.return_value': Mock(
        series=episode.series, season_number=1, episode_numbers=[1]
    )})
    processor = Mock(_output=[], **{'process.return_value': False})
    processor_class = Mock(return_value=processor)
    failed_processor_class = Mock(wraps=failed_processor.FailedProcessor)
    queue_item_class = Mock()
    scheduler = Mock()
    history_update = Mock()
    original_delete_folder = ProcessResult.delete_folder

    def delete_selected_file(path, check_empty=True):
        # Fail before deleting if the cleanup target ever expands to the parent.
        assert path == local_path
        return original_delete_folder(path, check_empty=check_empty)

    delete_folder = Mock(side_effect=delete_selected_file)
    monkeypatch.setattr(app, 'TV_DOWNLOAD_DIR', os.path.dirname(local_path))
    monkeypatch.setattr(app, 'USE_FAILED_DOWNLOADS', True)
    monkeypatch.setattr(app, 'POSTPONE_IF_SYNC_FILES', False)
    monkeypatch.setattr(app, 'POSTPONE_IF_NO_SUBS', False)
    monkeypatch.setattr(app, 'forced_search_queue_scheduler', scheduler)
    monkeypatch.setattr('medusa.process_tv.post_processor.PostProcessor', processor_class)
    monkeypatch.setattr('medusa.process_tv.failed_processor.FailedProcessor', failed_processor_class)
    monkeypatch.setattr('medusa.failed_processor.NameParser', Mock(return_value=parser))
    monkeypatch.setattr('medusa.failed_processor.FailedQueueItem', queue_item_class)
    monkeypatch.setattr(ProcessResult, 'already_postprocessed', Mock(return_value=False))
    monkeypatch.setattr(ProcessResult, 'delete_folder', delete_folder)
    monkeypatch.setattr(PostProcessQueueItem, 'update_resource', history_update)
    return Mock(
        local_path=local_path, remote_path=remote_path, sibling=sibling, episode=episode,
        parser=parser, processor=processor, processor_class=processor_class,
        failed_processor_class=failed_processor_class, queue_item_class=queue_item_class,
        scheduler=scheduler, delete_folder=delete_folder, history_update=history_update
    )


@pytest.mark.parametrize('resource', [None, ''])
@pytest.mark.parametrize('single_resource', [False, True])
@pytest.mark.parametrize('media_raises', [False, True])
@pytest.mark.parametrize('delete_failed', [False, True])
def test_mapped_file_failure_uses_local_file_without_deleting_siblings(
        mapped_file_failure, monkeypatch, resource, single_resource, media_raises, delete_failed):
    """Resolve both failure metadata and cleanup from the selected local file."""
    state = mapped_file_failure
    monkeypatch.setattr(app, 'DELETE_FAILED', delete_failed)
    if media_raises:
        state.processor.process.side_effect = EpisodePostProcessingFailedException('media processing failed')
    item = PostProcessQueueItem(
        path=state.remote_path, resource_name=resource, info_hash='test-hash',
        process_method='copy', process_single_resource=single_resource
    )

    result = item.process_path()

    state.processor_class.assert_called_once_with(state.local_path, None, 'copy', False)
    state.processor.process.assert_called_once_with()
    state.failed_processor_class.assert_called_once_with(
        state.local_path, os.path.basename(state.local_path), []
    )
    state.parser.parse.assert_called_once_with('show.name.s01e01', use_cache=False)
    state.queue_item_class.assert_called_once_with(state.episode.series, [state.episode])
    state.scheduler.action.add_item.assert_called_once_with(state.queue_item_class.return_value)
    assert result.input_path == state.local_path
    assert result.result is False
    assert result.succeeded is False
    assert item.success is False
    state.history_update.assert_called_once()
    assert state.history_update.call_args[0][0].status == ClientStatusEnum.FAILED.value | ClientStatusEnum.POSTPROCESSED.value
    assert not os.path.exists(state.remote_path)
    assert os.path.isfile(state.local_path)
    assert os.path.isfile(state.sibling)
    if delete_failed:
        state.delete_folder.assert_called_once_with(state.local_path, check_empty=False)
    else:
        state.delete_folder.assert_not_called()


@pytest.mark.parametrize('known_episodes', [False, True])
def test_mapped_file_failure_preserves_release_and_episode_metadata(
        mapped_file_failure, monkeypatch, known_episodes):
    """Mapping a failed file must not discard metadata supplied by its caller."""
    state = mapped_file_failure
    monkeypatch.setattr(app, 'DELETE_FAILED', True)
    episodes = [state.episode] if known_episodes else []
    resource = None if known_episodes else 'original.release.s01e01.nzb'
    item = PostProcessQueueItem(
        path=state.remote_path, resource_name=resource, episodes=episodes,
        info_hash='test-hash', process_method='copy', process_single_resource=True
    )

    result = item.process_path()

    state.failed_processor_class.assert_called_once_with(
        state.local_path, resource or os.path.basename(state.local_path), episodes
    )
    if known_episodes:
        state.parser.parse.assert_not_called()
    else:
        state.parser.parse.assert_called_once_with('original.release.s01e01', use_cache=False)
    state.queue_item_class.assert_called_once_with(state.episode.series, [state.episode])
    state.scheduler.action.add_item.assert_called_once_with(state.queue_item_class.return_value)
    state.delete_folder.assert_called_once_with(state.local_path, check_empty=False)
    assert result.result is False
    assert result.succeeded is False
    assert os.path.isfile(state.local_path)
    assert os.path.isfile(state.sibling)
