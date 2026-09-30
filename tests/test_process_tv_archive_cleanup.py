# coding=utf-8
"""Tests for retaining extracted files when archive processing is incomplete."""
from __future__ import unicode_literals

import os

from medusa import app
from medusa.process_tv import PostProcessQueueItem, ProcessResult
from medusa.schedulers.download_handler import ClientStatusEnum

from mock.mock import Mock

import pytest


@pytest.mark.parametrize('process_method', ['hardlink', 'symlink', 'reflink', 'copy', 'move'])
@pytest.mark.parametrize('first_outcome', ['failed', 'postponed', 'succeeded'])
def test_archive_cleanup_requires_complete_processing(create_file, monkeypatch, process_method, first_outcome):
    """A later success must not delete failed or postponed extracted media."""
    archive = create_file('download/release.rar')
    first_video = create_file('download/show.name.s01e01.mkv')
    second_video = create_file('download/show.name.s01e02.mkv')
    metadata = create_file('download/readme.txt')
    path = os.path.dirname(archive)
    first_processor = Mock(_output=[], **{'process.return_value': first_outcome != 'failed'})
    second_processor = Mock(_output=[], **{'process.return_value': True})
    first_processor.list_associated_files.return_value = []
    second_processor.list_associated_files.return_value = ['show.name.s01e02.en.srt']
    processor_class = Mock(side_effect=[first_processor, second_processor])
    monkeypatch.setattr('medusa.process_tv.post_processor.PostProcessor', processor_class)
    monkeypatch.setattr('medusa.process_tv.get_embedded_subtitles', Mock(return_value=set()))
    monkeypatch.setattr(ProcessResult, 'already_postprocessed', Mock(return_value=False))
    monkeypatch.setattr(ProcessResult, 'subtitles_enabled', Mock(return_value=True))
    monkeypatch.setattr(app, 'POSTPONE_IF_NO_SUBS', first_outcome == 'postponed')
    monkeypatch.setattr(app, 'IGNORE_EMBEDDED_SUBS', True)
    monkeypatch.setattr(app, 'DELRARCONTENTS', True)
    monkeypatch.setattr(app, 'NO_DELETE', False)
    sut = ProcessResult(path, process_method=process_method, process_single_resource=True)
    sut.video_files = [os.path.basename(first_video), os.path.basename(second_video)]
    sut.video_in_rar = list(sut.video_files)
    sut.rar_content = sut.video_files + [os.path.basename(metadata)]
    sut.unwanted_files = [os.path.basename(archive), os.path.basename(metadata)]

    sut.process_files(path)
    sut._clean_up(path, proc_type='auto')

    assert processor_class.call_count == 2
    second_processor.process.assert_called_once_with()
    if first_outcome == 'postponed':
        first_processor.process.assert_not_called()
        assert sut.postpone_any is True
    else:
        first_processor.process.assert_called_once_with()
    assert sut.succeeded is (first_outcome != 'failed')
    incomplete = first_outcome != 'succeeded'
    assert os.path.isfile(first_video) is incomplete
    assert os.path.isfile(second_video) is incomplete
    assert os.path.isfile(metadata) is incomplete
    assert os.path.isfile(archive) is (incomplete or process_method != 'move')


@pytest.mark.parametrize('first_succeeded', [False, True])
def test_archive_history_reflects_all_media_results(create_file, monkeypatch, first_succeeded):
    """One failed member keeps the download failed after a later member succeeds."""
    archive = create_file('download/release.rar')
    videos = [create_file('download/show.name.s01e01.mkv'), create_file('download/show.name.s01e02.mkv')]
    first_processor = Mock(_output=[], **{'process.return_value': first_succeeded})
    second_processor = Mock(_output=[], **{'process.return_value': True})
    processor_class = Mock(side_effect=[first_processor, second_processor])
    failed_processor = Mock(output='Failed-download handling completed.', **{'process.return_value': True})
    failed_processor_class = Mock(return_value=failed_processor)
    history_update = Mock()
    monkeypatch.setattr('medusa.process_tv.post_processor.PostProcessor', processor_class)
    monkeypatch.setattr('medusa.process_tv.failed_processor.FailedProcessor', failed_processor_class)
    monkeypatch.setattr(ProcessResult, 'already_postprocessed', Mock(return_value=False))
    monkeypatch.setattr(ProcessResult, 'unrar', Mock(return_value=[os.path.basename(video) for video in videos]))
    monkeypatch.setattr(PostProcessQueueItem, 'update_resource', history_update)
    monkeypatch.setattr(app, 'UNPACK', True)
    monkeypatch.setattr(app, 'DELRARCONTENTS', False)
    monkeypatch.setattr(app, 'POSTPONE_IF_NO_SUBS', False)
    monkeypatch.setattr(app, 'USE_FAILED_DOWNLOADS', True)
    monkeypatch.setattr(app, 'DELETE_FAILED', False)
    item = PostProcessQueueItem(
        path=archive, info_hash='test-hash', process_method='copy', process_single_resource=True
    )

    result = item.process_path()

    first_processor.process.assert_called_once_with()
    second_processor.process.assert_called_once_with()
    assert result.succeeded is first_succeeded
    assert item.success is first_succeeded
    if first_succeeded:
        failed_processor_class.assert_not_called()
    else:
        failed_processor_class.assert_called_once_with(archive, None, [])
        failed_processor.process.assert_called_once_with()
    history_update.assert_called_once()
    expected_status = ClientStatusEnum.COMPLETED if first_succeeded else ClientStatusEnum.FAILED
    assert history_update.call_args[0][0].status == expected_status.value | ClientStatusEnum.POSTPROCESSED.value


@pytest.mark.parametrize('incomplete_state', ['result', 'succeeded', 'postpone_any'])
@pytest.mark.parametrize('force', [False, True])
def test_delete_files_requires_force_after_incomplete_processing(create_file, incomplete_state, force):
    """Only an explicit force flag may override incomplete processing during file cleanup."""
    path = create_file('download/readme.txt')
    sut = ProcessResult(os.path.dirname(path))
    setattr(sut, incomplete_state, incomplete_state == 'postpone_any')

    sut.delete_files(os.path.dirname(path), [os.path.basename(path)], force=force)

    assert os.path.isfile(path) is not force
