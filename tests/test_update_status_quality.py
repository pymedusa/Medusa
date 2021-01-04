# coding=utf-8
"""Tests for medusa/tv/episode.py:update_status_quality"""
from __future__ import unicode_literals
from medusa.common import (ARCHIVED, DOWNLOADED, IGNORED, Quality, SKIPPED, SNATCHED, SNATCHED_BEST,
                           SNATCHED_PROPER, UNAIRED, UNSET, WANTED, statusStrings)

import pytest


@pytest.fixture
def create_episode(tvshow, create_tvepisode, create_file):
    def create(filepath, status, size, quality):
        path = create_file(filepath, size=size) if filepath else ''
        episode = create_tvepisode(tvshow, 2, 14, filepath=path)
        episode.location = path
        if status:
            episode.status = status
        if quality:
            episode.quality = quality

        return episode

    return create


@pytest.mark.parametrize('p', [
    {  # p0: File name and size are the same
        'status': SNATCHED,
        'quality': Quality.SDTV,
        'filepath': 'Show.S01E01.HDTV.X264-GROUP.mkv',
        'expected': (DOWNLOADED, Quality.SDTV)
    },
    {  # p1: Not a valid media file
        'status': DOWNLOADED,
        'quality': Quality.FULLHDTV,
        'location': 'Show.S01E02.1080p.HDTV.X264-GROUP.mkv',
        'filepath': 'Show.S01E02.1080p.HDTV.X264-GROUP.srt',
        'expected': (DOWNLOADED, Quality.FULLHDTV)
    },
    {  # p2: File name is the same, different size
        'status': SNATCHED,
        'quality': Quality.SDTV,
        'location': 'Show.S01E03.HDTV.X264-GROUP.mkv',
        'filepath': 'Show.S01E03.HDTV.X264-GROUP.mkv',
        'new_size': 53,
        'expected': (DOWNLOADED, Quality.SDTV)
    },
    {  # p3: File name is different, same size
        'status': DOWNLOADED,
        'quality': Quality.SDTV,
        'location': 'Show.S01E04.HDTV.X264-GROUP.mkv',
        'filepath': 'Show.S01E04.HDTV.X264-OTHERGROUP.mkv',
        'expected': (DOWNLOADED, Quality.SDTV)
    },
    {  # p4: File name and size are both different
        'status': DOWNLOADED,
        'quality': Quality.HDTV,
        'location': 'Show.S01E05.720p.HDTV.X264-GROUP.mkv',
        'filepath': 'Show.S01E05.720p.HDTV.X264-SOMEOTHERGROUP.mkv',
        'new_size': 85,
        'expected': (DOWNLOADED, Quality.HDTV)
    },
    {  # p5: No previous file present (location)
        'status': DOWNLOADED,
        'quality': Quality.FULLHDTV,
        'filepath': 'Show.S01E06.1080p.HDTV.X264-GROUP.mkv',
        'expected': (ARCHIVED, Quality.FULLHDTV)
    },
    {  # p6: Default status and no previous file present (location)
        'filepath': 'Show.S01E07.720p.HDTV.X264-GROUP.mkv',
        'expected': (ARCHIVED, Quality.HDTV)
    },
    {  # p7: Snatched and download not finished
        'status': SNATCHED,
        'quality': Quality.FULLHDTV,
        'location': 'Show.S01E08.1080p.HDTV.X264-GROUP.mkv',
        'filepath': 'Show.S01E08.1080p.HDTV.X264-GROUP.mkv',
        'expected': (SNATCHED, Quality.FULLHDTV)
    },
    {  # p8: Previous status was Skipped
        'status': SKIPPED,
        'quality': Quality.NA,
        'filepath': 'Show.S01E09.1080p.HDTV.X264-GROUP.mkv',
        'expected': (ARCHIVED, Quality.FULLHDTV)
    },
    {  # p9: Previous status was Unaired
        'status': UNAIRED,
        'quality': Quality.NA,
        'filepath': 'Show.S01E10.HDTV.X264-GROUP.mkv',
        'expected': (ARCHIVED, Quality.SDTV)
    },
    {  # p10: Previous status was Ignored
        'status': IGNORED,
        'quality': Quality.NA,
        'filepath': 'Show.S01E11.HDTV.X264-GROUP.mkv',
        'expected': (ARCHIVED, Quality.SDTV)
    },
    {  # p11: Previous status was Unset
        'status': UNSET,
        'quality': Quality.NA,
        'filepath': 'Show.S01E11.HDTV.X264-GROUP.mkv',
        'expected': (ARCHIVED, Quality.SDTV)
    },
    {  # p12: Snatched and download is finished
        'status': SNATCHED,
        'quality': Quality.HDTV,
        'location': 'Show.S01E12.720p.HDTV.X264-GROUP.mkv',
        'filepath': 'Show.S01E12.720p.HDTV.X264-BETTERGROUP.mkv',
        'new_size': 29,
        'expected': (DOWNLOADED, Quality.HDTV)
    },
    {  # p13: Snatched a Proper and download is finished
        'status': SNATCHED_PROPER,
        'quality': Quality.FULLHDTV,
        'location': 'Show.S01E13.1080p.HDTV.X264-GROUP.mkv',
        'filepath': 'Show.S01E13.PROPER.1080p.HDTV.X264-GROUP.mkv',
        'new_size': 89,
        'expected': (DOWNLOADED, Quality.FULLHDTV)
    },
    {  # p14: Snatched a Proper (Best) and download is finished (higher quality)
        'status': SNATCHED_BEST,
        'quality': Quality.SDTV,
        'location': 'Show.S01E14.HDTV.X264-GROUP.mkv',
        'filepath': 'Show.S01E14.720p.HDTV.X264-GROUP.mkv',
        'expected': (DOWNLOADED, Quality.HDTV)
    },
    {  # p15: Snatched a Proper (Best) and download is finished (lower quality)
        'status': SNATCHED_BEST,
        'quality': Quality.FULLHDTV,
        'location': 'Show.S01E15.1080p.HDTV.X264-GROUP.mkv',
        'filepath': 'Show.S01E15.HDTV.X264-GROUP.mkv',
        'expected': (DOWNLOADED, Quality.SDTV)
    },
    {  # p16: Previous status was Wanted and no previous file present (location)
        'status': WANTED,
        'quality': Quality.NA,
        'filepath': 'Show.S01E16.HDTV.X264-GROUP.mkv',
        'expected': (DOWNLOADED, Quality.SDTV)
    },
    {  # p17: Previous status was Wanted
        'status': WANTED,
        'quality': Quality.FULLHDTV,
        'location': 'Show.S01E17.1080p.HDTV.X264-GROUP.mkv',
        'filepath': 'Show.S01E17.720p.HDTV.X264-GROUP.mkv',
        'new_size': 38,
        'expected': (ARCHIVED, Quality.HDTV)
    },
])
def test_update_status_quality(p, create_episode, create_file):
    """Run the test."""
    # Given
    location = p.get('location')
    status = p.get('status')
    quality = p.get('quality')
    episode = create_episode(filepath=location, status=status, quality=quality, size=42)
    filepath = create_file(p['filepath'], size=p.get('new_size', 42))
    exp_status, exp_quality = p['expected']

    # When
    episode.update_status_quality(filepath)
    actual_status = episode.status
    actual_quality = episode.quality

    # Then
    assert statusStrings[exp_status] == statusStrings[actual_status]
    assert Quality.qualityStrings[exp_quality] == Quality.qualityStrings[actual_quality]
