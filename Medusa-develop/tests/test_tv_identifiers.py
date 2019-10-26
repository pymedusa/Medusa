# coding=utf-8
"""Tests for medusa.tv identifiers."""
from __future__ import unicode_literals

from datetime import datetime

from medusa.tv.episode import AbsoluteNumber, AirByDateNumber, EpisodeNumber, RelativeNumber
from medusa.tv.indexer import Indexer
from medusa.tv.series import SeriesIdentifier
import pytest


@pytest.mark.parametrize('p', [
    {  # p0: tvdb
        'slug': 'tvdb',
        'expected': Indexer(1),
    },
    {  # p1: tvmaze
        'slug': 'tvmaze',
        'expected': Indexer(3),
    },
    {  # p2: tmdb
        'slug': 'tmdb',
        'expected': Indexer(4),
    },
    {  # p3: invalid one
        'slug': 'another',
        'expected': None,
    }
])
def test_indexer_identifier(p):
    # Given
    slug = p['slug']
    expected = p['expected']

    # When
    actual = Indexer.from_slug(slug)

    # Then
    if expected is None:
        assert actual is None
    else:
        assert actual
        assert expected == actual
        assert Indexer(expected.id + 1) != actual
        assert expected.id != actual


@pytest.mark.parametrize('p', [
    {  # p0: tvdb
        'slug': 'tvdb1234',
        'expected': SeriesIdentifier(Indexer(1), 1234),
    },
    {  # p1: tvmaze
        'slug': 'tvmaze567',
        'expected': SeriesIdentifier(Indexer(3), 567),
    },
    {  # p2: tmdb
        'slug': 'tmdb89',
        'expected': SeriesIdentifier(Indexer(4), 89),
    },
    {  # p3: invalid one
        'slug': 'another1122',
        'expected': None,
    }
])
def test_series_identifier(p):
    # Given
    slug = p['slug']
    expected = p['expected']

    # When
    actual = SeriesIdentifier.from_slug(slug)

    # Then
    if expected is None:
        assert actual is None
    else:
        assert actual
        assert expected == actual
        assert expected.id == actual.id
        assert expected.indexer == actual.indexer
        assert expected.id != actual
        assert expected.indexer != actual


@pytest.mark.parametrize('p', [
    {  # p0: s1
        'slug': 's1',
        'expected': None,
    },
    {  # p1: s01
        'slug': 's01',
        'expected': None,
    },
    {  # p2: S01
        'slug': 'S01',
        'expected': None,
    },
    {  # p3: s12
        'slug': 's12',
        'expected': None,
    },
    {  # p4: s123
        'slug': 's123',
        'expected': None,
    },
    {  # p5: s1234
        'slug': 's1234',
        'expected': None,
    },
    {  # p6: s12345
        'slug': 's12345',
        'expected': None,
    },
    {  # p7: e2
        'slug': 'e2',
        'expected': AbsoluteNumber(2),
    },
    {  # p8: e02
        'slug': 'e02',
        'expected': AbsoluteNumber(2),
    },
    {  # p9: e12
        'slug': 'e12',
        'expected': AbsoluteNumber(12),
    },
    {  # p10: e123
        'slug': 'e123',
        'expected': AbsoluteNumber(123),
    },
    {  # p11: e1234
        'slug': 'e1234',
        'expected': AbsoluteNumber(1234),
    },
    {  # p12: E15
        'slug': 'E15',
        'expected': AbsoluteNumber(15),
    },
    {  # p13: s01e02
        'slug': 's01e02',
        'expected': RelativeNumber(1, 2),
    },
    {  # p14: s2017e02
        'slug': 's2017e02',
        'expected': RelativeNumber(2017, 2),
    },
    {  # p15: s01e9999
        'slug': 's01e9999',
        'expected': RelativeNumber(1, 9999),
    },
    {  # p16: 2017-07-16
        'slug': '2017-07-16',
        'expected': AirByDateNumber(datetime(year=2017, month=7, day=16)),
    },
    {  # p17: 2017-17-16 (invalid date)
        'slug': '2017-17-16',
        'expected': None,
    },
    {  # p18: Invalid
        'slug': 's01e022017-07-16',
        'expected': None,
    },
    {  # p19: Invalid
        'slug': '22017-07-16',
        'expected': None,
    },
    {  # p20: Invalid
        'slug': 'ss01',
        'expected': None,
    },
    {  # p21: Invalid
        'slug': 'ee01',
        'expected': None,
    },
])
def test_episode_identifier(p):
    # Given
    slug = p['slug']
    expected = p['expected']

    # When
    actual = EpisodeNumber.from_slug(slug)

    # Then
    if expected is None:
        assert not actual
    else:
        assert actual
        assert expected == actual
        assert slug != actual
