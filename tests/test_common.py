# coding=utf-8
"""Tests for medusa.common.py."""

from medusa.common import Quality

import pytest


@pytest.mark.parametrize('p', [
    {  # p0: No screen_size, no format
        'expected': Quality.UNKNOWN
    },
    {  # p1: screen_size but no format
        'screen_size': '720p',
        'expected': Quality.UNKNOWN
    },
    {  # p2: format but no screen_size
        'format': 'HDTV',
        'expected': Quality.UNKNOWN
    },
    {  # p3
        'screen_size': '720p',
        'format': 'HDTV',
        'expected': Quality.HDTV
    },
    {  # p4
        'screen_size': '720p',
        'format': 'WEB-DL',
        'expected': Quality.HDWEBDL
    },
    {  # p5
        'screen_size': '720p',
        'format': 'WEBRip',
        'expected': Quality.HDWEBDL
    },
    {  # p6
        'screen_size': '720p',
        'format': 'BluRay',
        'expected': Quality.HDBLURAY
    },
    {  # p7
        'screen_size': '1080i',
        'expected': Quality.RAWHDTV
    },
    {  # p8
        'screen_size': '1080p',
        'format': 'HDTV',
        'expected': Quality.FULLHDTV
    },
    {  # p9
        'screen_size': '1080p',
        'format': 'WEB-DL',
        'expected': Quality.FULLHDWEBDL
    },
    {  # p10
        'screen_size': '1080p',
        'format': 'WEBRip',
        'expected': Quality.FULLHDWEBDL
    },
    {  # p11
        'screen_size': '1080p',
        'format': 'BluRay',
        'expected': Quality.FULLHDBLURAY
    },
    {  # p12
        'screen_size': '4K',
        'format': 'HDTV',
        'expected': Quality.UHD_4K_TV
    },
    {  # p13
        'screen_size': '4K',
        'format': 'WEB-DL',
        'expected': Quality.UHD_4K_WEBDL
    },
    {  # p14
        'screen_size': '4K',
        'format': 'WEBRip',
        'expected': Quality.UHD_4K_WEBDL
    },
    {  # p15
        'screen_size': '4K',
        'format': 'BluRay',
        'expected': Quality.UHD_4K_BLURAY
    },
    {  # p16: multiple screen sizes
        'screen_size': ['4K', '720p'],
        'format': 'BluRay',
        'expected': Quality.UNKNOWN
    },
    {  # p17: multiple formats
        'screen_size': '720p',
        'format': ['HDTV', 'BluRay'],
        'expected': Quality.UNKNOWN
    },
    {  # p18: format not mapped (at least not yet)
        'screen_size': '480p',
        'format': 'HDTV',
        'expected': Quality.UNKNOWN
    },
])
def test_from_guessit(p):
    # Given
    guess = {
        'screen_size': p.get('screen_size'),
        'format': p.get('format'),
    }
    expected = p['expected']

    # When
    actual = Quality.from_guessit(guess)

    # Then
    assert expected == actual


@pytest.mark.parametrize('p', [
    {  # p0
        'quality': Quality.UNKNOWN,
        'expected': dict(),
    },
    {  # p1: invalid quality
        'quality': 0,
        'expected': dict()
    },
    {  # p2: another invalid quality
        'quality': 9999999,
        'expected': dict()
    },
    {  # p3
        'quality': Quality.HDTV,
        'expected': {
            'screen_size': '720p',
            'format': 'HDTV'
        }
    },
    {  # p4
        'quality': Quality.HDWEBDL,
        'expected': {
            'screen_size': '720p',
            'format': 'WEB-DL',
        }
    },
    {  # p5
        'quality': Quality.HDBLURAY,
        'expected': {
            'screen_size': '720p',
            'format': 'BluRay',
        }
    },
    {  # p6
        'quality': Quality.RAWHDTV,
        'expected': {
            'screen_size': '1080i'
        }
    },
    {  # p7
        'quality': Quality.FULLHDTV,
        'expected': {
            'screen_size': '1080p',
            'format': 'HDTV',
        }
    },
    {  # p8
        'quality': Quality.FULLHDWEBDL,
        'expected': {
            'screen_size': '1080p',
            'format': 'WEB-DL',
        }
    },
    {  # p9
        'quality': Quality.FULLHDBLURAY,
        'expected': {
            'screen_size': '1080p',
            'format': 'BluRay',
        }
    },
    {  # p10
        'quality': Quality.UHD_4K_TV,
        'expected': {
            'screen_size': '4K',
            'format': 'HDTV',
        }
    },
    {  # p11
        'quality': Quality.UHD_4K_WEBDL,
        'expected': {
            'screen_size': '4K',
            'format': 'WEB-DL',
        }
    },
    {  # p12
        'quality': Quality.UHD_4K_BLURAY,
        'expected': {
            'screen_size': '4K',
            'format': 'BluRay',
        }
    },
    {  # p13: guessit unsupported quality
        'quality': Quality.UHD_8K_BLURAY,
        'expected': dict()
    }
])
def test_to_guessit(p):
    # Given
    quality = p['quality']
    expected = p['expected']

    # When
    actual = Quality.to_guessit(quality)

    # Then
    assert expected == actual


