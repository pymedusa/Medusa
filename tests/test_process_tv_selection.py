# coding=utf-8
"""Tests for validating the resource selected for post-processing."""
from __future__ import unicode_literals

import ntpath
import os
import posixpath

from medusa.process_tv import PostProcessQueueItem, ProcessResult

from mock.mock import Mock

import pytest


@pytest.fixture
def selected_file_processor(monkeypatch):
    """Keep validation real while avoiding media lookup and processing side effects."""
    processor_class = Mock(return_value=Mock(_output=[], **{'process.return_value': True}))
    failed_handler = Mock()
    monkeypatch.setattr('medusa.process_tv.post_processor.PostProcessor', processor_class)
    monkeypatch.setattr(ProcessResult, 'already_postprocessed', Mock(return_value=False))
    monkeypatch.setattr(ProcessResult, 'process_failed', failed_handler)
    return processor_class, failed_handler


@pytest.mark.parametrize('sibling_name', ['_FAILED_other', '_UNPACK_other', '_unpack_other'])
@pytest.mark.parametrize('nested', [False, True])
def test_selected_file_ignores_unrelated_folders(create_file, selected_file_processor, sibling_name, nested):
    """Other downloads must not fail or block a specifically selected file."""
    resource_name = os.path.join('release', 'show.name.s01e01.mkv') if nested else 'show.name.s01e01.mkv'
    path = create_file(os.path.join('downloads', resource_name))
    sibling = create_file(os.path.join('downloads', sibling_name, 'other.show.s01e01.mkv'))
    process_path = os.path.dirname(os.path.dirname(sibling))
    processor_class, failed_handler = selected_file_processor
    item = PostProcessQueueItem(
        path=process_path, resource_name=resource_name, process_method='copy', process_single_resource=True
    )

    result = item.process_path()

    processor_class.assert_called_once_with(os.path.realpath(path), resource_name, 'copy', False)
    failed_handler.assert_not_called()
    assert result.result is True
    assert result.failed is False
    assert os.path.isfile(sibling)


@pytest.mark.parametrize('selection', ['relative', 'absolute', 'direct'])
@pytest.mark.parametrize('filename,processable', [
    ('RARBG.mp4', False),
    ('RARBG.to.avi', False),
    ('._episode.mkv', False),
    ('show.name.s01e01.mkv', True),
])
def test_selected_file_respects_media_exclusions(
        create_file, selected_file_processor, monkeypatch, app_config, selection, filename, processable):
    """A sole selected artifact stays skipped without failed handling or history changes."""
    resource_name = os.path.join('nested', filename)
    path = create_file(os.path.join('downloads', resource_name))
    process_path = path if selection == 'direct' else os.path.dirname(os.path.dirname(path))
    if selection != 'relative':
        resource_name = path if selection == 'absolute' else None
    processor_class, failed_handler = selected_file_processor
    history_update = Mock()
    monkeypatch.setattr(PostProcessQueueItem, 'update_resource', history_update)
    app_config('POSTPONE_IF_SYNC_FILES', False)
    app_config('POSTPONE_IF_NO_SUBS', False)
    item = PostProcessQueueItem(
        path=process_path, resource_name=resource_name, info_hash='download-id',
        process_method='copy', process_single_resource=True
    )

    result = item.process_path()

    if processable:
        processor_class.assert_called_once_with(os.path.realpath(path), resource_name, 'copy', False)
        history_update.assert_called_once()
    else:
        processor_class.assert_not_called()
        history_update.assert_not_called()
    failed_handler.assert_not_called()
    assert result.result is processable
    assert result.skipped is not processable
    assert result.succeeded is True
    assert result.failed is False
    assert os.path.isfile(path)


@pytest.mark.parametrize('selection', ['relative', 'absolute', 'direct'])
def test_selected_archive_remains_processable(create_file, selection):
    """Media filename exclusions must not reject a valid selected RAR archive."""
    path = create_file(os.path.join('downloads', 'nested', 'release.rar'))
    process_path = path if selection == 'direct' else os.path.dirname(os.path.dirname(path))
    sut = ProcessResult(process_path)
    if selection == 'relative':
        sut.resource_name = os.path.join('nested', 'release.rar')
    elif selection == 'absolute':
        sut.resource_name = path

    assert sut.should_process(sut.input_path, sut._resolve_target(sut.input_path).file_path) is True


