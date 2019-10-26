# coding=utf-8
"""Tests for medusa.common.py."""
from __future__ import unicode_literals

from medusa.common import Quality

import pytest


@pytest.mark.parametrize('p', [
    {  # p0: No screen_size, no source
        'expected': Quality.UNKNOWN
    },
    {  # p1: screen_size but no source
        'screen_size': '720p',
        'expected': Quality.UNKNOWN
    },
    {  # p2: source but no screen_size
        'source': 'HDTV',
        'expected': Quality.UNKNOWN
    },
    {  # p3
        'screen_size': '720p',
        'source': 'HDTV',
        'expected': Quality.HDTV
    },
    {  # p4
        'screen_size': '720p',
        'source': 'Web',
        'expected': Quality.HDWEBDL
    },
    {  # p5
        'screen_size': '720p',
        'source': 'Blu-ray',
        'expected': Quality.HDBLURAY
    },
    {  # p6
        'screen_size': '1080i',
        'expected': Quality.RAWHDTV
    },
    {  # p7
        'screen_size': '1080p',
        'source': 'HDTV',
        'expected': Quality.FULLHDTV
    },
    {  # p8
        'screen_size': '1080p',
        'source': 'Web',
        'expected': Quality.FULLHDWEBDL
    },
    {  # p9
        'screen_size': '1080p',
        'source': 'Blu-ray',
        'expected': Quality.FULLHDBLURAY
    },
    {  # p10
        'screen_size': '2160p',
        'source': 'HDTV',
        'expected': Quality.UHD_4K_TV
    },
    {  # p11
        'screen_size': '2160p',
        'source': 'Web',
        'expected': Quality.UHD_4K_WEBDL
    },
    {  # p12
        'screen_size': '2160p',
        'source': 'Blu-ray',
        'expected': Quality.UHD_4K_BLURAY
    },
    {  # p13
        'screen_size': '4320p',
        'source': 'HDTV',
        'expected': Quality.UHD_8K_TV
    },
    {  # p14
        'screen_size': '4320p',
        'source': 'Web',
        'expected': Quality.UHD_8K_WEBDL
    },
    {  # p15
        'screen_size': '4320p',
        'source': 'Blu-ray',
        'expected': Quality.UHD_8K_BLURAY
    },
    {  # p16: multiple screen sizes
        'screen_size': ['2160p', '720p'],
        'source': 'Blu-ray',
        'expected': Quality.UNKNOWN
    },
    {  # p17: multiple sources
        'screen_size': '720p',
        'source': ['HDTV', 'Blu-ray'],
        'expected': Quality.UNKNOWN
    },
    {  # p18: source not mapped (at least not yet)
        'screen_size': '480p',
        'source': 'HDTV',
        'expected': Quality.UNKNOWN
    },
])
def test_from_guessit(p):
    # Given
    guess = {
        'screen_size': p.get('screen_size'),
        'source': p.get('source'),
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
            'source': 'HDTV'
        }
    },
    {  # p4
        'quality': Quality.HDWEBDL,
        'expected': {
            'screen_size': '720p',
            'source': 'Web',
        }
    },
    {  # p5
        'quality': Quality.HDBLURAY,
        'expected': {
            'screen_size': '720p',
            'source': 'Blu-ray',
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
            'source': 'HDTV',
        }
    },
    {  # p8
        'quality': Quality.FULLHDWEBDL,
        'expected': {
            'screen_size': '1080p',
            'source': 'Web',
        }
    },
    {  # p9
        'quality': Quality.FULLHDBLURAY,
        'expected': {
            'screen_size': '1080p',
            'source': 'Blu-ray',
        }
    },
    {  # p10
        'quality': Quality.UHD_4K_TV,
        'expected': {
            'screen_size': '2160p',
            'source': 'HDTV',
        }
    },
    {  # p11
        'quality': Quality.UHD_4K_WEBDL,
        'expected': {
            'screen_size': '2160p',
            'source': 'Web',
        }
    },
    {  # p12
        'quality': Quality.UHD_4K_BLURAY,
        'expected': {
            'screen_size': '2160p',
            'source': 'Blu-ray',
        }
    },
    {  # p13
        'quality': Quality.UHD_8K_TV,
        'expected': {
            'screen_size': '4320p',
            'source': 'HDTV',
        }
    },
    {  # p14
        'quality': Quality.UHD_8K_WEBDL,
        'expected': {
            'screen_size': '4320p',
            'source': 'Web',
        }
    },
    {  # p15
        'quality': Quality.UHD_8K_BLURAY,
        'expected': {
            'screen_size': '4320p',
            'source': 'Blu-ray',
        }
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


@pytest.mark.parametrize('p', [
    {  # p0 - Invalid combined quality
        'quality': -4,
        'expected': False
    },
    {  # p1 - Valid 'allowed' quality
        'quality': Quality.HDTV,
        'expected': True
    },
    {  # p2 - Valid 'allowed' quality + valid 'preferred' quality
        'quality': Quality.combine_qualities([Quality.HDTV], [Quality.HDWEBDL]),
        'expected': True
    },
    {  # p3 - Valid 'allowed' quality + **invalid** 'preferred' quality
        'quality': Quality.combine_qualities([Quality.HDTV], [-4]),
        'expected': False
    },
])
def test_is_valid_combined_quality(p):
    # Given
    quality = p['quality']
    expected = p['expected']

    # When
    actual = Quality.is_valid_combined_quality(quality)

    # Then
    assert expected == actual
