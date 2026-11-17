# coding=utf-8
"""Tests for medusa/process_tv.py."""
from __future__ import unicode_literals
import os

from medusa import app
from medusa.post_processor import PostProcessor
from medusa.process_tv import PostProcessQueueItem, ProcessResult
from medusa.schedulers.download_handler import ClientStatusEnum

from mock.mock import Mock

import pytest


@pytest.mark.parametrize('p', [
    {
        'path': 'media/postprocess/',
        'resource_name': None,
        'failed': False,
        'expected': True,
        'structure': (
            'bow.514.hdtv-lol[ettv].mkv',
            'bow.514.hdtv-lol.srt',
            {'samples': (
                'sample.mkv', 'other.mkv',
                {'inception': ()}
            )}
        )
    },
    {
        'path': 'media/postprocess/',
        'resource_name': None,
        'failed': False,
        'expected': True,
        'structure': (
            'bow.514.hdtv-lol[ettv].mkv',
            {'samples': (
                'sample.mkv', 'other.mkv',
                {'inception': (
                    'cool.txt', 'bla.nfo'
                )}
            )}
        )
    },
    {
        'path': 'media/postprocess/',
        'resource_name': None,
        'failed': False,
        'expected': False,
        'structure': (
            'bow.514.hdtv-lol.srt',
        )
    },
])
def test_should_process(p, create_structure):
    """Run the test."""
    # Given
    test_path = create_structure(p['path'], structure=p['structure'])
    path = os.path.join(test_path, os.path.normcase(p['path']))
    sut = ProcessResult(path, failed=p['failed'])

    # When
    result = sut.should_process(path)

    # Then
    assert p['expected'] == result


def test_should_process_single_file(create_structure):
    """A video file passed as the processing path itself should be processed.

    Torrent clients hand the content path of a single-file torrent straight to
    post-processing, so the path is the video file and not a folder.
    """
    # Given
    structure = ('show.name.s01e01.720p.webrip.x264-group.mkv',)
    test_path = create_structure('media/postprocess', structure=structure)
    path = os.path.join(test_path, os.path.normcase('media/postprocess'),
                        'show.name.s01e01.720p.webrip.x264-group.mkv')
    sut = ProcessResult(path)

    # When
    result = sut.should_process(path)

    # Then
    assert result is True


def test_should_not_process_single_non_media_file(create_structure):
    """A non-media file passed as the processing path itself should not be processed."""
    # Given
    structure = ('show.name.s01e01.720p.webrip.x264-group.nfo',)
    test_path = create_structure('media/postprocess', structure=structure)
    path = os.path.join(test_path, os.path.normcase('media/postprocess'),
                        'show.name.s01e01.720p.webrip.x264-group.nfo')
    sut = ProcessResult(path)

    # When
    result = sut.should_process(path)

    # Then
    assert result is False


def test_process_reports_no_items_without_failing_download(create_structure):
    """An empty scan is neither a completed post-process nor a failed download."""
    # Given
    structure = ('show.name.s01e01.720p.webrip.x264-group.srt',)
    test_path = create_structure('media/postprocess', structure=structure)
    path = os.path.join(test_path, os.path.normcase('media/postprocess'))
    sut = ProcessResult(path)

    # When
    sut.process()

    # Then
    assert sut.result is False
    assert sut.succeeded is True
    assert 'No processable items found.' in sut.output
    assert 'Post-processing completed.' not in sut.output
    assert 'Problem(s) during processing' not in sut.output


@pytest.mark.parametrize('with_resource', [False, True])
@pytest.mark.parametrize('extension', ['mkv', 'rar'])
def test_get_files_direct_file(create_file, with_resource, extension):
    """Resolve a direct file without walking it or appending its name twice."""
    path = create_file('show.name.s01e01.' + extension)
    sut = ProcessResult(path)
    sut.resource_name = os.path.basename(path) if with_resource else None

    assert list(sut._get_files(sut.input_path)) == [
        (os.path.dirname(sut.input_path), [os.path.basename(path)])
    ]


