# coding=utf-8
"""Protect downloads whose archives cannot be unpacked."""
from __future__ import unicode_literals

import os

from medusa import app
from medusa.process_tv import PostProcessQueueItem, ProcessResult
from medusa.schedulers.download_handler import ClientStatusEnum

from mock.mock import Mock

import pytest


@pytest.mark.parametrize('input_form', ['file', 'directory', 'directory_and_resource'])
@pytest.mark.parametrize('process_method', ['move', 'copy', 'hardlink'])
def test_disabled_unpacking_preserves_archive(create_file, monkeypatch, input_form, process_method):
    """Unprocessed archives must not be deleted or recorded as completed downloads."""
    archive = create_file('downloads/show.s01e01.rar')
    volume = create_file('downloads/show.s01e01.r00')
    path = archive if input_form == 'file' else os.path.dirname(archive)
    resource = os.path.basename(archive) if input_form == 'directory_and_resource' else None
    history_update = Mock()
    failed_handler = Mock()
    processor = Mock()
    monkeypatch.setattr(app, 'UNPACK', False)
    monkeypatch.setattr(app, 'NO_DELETE', False)
    monkeypatch.setattr(app, 'ALLOWED_EXTENSIONS', ['srt', 'nfo', 'sub', 'idx'])
    monkeypatch.setattr(PostProcessQueueItem, 'update_resource', history_update)
    monkeypatch.setattr(ProcessResult, 'process_failed', failed_handler)
    monkeypatch.setattr('medusa.process_tv.post_processor.PostProcessor', processor)
    item = PostProcessQueueItem(
        path=path, resource_name=resource, info_hash='archive-hash',
        process_method=process_method, process_single_resource=True
    )

    result = item.process_path()

    assert os.path.isfile(archive)
    assert os.path.isfile(volume)
    assert result.result is False
    assert result.postpone_any is True
    assert result.succeeded is True
    history_update.assert_not_called()
    failed_handler.assert_not_called()
    processor.assert_not_called()


def test_disabled_unpacking_processes_externally_extracted_media(create_file, monkeypatch):
    """Process externally extracted videos without deleting the retained archives or volumes."""
    archive = create_file('downloads/show.s01e01.rar')
    volume = create_file('downloads/show.s01e01.r00')
    video = create_file('downloads/show.s01e02.mkv')
    history_update = Mock()
    processor = Mock(return_value=Mock(_output=[], **{'process.return_value': True}))
    monkeypatch.setattr(app, 'UNPACK', False)
    monkeypatch.setattr(ProcessResult, 'already_postprocessed', Mock(return_value=False))
    monkeypatch.setattr(PostProcessQueueItem, 'update_resource', history_update)
    monkeypatch.setattr('medusa.process_tv.post_processor.PostProcessor', processor)
    item = PostProcessQueueItem(
        path=os.path.dirname(archive), info_hash='archive-hash',
        process_method='move', process_single_resource=True
    )

    result = item.process_path()

    assert os.path.isfile(archive)
    assert os.path.isfile(volume)
    assert result.result is True
    assert result.postpone_any is False
    history_update.assert_called_once()
    assert history_update.call_args[0][0].status == ClientStatusEnum.COMPLETED.value | ClientStatusEnum.POSTPROCESSED.value
    processor.assert_called_once_with(os.path.realpath(video), None, 'move', False)
    processor.return_value.process.assert_called_once_with()


def test_disabled_unpacking_does_not_block_selected_video(create_file, monkeypatch):
    """An unrelated sibling archive does not prevent processing a selected video."""
    archive = create_file('downloads/other.show.rar')
    video = create_file('downloads/show.s01e02.mkv')
    processor = Mock(_output=[], **{'process.return_value': True})
    monkeypatch.setattr(app, 'UNPACK', False)
    monkeypatch.setattr(ProcessResult, 'already_postprocessed', Mock(return_value=False))
    monkeypatch.setattr('medusa.process_tv.post_processor.PostProcessor', Mock(return_value=processor))
    item = PostProcessQueueItem(path=video, process_method='copy', process_single_resource=True)

    result = item.process_path()

    assert os.path.isfile(archive)
    assert result.result is True
    assert result.postpone_any is False
    processor.process.assert_called_once_with()
