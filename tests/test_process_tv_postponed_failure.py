# coding=utf-8
"""Keep mixed failed and subtitle-postponed releases available for another attempt."""
from __future__ import unicode_literals

import os

from medusa import app
from medusa.process_tv import PostProcessQueueItem, ProcessResult
from medusa.schedulers.download_handler import ClientStatusEnum

from mock.mock import Mock

import pytest


@pytest.fixture
def postponed_failure_mocks(monkeypatch):
    """Mock processors and destructive actions, retaining real subtitle decisions."""
    processors = {}

    def get_processor(file_path, resource_name, process_method, is_priority):
        assert os.path.isfile(file_path)
        processor = Mock(_output=[], **{'process.return_value': False})
        processor.list_associated_files.return_value = [] if 'waiting' in file_path else [file_path + '.srt']
        processors[file_path] = processor
        return processor

    failed_processor = Mock(output='', **{'process.return_value': True})
    failed_processor_class = Mock(return_value=failed_processor)
    delete_folder = Mock(return_value=True)
    history_update = Mock()
    monkeypatch.setattr(app, 'USE_FAILED_DOWNLOADS', True)
    monkeypatch.setattr(app, 'DELETE_FAILED', True)
    monkeypatch.setattr(app, 'POSTPONE_IF_SYNC_FILES', False)
    monkeypatch.setattr(app, 'POSTPONE_IF_NO_SUBS', True)
    monkeypatch.setattr(app, 'IGNORE_EMBEDDED_SUBS', True)
    monkeypatch.setattr(app, 'UNPACK', True)
    monkeypatch.setattr(app, 'DELRARCONTENTS', False)
    monkeypatch.setattr(app, 'KODI_LIBRARY_CLEAN_PENDING', False)
    monkeypatch.setattr(app, 'USE_TORRENTS', False)
    monkeypatch.setattr('medusa.process_tv.post_processor.PostProcessor', Mock(side_effect=get_processor))
    monkeypatch.setattr('medusa.process_tv.failed_processor.FailedProcessor', failed_processor_class)
    monkeypatch.setattr(ProcessResult, 'already_postprocessed', Mock(return_value=False))
    monkeypatch.setattr(ProcessResult, 'subtitles_enabled', Mock(return_value=True))
    monkeypatch.setattr(ProcessResult, 'delete_folder', delete_folder)
    monkeypatch.setattr(PostProcessQueueItem, 'update_resource', history_update)
    return processors, failed_processor_class, delete_folder, history_update


@pytest.mark.parametrize('postponed_first', [False, True])
@pytest.mark.parametrize('trailing_metadata', [False, True])
def test_postponed_release_cannot_trigger_failed_download_cleanup(
        create_file, postponed_failure_mocks, postponed_first, trailing_metadata):
    """Any pending episode protects the whole release, regardless of the final batch."""
    first_name, second_name = ('waiting.s01e01.mkv', 'failed.s01e02.mkv')
    if not postponed_first:
        first_name, second_name = second_name, first_name
    # Bottom-up traversal visits the deeper episode first, independently of directory ordering.
    first = create_file('downloads/release/season/part/' + first_name)
    second = create_file('downloads/release/season/' + second_name)
    release = os.path.dirname(os.path.dirname(second))
    retained_files = [first, second]
    if trailing_metadata:
        retained_files.append(create_file('downloads/release/release.nfo'))
    item = PostProcessQueueItem(
        path=release, resource_name='release.nzb', info_hash='test-hash',
        process_method='copy', process_single_resource=True
    )

    result = item.process_path()

    processors, failed_processor_class, delete_folder, history_update = postponed_failure_mocks
    assert list(processors) == [first, second]
    for path, processor in processors.items():
        if 'waiting' in os.path.basename(path):
            processor.process.assert_not_called()
        else:
            processor.process.assert_called_once_with()
    assert result.postpone_any is True
    assert result.succeeded is False
    assert result.skipped is False
    assert item.success is None
    failed_processor_class.assert_not_called()
    delete_folder.assert_not_called()
    history_update.assert_not_called()
    assert all(os.path.isfile(path) for path in retained_files)


@pytest.mark.parametrize('process_method', ['hardlink', 'symlink', 'reflink'])
def test_empty_archive_link_batch_cannot_clear_release_postponement(
        create_file, monkeypatch, postponed_failure_mocks, process_method):
    """The empty non-archive batch cannot allow failure handling for pending RAR members."""
    archive = create_file('downloads/release.rar')
    failed = create_file('downloads/failed.s01e01.mkv')
    pending = create_file('downloads/waiting.s01e02.mkv')
    monkeypatch.setattr(ProcessResult, 'unrar', Mock(return_value=[os.path.basename(failed), os.path.basename(pending)]))
    item = PostProcessQueueItem(
        path=archive, info_hash='test-hash', process_method=process_method, process_single_resource=True
    )

    result = item.process_path()

    processors, failed_processor_class, delete_folder, history_update = postponed_failure_mocks
    processors[failed].process.assert_called_once_with()
    processors[pending].process.assert_not_called()
    assert result.postpone_any is True
    assert result.succeeded is False
    assert result.process_method == process_method
    failed_processor_class.assert_not_called()
    delete_folder.assert_not_called()
    history_update.assert_not_called()
    assert all(os.path.isfile(path) for path in (archive, failed, pending))


@pytest.mark.parametrize('delete_failed', [False, True])
def test_non_postponed_failure_still_uses_failed_download_handling(
        create_file, monkeypatch, postponed_failure_mocks, delete_failed):
    """Failed media with subtitles retains the configured retry and deletion behavior."""
    video = create_file('downloads/release/failed.s01e01.mkv')
    release = os.path.dirname(video)
    monkeypatch.setattr(app, 'DELETE_FAILED', delete_failed)
    item = PostProcessQueueItem(
        path=release, resource_name='release.nzb', info_hash='test-hash',
        process_method='copy', process_single_resource=True
    )

    result = item.process_path()

    processors, failed_processor_class, delete_folder, history_update = postponed_failure_mocks
    processors[video].process.assert_called_once_with()
    assert result.postpone_any is False
    assert result.succeeded is False
    assert item.success is False
    failed_processor_class.assert_called_once_with(release, 'release.nzb', [])
    failed_processor_class.return_value.process.assert_called_once_with()
    if delete_failed:
        delete_folder.assert_called_once_with(release, check_empty=False)
    else:
        delete_folder.assert_not_called()
    history_update.assert_called_once()
    assert history_update.call_args[0][0].status == ClientStatusEnum.FAILED.value | ClientStatusEnum.POSTPROCESSED.value
    assert os.path.isfile(video)
