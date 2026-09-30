# coding=utf-8
"""Tests for resolving post-processing requests without changing their scope."""
from __future__ import unicode_literals

import os

from medusa.process_tv import ProcessResult

from mock.mock import Mock

import pytest


@pytest.mark.parametrize('extension', ['mkv', 'rar'])
@pytest.mark.parametrize('absolute_resource', [False, True])
def test_selected_nested_file_keeps_request_directory(
        create_file, create_dir, extension, absolute_resource):
    """Selecting a nested file must preserve its extraction and cleanup directory."""
    root = os.path.realpath(create_dir('downloads'))
    filename = os.path.join('release', 'episode.' + extension)
    selected = os.path.realpath(create_file(os.path.join('downloads', filename)))
    create_file('downloads/unrelated.mkv')
    resource = selected if absolute_resource else filename
    result = ProcessResult(root)
    result.resource_name = resource

    target = result._resolve_target(result.input_path)

    assert target.path == root
    assert target.directory == root
    assert target.filename == resource
    assert target.file_path == selected
    assert list(result._get_files(target)) == [(root, [resource])]
    assert result.resource_name == resource


@pytest.mark.parametrize('resource_kind', ['none', 'nzb', 'absolute_file'])
def test_direct_file_takes_precedence_over_release_metadata(create_file, resource_kind):
    """Release metadata neither replaces the direct file nor changes its scan root."""
    selected = os.path.realpath(create_file('downloads/episode.mkv'))
    sibling = os.path.realpath(create_file('downloads/unrelated.mkv'))
    resource = {'none': None, 'nzb': 'original.release.nzb', 'absolute_file': sibling}[resource_kind]
    result = ProcessResult(selected)
    result.resource_name = resource

    target = result._resolve_target(result.input_path)

    assert target.path == selected
    assert target.directory == os.path.dirname(selected)
    assert target.filename == os.path.basename(selected)
    assert target.file_path == selected
    assert list(result._get_files(target)) == [(os.path.dirname(selected), [os.path.basename(selected)])]
    assert result.resource_name == resource


@pytest.mark.parametrize('resource', ['release', 'release.nzb'])
def test_selected_directory_is_walked_bottom_up(create_file, create_dir, resource):
    """An existing child directory takes precedence over NZB metadata handling."""
    root = os.path.realpath(create_dir('downloads'))
    selected = os.path.realpath(create_dir(os.path.join('downloads', resource)))
    create_file(os.path.join('downloads', resource, 'root.mkv'))
    create_file(os.path.join('downloads', resource, 'nested', 'z.mkv'))
    create_file(os.path.join('downloads', resource, 'nested', 'a.mkv'))
    create_file(os.path.join('downloads', resource, 'nested', 'deeper', 'deep.mkv'))
    create_file('downloads/unrelated.mkv')
    result = ProcessResult(root)
    result.resource_name = resource

    target = result._resolve_target(result.input_path)

    assert target.path == root
    assert target.directory == selected
    assert target.filename is None
    assert target.file_path is None
    assert list(result._get_files(target)) == [
        (os.path.join(selected, 'nested', 'deeper'), ['deep.mkv']),
        (os.path.join(selected, 'nested'), ['a.mkv', 'z.mkv']),
        (selected, ['root.mkv']),
    ]
    assert result.resource_name == resource


@pytest.mark.parametrize('resource', [None, 'release', 'release.nzb'])
def test_root_directory_target_traversal_matches_scope(create_file, create_dir, resource):
    """Broad scans defer children to paths; a named release includes them directly."""
    root = os.path.realpath(create_dir('downloads/release'))
    create_file('downloads/release/z.mkv')
    create_file('downloads/release/a.mkv')
    create_file('downloads/release/nested/other.mkv')
    result = ProcessResult(root)
    result.resource_name = resource

    target = result._resolve_target(result.input_path)

    assert target.path == root
    assert target.directory == root
    assert target.filename is None
    assert target.file_path is None
    expected = [(root, ['a.mkv', 'z.mkv'])]
    if resource:
        expected.insert(0, (os.path.join(root, 'nested'), ['other.mkv']))
    assert list(result._get_files(target)) == expected


