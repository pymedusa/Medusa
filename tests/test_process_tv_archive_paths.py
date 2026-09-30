# coding=utf-8
"""Regression tests for paths of extracted archive members."""
from __future__ import unicode_literals

import os

from medusa import app, helpers
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
            member = Mock(filename=filename, file_size=0)
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


@pytest.mark.parametrize('episode', ['episode.mkv', 'nested/episode.mkv'])
@pytest.mark.parametrize('artifact', [
    'RARBG.mp4',
    'nested/RARBG.mp4',
    'nested/RARBG.com.mp4',
    'nested/RARBG.to.avi',
    '__MACOSX/._episode.mkv',
    'sample/episode.mkv',
    'nested/Sample/episode.mkv',
    'nested/episode.sample.mkv',
])
def test_extracted_members_preserve_media_exclusions(
        archive_setup, create_file, monkeypatch, episode, artifact):
    """Ignore archive artifacts without flattening episodes or losing sample-path checks."""
    extracted_path = create_file('downloads/' + episode)
    create_file('downloads/' + artifact)
    sut, _, _ = archive_setup([episode, artifact])

    processor = Mock()
    processor.process.return_value = True
    processor._output = []
    artifact_processor = Mock()
    artifact_processor.process.return_value = False
    artifact_processor._output = []

    def get_processor(file_path, resource_name, process_method, is_priority):
        return processor if file_path == extracted_path else artifact_processor

    processor_class = Mock(side_effect=get_processor)
    monkeypatch.setattr('medusa.process_tv.post_processor.PostProcessor', processor_class)

    sut.prepare_files(sut.input_path, ['release.rar'], force=False)
    sut.process_files(sut.input_path)

    processor_class.assert_called_once_with(extracted_path, None, 'copy', None)
    processor.process.assert_called_once_with()
    artifact_processor.process.assert_not_called()
    assert sut.result is True
    assert sut.succeeded is True


@pytest.mark.parametrize('resource_name', [None, 'release.rar'])
def test_previously_processed_nested_archive_member_stays_skipped(archive_setup, monkeypatch, resource_name):
    """A skipped extraction must retain its basename-based media history check."""
    sut, archive, history_check = archive_setup(['nested/episode.mkv'])
    sut.resource_name = resource_name
    history_check.return_value = True
    processor_class = Mock()
    monkeypatch.setattr('medusa.process_tv.post_processor.PostProcessor', processor_class)

    sut.prepare_files(sut.input_path, ['release.rar'])
    sut.process_files(sut.input_path)

    archive.extractall.assert_not_called()
    processor_class.assert_not_called()
    assert history_check.call_args_list == [call('episode.mkv'), call('episode.mkv')]
    assert sut.result is True


@pytest.mark.parametrize('folder', ['@eaDir', '#recycle', '.@__thumb', '.hidden'])
@pytest.mark.parametrize('prefix', ['', 'nested/'])
def test_extracted_members_respect_ignored_ancestors(
        archive_setup, create_file, monkeypatch, folder, prefix):
    """Validate all extracted parent directories without rejecting ordinary episodes."""
    episode = 'season/episode.mkv'
    ignored_member = prefix + folder + '/other.mkv'
    episode_path = create_file('downloads/' + episode)
    create_file('downloads/' + ignored_member)
    sut, _, _ = archive_setup([episode, ignored_member])
    processor = Mock(_output=[], **{'process.return_value': True})
    processor_class = Mock(return_value=processor)
    monkeypatch.setattr('medusa.process_tv.post_processor.PostProcessor', processor_class)

    sut.prepare_files(sut.input_path, ['release.rar'])
    sut.process_files(sut.input_path)

    processor_class.assert_called_once_with(episode_path, None, 'copy', None)
    assert [video.name for video in sut.video_in_rar] == [os.path.join('season', 'episode.mkv')]
    assert sut.succeeded is True
    assert sut.result is True