@pytest.mark.parametrize('input_form', ['file', 'file_and_resource', 'directory_and_resource'])
@pytest.mark.parametrize('proc_type,delete_on', [('auto', False), ('manual', False), ('manual', True)])
def test_process_single_video_respects_cleanup(create_file, monkeypatch, input_form, proc_type, delete_on):
    """Process the selected file while retaining the existing manual deletion behavior."""
    path = create_file('downloads/show.name.s01e01.mkv')
    sibling = create_file('downloads/other.show.s01e01.mkv')
    resource = os.path.basename(path) if input_form != 'file' else None
    process_path = os.path.dirname(path) if input_form == 'directory_and_resource' else path
    processor = Mock()
    processor.process.return_value = True
    processor._output = []
    processor_class = Mock(return_value=processor)
    failed_handler = Mock()
    monkeypatch.setattr('medusa.process_tv.post_processor.PostProcessor', processor_class)
    monkeypatch.setattr(ProcessResult, 'already_postprocessed', Mock(return_value=False))
    monkeypatch.setattr(ProcessResult, 'process_failed', failed_handler)
    monkeypatch.setattr(app, 'NO_DELETE', False)
    item = PostProcessQueueItem(
        path=process_path, resource_name=resource, process_method='move',
        proc_type=proc_type, delete_on=delete_on, process_single_resource=True
    )

    result = item.process_path()

    processor_class.assert_called_once_with(os.path.realpath(path), resource, 'move', False)
    processor.process.assert_called_once_with()
    failed_handler.assert_not_called()
    assert result.result is True
    assert result.succeeded is True
    assert os.path.isfile(sibling) is not delete_on
    assert os.path.isdir(os.path.dirname(path)) is not delete_on


@pytest.mark.parametrize('input_form', ['file', 'file_and_resource', 'directory_and_resource'])
@pytest.mark.parametrize('folder_name,failed', [
    ('_UNPACK_release', False), ('_unpack_release', False),
    ('_FAILED_release', True), ('_UNDERSIZED_release', True),
    ('@eaDir', False), ('.hidden', False),
])
def test_single_file_respects_parent_folder(create_file, monkeypatch, input_form, folder_name, failed):
    """Selecting a file must not bypass validation of its containing folder."""
    path = create_file(folder_name + '/show.name.s01e01.mkv')
    resource = os.path.basename(path) if input_form != 'file' else None
    process_path = os.path.dirname(path) if input_form == 'directory_and_resource' else path
    processor_class = Mock()
    failed_handler = Mock()
    monkeypatch.setattr('medusa.process_tv.post_processor.PostProcessor', processor_class)
    monkeypatch.setattr(ProcessResult, 'process_failed', failed_handler)
    item = PostProcessQueueItem(path=process_path, resource_name=resource, process_method='copy', process_single_resource=True)

    result = item.process_path()

    processor_class.assert_not_called()
    assert result.result is False
    assert result.failed is failed
    assert os.path.isfile(path)
    if failed:
        failed_handler.assert_called_once_with(process_path)
    else:
        failed_handler.assert_not_called()


@pytest.mark.parametrize('folder_name', ['_UNPACK_show.name.s01e01', '_unpack_show.name.s01e01', '@eaDir', 'empty'])
def test_skipped_folder_does_not_trigger_failed_download(create_dir, monkeypatch, folder_name):
    """Unpacking, ignored and empty folders must not trigger failed download handling."""
    path = create_dir(folder_name)
    failed_handler = Mock()
    history_update = Mock()
    monkeypatch.setattr(ProcessResult, 'process_failed', failed_handler)
    monkeypatch.setattr(PostProcessQueueItem, 'update_resource', history_update)
    item = PostProcessQueueItem(path=path, info_hash='test-hash', process_method='copy', process_single_resource=True)

    result = item.process_path()

    failed_handler.assert_not_called()
    history_update.assert_not_called()
    assert result.result is False
    assert result.skipped is True


@pytest.mark.parametrize('folder_name', ['_FAILED_show.name.s01e01', '_UNDERSIZED_show.name.s01e01'])
def test_failed_folder_still_triggers_failed_download(create_dir, monkeypatch, folder_name):
    """Preserve failure handling for folders explicitly marked as failed downloads."""
    path = create_dir(folder_name)
    failed_handler = Mock()
    history_update = Mock()
    monkeypatch.setattr(ProcessResult, 'process_failed', failed_handler)
    monkeypatch.setattr(PostProcessQueueItem, 'update_resource', history_update)
    item = PostProcessQueueItem(path=path, info_hash='test-hash', process_method='copy', process_single_resource=True)

    result = item.process_path()

    failed_handler.assert_called_once_with(path)
    assert result.failed is True
    assert result.skipped is False
    history_update.assert_called_once()
    assert history_update.call_args[0][0].status == ClientStatusEnum.FAILED.value | ClientStatusEnum.POSTPROCESSED.value