@pytest.mark.parametrize('folder_name,failed', [
    ('_UNPACK_release', False), ('_unpack_release', False),
    ('_FAILED_release', True), ('_UNDERSIZED_release', True),
    ('@eaDir', False), ('.hidden', False),
])
@pytest.mark.parametrize('nested', [False, True])
def test_nested_resource_respects_folder_state(create_file, selected_file_processor, folder_name, failed, nested):
    """A nested resource must respect both its parent and intermediate folders."""
    parts = [folder_name, 'inner', 'show.name.s01e01.mkv'] if nested else [folder_name, 'show.name.s01e01.mkv']
    resource_name = os.path.join(*parts)
    path = create_file(os.path.join('downloads', resource_name))
    process_path = path
    for _ in parts:
        process_path = os.path.dirname(process_path)
    processor_class, failed_handler = selected_file_processor
    item = PostProcessQueueItem(
        path=process_path, resource_name=resource_name, process_method='copy', process_single_resource=True
    )

    result = item.process_path()

    processor_class.assert_not_called()
    assert result.result is False
    assert result.failed is failed
    assert os.path.isfile(path)
    if failed:
        failed_handler.assert_called_once_with(process_path)
    else:
        failed_handler.assert_not_called()


@pytest.mark.parametrize('folder_name,failed', [
    ('_UNPACK_release', False), ('_unpack_release', False),
    ('_FAILED_release', True), ('_UNDERSIZED_release', True),
    ('@eaDir', False), ('.hidden', False),
])
def test_nested_resource_respects_input_folder(create_file, selected_file_processor, folder_name, failed):
    """Validating the selected file must not bypass the input folder's own state."""
    resource_name = os.path.join('inner', 'show.name.s01e01.mkv')
    path = create_file(os.path.join(folder_name, resource_name))
    process_path = os.path.dirname(os.path.dirname(path))
    processor_class, failed_handler = selected_file_processor
    item = PostProcessQueueItem(
        path=process_path, resource_name=resource_name, process_method='copy', process_single_resource=True
    )

    result = item.process_path()

    processor_class.assert_not_called()
    assert result.result is False
    assert result.failed is failed
    assert os.path.isfile(path)
    if failed:
        failed_handler.assert_called_once_with(process_path)
    else:
        failed_handler.assert_not_called()


@pytest.mark.parametrize('path_module,root,resource,parents,expected', [
    (ntpath, r'C:\Downloads', r'c:\downloads\show.mkv', [], True),
    (ntpath, r'C:\Downloads', r'c:\downloads\Season 01\show.mkv', [r'c:\downloads\Season 01'], True),
    (ntpath, 'C:\\', r'c:\Season 01\show.mkv', [r'c:\Season 01'], True),
    (ntpath, r'\\Server\Share\Downloads', r'\\server\share\downloads\Season 01\show.mkv',
     [r'\\server\share\downloads\Season 01'], True),
    (ntpath, r'\\Server\Share', r'\\server\share\show.mkv', [], True),
    (ntpath, r'\\Server\Share', r'\\server\share\Season 01\show.mkv',
     [r'\\server\share\Season 01'], True),
    (ntpath, r'\\Server\Share', r'\\server\share\_UNPACK_release\inner\show.mkv',
     [r'\\server\share\_UNPACK_release\inner', r'\\server\share\_UNPACK_release'], False),
    (ntpath, '\\\\Server\\Share\\', r'\\server\share\_UNPACK_release\inner\show.mkv',
     [r'\\server\share\_UNPACK_release\inner', r'\\server\share\_UNPACK_release'], False),
    (ntpath, r'\\Server\Share', r'\\server\share\_FAILED_release\inner\show.mkv',
     [r'\\server\share\_FAILED_release\inner', r'\\server\share\_FAILED_release'], False),
    (ntpath, '\\\\Server\\Share\\', r'\\server\share\_FAILED_release\inner\show.mkv',
     [r'\\server\share\_FAILED_release\inner', r'\\server\share\_FAILED_release'], False),
    (ntpath, r'C:\Downloads', r'c:\downloads\_UNPACK_release\inner\show.mkv',
     [r'c:\downloads\_UNPACK_release\inner', r'c:\downloads\_UNPACK_release'], False),
    (ntpath, r'C:\Downloads', r'D:\Downloads\show.mkv', [], True),
    (posixpath, '/Downloads', '/downloads/Season 01/show.mkv', [], True),
])
def test_selected_file_parent_walk_uses_platform_case_rules(
        create_dir, monkeypatch, path_module, root, resource, parents, expected):
    """Stop at differently cased Windows roots without changing POSIX path comparisons."""
    sut = ProcessResult(create_dir('downloads'))
    visited = []

    def bounded_dirname(path):
        # Fail promptly if the regression returns, rather than hanging the test runner.
        assert len(visited) < 10, 'Parent-directory walk did not terminate'
        visited.append(path)
        return path_module.dirname(path)

    path_functions = Mock(wraps=path_module)
    path_functions.isfile.side_effect = lambda filename: filename == resource
    path_functions.dirname.side_effect = bounded_dirname
    monkeypatch.setattr('medusa.process_tv.os', Mock(path=path_functions, curdir='.'))
    monkeypatch.setattr('medusa.process_tv.helpers.is_hidden_folder', Mock(return_value=False))

    assert sut.should_process(root, resource) is expected
    assert visited == [resource] + parents
