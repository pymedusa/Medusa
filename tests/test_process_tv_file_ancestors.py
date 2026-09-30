# coding=utf-8
"""Tests for bounded ancestor validation of directly selected media files."""
from __future__ import unicode_literals

import ntpath
import os
import posixpath

from medusa.process_tv import PostProcessQueueItem, ProcessResult
from medusa.schedulers.download_handler import ClientStatusEnum

from mock.mock import Mock

import pytest


@pytest.fixture
def ancestor_processor(monkeypatch, app_config):
    """Keep validation real while replacing processing, cleanup and history effects."""
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


@pytest.mark.parametrize('marker,failed', [
    ('_UNPACK_release', False), ('_unpack_release', False),
    ('_FAILED_release', True), ('_UNDERSIZED_release', True),
    ('@eaDir', False), ('.hidden', False),
])
@pytest.mark.parametrize('nested', ['Season 1', os.path.join('Season 1', 'Episode 1')])
def test_direct_file_checks_ancestors_inside_download_root(
        create_file, create_dir, app_config, ancestor_processor, marker, failed, nested):
    """A direct file cannot bypass an enclosing release's staging or ignored state."""
    root = os.path.realpath(create_dir('downloads'))
    path = create_file(os.path.join('downloads', marker, nested, 'show.name.s01e01.mkv'))
    app_config('TV_DOWNLOAD_DIR', root)
    processor_class, failure_handler, history_update = ancestor_processor
    item = PostProcessQueueItem(
        path=path, process_method='copy', info_hash='download-id', process_single_resource=True
    )

    result = item.process_path()

    processor_class.assert_not_called()
    assert result.result is False
    assert result.failed is failed
    assert os.path.isfile(path)
    if failed:
        failure_handler.assert_called_once_with(path)
        history_update.assert_called_once()
        assert history_update.call_args[0][0].status == (
            ClientStatusEnum.FAILED.value | ClientStatusEnum.POSTPROCESSED.value
        )
    else:
        failure_handler.assert_not_called()
        history_update.assert_not_called()


@pytest.mark.parametrize('ancestor', ['ordinary', '.hidden', '_UNPACK_other', '_FAILED_other'])
def test_direct_file_does_not_validate_above_download_root(
        create_file, create_dir, app_config, ancestor_processor, ancestor):
    """An explicitly configured download root bounds checks of direct-file parents."""
    relative_root = os.path.join(ancestor, 'downloads')
    root = os.path.realpath(create_dir(relative_root))
    path = create_file(os.path.join(relative_root, 'release', 'Season 1', 'show.name.s01e01.mkv'))
    app_config('TV_DOWNLOAD_DIR', root)
    processor_class, failure_handler, history_update = ancestor_processor

    result = PostProcessQueueItem(
        path=path, process_method='copy', info_hash='download-id', process_single_resource=True
    ).process_path()

    processor_class.assert_called_once_with(os.path.realpath(path), None, 'copy', False)
    failure_handler.assert_not_called()
    history_update.assert_called_once()
    assert result.result is True
    assert result.failed is False
    assert os.path.isfile(path)


@pytest.mark.parametrize('configured_root', ['unset', 'elsewhere', 'prefix_sibling'])
@pytest.mark.parametrize('immediate_parent', [False, True])
def test_direct_file_outside_download_root_retains_immediate_parent_scope(
        create_file, create_dir, app_config, ancestor_processor, configured_root, immediate_parent):
    """Without a containing root, do not expand validation to unrelated ancestors."""
    root = os.path.realpath(create_dir('downloads'))
    selected_root = 'downloads-other' if configured_root == 'prefix_sibling' else 'elsewhere'
    relative = os.path.join(selected_root, '_UNPACK_release')
    if not immediate_parent:
        relative = os.path.join(relative, 'Season 1')
    path = create_file(os.path.join(relative, 'show.name.s01e01.mkv'))
    app_config('TV_DOWNLOAD_DIR', '' if configured_root == 'unset' else root)
    processor_class, failure_handler, history_update = ancestor_processor

    result = PostProcessQueueItem(
        path=path, process_method='copy', info_hash='download-id', process_single_resource=True
    ).process_path()

    if immediate_parent:
        processor_class.assert_not_called()
        history_update.assert_not_called()
        assert result.result is False
    else:
        processor_class.assert_called_once_with(os.path.realpath(path), None, 'copy', False)
        history_update.assert_called_once()
        assert result.result is True
    failure_handler.assert_not_called()
    assert result.failed is False
    assert os.path.isfile(path)