@pytest.mark.parametrize('extension,processed,expected', [
    ('mkv', True, ClientStatusEnum.COMPLETED),
    ('mkv', False, ClientStatusEnum.FAILED),
    ('exe', False, ClientStatusEnum.FAILED),
])
def test_processing_outcomes_still_update_history(create_file, monkeypatch, extension, processed, expected):
    """Keep success and real failures distinct from deliberately skipped input."""
    path = create_file('show.name.s01e01.' + extension)
    processor = Mock(_output=[], **{'process.return_value': processed})
    history_update = Mock()
    monkeypatch.setattr('medusa.process_tv.post_processor.PostProcessor', Mock(return_value=processor))
    monkeypatch.setattr(ProcessResult, 'already_postprocessed', Mock(return_value=False))
    monkeypatch.setattr(ProcessResult, 'process_failed', Mock())
    monkeypatch.setattr(PostProcessQueueItem, 'update_resource', history_update)
    item = PostProcessQueueItem(path=path, info_hash='test-hash', process_method='copy', process_single_resource=True)

    result = item.process_path()

    assert result.skipped is False
    history_update.assert_called_once()
    assert history_update.call_args[0][0].status == expected.value | ClientStatusEnum.POSTPROCESSED.value


def test_failed_archive_still_updates_history(create_file, monkeypatch):
    """An attempted but failed extraction is not an empty or skipped scan."""
    path = create_file('show.name.s01e01.rar')
    history_update = Mock()
    monkeypatch.setattr(app, 'UNPACK', True)
    monkeypatch.setattr('medusa.process_tv.RarFile', Mock(side_effect=ValueError('Rar requires a password')))
    monkeypatch.setattr(PostProcessQueueItem, 'update_resource', history_update)
    item = PostProcessQueueItem(path=path, info_hash='test-hash', process_method='copy', process_single_resource=True)

    result = item.process_path()

    assert result.result is False
    assert result.skipped is False
    history_update.assert_called_once()
    assert history_update.call_args[0][0].status == ClientStatusEnum.FAILED.value | ClientStatusEnum.POSTPROCESSED.value


@pytest.mark.parametrize('input_form', [
    'directory', 'file', 'file_and_resource', 'directory_and_resource', 'directory_and_nested_resource'
])
@pytest.mark.parametrize('marker', ['.syncthing.show.tmp', 'transfer.part'])
def test_sync_files_still_postpone_processing(create_file, monkeypatch, input_form, marker):
    """Check sibling sync markers even when only one file was selected."""
    download_dir = 'downloads/release' if input_form == 'directory_and_nested_resource' else 'downloads'
    path = create_file(download_dir + '/show.name.s01e01.mkv')
    create_file(download_dir + '/' + marker)
    resource = os.path.basename(path) if input_form.endswith('and_resource') else None
    process_path = path if input_form in ('file', 'file_and_resource') else os.path.dirname(path)
    if input_form == 'directory_and_nested_resource':
        resource = os.path.join('release', os.path.basename(path))
        process_path = os.path.dirname(process_path)
    failed_handler = Mock()
    processor_class = Mock(return_value=Mock(_output=[], **{'process.return_value': True}))
    history_update = Mock()
    monkeypatch.setattr(ProcessResult, 'process_failed', failed_handler)
    monkeypatch.setattr(ProcessResult, 'already_postprocessed', Mock(return_value=False))
    monkeypatch.setattr('medusa.process_tv.post_processor.PostProcessor', processor_class)
    monkeypatch.setattr(PostProcessQueueItem, 'update_resource', history_update)
    monkeypatch.setattr(app, 'POSTPONE_IF_SYNC_FILES', True)
    item = PostProcessQueueItem(
        path=process_path, info_hash='test-hash', resource_name=resource,
        process_method='copy', process_single_resource=True
    )

    result = item.process_path()

    failed_handler.assert_not_called()
    processor_class.assert_not_called()
    history_update.assert_not_called()
    assert result.postpone_processing is True
    assert result.postpone_any is True
    assert result.result is False
    assert result.succeeded is True
    assert 'No processable items found.' not in result.output