@pytest.mark.parametrize('folder', ['@eaDir', '#recycle', '.@__thumb', '.hidden'])
@pytest.mark.parametrize('prefix', ['', 'nested/'])
def test_archive_directory_scan_does_not_rediscover_ignored_members(
        archive_setup, create_file, monkeypatch, folder, prefix):
    """Neither initial extraction nor later traversal may process ignored members."""
    episode = 'episode.mkv'
    ignored_member = prefix + folder + '/other.mkv'
    create_file('downloads/release.rar')
    sut, archive, _ = archive_setup([episode, ignored_member])
    monkeypatch.setattr(app, 'POSTPONE_IF_SYNC_FILES', False)
    monkeypatch.setattr(app, 'USE_FAILED_DOWNLOADS', False)
    monkeypatch.setattr(app, 'USE_TORRENTS', False)
    monkeypatch.setattr(app, 'KODI_LIBRARY_CLEAN_PENDING', False)

    def extractall(path):
        for filename in [episode, ignored_member]:
            create_file(os.path.join('downloads', filename))

    archive.extractall.side_effect = extractall
    processor = Mock(_output=[], **{'process.return_value': True})
    processor_class = Mock(return_value=processor)
    monkeypatch.setattr('medusa.process_tv.post_processor.PostProcessor', processor_class)

    sut.process(force=True, is_priority=True)

    archive.extractall.assert_called_once_with(path=sut.input_path)
    processor_class.assert_called_once_with(os.path.join(sut.input_path, episode), None, 'copy', True)
    assert sut.succeeded is True
    assert sut.result is True


@pytest.mark.parametrize('prefix', ['', 'nested/'])
def test_extracted_members_respect_filesystem_hidden_ancestors(
        archive_setup, create_file, monkeypatch, prefix):
    """Hidden Windows directories need not have dot-prefixed names."""
    episode_path = create_file('downloads/episode.mkv')
    hidden_folder = prefix + 'hidden-by-attribute'
    hidden_member = hidden_folder + '/child/other.mkv'
    create_file('downloads/' + hidden_member)
    sut, _, _ = archive_setup(['episode.mkv', hidden_member])
    hidden_path = os.path.normcase(os.path.join(sut.input_path, hidden_folder.replace('/', os.path.sep)))
    is_hidden_folder = helpers.is_hidden_folder

    def has_hidden_attribute(path):
        return os.path.normcase(path) == hidden_path or is_hidden_folder(path)

    monkeypatch.setattr(helpers, 'is_hidden_folder', has_hidden_attribute)
    processor = Mock(_output=[], **{'process.return_value': True})
    processor_class = Mock(return_value=processor)
    monkeypatch.setattr('medusa.process_tv.post_processor.PostProcessor', processor_class)

    sut.prepare_files(sut.input_path, ['release.rar'])
    sut.process_files(sut.input_path)

    processor_class.assert_called_once_with(episode_path, None, 'copy', None)
    assert sut.succeeded is True
    assert sut.result is True


@pytest.mark.parametrize('folder', ['@eaDirBackup', '#recycle-old', 'season.1'])
def test_extracted_members_do_not_reject_similar_folder_names(
        archive_setup, create_file, monkeypatch, folder):
    """Ignored folder matching remains exact, not a prefix or substring check."""
    member = folder + '/episode.mkv'
    extracted_path = create_file('downloads/' + member)
    sut, _, _ = archive_setup([member])
    processor = Mock(_output=[], **{'process.return_value': True})
    processor_class = Mock(return_value=processor)
    monkeypatch.setattr('medusa.process_tv.post_processor.PostProcessor', processor_class)

    sut.prepare_files(sut.input_path, ['release.rar'])
    sut.process_files(sut.input_path)

    processor_class.assert_called_once_with(extracted_path, None, 'copy', None)
    assert sut.succeeded is True
    assert sut.result is True
