# coding=utf-8
"""Tests for medusa/test_list_associated_files.py."""
from __future__ import unicode_literals

from medusa.name_parser.parser import NameParser

import guessit
import pytest


@pytest.mark.parametrize('p', [
    # The regular Show uses xem data. To map scene S06E29 to indexer S06E28
    {
        'name': u'Regular.Show.S06E29.Dumped.at.the.Altar.720p.HDTV.x264-W4F',
        'indexer_id': 1,
        'indexer': 188401,
        'mocks': [
            ('medusa.scene_numbering.get_indexer_numbering', (6, 28))
        ],
        'series_info': {
            'name': u'Regular Show',
            'is_scene': True
        },
        'expected': ([28], [6], []),
    },
    {
        'name': u'Inside.West.Coast.Customs.S06E04.720p.WEB.x264-TBS',
        'indexer_id': 1,
        'indexer': 307007,
        'mocks': [
            ('medusa.scene_numbering.get_indexer_numbering', (8, 4))
        ],
        'series_info': {
            'name': u'Inside West Coast Customs',
            'is_scene': True
        },
        'expected': ([4], [8], []),
    },
    {
        'name': u'The.100.S04E13.1080p.BluRay.x264-SPRINTER-Scrambled',
        'indexer_id': 1,
        'indexer': 307007,
        'mocks': [
            ('medusa.scene_numbering.get_indexer_numbering', (None, None))
        ],
        'series_info': {
            'name': u'The 100',
            'is_scene': False
        },
        'expected': ([13], [4], []),
    },
    {
        'name': u'American.Dad.S14E02.XviD-AFG',
        'indexer_id': 1,
        'indexer': 73141,
        'mocks': [
            ('medusa.scene_numbering.get_indexer_numbering', (15, 1))
        ],
        'series_info': {
            'name': u'American Dad',
            'is_scene': True
        },
        'expected': ([1], [15], []),
    },
    {
        'name': u'Universe.Possible.Worlds.S01E12.HDTV.x264-aAF',
        'indexer_id': 1,
        'indexer': 260586,
        'mocks': [
            ('medusa.scene_exceptions.get_season_from_name', 2),
            ('medusa.scene_numbering.get_indexer_numbering', (2, 12))
        ],
        'series_info': {
            'name': u'Universe (2014)',
            'is_scene': False
        },
        'expected': ([12], [2], []),
    },
    {
        'name': u'Universe.Possible.Worlds.S01E12.HDTV.x264-aAF',
        'indexer_id': 1,
        'indexer': 260586,
        'mocks': [
            ('medusa.scene_exceptions.get_season_from_name', 2),
            ('medusa.scene_numbering.get_indexer_numbering', (2, 12))
        ],
        'series_info': {
            'name': u'Universe (2014)',
            'is_scene': True
        },
        'expected': ([12], [2], []),
    },
    # Unique episode title must win over a conflicting parsed episode number.
    {
        'name': u'Show.Name.01l12.Wrong.Title.Should.Not.Matter',
        'indexer_id': 1,
        'indexer': 194591,
        'mocks': [
            ('medusa.scene_exceptions.get_season_from_name', None),
            ('medusa.scene_numbering.get_indexer_numbering', (None, None)),
        ],
        'series_info': {
            'name': u'Show Name',
            'is_scene': False,
        },
        'guess_override': {
            'title': 'Show Name',
            'season': 1,
            'episode': 1,
            'episode_title': 'Episode Beta',
            'type': 'episode',
        },
        'library_episodes': [
            {'season': 1, 'episode': 1, 'name': 'Episode Alpha'},
            {'season': 1, 'episode': 5, 'name': 'Episode Beta'},
        ],
        'expected': ([5], [1], []),
    },
    # Wrong release number + correct unique title => title wins (inversion fix).
    {
        'name': u'Show Name - 05 - Episode Gamma.avi',
        'indexer_id': 1,
        'indexer': 194591,
        'mocks': [
            ('medusa.scene_exceptions.get_season_from_name', None),
            ('medusa.scene_numbering.get_indexer_numbering', (None, None)),
        ],
        'series_info': {
            'name': u'Show Name',
            'is_scene': False,
        },
        'guess_override': {
            'title': 'Show Name',
            'season': 1,
            'episode': 5,
            'episode_title': 'Episode Gamma',
            'type': 'episode',
        },
        'library_episodes': [
            {'season': 1, 'episode': 5, 'name': 'Episode Beta'},
            {'season': 1, 'episode': 8, 'name': 'Episode Gamma'},
        ],
        'expected': ([8], [1], []),
    },
    # Ambiguous duplicated titles: number may disambiguate among title matches only.
    {
        'name': u'Show.Name.07l12.Shared.Title',
        'indexer_id': 1,
        'indexer': 194591,
        'mocks': [
            ('medusa.scene_exceptions.get_season_from_name', None),
            ('medusa.scene_numbering.get_indexer_numbering', (None, None)),
        ],
        'series_info': {
            'name': u'Show Name',
            'is_scene': False,
        },
        'guess_override': {
            'title': 'Show Name',
            'season': 1,
            'episode': 7,
            'episode_title': 'Shared Title',
            'type': 'episode',
        },
        'library_episodes': [
            {'season': 1, 'episode': 2, 'name': 'Shared Title'},
            {'season': 1, 'episode': 7, 'name': 'Shared Title'},
        ],
        'expected': ([7], [1], []),
    },
    # Ambiguous title + number outside title matches => refuse (do not trust number).
    {
        'name': u'Show.Name.05l12.Shared.Title',
        'indexer_id': 1,
        'indexer': 194591,
        'mocks': [
            ('medusa.scene_exceptions.get_season_from_name', None),
            ('medusa.scene_numbering.get_indexer_numbering', (None, None)),
        ],
        'series_info': {
            'name': u'Show Name',
            'is_scene': False,
        },
        'guess_override': {
            'title': 'Show Name',
            'season': 1,
            'episode': 5,
            'episode_title': 'Shared Title',
            'type': 'episode',
        },
        'library_episodes': [
            {'season': 1, 'episode': 2, 'name': 'Shared Title'},
            {'season': 1, 'episode': 7, 'name': 'Shared Title'},
            {'season': 1, 'episode': 5, 'name': 'Episode Beta'},
        ],
        'expected_exception': 'InvalidNameException',
    },
    # Title-only release (no episode number) resolves by unique title.
    {
        'name': u'Show.Name.Episode.Gamma.mkv',
        'indexer_id': 1,
        'indexer': 194591,
        'mocks': [
            ('medusa.scene_exceptions.get_season_from_name', None),
            ('medusa.scene_numbering.get_indexer_numbering', (None, None)),
        ],
        'series_info': {
            'name': u'Show Name',
            'is_scene': False,
        },
        'guess_override': {
            'title': 'Show Name',
            'episode_title': 'Episode Gamma',
            'type': 'episode',
        },
        'library_episodes': [
            {'season': 1, 'episode': 8, 'name': 'Episode Gamma'},
        ],
        'expected': ([8], [1], []),
    },
])
def test_series_parsing(p, create_tvshow, create_tvepisode, monkeypatch, monkeypatch_function_return):
    from medusa.name_parser.parser import InvalidNameException

    monkeypatch_function_return(p['mocks'])

    parser = NameParser()
    guess = p.get('guess_override') or guessit.guessit(p['name'])
    result = parser.to_parse_result(p['name'], guess)

    # confirm passed in show object indexer id matches result show object indexer id
    result.series = create_tvshow(name=p['series_info']['name'])
    result.series.scene = p['series_info']['is_scene']

    library_episodes = []
    for episode_info in p.get('library_episodes', []):
        library_episodes.append(create_tvepisode(
            result.series,
            episode_info['season'],
            episode_info['episode'],
            name=episode_info['name'],
        ))
    monkeypatch.setattr(result.series, 'get_all_episodes', lambda season=None, has_location=False: library_episodes)

    if p.get('expected_exception') == 'InvalidNameException':
        with pytest.raises(InvalidNameException):
            parser._parse_series(result)
        return

    actual = parser._parse_series(result)

    expected = p['expected']

    assert expected == actual


def test_parse_series_accepts_guessit_season_range_without_crash(create_tvshow, create_tvepisode, monkeypatch):
    """Season ranges (list) must not crash the year-as-season guard."""
    from medusa.name_parser.parser import ParseResult

    series = create_tvshow(name='Show Name')
    monkeypatch.setattr(series, 'get_all_episodes', lambda season=None, has_location=False: [])
    result = ParseResult(
        guess={'title': 'Show Name', 'season': [1, 2, 3, 4]},
        original_name='Show.Name.S01-04.1080p.mkv',
        series_name='Show Name',
        season_number=[1, 2, 3, 4],
        episode_numbers=[],
    )
    result.series = series

    episodes, seasons, absolutes = NameParser._parse_series(result)

    assert episodes == []
    assert absolutes == []
    assert seasons == [1, 2, 3, 4]