def test_single_file_sync_scan_can_be_disabled(create_file, monkeypatch):
    """Disabling the sync guard avoids scanning the selected file's parent."""
    path = create_file('downloads/show.name.s01e01.mkv')
    create_file('downloads/transfer.part')
    resource = os.path.basename(path)
    processor_class = Mock(return_value=Mock(_output=[], **{'process.return_value': True}))
    scan = Mock(wraps=os.scandir)
    monkeypatch.setattr(os, 'scandir', scan)
    monkeypatch.setattr(app, 'POSTPONE_IF_SYNC_FILES', False)
    monkeypatch.setattr(ProcessResult, 'already_postprocessed', Mock(return_value=False))
    monkeypatch.setattr('medusa.process_tv.post_processor.PostProcessor', processor_class)
    item = PostProcessQueueItem(path=path, resource_name=resource, process_method='copy', process_single_resource=True)

    result = item.process_path()

    scan.assert_not_called()
    processor_class.assert_called_once_with(os.path.realpath(path), resource, 'copy', False)
    assert result.result is True
    assert result.postpone_any is False


def test_single_file_sync_scan_ignores_directories(create_file, create_dir, monkeypatch):
    """Sync-named directories and markers in unrelated subfolders do not postpone a file."""
    path = create_file('downloads/show.name.s01e01.mkv')
    create_dir('downloads/transfer.part')
    create_file('downloads/other/.syncthing.show.tmp')
    resource = os.path.basename(path)
    processor_class = Mock(return_value=Mock(_output=[], **{'process.return_value': True}))
    monkeypatch.setattr(app, 'POSTPONE_IF_SYNC_FILES', True)
    monkeypatch.setattr(ProcessResult, 'already_postprocessed', Mock(return_value=False))
    monkeypatch.setattr('medusa.process_tv.post_processor.PostProcessor', processor_class)
    item = PostProcessQueueItem(path=path, resource_name=resource, process_method='copy', process_single_resource=True)

    result = item.process_path()

    processor_class.assert_called_once_with(os.path.realpath(path), resource, 'copy', False)
    assert result.result is True
    assert result.postpone_any is False


def test_single_file_sync_scan_error_postpones_processing(create_file, monkeypatch):
    """An unreadable parent must not bypass the sync guard or finalize history."""
    path = create_file('downloads/show.name.s01e01.mkv')
    processor_class = Mock(return_value=Mock(_output=[], **{'process.return_value': True}))
    failed_handler = Mock()
    history_update = Mock()
    monkeypatch.setattr(os, 'scandir', Mock(side_effect=OSError('access denied')))
    monkeypatch.setattr(app, 'POSTPONE_IF_SYNC_FILES', True)
    monkeypatch.setattr(ProcessResult, 'already_postprocessed', Mock(return_value=False))
    monkeypatch.setattr(ProcessResult, 'process_failed', failed_handler)
    monkeypatch.setattr(PostProcessQueueItem, 'update_resource', history_update)
    monkeypatch.setattr('medusa.process_tv.post_processor.PostProcessor', processor_class)
    item = PostProcessQueueItem(
        path=path, resource_name=os.path.basename(path), info_hash='test-hash',
        process_method='copy', process_single_resource=True
    )

    result = item.process_path()

    processor_class.assert_not_called()
    failed_handler.assert_not_called()
    history_update.assert_not_called()
    assert result.postpone_processing is True
    assert result.postpone_any is True
    assert 'Unable to check temporary sync files' in result.output
    assert 'Found temporary sync files' not in result.output