@pytest.mark.parametrize('resource', [None, 'show.name.s01e01.mkv'])
def test_explicit_directory_keeps_its_own_validation_boundary(
        create_file, create_dir, app_config, ancestor_processor, resource):
    """A configured download root must not expand an explicit directory selection."""
    root = os.path.realpath(create_dir('downloads'))
    selected = os.path.realpath(create_dir('downloads/_UNPACK_release/selected'))
    path = create_file('downloads/_UNPACK_release/selected/show.name.s01e01.mkv')
    app_config('TV_DOWNLOAD_DIR', root)
    processor_class, failure_handler, history_update = ancestor_processor

    result = PostProcessQueueItem(
        path=selected, resource_name=resource, process_method='copy',
        info_hash='download-id', process_single_resource=True
    ).process_path()

    processor_class.assert_called_once_with(os.path.realpath(path), resource, 'copy', False)
    failure_handler.assert_not_called()
    history_update.assert_called_once()
    assert result.result is True
    assert result.failed is False
    assert os.path.isfile(path)


@pytest.mark.parametrize('sibling', ['_FAILED_other', '_UNPACK_other', '@eaDir', '.hidden'])
def test_direct_file_ancestor_validation_does_not_scan_siblings(
        create_file, create_dir, app_config, ancestor_processor, sibling):
    """Checking ancestor names must not validate other downloads in those folders."""
    root = os.path.realpath(create_dir('downloads'))
    path = create_file('downloads/release/Season 1/show.name.s01e01.mkv')
    other = create_file(os.path.join('downloads', 'release', sibling, 'other.show.s01e01.mkv'))
    app_config('TV_DOWNLOAD_DIR', root)
    processor_class, failure_handler, history_update = ancestor_processor

    result = PostProcessQueueItem(
        path=path, process_method='copy', info_hash='download-id', process_single_resource=True
    ).process_path()

    processor_class.assert_called_once_with(os.path.realpath(path), None, 'copy', False)
    failure_handler.assert_not_called()
    history_update.assert_called_once()
    assert result.result is True
    assert result.failed is False
    assert os.path.isfile(other)


@pytest.mark.parametrize('path_module,download_root,resource,validation_root,expected', [
    (ntpath, r'C:\Downloads', r'c:\downloads\_UNPACK_release\inner\show.mkv',
     r'c:\downloads', False),
    (ntpath, 'C:\\', r'c:\_FAILED_release\inner\show.mkv', 'c:\\', False),
    (ntpath, r'\\Server\Share', r'\\server\share\_UNPACK_release\inner\show.mkv',
     '\\\\server\\share\\', False),
    (ntpath, '\\\\Server\\Share\\', r'\\server\share\_UNPACK_release\inner\show.mkv',
     '\\\\server\\share\\', False),
    (ntpath, r'D:\Downloads', r'C:\_UNPACK_release\inner\show.mkv',
     r'c:\_unpack_release\inner', True),
    (ntpath, r'\\Server\Other', r'\\Server\Share\_UNPACK_release\inner\show.mkv',
     r'\\server\share\_unpack_release\inner', True),
    (ntpath, r'C:\Downloads', r'c:\downloads-other\_UNPACK_release\inner\show.mkv',
     r'c:\downloads-other\_unpack_release\inner', True),
    (posixpath, '/Downloads', '/downloads/_UNPACK_release/inner/show.mkv',
     '/downloads/_UNPACK_release/inner', True),
    (posixpath, '/downloads/_UNPACK_release', '/downloads/_UNPACK_release/inner/show.mkv',
     '/downloads/_UNPACK_release', False),
])
def test_direct_file_validation_root_respects_platform_path_boundaries(
        create_dir, monkeypatch, app_config, path_module, download_root, resource, validation_root, expected):
    """Containment is case-aware, supports UNC roots and does not cross drive boundaries."""
    result = ProcessResult(create_dir('downloads'))
    result.input_path = resource
    result._original_file_path = resource
    # Bypass the public setter, which creates a real configured directory.
    app_config('_TV_DOWNLOAD_DIR', download_root)
    visited = []

    def bounded_dirname(path):
        assert len(visited) < 20, 'Parent-directory walk did not terminate'
        visited.append(path)
        return path_module.dirname(path)

    path_functions = Mock(wraps=path_module)
    path_functions.isfile.side_effect = lambda filename: filename == resource
    # These synthetic roots need normalization, not filesystem or network lookups.
    path_functions.realpath.side_effect = path_module.normpath
    path_functions.dirname.side_effect = bounded_dirname
    monkeypatch.setattr('medusa.process_tv.os', Mock(path=path_functions, curdir='.'))
    monkeypatch.setattr('medusa.process_tv.helpers.is_hidden_folder', Mock(return_value=False))

    assert result._get_validation_root(resource) == validation_root
    assert result.should_process(resource, resource) is expected