@pytest.mark.parametrize('p', [
    {  # p0: no resolution, source or codec
        'name': 'Show Name - 2x03 - Ep Name.mkv',
        'expected': Quality.UNKNOWN
    },
    {  # p1: SDDVD, only source
        'name': 'Show Name - 2x03 - DVD - Ep Name.mkv',
        'expected': Quality.SDDVD
    },
    {  # p2: SDDVD, only source
        'name': 'Show Name - 2x03 - BluRay - Ep Name.mkv',
        'expected': Quality.SDDVD
    },
    {  # p3: SDTV, only source
        'name': 'Show Name - 2x03 - WEB - Ep Name.mkv',
        'expected': Quality.SDTV
    },
    {  # p4: SDTV, only source
        'name': 'Show Name - 2x03 - AMZN - Ep Name.mkv',
        'expected': Quality.SDTV
    },
    {  # p5: SDTV, only source
        'name': 'Show Name - 2x03 - DSR - Ep Name.mkv',
        'expected': Quality.SDTV
    },
    {  # p6: SDTV, only 480p resolution
        'name': 'Show Name - 2x03 - 480p - Ep Name.mkv',
        'expected': Quality.SDTV
    },
    {  # p7: SDTV, source and codec
        'name': 'Show Name - 2x03 - HDTV x264 - Ep Name.mkv',
        'expected': Quality.SDTV
    },
    {  # p8: SDTV, only source
        'name': 'Show Name - 2x03 - HDTV - Ep Name.mkv',
        'expected': Quality.SDTV
    },
    {  # p9: 720p, only with resolution
        'name': 'Show Name - 2x03 - 720p - Ep Name.mkv',
        'expected': Quality.HDTV
    },
    {  # p10: 720p, resolution and source
        'name': 'Show Name - 2x03 - 720p HDTV - Ep Name.mkv',
        'expected': Quality.HDTV
    },
    {  # p11: 720p, resolution, source and codec
        'name': 'Show Name - 2x03 - 720p HDTV x264 - Ep Name.mkv',
        'expected': Quality.HDTV
    },
    {  # p12: 720p, source and codec
        'name': 'Show Name - 2x03 - HR WS PDTV x264 - Ep Name.mkv',
        'expected': Quality.HDTV
    },
    {  # p13: 1080p, only with resolution
        'name': 'Show Name - 2x03 - 1080p - Ep Name.mkv',
        'expected': Quality.FULLHDTV
    },
    {  # p14: 1080p, resolution and source
        'name': 'Show Name - 2x03 - 1080p BluRay - Ep Name.mkv',
        'expected': Quality.FULLHDBLURAY
    },
    {  # p15: 1080p, resolution and source
        'name': 'Show Name - 2x03 - 1080p WEB - Ep Name.mkv',
        'expected': Quality.FULLHDWEBDL
    },
    {  # p16: 1080p, resolution and source
        'name': 'Show Name - 2x03 - 1080p AMZN - Ep Name.mkv',
        'expected': Quality.FULLHDWEBDL
    },
    {  # p17: 1080p, resolution, source and codec
        'name': 'Show Name - 2x03 - 1080p HDTV MPEG - Ep Name.mkv',
        'expected': Quality.RAWHDTV
    },
    {  # p18: 1080i, resolution, source and codec
        'name': 'Show Name - 2x03 - 1080i HDTV MPEG - Ep Name.mkv',
        'expected': Quality.RAWHDTV
    },
    {  # p19: 1080i, resolution, source and codec
        'name': 'Show Name - 2x03 - 1080i HDTV h264 - Ep Name.mkv',
        'expected': Quality.RAWHDTV
    },
    {  # p20: 2160p, resolution and source
        'name': 'Show Name - 2x03 - 2160p BluRay - Ep Name.mkv',
        'expected': Quality.UHD_4K_BLURAY
    },
    {  # p21: 2160p, resolution and source
        'name': 'Show Name - 2x03 - 2160p WEB - Ep Name.mkv',
        'expected': Quality.UHD_4K_WEBDL
    },
    {  # p22: 4320p, resolution and source
        'name': 'Show Name - 2x03 - 4320p HDTV - Ep Name.mkv',
        'expected': Quality.UHD_8K_TV
    },
    {  # p23: SDTV, anime, only resolution
        'name': 'Show Name - 2x03 - 480p - Ep Name.mkv',
        'anime': True,
        'expected': Quality.SDTV
    },
    {  # p24: SDDVD, anime, only source
        'name': 'Show Name - 2x03 - DVD - Ep Name.mkv',
        'anime': True,
        'expected': Quality.SDDVD
    },
    {  # p25: 720p, anime, resolution and source
        'name': 'Show Name - 2x03 - 720p BluRay - Ep Name.mkv',
        'anime': True,
        'expected': Quality.HDBLURAY
    },
    {  # p26: 720p, anime, only resolution
        'name': 'Show Name - 2x03 - 720p - Ep Name.mkv',
        'anime': True,
        'expected': Quality.HDTV
    },
    {  # p27: 1080p, anime, resolution and source
        'name': 'Show Name - 2x03 - 1080p BluRay - Ep Name.mkv',
        'anime': True,
        'expected': Quality.FULLHDBLURAY
    },
    {  # p28: 1080p, anime, only resolution
        'name': 'Show Name - 2x03 - 1080p - Ep Name.mkv',
        'anime': True,
        'expected': Quality.FULLHDTV
    },
])
def test_quality_from_name(p):
    # Given
    name = p['name']
    anime = p.get('anime', False)
    expected = p['expected']

    # When
    actual = Quality.quality_from_name(name, anime)

    # Then
    assert expected == actual


