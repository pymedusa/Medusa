# coding=utf-8
"""Tests for medusa/process_tv.py."""
import os

from medusa.process_tv import ProcessResult

import pytest


@pytest.mark.parametrize('p', [
    {
        'path': 'media/postprocess/',
        'dirName': 'main show dir',
        'nzbNameOriginal': None,
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
        'dirName': 'main show dir',
        'nzbNameOriginal': None,
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
        'dirName': 'main show dir',
        'nzbNameOriginal': None,
        'failed': False,
        'expected': False,
        'structure': (
            'bow.514.hdtv-lol.srt',
        )
    },
])
def test_validate_dir(p, create_structure):
    """Run the test."""
    # Given
    sut = ProcessResult()
    path = create_structure(path=os.path.join(p['path'], p['dirName']), structure=p['structure'])
    test_path = os.path.join(path, os.path.normcase(p['path']))

    # When
    result = sut.validate_dir(test_path, p['dirName'], p['nzbNameOriginal'], p['failed'])

    # Then
    assert p['expected'] == result
