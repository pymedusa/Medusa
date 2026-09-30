# coding=utf-8
"""Regression tests retaining extraction failures across successful media processing."""
from __future__ import unicode_literals

import os

from medusa import app
from medusa.process_tv import PostProcessQueueItem, ProcessResult
from medusa.schedulers.download_handler import ClientStatusEnum

from mock.mock import Mock

import pytest

from rarfile import BadRarFile


@pytest.mark.parametrize('outcome', ['password', 'testrar', 'extractall', 'success'])
@pytest.mark.parametrize('sibling_directory', ['', 'later'])
@pytest.mark.parametrize('use_failed_downloads,delete_failed', [(False, True), (True, False)])
def test_extraction_failure_survives_successful_sibling(
        create_file, monkeypatch, outcome, sibling_directory, use_failed_downloads, delete_failed):
    """Later success must not erase extraction failure or enable archive cleanup."""
    archive = create_file('downloads/release.rar')
    directory = os.path.dirname(archive)
    sibling = create_file(os.path.join('downloads', sibling_directory, 'show.name.s01e02.mkv'))
    member = Mock(filename='show.name.s01e01.mkv')
    member.isdir.return_value = False
    rar_handle = Mock()
    rar_handle.needs_password.return_value = outcome == 'password'
    rar_handle.infolist.return_value = [member]
    if outcome == 'testrar':
        rar_handle.testrar.side_effect = BadRarFile('archive verification failed')
    elif outcome == 'extractall':
        rar_handle.extractall.side_effect = RuntimeError('extractor failed unexpectedly')
    else:
        def extractall(path):
            assert path == directory
            create_file('downloads/' + member.filename)

        rar_handle.extractall.side_effect = extractall

    def get_processor(file_path, resource_name, process_method, is_priority):
        assert os.path.isfile(file_path)
        return Mock(_output=[], **{'process.return_value': True})

    processor_class = Mock(side_effect=get_processor)
    failed_processor = Mock(output='', **{'process.return_value': True})
    failed_processor_class = Mock(return_value=failed_processor)
    history_update = Mock()
    # Folder removal is outside this test; file cleanup remains real and fixture-scoped.
    delete_folder = Mock(return_value=False)
    monkeypatch.setattr('medusa.process_tv.RarFile', Mock(return_value=rar_handle))
    monkeypatch.setattr('medusa.process_tv.post_processor.PostProcessor', processor_class)
    monkeypatch.setattr('medusa.process_tv.failed_processor.FailedProcessor', failed_processor_class)
    monkeypatch.setattr(ProcessResult, 'already_postprocessed', Mock(return_value=False))
    monkeypatch.setattr(ProcessResult, 'delete_folder', delete_folder)
    monkeypatch.setattr(PostProcessQueueItem, 'update_resource', history_update)
    monkeypatch.setattr(app, 'UNPACK', True)
    monkeypatch.setattr(app, 'DELRARCONTENTS', False)
    monkeypatch.setattr(app, 'POSTPONE_IF_SYNC_FILES', False)
    monkeypatch.setattr(app, 'POSTPONE_IF_NO_SUBS', False)
    monkeypatch.setattr(app, 'USE_FAILED_DOWNLOADS', use_failed_downloads)
    monkeypatch.setattr(app, 'DELETE_FAILED', delete_failed)
    monkeypatch.setattr(app, 'NO_DELETE', False)
    item = PostProcessQueueItem(
        path=directory, info_hash='test-hash', process_method='move', process_single_resource=True
    )

    result = item.process_path()

    succeeded = outcome == 'success'
    processed_paths = [arguments[0][0] for arguments in processor_class.call_args_list]
    assert sibling in processed_paths
    assert len(processed_paths) == (2 if succeeded else 1)
    assert result.succeeded is succeeded
    assert item.success is succeeded
    assert result.skipped is False
    assert os.path.isfile(archive) is not succeeded
    history_update.assert_called_once()
    expected_status = ClientStatusEnum.COMPLETED if succeeded else ClientStatusEnum.FAILED
    assert history_update.call_args[0][0].status == expected_status.value | ClientStatusEnum.POSTPROCESSED.value
    if not succeeded and use_failed_downloads:
        failed_processor_class.assert_called_once_with(directory, None, [])
        failed_processor.process.assert_called_once_with()
    else:
        failed_processor_class.assert_not_called()
    if outcome == 'password':
        rar_handle.testrar.assert_not_called()
        rar_handle.extractall.assert_not_called()
    elif outcome == 'testrar':
        rar_handle.testrar.assert_called_once_with()
        rar_handle.extractall.assert_not_called()
    else:
        rar_handle.extractall.assert_called_once_with(path=directory)
