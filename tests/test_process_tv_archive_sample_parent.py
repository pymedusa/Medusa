# coding=utf-8
"""Regression tests for archive media filtering against its extraction directory."""
from __future__ import unicode_literals

import os

from medusa import app
from medusa.process_tv import ProcessResult

from mock.mock import Mock

import pytest


@pytest.mark.parametrize('direct_archive', [False, True])
@pytest.mark.parametrize('parent,member,processable', [
    ('Sample', 'Show.S01E01.mkv', False),
    (os.path.join('season', 'Sample'), 'Show.S01E01.mkv', False),
    ('season', 'Sample/Show.S01E01.mkv', False),
    ('season', 'Show.S01E01.mkv', True),
])
def test_archive_respects_parent_and_member_media_exclusions(
        create_file, create_dir, monkeypatch, direct_archive, parent, member, processable):
    """An extracted file has the same media eligibility as a loose file at that path."""
    root = create_dir('downloads')
    archive_path = create_file(os.path.join('downloads', parent, 'release.rar'))
    extracted_path = os.path.join(os.path.dirname(archive_path), member.replace('/', os.path.sep))
    monkeypatch.setattr(app, 'UNPACK', True)
    monkeypatch.setattr(app, 'DELRARCONTENTS', False)
    monkeypatch.setattr(app, 'POSTPONE_IF_NO_SUBS', False)
    monkeypatch.setattr(app, 'POSTPONE_IF_SYNC_FILES', False)
    monkeypatch.setattr(app, 'USE_FAILED_DOWNLOADS', False)
    monkeypatch.setattr(app, 'USE_TORRENTS', False)
    monkeypatch.setattr(app, 'KODI_LIBRARY_CLEAN_PENDING', False)

    archive = Mock()
    archive.needs_password.return_value = False
    archive.infolist.return_value = [Mock(filename=member, **{'isdir.return_value': False})]
    archive.extractall.side_effect = lambda path: create_file(os.path.join('downloads', parent, member))
    monkeypatch.setattr('medusa.process_tv.RarFile', Mock(return_value=archive))
    processor = Mock(_output=[], **{'process.return_value': True})
    processor_class = Mock(return_value=processor)
    monkeypatch.setattr('medusa.process_tv.post_processor.PostProcessor', processor_class)
    monkeypatch.setattr(ProcessResult, '_clean_up', Mock())
    monkeypatch.setattr(ProcessResult, 'delete_files', Mock())
    result = ProcessResult(archive_path if direct_archive else root, process_method='copy')

    result.process(force=True)

    archive.extractall.assert_called_once_with(path=os.path.dirname(archive_path))
    assert result._is_media_file(extracted_path) is processable
    if processable:
        processor_class.assert_called_once_with(extracted_path, None, 'copy', None)
    else:
        processor_class.assert_not_called()
    assert os.path.isfile(archive_path)
    assert os.path.isfile(extracted_path)
