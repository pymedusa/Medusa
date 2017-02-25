# coding=utf-8
"""Tests for medusa/process_tv.py."""
import os

from medusa.process_tv import ProcessResult

import pytest


@pytest.mark.parametrize('p', [
    {
        'path': '/media/postprocess/',
        'dirName': 'main show dir',
        'nzbNameOriginal': None,
        'failed': False,
        'expected': False,
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
        'path': '/media/postprocess/',
        'dirName': 'main show dir',
        'nzbNameOriginal': None,
        'failed': False,
        'expected': False,
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
])
def test_validate_dir(p, create_structure):
    """Run the test."""
    # Given
    sut = ProcessResult()
    create_structure(path=os.path.join(p['path'], p['dirName']), structure=p['structure'])

    # When
    result = sut.validateDir(p['path'], p['dirName'], p['nzbNameOriginal'], p['failed'])

    # Then
    assert p['expected'] == result
