# coding=utf-8
"""Tests for medusa/process_tv.py."""
import os

from medusa import app

from medusa.post_processor import PostProcessor
from medusa.process_tv import ProcessResult

import pytest


class TestPostProcessor(PostProcessor):
    """A test `PostProcessor` object."""

    def __init__(self, file_path=None, nzb_name=None, process_method=None, is_priority=None):
        """Initialize the object."""
        super(PostProcessor, self).__init__()

    @staticmethod
    def _rar_basename(filepath, files):
        for files in files:
            if os.path.splitext(os.path.basename(files))[1] == '.rar':
                return os.path.basename(os.path.splitext(os.path.basename(files))[0])

    def _log(self, message=None, level=None):
        pass


@pytest.mark.parametrize('p', [
    {  # p0: Process file and no associated files
        'path': 'media/postprocess/',
        'nzb_name': None,
        'failed': False,
        'expected': True,
        'structure': (
            'bow.514.hdtv-lol[ettv].mkv',
            'bow.514.hdtv-lol.srt',
            {'samples': (
                'sample.mkv', 'other.mkv',
                {'inception': ()}
            )}
        ),
        'expected_associated_files': [],
        'allowed_extensions': "nfo,srt"
    },
    {  # p1: Process file and no associated file
        'path': 'media/postprocess/',
        'nzb_name': None,
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
        ),
        'expected_associated_files': [],
        'allowed_extensions': "nfo,srt"
    },
    {  # p2: Don't Process file and not associated file
        'path': 'media/postprocess/',
        'nzb_name': None,
        'failed': False,
        'expected': False,
        'structure': (
            'bow.514.hdtv-lol.srt',
        ),
        'expected_associated_files': [],
        'allowed_extensions': "nfo,srt"
    },
    {  # p3: Process file and .srt and .nfo associated files
        'path': 'media/postprocess/',
        'nzb_name': None,
        'failed': False,
        'expected': True,
        'structure': (
                'Show.S01E01.720p.HDTV.X264-DIMENSION.mkv',
                'Show.S01E01.720p.HDTV.X264-DIMENSION.pt-BR.srt',
                'Show.S01E01.720p.HDTV.X264-DIMENSION.nfo',
                'Show.S01E01.720p.HDTV.X264-DIMENSION.sfv',
                {'samples': (
                    'sample.mkv', 'other.mkv',
                    {'inception': (
                        'cool.txt', 'bla.nfo'
                    )}
                )}
        ),
        'expected_associated_files': ['Show.S01E01.720p.HDTV.X264-DIMENSION.pt-BR.srt',
                                      'Show.S01E01.720p.HDTV.X264-DIMENSION.nfo',
                                      ],
        'allowed_extensions': "nfo,srt"

    },
    {  # p4: Process file and only .nfo associated file
        'path': 'media/postprocess/',
        'nzb_name': None,
        'failed': False,
        'expected': True,
        'structure': (
                'Show.S01E01.720p.HDTV.X264-DIMENSION.mkv',
                'Show.S01E01.720p.HDTV.X264-DIMENSION.pt-BR.srt',
                'Show.S01E01.720p.HDTV.X264-DIMENSION.nfo',
                'Show.S01E01.720p.HDTV.X264-DIMENSION.sfv'
        ),
        'expected_associated_files': ['Show.S01E01.720p.HDTV.X264-DIMENSION.nfo',
                                      ],
        'allowed_extensions': "nfo"
    },
    {  # p5: Process file and no allowed extensions
        'path': 'media/postprocess/',
        'nzb_name': None,
        'failed': False,
        'expected': True,
        'structure': (
                'Show.S01E01.720p.HDTV.X264-DIMENSION.mkv',
                'Show.S01E01.720p.HDTV.X264-DIMENSION.pt-BR.srt',
                'Show.S01E01.720p.HDTV.X264-DIMENSION.nfo',
                'Show.S01E01.720p.HDTV.X264-DIMENSION.sfv'
        ),
        'expected_associated_files': [],
        'allowed_extensions': ""
    },
    {  # p6: Process file. RARed file with .rar associated file
        'path': 'media/postprocess/',
        'nzb_name': None,
        'failed': False,
        'expected': True,
        'structure': (
                'Show.S01E01.720p.HDTV.X264-DIMENSION.mkv',
                'show.101.720p-dimension.rar',
                'show.101.720p-dimension.nfo'
        ),
        'expected_associated_files': ['show.101.720p-dimension.nfo'],
        'allowed_extensions': "nfo"
    },
])
def test_should_process(p, create_structure):
    """Run the test."""
    # Given
    test_path = create_structure(p['path'], structure=p['structure'])
    path = os.path.join(test_path, os.path.normcase(p['path']))
    file = os.path.join(path, p['structure'][0])
    expected_associated_files = p['expected_associated_files']
    app.ALLOWED_EXTENSIONS = p['allowed_extensions']
    app.MOVE_ASSOCIATED_FILES = 1

    sut = ProcessResult(path)
    processor = TestPostProcessor(file)

    # When
    result = sut.should_process(path, p['nzb_name'], p['failed'])
    found_associated_files = processor.list_associated_files(file)
    associated_files_basenames = [os.path.basename(i) for i in found_associated_files]

    # Then
    assert set(associated_files_basenames) == set(expected_associated_files)
    assert p['expected'] == result
