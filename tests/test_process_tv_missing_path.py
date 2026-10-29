# coding=utf-8
"""Regression tests for post-processing unavailable download paths."""
from __future__ import unicode_literals

import os

from medusa import app
from medusa.process_tv import PostProcessQueueItem
from medusa.schedulers.download_handler import ClientStatusEnum

from mock.mock import Mock

import pytest


@pytest.mark.parametrize('path_state', ['missing', 'inaccessible', 'missing_mapped_path'])
@pytest.mark.parametrize('failed', [False, True])
def test_unavailable_path_preserves_download_status(tmpdir, create_dir, monkeypatch, path_state, failed):
    """Only a download explicitly reported as failed should be finalized without its path."""
    path = str(tmpdir.join('unavailable-release'))
    monkeypatch.setattr(app, 'TV_DOWNLOAD_DIR', '')
    monkeypatch.setattr(app, 'USE_FAILED_DOWNLOADS', True)
    monkeypatch.setattr(app, 'DELETE_FAILED', False)
    if path_state == 'inaccessible':
        path = create_dir('unavailable-release')
        isdir = os.path.isdir
        monkeypatch.setattr(os.path, 'isdir', lambda value: False if value == path else isdir(value))
    elif path_state == 'missing_mapped_path':
        monkeypatch.setattr(app, 'TV_DOWNLOAD_DIR', create_dir('local-downloads'))

    processor_class = Mock()
    failed_processor = Mock(output='', **{'process.return_value': True})
    failed_processor_class = Mock(return_value=failed_processor)
    history_update = Mock()
    monkeypatch.setattr('medusa.process_tv.post_processor.PostProcessor', processor_class)
    monkeypatch.setattr('medusa.process_tv.failed_processor.FailedProcessor', failed_processor_class)
    monkeypatch.setattr(PostProcessQueueItem, 'update_resource', history_update)
    item = PostProcessQueueItem(
        path=path, resource_name='show.name.s01e01.mkv', info_hash='test-hash',
        process_method='copy', process_single_resource=True, failed=failed
    )

    result = item.process_path()

    processor_class.assert_not_called()
    assert result.failed is failed
    assert result.skipped is not failed
    assert 'Post-processing completed.' not in result.output
    if failed:
        failed_processor_class.assert_called_once_with(path, item.resource_name, [])
        failed_processor.process.assert_called_once_with()
        history_update.assert_called_once()
        assert history_update.call_args[0][0].status == ClientStatusEnum.FAILED.value | ClientStatusEnum.POSTPROCESSED.value
    else:
        assert result.result is False
        failed_processor_class.assert_not_called()
        history_update.assert_not_called()
