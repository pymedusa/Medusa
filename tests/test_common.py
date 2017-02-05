# coding=utf-8
"""Tests for medusa.common.py."""

from medusa.common import DOWNLOADED, Quality
import pytest


class TestQuality(object):
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
    def test_from_guessit(self, p):
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
    def test_to_guessit(self, p):
        # Given
        quality = Quality.composite_status(DOWNLOADED, p['quality'])
        expected = p['expected']

        # When
        actual = Quality.to_guessit(quality)

        # Then
        assert expected == actual
