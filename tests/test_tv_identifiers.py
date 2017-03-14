# coding=utf-8
"""Tests for medusa.tv identifiers"""
from datetime import datetime

from medusa.tv.base import Indexer
from medusa.tv.episode import EpisodeIdentifier
from medusa.tv.series import SeriesIdentifier
import pytest


@pytest.mark.parametrize('p', [
    {  # p0: tvdb
        'slug': 'tvdb',
        'expected': 1,
    },
    {  # p1: tvmaze
        'slug': 'tvmaze',
        'expected': 3,
    },
    {  # p2: tmdb
        'slug': 'tmdb',
        'expected': 4,
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
        assert slug == actual
        assert expected == actual
        assert Indexer(expected) == actual
        assert Indexer(expected + 1) != actual
        assert float(expected) != actual


@pytest.mark.parametrize('p', [
    {  # p0: tvdb
        'slug': 'tvdb1234',
        'expected_indexer': 1,
        'expected_indexer_id': 1234
    },
    {  # p1: tvmaze
        'slug': 'tvmaze567',
        'expected_indexer': 3,
        'expected_indexer_id': 567
    },
    {  # p2: tmdb
        'slug': 'tmdb89',
        'expected_indexer': 4,
        'expected_indexer_id': 89
    },
    {  # p3: invalid one
        'slug': 'another1122',
        'expected_indexer': None,
        'expected_indexer_id': None
    }
])
def test_series_identifier(p):
    # Given
    slug = p['slug']
    expected_indexer = p['expected_indexer']
    expected_indexer_id = p['expected_indexer_id']

    # When
    actual = SeriesIdentifier.from_slug(slug)

    # Then
    if expected_indexer is None:
        assert actual is None
    else:
        assert actual
        assert slug == actual
        assert expected_indexer == actual.indexer
        assert expected_indexer_id == actual.indexer_id
        assert expected_indexer != actual


@pytest.mark.parametrize('p', [
    {  # p0: s1
        'identifier': 's1',
        'expected': 's01',
        'expected_season': 1,
        'expected_episode': None,
        'expected_air_date': None,
    },
    {  # p1: s01
        'identifier': 's01',
        'expected': 's01',
        'expected_season': 1,
        'expected_episode': None,
        'expected_air_date': None,
    },
    {  # p2: S01
        'identifier': 'S01',
        'expected': 's01',
        'expected_season': 1,
        'expected_episode': None,
        'expected_air_date': None,
    },
    {  # p3: s12
        'identifier': 's12',
        'expected': 's12',
        'expected_season': 12,
        'expected_episode': None,
        'expected_air_date': None,
    },
    {  # p4: s123
        'identifier': 's123',
        'expected': 's123',
        'expected_season': 123,
        'expected_episode': None,
        'expected_air_date': None,
    },
    {  # p5: s1234
        'identifier': 's1234',
        'expected': 's1234',
        'expected_season': 1234,
        'expected_episode': None,
        'expected_air_date': None,
    },
    {  # p6: s12345
        'identifier': 's12345',
        'expected': None,
        'expected_season': None,
        'expected_episode': None,
        'expected_air_date': None,
    },
    {  # p7: e2
        'identifier': 'e2',
        'expected': 'e02',
        'expected_season': None,
        'expected_episode': 2,
        'expected_air_date': None,
    },
    {  # p8: e02
        'identifier': 'e02',
        'expected': 'e02',
        'expected_season': None,
        'expected_episode': 2,
        'expected_air_date': None,
    },
    {  # p9: e12
        'identifier': 'e12',
        'expected': 'e12',
        'expected_season': None,
        'expected_episode': 12,
        'expected_air_date': None,
    },
    {  # p10: e123
        'identifier': 'e123',
        'expected': 'e123',
        'expected_season': None,
        'expected_episode': 123,
        'expected_air_date': None,
    },
    {  # p11: e1234
        'identifier': 'e1234',
        'expected': None,
        'expected_season': None,
        'expected_episode': None,
        'expected_air_date': None,
    },
    {  # p12: E15
        'identifier': 'E15',
        'expected': 'e15',
        'expected_season': None,
        'expected_episode': 15,
        'expected_air_date': None,
    },
    {  # p13: s01e02
        'identifier': 's01e02',
        'expected': 's01e02',
        'expected_season': 1,
        'expected_episode': 2,
        'expected_air_date': None,
    },
    {  # p14: s2017e02
        'identifier': 's2017e02',
        'expected': 's2017e02',
        'expected_season': 2017,
        'expected_episode': 2,
        'expected_air_date': None,
    },
    {  # p15: 2017-07-16
        'identifier': '2017-07-16',
        'expected': '2017-07-16',
        'expected_season': None,
        'expected_episode': None,
        'expected_air_date': datetime.strptime('2017-07-16', '%Y-%m-%d'),
    },
    {  # p16: 2017-17-16 (invalid date)
        'identifier': '2017-17-16',
        'expected': None,
        'expected_season': None,
        'expected_episode': None,
        'expected_air_date': None,
    },
    {  # p17: Invalid
        'identifier': 's01e022017-07-16',
        'expected': None,
        'expected_season': None,
        'expected_episode': None,
        'expected_air_date': None,
    },
    {  # p18: Invalid
        'identifier': '22017-07-16',
        'expected': None,
        'expected_season': None,
        'expected_episode': None,
        'expected_air_date': None,
    },
    {  # p19: Invalid
        'identifier': 'ss01',
        'expected': None,
        'expected_season': None,
        'expected_episode': None,
        'expected_air_date': None,
    },
    {  # p20: Invalid
        'identifier': 'ee01',
        'expected': None,
        'expected_season': None,
        'expected_episode': None,
        'expected_air_date': None,
    },
])
def test_episode_identifier(p):
    # Given
    identifier = p['identifier']
    expected = p['expected']
    expected_season = p['expected_season']
    expected_episode = p['expected_episode']
    expected_air_date = p['expected_air_date']

    # When
    actual = EpisodeIdentifier.from_identifier(identifier)

    # Then
    if expected is None:
        assert actual is None
    else:
        assert actual
        assert expected == actual
        assert expected_season == actual.season
        assert expected_episode == actual.episode
        assert expected_air_date == actual.air_date
        assert expected_season != actual
