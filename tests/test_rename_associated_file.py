# coding=utf-8
"""Tests for medusa/post_processor.py."""
from __future__ import unicode_literals
import os

from medusa import app
from medusa.post_processor import PostProcessor as Sut

import pytest


@pytest.mark.parametrize('p', [
    {  # p0: Subtitle with language. No subtitles dir set.
        'new_path': 'media/shows/great show/season 1/',
        'new_basename': 'Great Show - S01E04 - Best Episode',
        'filepath': 'downloads/tv/great.show.s01e04.720p.hdtv.x264-group.en.srt',
        'expected': 'media/shows/great show/season 1/Great Show - S01E04 - Best Episode.en.srt'
    },
    {  # p1: Subtitle without language. No subtitles dir set.
        'new_path': 'media/shows/great show/season 1/',
        'new_basename': 'Great Show - S01E04 - Best Episode',
        'filepath': 'downloads/tv/great.show.s01e04.720p.hdtv.x264-group.srt',
        'expected': 'media/shows/great show/season 1/Great Show - S01E04 - Best Episode.srt'
    },
    {  # p2: Subtitle with language. Absolute subtitles dir set.
        'new_path': 'media/shows/great show/season 1/',
        'new_basename': 'Great Show - S01E04 - Best Episode',
        'filepath': 'downloads/tv/great.show.s01e04.720p.hdtv.x264-group.it.srt',
        'subtitles': {'dir': 'downloads/subtitles/', 'absolute': True},
        'expected': 'Great Show - S01E04 - Best Episode.it.srt'
    },
    {  # p3: Subtitle without language. Absolute subtitles dir set.
        'new_path': 'media/shows/great show/season 1/',
        'new_basename': 'Great Show - S01E04 - Best Episode',
        'filepath': 'downloads/tv/great.show.s01e04.720p.hdtv.x264-group.srt',
        'subtitles': {'dir': 'downloads/subtitles/', 'absolute': True},
        'expected': 'Great Show - S01E04 - Best Episode.srt'
    },
    {  # p4: Subtitle with language. Relative subtitles dir set.
        'new_path': 'media/shows/great show/season 1/',
        'new_basename': 'Great Show - S01E04 - Best Episode',
        'filepath': 'downloads/tv/great.show.s01e04.720p.hdtv.x264-group.it.srt',
        'subtitles': {'dir': 'subs', 'absolute': False},
        'expected': 'media/shows/great show/season 1/subs/Great Show - S01E04 - Best Episode.it.srt'
    },
    {  # p5: Subtitle without language. Relative subtitles dir set.
        'new_path': 'media/shows/great show/season 1/',
        'new_basename': 'Great Show - S01E04 - Best Episode',
        'filepath': 'downloads/tv/great.show.s01e04.720p.hdtv.x264-group.srt',
        'subtitles': {'dir': 'subs', 'absolute': False},
        'expected': 'media/shows/great show/season 1/subs/Great Show - S01E04 - Best Episode.srt'
    },
    {  # p6: Subtitle with language. No subtitles dir set.
        'new_path': 'media/shows/riko or marty/season 3/',
        'new_basename': 'riko.or.marty.s03e05.1080p.web-dl',
        'filepath': 'downloads/tv/riko.or.marty.s03e05.1080p.web-dl.eng.srt',
        'expected': 'media/shows/riko or marty/season 3/riko.or.marty.s03e05.1080p.web-dl.eng.srt'
    },
    {  # p7: Subtitle with language. No subtitles dir set. New basename empty.
        'new_path': 'media/shows/riko or marty/season 3/',
        'filepath': 'downloads/tv/riko.or.marty.s03e05.1080p.web-dl.eng.srt',
        'expected': 'media/shows/riko or marty/season 3/riko.or.marty.s03e05.1080p.web-dl.eng.srt'
    },
    {  # p8: Subtitle with language. No subtitles dir set.
        'new_path': 'media/shows/riko or marty/season 3/',
        'filepath': 'downloads/tv/riko.or.marty.s03e05.1080p.web-dl.PT-BR.srt',
        'expected': 'media/shows/riko or marty/season 3/riko.or.marty.s03e05.1080p.web-dl.pt-BR.srt'
    },
    {  # p9: NFO with renaming. New basename empty.
        'new_path': 'media/shows/riko or marty/season 3/',
        'filepath': 'downloads/tv/riko.or.marty.s03e05.1080p.web-dl.nfo',
        'expected': 'media/shows/riko or marty/season 3/riko.or.marty.s03e05.1080p.web-dl.nfo-orig'
    },
    {  # p10: NFO without renaming
        'new_path': 'media/shows/riko or marty/season 3/',
        'filepath': 'downloads/tv/riko.or.marty.s03e05.1080p.web-dl.nfo',
        'nfo_rename': 0,
        'expected': 'media/shows/riko or marty/season 3/riko.or.marty.s03e05.1080p.web-dl.nfo'
    },
    {  # p11: MKV without new basename
        'new_path': 'media/shows/riko or marty/season 3/',
        'filepath': 'downloads/tv/riko.or.marty.s03e05.1080p.web-dl.mkv',
        'expected': 'media/shows/riko or marty/season 3/riko.or.marty.s03e05.1080p.web-dl.mkv'
    },
    {  # p12: MKV with new basename
        'new_path': 'media/shows/riko or marty/season 3/',
        'new_basename': 'Riko or Marty S03E05 Episode Name',
        'filepath': 'downloads/tv/riko.or.marty.s03e05.1080p.web-dl.mkv',
        'expected': 'media/shows/riko or marty/season 3/Riko or Marty S03E05 Episode Name.mkv'
    },
    {  # p13: Space before subtitle extension
        'new_path': 'media/shows/gomorra/season 3/',
        'new_basename': 'Gomorra S03E15 Episode Name',
        'filepath': 'downloads/tv/Gomorra S03 E11 - x264 .srt',
        'expected': 'media/shows/gomorra/season 3/Gomorra S03E15 Episode Name.srt'
    },
    {  # p14: Subtitle with language tag
        'new_path': 'media/shows/riko or marty/season 3/',
        'filepath': 'downloads/tv/riko.or.marty.s03e05.1080p.web-dl.en-au.srt',
        'expected': 'media/shows/riko or marty/season 3/riko.or.marty.s03e05.1080p.web-dl.en-AU.srt'
    },
])
def test_rename_associated_file(p, create_dir, monkeypatch):
    """Test rename_associated_file."""
    # Given
    new_path = p['new_path']
    new_basename = p.get('new_basename')
    filepath = p['filepath']

    monkeypatch.setattr(app, 'NFO_RENAME', p.get('nfo_rename', 1))

    if p.get('subtitles'):
        # Workaround for absolute subtitles directory
        if p['subtitles']['absolute']:
            subs_dir = create_dir(p['subtitles']['dir'])
            monkeypatch.setattr(app, 'SUBTITLES_DIR', subs_dir)
            p['expected'] = os.path.join(subs_dir, p['expected'])
        else:
            monkeypatch.setattr(app, 'SUBTITLES_DIR', p['subtitles']['dir'])

    # When
    result = Sut.rename_associated_file(new_path, new_basename, filepath)

    # Then
    assert os.path.normcase(result) == os.path.normcase(p['expected'])
