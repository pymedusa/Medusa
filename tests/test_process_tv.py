# coding=utf-8
"""Tests for medusa/process_tv.py."""
from __future__ import unicode_literals
import os

from medusa import app
from medusa.post_processor import PostProcessor
from medusa.process_tv import ProcessResult

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
    sut = ProcessResult(path)

    # When
    result = sut.should_process(path, p['failed'])

    # Then
    assert p['expected'] == result


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
        assert os.path.join(test_path, os.path.normcase(p['expected'])) == result_path


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
                      ['show.name.s02e01.webrip.x264-kovalski.mkv', 'sample.mkv']),
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
    },
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
