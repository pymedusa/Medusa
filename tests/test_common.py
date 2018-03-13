# coding=utf-8
"""Tests for medusa.common.py."""

from medusa.common import DOWNLOADED, Quality
import pytest


class TestQuality(object):
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
            'source': 'WEB-DL',
            'expected': Quality.HDWEBDL
        },
        {  # p5
            'screen_size': '720p',
            'source': 'WEBRip',
            'expected': Quality.HDWEBDL
        },
        {  # p6
            'screen_size': '720p',
            'source': 'BluRay',
            'expected': Quality.HDBLURAY
        },
        {  # p7
            'screen_size': '1080i',
            'expected': Quality.RAWHDTV
        },
        {  # p8
            'screen_size': '1080p',
            'source': 'HDTV',
            'expected': Quality.FULLHDTV
        },
        {  # p9
            'screen_size': '1080p',
            'source': 'WEB-DL',
            'expected': Quality.FULLHDWEBDL
        },
        {  # p10
            'screen_size': '1080p',
            'source': 'WEBRip',
            'expected': Quality.FULLHDWEBDL
        },
        {  # p11
            'screen_size': '1080p',
            'source': 'BluRay',
            'expected': Quality.FULLHDBLURAY
        },
        {  # p12
            'screen_size': '4K',
            'source': 'HDTV',
            'expected': Quality.UHD_4K_TV
        },
        {  # p13
            'screen_size': '4K',
            'source': 'WEB-DL',
            'expected': Quality.UHD_4K_WEBDL
        },
        {  # p14
            'screen_size': '4K',
            'source': 'WEBRip',
            'expected': Quality.UHD_4K_WEBDL
        },
        {  # p15
            'screen_size': '4K',
            'source': 'BluRay',
            'expected': Quality.UHD_4K_BLURAY
        },
        {  # p16: multiple screen sizes
            'screen_size': ['4K', '720p'],
            'source': 'BluRay',
            'expected': Quality.UNKNOWN
        },
        {  # p17: multiple sources
            'screen_size': '720p',
            'source': ['HDTV', 'BluRay'],
            'expected': Quality.UNKNOWN
        },
        {  # p18: source not mapped (at least not yet)
            'screen_size': '480p',
            'source': 'HDTV',
            'expected': Quality.UNKNOWN
        },
    ])
    def test_from_guessit(self, p):
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
                'source': 'WEB-DL',
            }
        },
        {  # p5
            'quality': Quality.HDBLURAY,
            'expected': {
                'screen_size': '720p',
                'source': 'BluRay',
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
                'source': 'WEB-DL',
            }
        },
        {  # p9
            'quality': Quality.FULLHDBLURAY,
            'expected': {
                'screen_size': '1080p',
                'source': 'BluRay',
            }
        },
        {  # p10
            'quality': Quality.UHD_4K_TV,
            'expected': {
                'screen_size': '4K',
                'source': 'HDTV',
            }
        },
        {  # p11
            'quality': Quality.UHD_4K_WEBDL,
            'expected': {
                'screen_size': '4K',
                'source': 'WEB-DL',
            }
        },
        {  # p12
            'quality': Quality.UHD_4K_BLURAY,
            'expected': {
                'screen_size': '4K',
                'source': 'BluRay',
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
