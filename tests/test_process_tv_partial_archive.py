# coding=utf-8
"""Regression tests for archives with only some members already handled."""
from __future__ import unicode_literals

import os

from medusa import app
from medusa.process_tv import ProcessResult

from mock.mock import Mock

import pytest

from rarfile import sanitize_filename


@pytest.fixture
def partial_archive_setup(create_file, create_dir, monkeypatch):
    """Materialize fake archive members and reject processing of missing files."""
    archive_path = create_file('downloads/release.rar')
    path = os.path.dirname(archive_path)
    monkeypatch.setattr(app, 'UNPACK', True)
    monkeypatch.setattr(app, 'POSTPONE_IF_NO_SUBS', False)
    monkeypatch.setattr(app, 'DELRARCONTENTS', False)

    def configure(members, processed=(), extracted=(), postpone=False):
        monkeypatch.setattr(app, 'POSTPONE_IF_NO_SUBS', postpone)
        for member in extracted:
            create_file(os.path.join('downloads', member))

        archive = Mock()
        archive.needs_password.return_value = False
        archive_members = [
            Mock(filename=member, file_size=0, **{'isdir.return_value': member.endswith('/')}) for member in members
        ]
        archive.infolist.return_value = archive_members

        def extractall(path, members=None):
            for member in archive_members if members is None else members:
                filename = sanitize_filename(member.filename, os.path.sep, os.name == 'nt')
                if member.isdir():
                    create_dir(os.path.join('downloads', filename))
                else:
                    create_file(os.path.join('downloads', filename))

        archive.extractall.side_effect = extractall
        monkeypatch.setattr('medusa.process_tv.RarFile', Mock(return_value=archive))

        def get_processor(file_path, resource_name, process_method, is_priority):
            assert os.path.isfile(file_path), 'Archive member was not extracted: {0}'.format(file_path)
            return Mock(_output=[], **{'process.return_value': True})

        processor_class = Mock(side_effect=get_processor)
        monkeypatch.setattr('medusa.process_tv.post_processor.PostProcessor', processor_class)
        sut = ProcessResult(path, process_method='copy')
        monkeypatch.setattr(sut, 'already_postprocessed', Mock(side_effect=lambda name: name in processed))
        return sut, archive, processor_class

    return configure


@pytest.mark.parametrize('processed', ['Show.S01E01.mkv', 'Show.S01E02.mkv'])
def test_partially_processed_archive_extracts_remaining_episode(partial_archive_setup, processed):
    """One historical member must not prevent extraction of an unprocessed episode."""
    members = ['Season 1/Show.S01E01.mkv', 'Season 1/Show.S01E02.mkv']
    sut, archive, processor_class = partial_archive_setup(members, processed=[processed])

    sut.prepare_files(sut.input_path, ['release.rar'])
    sut.process_files(sut.input_path)

    remaining = next(member for member in members if os.path.basename(member) != processed)
    archive.extractall.assert_called_once_with(
        path=sut.input_path,
        members=[member for member in archive.infolist.return_value
                 if os.path.basename(member.filename) != processed])
    processor_class.assert_called_once_with(
        os.path.join(sut.input_path, remaining.replace('/', os.path.sep)), None, 'copy', None)
    assert sut.result is True
    assert sut.succeeded is True


@pytest.mark.parametrize('force', [False, True])
def test_all_historical_archive_members_respect_force(partial_archive_setup, force):
    """An entirely processed archive is skipped unless processing is forced."""
    members = ['Show.S01E01.mkv', 'Show.S01E02.mkv']
    sut, archive, processor_class = partial_archive_setup(members, processed=members)

    sut.prepare_files(sut.input_path, ['release.rar'], force=force)
    sut.process_files(sut.input_path, force=force)

    if force:
        archive.extractall.assert_called_once_with(path=sut.input_path)
        assert sorted(call.args[0] for call in processor_class.call_args_list) == [
            os.path.join(sut.input_path, member) for member in members
        ]
    else:
        archive.extractall.assert_not_called()
        archive.testrar.assert_not_called()
        processor_class.assert_not_called()
    assert sut.result is True


@pytest.mark.parametrize('extracted', ['Season 1/Show.S01E01.mkv', 'Season 1/Show.S01E02.mkv'])
def test_partial_existing_extraction_does_not_hide_missing_episode(partial_archive_setup, extracted):
    """Subtitle postponement can reuse existing members only when none are missing."""
    members = ['Season 1/Show.S01E01.mkv', 'Season 1/Show.S01E02.mkv']
    sut, archive, processor_class = partial_archive_setup(members, extracted=[extracted], postpone=True)

    sut.prepare_files(sut.input_path, ['release.rar'])
    sut.process_files(sut.input_path)

    archive.extractall.assert_called_once_with(
        path=sut.input_path,
        members=[member for member in archive.infolist.return_value if member.filename != extracted])
    assert sorted(call.args[0] for call in processor_class.call_args_list) == [
        os.path.join(sut.input_path, member.replace('/', os.path.sep)) for member in members
    ]
    assert sut.succeeded is True


@pytest.mark.parametrize('force', [False, True])
def test_complete_existing_extraction_is_reused(partial_archive_setup, force):
    """Keep the existing subtitle-retry behavior, including when history is forced."""
    members = ['Show.S01E01.mkv', 'Show.S01E02.mkv']
    sut, archive, processor_class = partial_archive_setup(members, extracted=members, postpone=True)

    sut.prepare_files(sut.input_path, ['release.rar'], force=force)
    sut.process_files(sut.input_path, force=force)

    archive.extractall.assert_not_called()
    archive.testrar.assert_not_called()
    assert processor_class.call_count == 2
    assert sut.succeeded is True