@pytest.mark.parametrize('p', [
    {   # resource_name is a folder
        'path': 'media/postprocess/Show.Name.S01E03.720p.WEBRip.x264-SKGTV',
        'resource_name': 'Show.Name.S01E03.720p.WEBRip.x264-SKGTV',
        'failed': False,
        'expected': 'media/postprocess/Show.Name.S01E03.720p.WEBRip.x264-SKGTV',
        'structure': (
            'show.name.103.720p.webrip.x264-skgtv.mkv',
            {'other': (
                'readme.txt', 'sample.mkv',
            )}
        )
    },
    {   # resource_name is a file
        'path': 'media/postprocess',
        'resource_name': 'show.name.s01e01.show.title.1080p.webrip.x264-kovalski.mkv',
        'failed': False,
        'expected': 'media/postprocess',
        'structure': (
            'show.name.s01e01.show.title.1080p.webrip.x264-kovalski.mkv',
            'readme.txt',
            {'samples': (
                'sample.mkv', 'other.mkv',
            )}
        )
    },
    {   # resource_name is an NZB file
        'path': 'media/postprocess',
        'resource_name': 'show.name.s02e01.show.title.1080p.webrip.x264-kovalski.nzb',
        'failed': False,
        'expected': 'media/postprocess',
        'structure': (
            'show.name.s02e01.show.title.1080p.webrip.x264-kovalski.mkv',
            'sample.mkv',
            {'readme': (
                'readme.txt',
            )}
        )
    },
])
def test_paths(monkeypatch, p, create_structure):
    """Run the test."""
    # Given
    test_path = create_structure(p['path'], structure=p['structure'])
    path = os.path.join(test_path, os.path.normcase(p['path']))
    sut = ProcessResult(path)
    monkeypatch.setattr(sut, 'resource_name', p['resource_name'])

    # When
    result = sut.paths

    # Then
    for result_path in result:
        assert os.path.join(test_path, os.path.normcase(p['expected'])).lower() == result_path.lower()


@pytest.mark.parametrize('p', [
    {   # resource_name is a folder
        'path': 'media/postprocess/Show.Name.S01E03.HDTV.x264-LOL',
        'resource_name': 'Show.Name.S01E03.HDTV.x264-LOL',
        'failed': False,
        'expected': [('media/postprocess/Show.Name.S01E03.HDTV.x264-LOL',
                      ['show.name.103.hdtv.x264-lol.mkv']),
                     ('media/postprocess/Show.Name.S01E03.HDTV.x264-LOL/other',
                      ['readme.txt', 'sample.mkv'])
                     ],
        'structure': (
            'show.name.103.hdtv.x264-lol.mkv',
            {'other': (
                'readme.txt', 'sample.mkv',
            )}
        )
    },
    {   # resource_name is a file
        'path': 'media/postprocess',
        'resource_name': 'show.name.s01e01.webrip.x264-group.mkv',
        'failed': False,
        'expected': [('media/postprocess', ['show.name.s01e01.webrip.x264-group.mkv'])],
        'structure': (
            'show.name.s01e01.webrip.x264-group.mkv',
            'unrelated.video.file.mkv'
            'readme.txt',
            {'samples': (
                'sample.mkv', 'other.mkv',
            )}
        )
    },
    {   # resource_name is an NZB file
        'path': 'media/postprocess',
        'resource_name': 'show.name.s02e01.webrip.x264-kovalski.nzb',
        'failed': False,
        'expected': [('media/postprocess',
                      ['sample.mkv', 'show.name.s02e01.webrip.x264-kovalski.mkv']),
                     ('media/postprocess/subfolder', ['readme.txt'])
                     ],
        'structure': (
            'sample.mkv',
            'show.name.s02e01.webrip.x264-kovalski.mkv',
            {'subfolder': (
                'readme.txt',
            )}
        )
    },
])
def test__get_files(monkeypatch, p, create_structure):
    """Run the test."""
    # Given
    test_path = create_structure(p['path'], structure=p['structure'])
    path = os.path.join(test_path, os.path.normcase(p['path']))
    sut = ProcessResult(path)
    monkeypatch.setattr(sut, 'resource_name', p['resource_name'])

    # When
    result = sut._get_files(path)

    # Then
    for i, (dir_path, filelist) in enumerate(result):
        assert dir_path == os.path.join(test_path, os.path.normcase(p['expected'][i][0]))
        assert filelist == p['expected'][i][1]


