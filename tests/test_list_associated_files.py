# coding=utf-8
"""Tests for medusa/test_list_associated_files.py."""
from __future__ import unicode_literals
import os

from medusa import app
from medusa.post_processor import PostProcessor

import pytest


def _rar_basename(filepath, files):
    for found_file in files:
        if os.path.splitext(os.path.basename(found_file))[1] == '.rar':
            return os.path.basename(os.path.splitext(os.path.basename(found_file))[0].lower())


@pytest.mark.parametrize('p', [
    {  # p0: No associated files. Wrong basename
        'path': 'media/postprocess/',
        'structure': (
            'bow.514.hdtv-lol[ettv].mkv',
            'bow.514.hdtv-lol.srt',
            {'samples': (
                'sample.mkv', 'other.mkv',
                {'inception': ()}
            )}
        ),
        'expected_associated_files': [],
        'allowed_extensions': 'nfo,srt'
    },
    {  # p1: No associated files
        'path': 'media/postprocess/',
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
        'allowed_extensions': 'nfo,srt'
    },
    {  # p2: No media file, so can't list associated files
        'path': 'media/postprocess/',
        'structure': (
            'bow.514.hdtv-lol.srt',
        ),
        'expected_associated_files': [],
        'allowed_extensions': 'nfo,srt'
    },
    {  # p3: .srt and .nfo associated files. Check subfolders
        'path': 'media/postprocess/',
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
        'allowed_extensions': 'nfo,srt',
        'subfolders': True,
        'refine': True
    },
    {  # p4: Only .nfo associated file allowed
        'path': 'media/postprocess/',
        'structure': (
                'Show.S01E01.720p.HDTV.X264-DIMENSION.mkv',
                'Show.S01E01.720p.HDTV.X264-DIMENSION.pt-BR.srt',
                'Show.S01E01.720p.HDTV.X264-DIMENSION.nfo',
                'Show.S01E01.720p.HDTV.X264-DIMENSION.sfv'
        ),
        'expected_associated_files': ['Show.S01E01.720p.HDTV.X264-DIMENSION.nfo',
                                      ],
        'allowed_extensions': 'nfo',
        'refine': True
    },
    {  # p5: No allowed extensions
        'path': 'media/postprocess/',
        'structure': (
                'Show.S01E01.720p.HDTV.X264-DIMENSION.mkv',
                'Show.S01E01.720p.HDTV.X264-DIMENSION.pt-BR.srt',
                'Show.S01E01.720p.HDTV.X264-DIMENSION.nfo',
                'Show.S01E01.720p.HDTV.X264-DIMENSION.sfv'
        ),
        'expected_associated_files': [],
        'allowed_extensions': '',
        'refine': True
    },
    {  # p6: Associated file based on RARed file
        'path': 'media/postprocess/',
        'structure': (
                'Show.S01E01.720p.HDTV.X264-DIMENSION.mkv',
                'show.101.720p-dimension.rar',
                'show.101.720p-dimension.nfo'
        ),
        'expected_associated_files': ['show.101.720p-dimension.nfo'],
        'allowed_extensions': 'nfo'
    },
    {  # p7: 'Subtitles only' param for associated files
        'path': 'media/postprocess/',
        'structure': (
                'Show.S01E01.720p.HDTV.X264-DIMENSION.mkv',
                'Show.S01E01.720p.HDTV.X264-DIMENSION.pt-BR.srt',
                'Show.S01E01.720p.HDTV.X264-DIMENSION.nfo',
                'Show.S01E01.720p.HDTV.X264-DIMENSION.sfv'
        ),
        'expected_associated_files': ['Show.S01E01.720p.HDTV.X264-DIMENSION.pt-BR.srt'],
        'allowed_extensions': 'nfo,srt',
        'subtitles_only': True
    },
    {  # p8: Subtitle in subfolder. Check subfolders enabled
        'path': 'media/postprocess/',
        'structure': (
                'Show.S01E01.720p.HDTV.X264-DIMENSION.mkv',
                {'subs': (
                    'RARBG.txt', 'Show.S01E01.720p.HDTV.X264-DIMENSION.pt-BR.srt',
                )}
        ),
        'expected_associated_files': ['Show.S01E01.720p.HDTV.X264-DIMENSION.pt-BR.srt',
                                      ],
        'allowed_extensions': 'nfo,srt',
        'subfolders': True
    },
])
def test_list_associated_files(p, create_structure, monkeypatch):
    """Run the test."""
    # Given
    test_path = create_structure(p['path'], structure=p['structure'])
    path = os.path.join(test_path, os.path.normcase(p['path']))
    file_path = os.path.join(path, p['structure'][0])

    expected_associated_files = p['expected_associated_files']
    subtitles_only = p.get('subtitles_only', False)
    subfolders = p.get('subfolders', False)
    refine = p.get('refine', False)

    monkeypatch.setattr(app, 'ALLOWED_EXTENSIONS', p['allowed_extensions'])
    monkeypatch.setattr(app, 'MOVE_ASSOCIATED_FILES', 1)

    processor = PostProcessor(file_path)
    processor._rar_basename = _rar_basename

    # When
    found_associated_files = processor.list_associated_files(file_path, subfolders=subfolders,
                                                             subtitles_only=subtitles_only, refine=refine)
    associated_files_basenames = [os.path.basename(i) for i in found_associated_files]

    # Then
    assert set(associated_files_basenames) == set(expected_associated_files)
