# coding=utf-8
"""Regression tests for paths of extracted archive members."""
from __future__ import unicode_literals

import os

from medusa import app
from medusa.process_tv import ProcessResult

from mock.mock import Mock, call

import pytest


@pytest.fixture
def archive_setup(create_dir, monkeypatch):
    """Create a fake archive without requiring an external extraction program."""
    path = create_dir('downloads')
    sut = ProcessResult(path, process_method='copy', process_single_resource=True)
    history_check = Mock(return_value=False)
    monkeypatch.setattr(sut, 'already_postprocessed', history_check)
    monkeypatch.setattr(app, 'UNPACK', True)
    monkeypatch.setattr(app, 'POSTPONE_IF_NO_SUBS', False)
    monkeypatch.setattr(app, 'DELRARCONTENTS', False)

    def configure(filenames):
        members = []
        for filename in filenames:
            member = Mock(filename=filename)
            member.isdir.return_value = filename.endswith('/')
            members.append(member)
        archive = Mock()
        archive.needs_password.return_value = False
        archive.infolist.return_value = members
        monkeypatch.setattr('medusa.process_tv.RarFile', Mock(return_value=archive))
        return sut, archive, history_check

    return configure


@pytest.mark.parametrize('members,expected', [
    (['episode.mkv'], ['episode.mkv']),
    (['nested/', 'nested/episode.mkv'], [os.path.join('nested', 'episode.mkv')]),
    (['first/episode.mkv', 'second/episode.mkv'],
     [os.path.join('first', 'episode.mkv'), os.path.join('second', 'episode.mkv')]),
])
def test_unrar_preserves_member_paths(archive_setup, members, expected):
    """Preserve extracted subdirectories and distinct files with the same basename."""
    sut, archive, history_check = archive_setup(members)

    unpacked = sut.unrar(sut.input_path, ['release.rar'])

    assert unpacked == expected
    archive.extractall.assert_called_once_with(path=sut.input_path)
    assert history_check.call_args_list == [call(os.path.basename(filename)) for filename in expected]


@pytest.mark.parametrize('member,expected', [
    ('../episode.mkv', 'episode.mkv'),
    ('/nested/episode.mkv', os.path.join('nested', 'episode.mkv')),
    ('nested/../episode.mkv', os.path.join('nested', 'episode.mkv')),
])
def test_unrar_uses_safe_extraction_paths(archive_setup, member, expected):
    """Track sanitized extraction paths, never archive-supplied absolute or parent paths."""
    sut, archive, _ = archive_setup([member])

    assert sut.unrar(sut.input_path, ['release.rar']) == [expected]
    archive.extractall.assert_called_once_with(path=sut.input_path)


def test_unrar_checks_nested_extracted_file(archive_setup, create_file, monkeypatch):
    """Subtitle postponement checks the extracted member, not a flattened filename."""
    filename = os.path.join('nested', 'episode.mkv')
    create_file(os.path.join('downloads', filename))
    sut, archive, history_check = archive_setup(['nested/episode.mkv'])
    monkeypatch.setattr(app, 'POSTPONE_IF_NO_SUBS', True)

    assert sut.unrar(sut.input_path, ['release.rar']) == [filename]

    archive.extractall.assert_not_called()
    archive.testrar.assert_not_called()
    history_check.assert_called_once_with('episode.mkv')


@pytest.mark.parametrize('member', ['episode.mkv', 'nested/episode.mkv'])
def test_extracted_member_reaches_postprocessor(archive_setup, create_file, monkeypatch, member):
    """Pass the actual extracted path to processing while retaining basename history checks."""
    extracted_path = create_file('downloads/' + member)
    sut, _, history_check = archive_setup([member])
    processor = Mock()
    processor.process.return_value = True
    processor._output = []
    processor_class = Mock(return_value=processor)
    monkeypatch.setattr('medusa.process_tv.post_processor.PostProcessor', processor_class)

    sut.prepare_files(sut.input_path, ['release.rar'], force=False)
    sut.process_files(sut.input_path)

    processor_class.assert_called_once_with(extracted_path, None, 'copy', None)
    processor.process.assert_called_once_with()
    assert history_check.call_args_list == [call('episode.mkv'), call('episode.mkv')]
    assert sut.result is True