def test_historical_and_existing_members_can_jointly_skip_extraction(partial_archive_setup):
    """A processed episode and an extracted pending episode need no re-extraction."""
    members = ['Show.S01E01.mkv', 'Show.S01E02.mkv']
    sut, archive, processor_class = partial_archive_setup(
        members, processed=members[:1], extracted=members[1:], postpone=True)

    sut.prepare_files(sut.input_path, ['release.rar'])
    sut.process_files(sut.input_path)

    archive.extractall.assert_not_called()
    processor_class.assert_called_once_with(os.path.join(sut.input_path, members[1]), None, 'copy', None)
    assert sut.succeeded is True


@pytest.mark.parametrize('metadata', ['release.nfo', 'Show.S01E01.en.srt'])
def test_existing_metadata_does_not_hide_missing_episodes(partial_archive_setup, metadata):
    """Existing metadata must not be mistaken for a complete archive extraction."""
    members = [metadata, 'Show.S01E01.mkv', 'Show.S01E02.mkv']
    sut, archive, processor_class = partial_archive_setup(members, extracted=[metadata], postpone=True)

    sut.prepare_files(sut.input_path, ['release.rar'])
    sut.process_files(sut.input_path)

    archive.extractall.assert_called_once_with(path=sut.input_path, members=archive.infolist.return_value[1:])
    assert sorted(call.args[0] for call in processor_class.call_args_list) == [
        os.path.join(sut.input_path, member) for member in members[1:]
    ]
    assert sut.succeeded is True


@pytest.mark.parametrize('preserved', ['Show.S01E01.mkv', 'Show.S01E02.en.srt'])
def test_subtitle_retry_preserves_existing_members(partial_archive_setup, create_file, preserved):
    """Extract missing members without overwriting previously retained media or subtitles."""
    members = [preserved, 'Show.S01E02.mkv']
    sut, archive, processor_class = partial_archive_setup(members, extracted=[preserved], postpone=True)
    preserved_path = create_file(os.path.join('downloads', preserved), lines=[b'Retained member contents'])
    archive.infolist.return_value[0].file_size = os.path.getsize(preserved_path)

    sut.prepare_files(sut.input_path, ['release.rar'])
    sut.process_files(sut.input_path)

    archive.extractall.assert_called_once_with(path=sut.input_path, members=archive.infolist.return_value[1:])
    assert os.path.isfile(os.path.join(sut.input_path, members[1]))
    with open(preserved_path, 'rb') as member_file:
        assert member_file.read() == b'Retained member contents'
    assert processor_class.call_count == (2 if preserved.endswith('.mkv') else 1)
    assert sut.succeeded is True


def test_partial_history_preserves_existing_processed_member(partial_archive_setup, create_file):
    """A historical member is neither re-extracted nor processed with its missing sibling."""
    members = ['Show.S01E01.mkv', 'Show.S01E02.mkv']
    sut, archive, processor_class = partial_archive_setup(members, processed=members[:1], extracted=members[:1])
    preserved_path = create_file(os.path.join('downloads', members[0]), lines=[b'Already processed contents'])

    sut.prepare_files(sut.input_path, ['release.rar'])
    sut.process_files(sut.input_path)

    archive.extractall.assert_called_once_with(path=sut.input_path, members=archive.infolist.return_value[1:])
    processor_class.assert_called_once_with(os.path.join(sut.input_path, members[1]), None, 'copy', None)
    with open(preserved_path, 'rb') as member_file:
        assert member_file.read() == b'Already processed contents'
    assert sut.succeeded is True


@pytest.mark.parametrize('members', [[], ['Season 1/']])
def test_archives_without_file_members_still_use_default_extraction(partial_archive_setup, members):
    """Do not suppress archive validation or directory extraction for an empty file list."""
    sut, archive, processor_class = partial_archive_setup(members)

    assert sut.unrar(sut.input_path, ['release.rar']) == []

    archive.testrar.assert_called_once_with()
    archive.extractall.assert_called_once_with(path=sut.input_path)
    processor_class.assert_not_called()
    if members:
        assert os.path.isdir(os.path.join(sut.input_path, 'Season 1'))


def test_partial_extraction_uses_original_members_and_sanitized_paths(partial_archive_setup, create_file):
    """Keep original archive entries for extraction but match existing safe destination paths."""
    members = ['nested/../Show.S01E01.mkv', '../Show.S01E02.mkv']
    preserved = os.path.join('nested', 'Show.S01E01.mkv')
    sut, archive, processor_class = partial_archive_setup(members, extracted=[preserved], postpone=True)
    preserved_path = create_file(os.path.join('downloads', preserved), lines=[b'Retained member contents'])
    archive.infolist.return_value[0].file_size = os.path.getsize(preserved_path)

    sut.prepare_files(sut.input_path, ['release.rar'])
    sut.process_files(sut.input_path)

    archive.extractall.assert_called_once_with(path=sut.input_path, members=archive.infolist.return_value[1:])
    assert sorted(call.args[0] for call in processor_class.call_args_list) == sorted([
        preserved_path, os.path.join(sut.input_path, 'Show.S01E02.mkv')
    ])
    with open(preserved_path, 'rb') as member_file:
        assert member_file.read() == b'Retained member contents'
    assert sut.succeeded is True
