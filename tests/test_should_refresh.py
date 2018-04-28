# coding=utf-8
"""Tests for medusa/test_should_refresh.py."""
from medusa.common import (ARCHIVED, DOWNLOADED, IGNORED, Quality, SKIPPED, SNATCHED,
                           SNATCHED_BEST, SNATCHED_PROPER, UNAIRED)
from medusa.tv import Series

import pytest


#  Tests order has ve same order as the rules order
@pytest.mark.parametrize('p', [
    {  # p0: File is the same: no
        'cur_status': Quality.composite_status(DOWNLOADED, Quality.HDTV),
        'same_file': True,
        'check_quality_again': False,
        'anime': False,
        'filepath': 'Show.S01E01.1080p.HDTV.X264-GROUP.mkv',
        'expected': False
    },
    {  # p1: Not valid media file: no
        'cur_status': Quality.composite_status(DOWNLOADED, Quality.HDTV),
        'same_file': False,
        'check_quality_again': False,
        'anime': False,
        'filepath': 'Show.S01E01.1080p.HDTV.X264-GROUP.srt',
        'expected': False
    },
    {  # p2: Check file again but new file has UNKNOWN quality: yes
        'cur_status': Quality.composite_status(DOWNLOADED, Quality.HDTV),
        'same_file': False,
        'check_quality_again': True,
        'anime': False,
        'filepath': 'Show.S01E01.mkv',
        'expected': True
    },
    {  # p3: Check file again and not UNKNOWN quality: yes
        'cur_status': Quality.composite_status(DOWNLOADED, Quality.HDTV),
        'same_file': False,
        'check_quality_again': True,
        'anime': False,
        'filepath': 'Show.S01E01.1080p.HDTV.X264-GROUP.mkv',
        'expected': True
    },
    {  # p4: Status is already DOWNLOADED: no
        'cur_status': Quality.composite_status(DOWNLOADED, Quality.HDTV),
        'same_file': False,
        'check_quality_again': False,
        'anime': False,
        'filepath': 'Show.S01E01.1080p.HDTV.X264-GROUP.mkv',
        'expected': False
    },
    {  # p5: Status is already IGNORED: no
        'cur_status': Quality.composite_status(IGNORED, None),
        'same_file': False,
        'check_quality_again': False,
        'anime': False,
        'filepath': 'Show.S01E01.1080p.HDTV.X264-GROUP.mkv',
        'expected': False
    },
    {  # p6: Status is already ARCHIVED: no
        'cur_status': Quality.composite_status(ARCHIVED, None),
        'same_file': False,
        'check_quality_again': False,
        'anime': False,
        'filepath': 'Show.S01E01.1080p.HDTV.X264-GROUP.mkv',
        'expected': False
    },
    {  # p7: Status is already SKIPPED: yes
        'cur_status': Quality.composite_status(SKIPPED, None),
        'same_file': False,
        'check_quality_again': False,
        'anime': False,
        'filepath': 'Show.S01E01.1080p.HDTV.X264-GROUP.mkv',
        'expected': True
    },
    {  # p8: Status is UNAIRED: yes
        'cur_status': Quality.composite_status(UNAIRED, None),
        'same_file': False,
        'check_quality_again': False,
        'anime': False,
        'filepath': 'Show.S01E01.1080p.HDTV.X264-GROUP.mkv',
        'expected': True
    },
    {  # p9: Status is SNATCHED BEST and new quality is lower: no
        'cur_status': Quality.composite_status(SNATCHED_BEST, Quality.HDTV),
        'same_file': False,
        'check_quality_again': False,
        'anime': False,
        'filepath': 'Show.S01E01.HDTV.X264-GROUP.mkv',
        'expected': False
    },
    {  # p10: Status is SNATCHED and new quality is higher: yes
        'cur_status': Quality.composite_status(SNATCHED, Quality.SDTV),
        'same_file': False,
        'check_quality_again': False,
        'anime': False,
        'filepath': 'Show.S01E01.720p.HDTV.X264-GROUP.mkv',
        'expected': True
    },
    {  # p11: Status is SNATCHED PROPER and new quality is higher NON-PROPER: yes
        'cur_status': Quality.composite_status(SNATCHED_PROPER, Quality.HDTV),
        'same_file': False,
        'check_quality_again': False,
        'anime': False,
        'filepath': 'Show.S01E01.1080p.HDTV.X264-GROUP.mkv',
        'expected': True
    },
    {  # p12: Status is SNATCHED PROPER and new quality is higher PROPER: yes
        'cur_status': Quality.composite_status(SNATCHED_PROPER, Quality.HDTV),
        'same_file': False,
        'check_quality_again': False,
        'anime': False,
        'filepath': 'Show.S01E01.1080p.HDTV.X264-GROUP.mkv',
        'expected': True
    },
    {  # p13: Status is SNATCHED PROPER and new quality is same: no
        'cur_status': Quality.composite_status(SNATCHED_PROPER, Quality.HDTV),
        'same_file': False,
        'check_quality_again': False,
        'anime': False,
        'filepath': 'Show.S01E01.720p.HDTV.X264-GROUP.mkv',
        'expected': False
    },
])
def test_should_refresh(p):
    """Run the test."""
    # Given
    cur_status = p['cur_status']
    same_file = p['same_file']
    check_quality_again = p['check_quality_again']
    anime = p['anime']
    filepath = p['filepath']
    expected = p['expected']

    # When
    replace, msg = Series.should_refresh_file(cur_status, same_file, check_quality_again, anime, filepath)
    actual = replace

    # Then
    if expected != actual:
        print msg
    assert expected == actual
