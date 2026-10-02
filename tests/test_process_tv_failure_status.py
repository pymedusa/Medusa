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
