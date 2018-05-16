# coding=utf-8
"""Tests for medusa/tv/episode.py:update_status"""
from medusa.common import (ARCHIVED, DOWNLOADED, IGNORED, Quality, SKIPPED, SNATCHED, SNATCHED_BEST,
                           SNATCHED_PROPER, UNAIRED, UNSET, WANTED, statusStrings)

import pytest


@pytest.fixture
def create_episode(tvshow, create_tvepisode, create_file):
    def create(filepath, status, size):
        path = create_file(filepath, size=size) if filepath else ''
        episode = create_tvepisode(tvshow, 2, 14, filepath=path)
        episode.location = path
        if status:
            episode.status = status

        return episode

    return create


@pytest.mark.parametrize('p', [
    {  # p0: File name and size are the same
        'status': Quality.composite_status(SNATCHED, Quality.SDTV),
        'filepath': 'Show.S01E01.HDTV.X264-GROUP.mkv',
        'expected': Quality.composite_status(DOWNLOADED, Quality.SDTV)
    },
    {  # p1: Not a valid media file
        'status': Quality.composite_status(DOWNLOADED, Quality.FULLHDTV),
        'location': 'Show.S01E02.1080p.HDTV.X264-GROUP.mkv',
        'filepath': 'Show.S01E02.1080p.HDTV.X264-GROUP.srt',
        'expected': Quality.composite_status(DOWNLOADED, Quality.FULLHDTV)
    },
    {  # p2: File name is the same, different size
        'status': Quality.composite_status(SNATCHED, Quality.SDTV),
        'location': 'Show.S01E03.HDTV.X264-GROUP.mkv',
        'filepath': 'Show.S01E03.HDTV.X264-GROUP.mkv',
        'new_size': 53,
        'expected': Quality.composite_status(DOWNLOADED, Quality.SDTV)
    },
    {  # p3: File name is different, same size
        'status': Quality.composite_status(DOWNLOADED, Quality.SDTV),
        'location': 'Show.S01E04.HDTV.X264-GROUP.mkv',
        'filepath': 'Show.S01E04.HDTV.X264-OTHERGROUP.mkv',
        'expected': Quality.composite_status(DOWNLOADED, Quality.SDTV)
    },
    {  # p4: File name and size are both different
        'status': Quality.composite_status(DOWNLOADED, Quality.HDTV),
        'location': 'Show.S01E05.720p.HDTV.X264-GROUP.mkv',
        'filepath': 'Show.S01E05.720p.HDTV.X264-SOMEOTHERGROUP.mkv',
        'new_size': 85,
        'expected': Quality.composite_status(DOWNLOADED, Quality.HDTV)
    },
    {  # p5: No previous file present (location)
        'status': Quality.composite_status(DOWNLOADED, Quality.FULLHDTV),
        'filepath': 'Show.S01E06.1080p.HDTV.X264-GROUP.mkv',
        'expected': Quality.composite_status(ARCHIVED, Quality.FULLHDTV)
    },
    {  # p6: Default status and no previous file present (location)
        'filepath': 'Show.S01E07.720p.HDTV.X264-GROUP.mkv',
        'expected': Quality.composite_status(ARCHIVED, Quality.HDTV)
    },
    {  # p7: Snatched and download not finished
        'status': Quality.composite_status(SNATCHED, Quality.FULLHDTV),
        'location': 'Show.S01E08.1080p.HDTV.X264-GROUP.mkv',
        'filepath': 'Show.S01E08.1080p.HDTV.X264-GROUP.mkv',
        'expected': Quality.composite_status(SNATCHED, Quality.FULLHDTV)
    },
    {  # p8: Previous status was Skipped
        'status': Quality.composite_status(SKIPPED, None),
        'filepath': 'Show.S01E09.1080p.HDTV.X264-GROUP.mkv',
        'expected': Quality.composite_status(ARCHIVED, Quality.FULLHDTV)
    },
    {  # p9: Previous status was Unaired
        'status': Quality.composite_status(UNAIRED, None),
        'filepath': 'Show.S01E10.HDTV.X264-GROUP.mkv',
        'expected': Quality.composite_status(ARCHIVED, Quality.SDTV)
    },
    {  # p10: Previous status was Ignored
        'status': Quality.composite_status(IGNORED, None),
        'filepath': 'Show.S01E11.HDTV.X264-GROUP.mkv',
        'expected': Quality.composite_status(ARCHIVED, Quality.SDTV)
    },
    {  # p11: Previous status was Unset
        'status': Quality.composite_status(UNSET, None),
        'filepath': 'Show.S01E11.HDTV.X264-GROUP.mkv',
        'expected': Quality.composite_status(ARCHIVED, Quality.SDTV)
    },
    {  # p12: Snatched and download is finished
        'status': Quality.composite_status(SNATCHED, Quality.HDTV),
        'location': 'Show.S01E12.720p.HDTV.X264-GROUP.mkv',
        'filepath': 'Show.S01E12.720p.HDTV.X264-BETTERGROUP.mkv',
        'new_size': 29,
        'expected': Quality.composite_status(DOWNLOADED, Quality.HDTV)
    },
    {  # p13: Snatched a Proper and download is finished
        'status': Quality.composite_status(SNATCHED_PROPER, Quality.FULLHDTV),
        'location': 'Show.S01E13.1080p.HDTV.X264-GROUP.mkv',
        'filepath': 'Show.S01E13.PROPER.1080p.HDTV.X264-GROUP.mkv',
        'new_size': 89,
        'expected': Quality.composite_status(DOWNLOADED, Quality.FULLHDTV)
    },
    {  # p14: Snatched a Proper (Best) and download is finished (higher quality)
        'status': Quality.composite_status(SNATCHED_BEST, Quality.SDTV),
        'location': 'Show.S01E14.HDTV.X264-GROUP.mkv',
        'filepath': 'Show.S01E14.720p.HDTV.X264-GROUP.mkv',
        'expected': Quality.composite_status(DOWNLOADED, Quality.HDTV)
    },
    {  # p15: Snatched a Proper (Best) and download is finished (lower quality)
        'status': Quality.composite_status(SNATCHED_BEST, Quality.FULLHDTV),
        'location': 'Show.S01E15.1080p.HDTV.X264-GROUP.mkv',
        'filepath': 'Show.S01E15.HDTV.X264-GROUP.mkv',
        'expected': Quality.composite_status(DOWNLOADED, Quality.SDTV)
    },
    {  # p16: Previous status was Wanted and no previous file present (location)
        'status': Quality.composite_status(WANTED, None),
        'filepath': 'Show.S01E16.HDTV.X264-GROUP.mkv',
        'expected': Quality.composite_status(DOWNLOADED, Quality.SDTV)
    },
    {  # p17: Previous status was Wanted
        'status': Quality.composite_status(WANTED, Quality.FULLHDTV),
        'location': 'Show.S01E17.1080p.HDTV.X264-GROUP.mkv',
        'filepath': 'Show.S01E17.720p.HDTV.X264-GROUP.mkv',
        'new_size': 38,
        'expected': Quality.composite_status(ARCHIVED, Quality.HDTV)
    },
])
def test_update_status(p, create_episode, create_file):
    """Run the test."""
    # Given
    location = p.get('location')
    status = p.get('status')
    episode = create_episode(filepath=location, status=status, size=42)
    filepath = create_file(p['filepath'], size=p.get('new_size', 42))
    expected = p['expected']

    # When
    episode.update_status(filepath)
    actual = episode.status

    # Then
    assert statusStrings[expected] == statusStrings[actual]
