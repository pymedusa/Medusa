# coding=utf-8
"""Tests for medusa/process_tv.py."""
import os

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