@pytest.mark.parametrize('p', [
    {   # matching subtitle, process
        'path': 'media/postprocess/Show.Name.S01E03.HDTV.x264-LOL',
        'video': 'show.name.103.hdtv.x264-lol.mkv',
        'ignore_subs': False,
        'expected': True,
        'structure': (
            'show.name.103.hdtv.x264-lol.mkv',
            'show.name.103.hdtv.x264-lol.en.srt',
        ),
        'subtitles_enabled': True
    },
    {   # no matching subtitle, postpone processing
        'path': 'media/postprocess/Show.Name.S01E03.HDTV.x264-LOL',
        'video': 'show.name.103.hdtv.x264-lol.mkv',
        'ignore_subs': False,
        'expected': False,
        'structure': (
            'show.name.103.hdtv.x264-lol.mkv',
        ),
        'subtitles_enabled': True
    },
    {   # matching subtitle, ignoring subtitles, process
        'path': 'media/postprocess',
        'video': 'show.name.103.hdtv.x264-lol.mkv',
        'ignore_subs': True,
        'expected': True,
        'structure': (
            'show.name.103.hdtv.x264-lol.mkv',
            'show.name.103.hdtv.x264-lol.en.srt',
        ),
        'subtitles_enabled': True
    },
    {   # matching subtitle, subtitles disabled, process
        'path': 'media/postprocess',
        'video': 'show.name.103.hdtv.x264-lol.mkv',
        'ignore_subs': False,
        'expected': True,
        'structure': (
            'show.name.103.hdtv.x264-lol.mkv',
            'show.name.103.hdtv.x264-lol.en.srt',
        ),
        'subtitles_enabled': False
    },
])
def test__process_postponed(monkeypatch, p, create_structure):
    """Run the test."""
    # Given
    test_path = create_structure(p['path'], structure=p['structure'])
    path = os.path.join(test_path, os.path.normcase(p['path']))
    video_path = os.path.join(path, p['video'])
    processor = PostProcessor(path)
    sut = ProcessResult(path)

    # Overwrite internal method
    sut.subtitles_enabled = lambda path, resource_name: p['subtitles_enabled']

    # When
    result = sut._process_postponed(processor, video_path, p['video'], p['ignore_subs'])

    # Then
    assert p['expected'] == result


"""
path: As how provided by the client (nzbToMedia webRoute/apiv1, Scheduled pp or download_handler)
    to the process_tv.
resource_name: Optional resource (file, folder, nzbName)
expected: Expected result from process_tv.process()
base_path: Base path used to create the temporary folder/file structure for the test.
structure: Use a tuple to create test files. Pass a dict in the tuple to create a more advanced
    folder file structure.
"""
@pytest.mark.parametrize('p', [
    {   # Resource name given, but not found
        'path': 'media/postprocess/complete',
        'resource_name': 'show.name.103.hdtv.x264-lol.mkv',
        'expected': [],
        'base_path': 'media/postprocess/complete',
        'structure': (
            'show.name.101.hdtv.x264-lol.mkv',
            'show.name.102.hdtv.x264-lol.mkv',
            'show.name.103.hdtv.x264-lol.en.srt',
        )
    },
    {   # Resource name given and found
        'path': 'media/postprocess/complete',
        'resource_name': 'show.name.103.hdtv.x264-lol.mkv',
        'expected': ['show.name.103.hdtv.x264-lol.mkv'],
        'base_path': 'media/postprocess/complete',
        'structure': (
            'show.name.103.hdtv.x264-lol.mkv',
            'show.name.102.hdtv.x264-lol.mkv',
            'show.name.103.hdtv.x264-lol.en.srt',
        )
    },
    {   # No resource name given
        'path': 'media/postprocess/complete',
        'expected': ['show.name.102.hdtv.x264-lol.mkv',
                     'show.name.103.hdtv.x264-lol.mkv'],
        'base_path': 'media/postprocess/complete',
        'structure': (
            'show.name.103.hdtv.x264-lol.mkv',
            'show.name.102.hdtv.x264-lol.mkv',
            'show.name.103.hdtv.x264-lol.en.srt',
        )
    },
    {   # No resource name given and no valid files
        'path': 'media/postprocess/complete',
        'expected': [],
        'base_path': 'media/postprocess/complete',
        'structure': (
            'show.name.103.hdtv.x264-lol.en.srt',
        )
    },
    {   # Resource name given, resource is nzb
        'path': 'media/postprocess/complete',
        'resource_name': 'show.name.103.hdtv.x264-lol.nzb',
        'expected': ['show.name.101.hdtv.x264-lol.mkv',
                     'show.name.102.hdtv.x264-lol.mkv'],
        'base_path': 'media/postprocess/complete',
        'structure': (
            'show.name.101.hdtv.x264-lol.mkv',
            'show.name.102.hdtv.x264-lol.mkv',
            'show.name.103.hdtv.x264-lol.nzb',
            'show.name.103.hdtv.x264-lol.en.srt',
        )
    },
    {   # Resource name given, resource is the same as path basename.
        'path': 'media/postprocess/complete/show.name.103.hdtv.x264-lol',
        'resource_name': 'show.name.103.hdtv.x264-lol',
        'expected': ['show.name.101.hdtv.x264-lol.mkv',
                     'show.name.102.hdtv.x264-lol.mkv'],
        'base_path': 'media/postprocess/complete/show.name.103.hdtv.x264-lol',
        'structure': (
            'show.name.101.hdtv.x264-lol.mkv',
            'show.name.102.hdtv.x264-lol.mkv',
            'show.name.103.hdtv.x264-lol.en.srt',
        )
    },
    {   # path is TV_DOWNLOAD_DIR and NO_DELETE is True, folder should be kept
        'path': 'media/postprocess',
        'resource_name': 'show.name.103.hdtv.x264-lol.1',
        'expected': ['show.name.103.hdtv.x264-lol.mkv'],
        'base_path': 'media/postprocess',
        'structure': (
            {'show.name.103.hdtv.x264-lol.1': (
                'show.name.103.hdtv.x264-lol.mkv',
            )},
        )
    },
    {   # Resource name given, resource is a folder.
        'path': 'media/postprocess/complete',
        'resource_name': '[Black.Lightning.S04E01.1080p.WEB.H264-CAKES[rartv]]',
        'expected': ['black.lightning.S04E01.1080p.web.h264-cakes[rartv].mkv'],
        'base_path': 'media/postprocess/complete',
        'structure': (
            {'[Black.Lightning.S04E01.1080p.WEB.H264-CAKES[rartv]]': (
                'RARBG.txt',
                'RARBG_DO_NOT_MIRROR.exe',
                'black.lightning.S04E01.1080p.web.h264-cakes[rartv].mkv',
                'black.lightning.S04E01.1080p.web.h264-cakes[rartv].nfo',
            )},
        )
    },
    {   # Resource name given, resource is a file (path also has the file). (as nzbToMedia can provide it)
        'path': 'media/postprocess/complete/[SubsPlease] Dr. Stone S2 - 05 (1080p) [C291694C].mkv',
        'resource_name': '[SubsPlease] Dr. Stone S2 - 05 (1080p) [C291694C].mkv',
        'expected': ['[SubsPlease] Dr. Stone S2 - 05 (1080p) [C291694C].mkv'],
        'base_path': 'media/postprocess/complete/[SubsPlease] Dr. Stone S2 - 05 (1080p) [C291694C].mkv',
        'structure': (
            '[SubsPlease] Dr. Stone S2 - 05 (1080p) [C291694C].mkv',
        )
    }
])
def test__process(monkeypatch, p, create_structure):
    """Run the test."""
    # Given
    test_path = create_structure(p['base_path'], structure=p['structure'])
    path = os.path.join(test_path, os.path.normcase(p['path']))
    sut = ProcessResult(path)
    sut.process_media = Mock(return_value=None)

    # When
    sut.process(resource_name=p.get('resource_name'))

    # Then
    assert p['expected'] == sut.video_files


