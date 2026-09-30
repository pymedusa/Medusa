# coding=utf-8
"""Do not reuse or import partially extracted archive members."""
from __future__ import unicode_literals

import os

from medusa.process_tv import ProcessResult

from mock.mock import Mock

import pytest


@pytest.fixture
def archive_retry(create_file, monkeypatch, app_config):
    """Use real fixture files while keeping archive and library operations controlled."""
    archive_path = create_file('release/episode.rar')
    root = os.path.dirname(archive_path)
    app_config('POSTPONE_IF_NO_SUBS', True)
    app_config('POSTPONE_IF_SYNC_FILES', False)
    app_config('UNPACK', True)
    app_config('DELRARCONTENTS', False)
    app_config('USE_TORRENTS', False)
    app_config('KODI_LIBRARY_CLEAN_PENDING', False)
    monkeypatch.setattr(ProcessResult, 'already_postprocessed', Mock(return_value=False))
    monkeypatch.setattr(ProcessResult, '_clean_up', Mock())
    monkeypatch.setattr(ProcessResult, 'process_failed', Mock())

    def configure(member_name='show.s01e01.mkv', size=16, existing=None, outcomes=None):
        member = Mock(filename=member_name, file_size=size, **{'isdir.return_value': False})
        member_path = os.path.join(root, member_name)
        if existing is not None:
            create_file(os.path.join('release', member_name), size=existing)
        archive = Mock(**{'needs_password.return_value': False, 'infolist.return_value': [member]})
        pending_outcomes = list(outcomes or ['success'])

        def extractall(path, members=None):
            assert path == root
            outcome = pending_outcomes.pop(0)
            if outcome == 'failure':
                create_file(os.path.join('release', member_name), size=size // 2)
                raise OSError('Simulated disk full during extraction')
            create_file(os.path.join('release', member_name), size=size)

        archive.extractall.side_effect = extractall
        monkeypatch.setattr('medusa.process_tv.RarFile', Mock(return_value=archive))
        imported = []

        def get_processor(path, *args):
            imported.append((path, os.path.getsize(path)))
            return Mock(_output=[], info_hash=None, **{'process.return_value': True})

        monkeypatch.setattr('medusa.process_tv.post_processor.PostProcessor', get_processor)
        return root, member_path, archive, imported

    return configure


@pytest.mark.parametrize('existing', [0, 8, 32])
@pytest.mark.parametrize('member_name', ['show.s01e01.mkv', 'Season 1/show.s01e01.mkv'])
@pytest.mark.parametrize('resource_name', [None, 'release.nzb'])
def test_retry_repairs_wrong_sized_member_before_import(archive_retry, existing, member_name, resource_name):
    """An existing pathname does not prove that extraction completed."""
    root, path, archive, imported = archive_retry(member_name, existing=existing)
    result = ProcessResult(root, process_method='copy')

    result.process(resource_name=resource_name)

    archive.extractall.assert_called_once()
    assert imported == [(os.path.normpath(path), 16)]
    assert result.succeeded is True


@pytest.mark.parametrize('size', [0, 16])
def test_complete_member_is_still_reused(archive_retry, size):
    """Correctly sized retained files do not need extraction again."""
    root, path, archive, imported = archive_retry(size=size, existing=size)

    ProcessResult(root, process_method='copy').process()

    archive.extractall.assert_not_called()
    assert imported == [(path, size)]


@pytest.mark.parametrize('member_name', ['show.s01e01.mkv', 'Season 1/show.s01e01.mkv'])
@pytest.mark.parametrize('resource_name', [None, 'release.nzb'])
def test_failed_extraction_is_repaired_on_fresh_retry(archive_retry, member_name, resource_name):
    """A failed extractor's partial output is not a reusable subtitle-retry file."""
    root, path, archive, imported = archive_retry(member_name, outcomes=['failure', 'success'])
    first = ProcessResult(root, process_method='copy')
    first.process(resource_name=resource_name)
    assert first.succeeded is False
    assert imported == []

    retry = ProcessResult(root, process_method='copy')
    retry.process(resource_name=resource_name)

    assert archive.extractall.call_count == 2
    assert imported == [(os.path.normpath(path), 16)]
    assert retry.succeeded is True


@pytest.mark.parametrize('member_name', ['show.s01e01.mkv', 'Season 1/show.s01e01.mkv'])
@pytest.mark.parametrize('resource_name', [None, 'release.nzb'])
def test_failed_repair_never_imports_partial_member(archive_retry, create_file, member_name, resource_name):
    """Keep bad members out of both the current batch and later directory discovery."""
    root, path, archive, imported = archive_retry(member_name, existing=8, outcomes=['failure'])
    independent = create_file('release/other.s01e02.mkv', size=24)
    result = ProcessResult(root, process_method='copy')

    result.process(resource_name=resource_name)

    archive.extractall.assert_called_once()
    assert imported == [(independent, 24)]
    assert os.path.getsize(path) == 8
    assert result.succeeded is False


def test_unreadable_member_size_is_not_assumed_complete(archive_retry, monkeypatch):
    """A failed stat must retry extraction, not silently reuse an unchecked file."""
    root, path, archive, _ = archive_retry(existing=8)
    original_getsize = os.path.getsize
    calls = []

    def getsize(filename):
        if filename == path and not calls:
            calls.append(filename)
            raise PermissionError('Simulated stat error')
        return original_getsize(filename)

    monkeypatch.setattr('medusa.process_tv.os.path.getsize', getsize)

    ProcessResult(root, process_method='copy').unrar(root, ['episode.rar'])

    archive.extractall.assert_called_once()