def test_nzb_file_is_metadata_when_supplied_as_resource(create_file, create_dir):
    """An existing NZB file must not replace the requested directory's media selection."""
    root = os.path.realpath(create_dir('downloads'))
    create_file('downloads/release.nzb')
    create_file('downloads/episode.mkv')
    result = ProcessResult(root)
    result.resource_name = 'release.nzb'

    target = result._resolve_target(result.input_path)

    assert target.directory == root
    assert target.filename is None
    assert target.file_path is None
    assert list(result._get_files(target)) == [(root, ['episode.mkv', 'release.nzb'])]


def test_existing_child_directory_precedes_repeated_root_name(create_file, create_dir):
    """When both root and child match the resource, the existing child remains selected."""
    root = os.path.realpath(create_dir('downloads/release'))
    selected = os.path.realpath(create_dir('downloads/release/release'))
    create_file('downloads/release/unrelated.mkv')
    create_file('downloads/release/release/episode.mkv')
    result = ProcessResult(root)
    result.resource_name = 'release'

    target = result._resolve_target(result.input_path)

    assert target.directory == selected
    assert target.filename is None
    assert list(result._get_files(target)) == [(selected, ['episode.mkv'])]


def test_matching_root_and_contained_file_names_keep_directory_selection(create_file, create_dir):
    """A matching root name retains folder traversal even if it also names a contained file."""
    root = os.path.realpath(create_dir('downloads/episode.mkv'))
    create_file('downloads/episode.mkv/episode.mkv')
    create_file('downloads/episode.mkv/sibling.mkv')
    result = ProcessResult(root)
    result.resource_name = 'episode.mkv'

    target = result._resolve_target(result.input_path)

    assert target.path == root
    assert target.directory == root
    assert target.filename is None
    assert target.file_path is None
    assert list(result._get_files(target)) == [(root, ['episode.mkv', 'sibling.mkv'])]


@pytest.mark.parametrize('marker,failed', [('_FAILED_other', True), ('_UNPACK_other', False)])
def test_matching_root_and_file_names_validate_the_directory(
        create_file, create_dir, monkeypatch, app_config, marker, failed):
    """Directory traversal must not inherit the narrower contained-file validation scope."""
    root = os.path.realpath(create_dir('downloads/episode.mkv'))
    selected = create_file('downloads/episode.mkv/episode.mkv')
    sibling = create_file('downloads/episode.mkv/sibling.mkv')
    create_dir(os.path.join('downloads', 'episode.mkv', marker))
    processor_class = Mock()
    monkeypatch.setattr('medusa.process_tv.post_processor.PostProcessor', processor_class)
    app_config('POSTPONE_IF_NO_SUBS', False)
    app_config('POSTPONE_IF_SYNC_FILES', False)
    app_config('KODI_LIBRARY_CLEAN_PENDING', False)
    app_config('USE_TORRENTS', False)
    result = ProcessResult(root, process_method='copy')

    result.process(resource_name='episode.mkv')

    processor_class.assert_not_called()
    assert result.result is False
    assert result.failed is failed
    assert result.postpone_any is not failed
    assert result.skipped is False
    assert os.path.isfile(selected)
    assert os.path.isfile(sibling)


@pytest.mark.parametrize('resource', ['missing.mkv', 'missing.NZB'])
def test_missing_resource_does_not_select_unrelated_media(create_file, create_dir, resource):
    """A missing selection is not a request to scan the containing directory."""
    root = os.path.realpath(create_dir('downloads'))
    create_file('downloads/unrelated.mkv')
    result = ProcessResult(root)
    result.resource_name = resource

    target = result._resolve_target(result.input_path)

    assert target.path == root
    assert target.directory is None
    assert target.filename is None
    assert target.file_path is None
    assert list(result._get_files(target)) == []


def test_root_children_are_discovered_after_root_processing(create_file, create_dir):
    """Traversal must discover folders created while processing an archive in the root."""
    root = os.path.realpath(create_dir('downloads'))
    result = ProcessResult(root)
    paths = iter(result.paths)

    assert next(paths) == root
    create_file('downloads/extracted/episode.mkv')

    assert list(paths) == [os.path.join(root, 'extracted')]