def test_process_rejects_direct_non_media_file(create_file):
    """Reject a non-media resource supplied directly as the processing path."""
    path = create_file('show.name.s01e01.exe', size=1024)
    sut = ProcessResult(path, process_single_resource=True)

    sut.process(resource_name=os.path.basename(path))

    assert sut.result is False
    assert sut.succeeded is False
    assert sut.missed_files == ['{0}: Not a valid video or RAR file'.format(path)]


def test_process_rejects_directory_non_media_resource(create_structure):
    """Reject a non-media resource even when its directory contains valid media."""
    resource_name = 'show.name.s01e01.exe'
    test_path = create_structure(
        'media/postprocess/complete',
        structure=(resource_name, 'unrelated.video.mkv')
    )
    path = os.path.join(test_path, os.path.normcase('media/postprocess/complete'))
    resource_path = os.path.join(path, resource_name)
    sut = ProcessResult(path, process_single_resource=True)

    sut.process(resource_name=resource_name)

    assert sut.result is False
    assert sut.succeeded is False
    assert sut.missed_files == ['{0}: Not a valid video or RAR file'.format(resource_path)]


@pytest.mark.parametrize('p', [
    {   # path is not TV_DOWNLOAD_DIR, folder should be deleted
        'path': 'media/postprocess/Show.Name.S01E03.HDTV.x264-LOL',
        'proc_type': 'manual',
        'delete': True,
        'expected': False,
        'structure': (
            'show.name.103.hdtv.x264-lol.mkv',
            'show.name.103.hdtv.x264-lol.en.srt',
            'readme.txt',
        ),
        'process_method': 'copy',
        'unwanted_files': ['readme.txt']
    },
    {   # path is TV_DOWNLOAD_DIR, folder shouldn't be deleted
        'path': 'media/postprocess',
        'proc_type': 'manual',
        'delete': True,
        'expected': ['show.name.103.hdtv.x264-lol.mkv'],
        'structure': (
            'show.name.103.hdtv.x264-lol.mkv',
            'show.name.103.hdtv.x264-lol.en.srt',
        ),
        'process_method': 'copy',
        'unwanted_files': ['show.name.103.hdtv.x264-lol.en.srt']
    },
    {   # delete is False, nothing should be deleted
        'path': 'media/postprocess',
        'proc_type': 'manual',
        'delete': False,
        'expected': ['show.name.103.hdtv.x264-lol.en.srt',
                     'show.name.103.hdtv.x264-lol.mkv'],
        'structure': (
            'show.name.103.hdtv.x264-lol.mkv',
            'show.name.103.hdtv.x264-lol.en.srt',
        ),
        'process_method': 'copy',
        'unwanted_files': ['show.name.103.hdtv.x264-lol.en.srt']
    },
    {   # delete is False and process_method move, still delete files
        'path': 'media/postprocess',
        'proc_type': 'manual',
        'delete': False,
        'expected': ['show.name.103.hdtv.x264-lol.mkv'],
        'structure': (
            'show.name.103.hdtv.x264-lol.mkv',
            'show.name.103.hdtv.x264-lol.en.srt',
        ),
        'process_method': 'move',
        'unwanted_files': ['show.name.103.hdtv.x264-lol.en.srt']
    },
    {   # path is not TV_DOWNLOAD_DIR and NO_DELETE is True, folder should be kept
        'path': 'media/postprocess/Show.Name.S01E03.HDTV.x264-LOL',
        'proc_type': 'auto',
        'delete': False,
        'expected': ['show.name.103.hdtv.x264-lol.mkv'],
        'structure': (
            'show.name.103.hdtv.x264-lol.mkv',
            'show.name.103.hdtv.x264-lol.en.srt',
            'readme.txt',
        ),
        'process_method': 'move',
        'unwanted_files': ['readme.txt', 'show.name.103.hdtv.x264-lol.en.srt'],
        'no_delete': True
    },
    {   # path is TV_DOWNLOAD_DIR, folder should be kept
        'path': 'media/postprocess',
        'proc_type': 'auto',
        'delete': False,
        'expected': ['show.name.103.hdtv.x264-lol.en.srt',
                     'show.name.103.hdtv.x264-lol.mkv'],
        'structure': (
            'show.name.103.hdtv.x264-lol.mkv',
            'show.name.103.hdtv.x264-lol.en.srt',
            'readme.txt',
        ),
        'process_method': 'move',
        'unwanted_files': ['readme.txt']
    },
    {   # path is TV_DOWNLOAD_DIR and NO_DELETE is True, folder should be kept
        'path': 'media/postprocess',
        'proc_type': 'auto',
        'delete': False,
        'expected': ['show.name.103.hdtv.x264-lol.en.srt',
                     'show.name.103.hdtv.x264-lol.mkv'],
        'structure': (
            'show.name.103.hdtv.x264-lol.mkv',
            'show.name.103.hdtv.x264-lol.en.srt',
            'readme.txt',
        ),
        'process_method': 'move',
        'unwanted_files': ['readme.txt'],
        'no_delete': True
    }
])
def test__clean_up(monkeypatch, p, create_structure):
    """Run the test."""
    # Given
    test_path = create_structure(p['path'], structure=p['structure'])
    path = os.path.join(test_path, os.path.normcase(p['path']))
    tv_download_dir = os.path.join(test_path, os.path.normcase('media/postprocess'))
    sut = ProcessResult(path)

    monkeypatch.setattr(app, 'TV_DOWNLOAD_DIR', tv_download_dir)
    monkeypatch.setattr(app, 'NO_DELETE', p.get('no_delete', False))
    monkeypatch.setattr(sut, 'process_method', p['process_method'])
    monkeypatch.setattr(sut, 'unwanted_files', p['unwanted_files'])

    # When
    sut._clean_up(path, p['proc_type'], p['delete'])
    if p['expected'] is False:
        expected = os.path.isdir(path)
    else:
        expected = sorted(os.listdir(path))

    # Then
    assert p['expected'] == expected