@pytest.mark.parametrize('p', [
    {  # p0 - No allowed / preferred
        'current_quality': Quality.HDTV,
        'new_quality': Quality.FULLHDTV,
        'allowed_qualities': [],
        'preferred_qualities': [],
        'expected': None
    },
    {  # p1 - Allowed -> Allowed upgrade
        'current_quality': Quality.HDTV,
        'new_quality': Quality.FULLHDTV,
        'allowed_qualities': [Quality.HDTV, Quality.FULLHDTV],
        'preferred_qualities': [],
        'expected': True
    },
    {  # p2 - Allowed -> Preferred upgrade
        'current_quality': Quality.HDTV,
        'new_quality': Quality.HDWEBDL,
        'allowed_qualities': [Quality.HDTV],
        'preferred_qualities': [Quality.HDWEBDL],
        'expected': True
    },
    {  # p3 - Preferred -> Preferred upgrade
        'current_quality': Quality.HDWEBDL,
        'new_quality': Quality.FULLHDWEBDL,
        'allowed_qualities': [],
        'preferred_qualities': [Quality.HDWEBDL, Quality.FULLHDWEBDL],
        'expected': True
    },
    {  # p4 - Allowed -> Allowed downgrade
        'current_quality': Quality.FULLHDTV,
        'new_quality': Quality.HDTV,
        'allowed_qualities': [Quality.HDTV, Quality.FULLHDTV],
        'preferred_qualities': [],
        'expected': False
    },
    {  # p5 - Allowed -> Preferred downgrade
        'current_quality': Quality.FULLHDTV,
        'new_quality': Quality.HDTV,
        'allowed_qualities': [Quality.FULLHDTV],
        'preferred_qualities': [Quality.HDTV],
        'expected': True
    },
    {  # p6 - Preferred -> Allowed downgrade
        'current_quality': Quality.FULLHDWEBDL,
        'new_quality': Quality.HDWEBDL,
        'allowed_qualities': [Quality.HDWEBDL],
        'preferred_qualities': [Quality.FULLHDWEBDL],
        'expected': False
    },
    {  # p7 - Preferred -> Preferred downgrade
        'current_quality': Quality.FULLHDWEBDL,
        'new_quality': Quality.HDWEBDL,
        'allowed_qualities': [],
        'preferred_qualities': [Quality.HDWEBDL, Quality.FULLHDWEBDL],
        'expected': False
    },
    {  # p8 - Current quality not in allowed
        'current_quality': Quality.NA,
        'new_quality': Quality.FULLHDTV,
        'allowed_qualities': [Quality.FULLHDTV],
        'preferred_qualities': [],
        'expected': True
    },
    {  # p9 - Current quality not in preferred
        'current_quality': Quality.NA,
        'new_quality': Quality.FULLHDTV,
        'allowed_qualities': [],
        'preferred_qualities': [Quality.FULLHDTV],
        'expected': True
    },
])
def test_is_higher_quality(p):
    # Given
    expected = p.pop('expected')
    kwargs = p

    # When
    actual = Quality.is_higher_quality(**kwargs)

    # Then
    assert expected == actual


def test_wanted_quality():
    # Given
    quality = Quality.FULLHDWEBDL
    allowed_qualities = [Quality.HDTV, Quality.HDWEBDL, Quality.HDBLURAY]
    preferred_qualities = [Quality.FULLHDTV, Quality.FULLHDWEBDL, Quality.FULLHDBLURAY]

    # When
    actual = Quality.wanted_quality(quality, allowed_qualities, preferred_qualities)

    # Then
    assert actual is True
