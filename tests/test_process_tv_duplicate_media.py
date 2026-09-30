# coding=utf-8
"""Regression tests for retained archive media encountered again during traversal."""
from __future__ import unicode_literals

import os

from medusa import app
from medusa.helper.exceptions import (
    EpisodePostProcessingAbortException,
    EpisodePostProcessingFailedException,
    EpisodePostProcessingPostponedException,
)
from medusa.process_tv import MediaFile, ProcessResult

from mock.mock import Mock, call

import pytest


@pytest.fixture
def retained_archive_setup(create_file, monkeypatch):
    """Extract real retained files so the directory scan can encounter them again."""
    archive_path = create_file('downloads/release.rar')
    path = os.path.dirname(archive_path)
    monkeypatch.setattr(app, 'UNPACK', True)
    monkeypatch.setattr(app, 'DELRARCONTENTS', False)
    monkeypatch.setattr(app, 'POSTPONE_IF_SYNC_FILES', False)
    monkeypatch.setattr(app, 'POSTPONE_IF_NO_SUBS', False)
    monkeypatch.setattr(app, 'USE_FAILED_DOWNLOADS', False)
    monkeypatch.setattr(app, 'USE_TORRENTS', False)
    monkeypatch.setattr(app, 'KODI_LIBRARY_CLEAN_PENDING', False)

    def configure(filenames):
        members = []
        for filename in filenames:
            member = Mock(filename=filename)
            member.isdir.return_value = False
            members.append(member)
        archive = Mock()
        archive.needs_password.return_value = False
        archive.infolist.return_value = members

        def extractall(path):
            for filename in filenames:
                create_file(os.path.join('downloads', filename))

        archive.extractall.side_effect = extractall
        monkeypatch.setattr('medusa.process_tv.RarFile', Mock(return_value=archive))
        processor = Mock(_output=[], **{'process.return_value': True})
        processor_class = Mock(return_value=processor)
        monkeypatch.setattr('medusa.process_tv.post_processor.PostProcessor', processor_class)
        sut = ProcessResult(path, process_method='copy')
        return sut, archive, processor_class, processor

    return configure


@pytest.mark.parametrize('filenames', [
    ['nested/episode.mkv'],
    ['first/episode.mkv', 'second/episode.mkv'],
])
def test_retained_archive_media_processed_once_per_path(retained_archive_setup, filenames):
    """Forced processing must not repeat archive members or conflate matching basenames."""
    sut, archive, processor_class, processor = retained_archive_setup(filenames)

    sut.process(force=True, is_priority=True)

    expected_paths = [os.path.join(sut.input_path, filename.replace('/', os.path.sep)) for filename in filenames]
    archive.extractall.assert_called_once_with(path=sut.input_path)
    assert sorted(item.args[0] for item in processor_class.call_args_list) == sorted(expected_paths)
    assert processor.process.call_count == len(expected_paths)
    assert all(os.path.isfile(path) for path in expected_paths)
    assert sut.result is True
    assert sut.succeeded is True


def test_retained_archive_media_can_be_processed_in_a_later_run(retained_archive_setup):
    """Remembering successful paths is limited to one call, even when reusing the result."""
    sut, archive, processor_class, processor = retained_archive_setup(['nested/episode.mkv'])

    sut.process(force=True, is_priority=True)
    sut.process(force=True, is_priority=True)

    file_path = os.path.join(sut.input_path, 'nested', 'episode.mkv')
    assert processor_class.call_args_list == [call(file_path, None, 'copy', True)] * 2
    assert processor.process.call_count == 2
    assert archive.extractall.call_count == 2
    assert os.path.isfile(file_path)


@pytest.mark.parametrize('first_result,succeeded', [
    (False, False),
    (EpisodePostProcessingFailedException('Failed'), False),
    (EpisodePostProcessingPostponedException('Postponed'), True),
    (EpisodePostProcessingAbortException('Aborted'), True),
])
def test_unsuccessful_archive_media_remains_eligible_for_processing(retained_archive_setup, first_result, succeeded):
    """An incomplete first attempt must not mark a retained file as successfully processed."""
    sut, _, processor_class, processor = retained_archive_setup(['nested/episode.mkv'])
    processor.process.side_effect = [first_result, True]

    sut.process(force=True, is_priority=True)

    file_path = os.path.join(sut.input_path, 'nested', 'episode.mkv')
    assert processor_class.call_args_list == [call(file_path, None, 'copy', True)] * 2
    assert processor.process.call_count == 2
    assert os.path.isfile(file_path)
    assert sut.succeeded is succeeded


@pytest.mark.parametrize('parent,filename', [
    ('nested', 'episode.mkv'),
    ('', os.path.join('nested', os.pardir, 'nested', 'episode.mkv')),
    ('', None),
])
def test_equivalent_media_paths_are_processed_once(retained_archive_setup, parent, filename):
    """Equivalent parent/name combinations identify one successfully processed media path."""
    sut, archive, processor_class, processor = retained_archive_setup(['nested/episode.mkv'])
    archive.extractall(path=sut.input_path)
    file_path = os.path.join(sut.input_path, 'nested', 'episode.mkv')

    original_media = MediaFile(os.path.join('nested', 'episode.mkv'), 'episode.mkv')
    equivalent_media = MediaFile(filename or file_path, 'episode.mkv')
    sut.process_media(sut.input_path, [original_media], force=True, is_priority=True)
    sut.process_media(os.path.join(sut.input_path, parent), [equivalent_media], force=True, is_priority=True)

    processor_class.assert_called_once_with(file_path, None, 'copy', True)
    processor.process.assert_called_once_with()
