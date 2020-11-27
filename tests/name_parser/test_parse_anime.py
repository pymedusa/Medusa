# coding=utf-8
"""Tests for medusa/test_list_associated_files.py."""
from __future__ import unicode_literals

from medusa.name_parser.parser import NameParser

import guessit
import pytest


@pytest.mark.parametrize('p', [
    {
        'name': u'[HorribleSubs] Cardcaptor Sakura Clear Card - 08 [720p].mkv',
        'indexer_id': 1,
        'indexer': 70668,
        'indexer_ep_season': 4,
        'indexer_ep_episodes': 8,
        'indexer_incorrect_absolute_ep_season': 1,
        'indexer_incorrect_absolute_ep_episodes': 8,
        'mocks': [
            ('medusa.scene_exceptions.get_season_from_name', 2),
            ('medusa.scene_numbering.get_indexer_abs_numbering', 78),
            ('medusa.helpers.get_all_episodes_from_absolute_number', (4, [8]))
        ],
        'series_info':{
            'name': u'Cardcaptor Sakura',
            'is_scene': True
        },
        'expected': ([8], [4], [78]),
    },
    {
        'name': u'[BakedFish].Cardcaptor.Sakura:.Clear.Card-hen.-.08.[720p][AAC]',
        'indexer_id': 1,
        'indexer': 70668,
        'indexer_ep_season': 4,
        'indexer_ep_episodes': 8,
        'indexer_incorrect_absolute_ep_season': 1,
        'indexer_incorrect_absolute_ep_episodes': 8,
        'mocks': [
            ('medusa.scene_exceptions.get_season_from_name', 2),
            ('medusa.scene_numbering.get_indexer_abs_numbering', 78),
            ('medusa.helpers.get_all_episodes_from_absolute_number', (4, [8]))
        ],
        'series_info': {
            'name': u'Cardcaptor Sakura',
            'is_scene': True
        },
        'expected': ([8], [4], [78]),
    },
    {
        'name': u'(Hi10).Cardcaptor.Sakura.-.08.(BD.1080p).(deanzel).(DualA).(4410B9A7)',
        'indexer_id': 1,
        'indexer': 70668,
        'indexer_ep_season': 4,
        'indexer_ep_episodes': 8,
        'indexer_incorrect_absolute_ep_season': 1,
        'indexer_incorrect_absolute_ep_episodes': 8,
        'mocks': [
            ('medusa.scene_exceptions.get_season_from_name', None),
            ('medusa.scene_numbering.get_indexer_abs_numbering', 8),
            ('medusa.helpers.get_all_episodes_from_absolute_number', (1, [8]))
        ],
        'series_info': {
            'name': u'Cardcaptor Sakura',
            'is_scene': True
        },
        'expected': ([8], [1], [8]),
    },
    # Jojo last episode of tvdb season 1. episode 26.
    {
        'name': u"JoJo's.Bizarre.Adventure.(2012).EP.26.The.Ascendant.One.(BD.AVC.1080p.FLAC.AC3).[Dual.Audio].[ACD1301E]",
        'indexer_id': 1,
        'indexer': 262954,
        'mocks': [
            ('medusa.scene_exceptions.get_season_from_name', None),
            ('medusa.scene_numbering.get_indexer_abs_numbering', 26),
            ('medusa.helpers.get_all_episodes_from_absolute_number', (1, [26]))
        ],
        'series_info': {
            'name': u"JoJo's.Bizarre.Adventure.(2012)",
            'is_scene': True
        },
        'expected': ([26], [1], [26]),
    },
    # Jojo last episode of tvdb season 1. episode 26.
    {
        'name': u"[HorribleSubs].JoJo's.Bizarre.Adventure.-.Stardust.Crusaders.Egypt.Arc.-.26.[1080p]",
        'indexer_id': 1,
        'indexer': 262954,
        'mocks': [
            ('medusa.scene_exceptions.get_season_from_name', 3),
            ('medusa.scene_numbering.get_indexer_abs_numbering', 52),
            ('medusa.helpers.get_all_episodes_from_absolute_number', (2, [26]))
        ],
        'series_info': {
            'name': u"JoJo's Bizarre Adventure",
            'is_scene': True
        },
        'expected': ([26], [2], [52]),
    },
    # Jojo last episode of tvdb season 1. episode 26.
    {
        'name': u"[HorribleSubs].JoJo's.Bizarre.Adventure.-.Diamond.is.Unbreakable.-.26.[1080p]",
        'indexer_id': 1,
        'indexer': 262954,
        'mocks': [
            ('medusa.scene_exceptions.get_season_from_name', 4),
            ('medusa.scene_numbering.get_indexer_abs_numbering', 100),
            ('medusa.helpers.get_all_episodes_from_absolute_number', (3, [26]))
        ],
        'series_info': {
            'name': u"JoJo's Bizarre Adventure",
            'is_scene': True
        },
        'expected': ([26], [3], [100]),
    },
    # Ajin season 2, ep 13 using a S0xE0x format.
    {
        'name': u'[Ajin2.com].Ajin.Season.2.Episode.13.[End].[720p].[Subbed]',
        'indexer_id': 1,
        'indexer': 300835,
        'mocks': [
            ('medusa.scene_exceptions.get_season_from_name', None),
            ('medusa.scene_numbering.get_indexer_numbering', (2, 13)),
            ('medusa.scene_numbering.get_indexer_abs_numbering', 26),
        ],
        'series_info': {
            'name': u"Ajin",
            'is_scene': True
        },
        'expected': ([13], [2], [26]),
    },
    # Ajin season 2, ep 13 using a S0xE0x format.
    {
        'name': u'[DragsterPS].AJIN.Demi-Human.S02E13.[1080p].[Multi-Audio].[Multi-Subs].[B2041D7E]',
        'indexer_id': 1,
        'indexer': 300835,
        'mocks': [
            ('medusa.scene_exceptions.get_season_from_name', None),
            ('medusa.scene_numbering.get_indexer_numbering', (2, 13)),
            ('medusa.scene_numbering.get_indexer_abs_numbering', 26),
        ],
        'series_info': {
            'name': u"Ajin",
            'is_scene': True
        },
        'expected': ([13], [2], [26]),
    },
    # Anime show, no scene names, no scene numbering.
    {
        'name': u'[Chotab].Dragon.Ball.Super.-.002.(BD.Hi10P.1080p).-.To.the.Promised.Resort!.Vegeta.Goes.on.a.Family.Trip!.[3814D4D3]',
        'indexer_id': 1,
        'indexer': 295068,
        'mocks': [
            ('medusa.scene_exceptions.get_season_from_name', None),
            ('medusa.scene_numbering.get_indexer_abs_numbering', 2),
            ('medusa.helpers.get_all_episodes_from_absolute_number', (1, [2]))
        ],
        'series_info': {
            'name': u"Dragon Ball Super",
            'is_scene': False
        },
        'expected': ([2], [1], [2]),
    },
    # Anime show, season scene name with one alias, with scene numbering. Using the season scene name.
    {
        'name': u"[HorribleSubs] JoJo's Bizarre Adventure - Stardust Crusaders - 12 [1080p].mkv",
        'indexer_id': 1,
        'indexer': 262954,
        'mocks': [
            ('medusa.scene_exceptions.get_season_from_name', 2),
            ('medusa.scene_numbering.get_indexer_abs_numbering', 38),
            ('medusa.helpers.get_all_episodes_from_absolute_number', (2, [12])),
        ],
        'series_info': {
            'name': u"JoJo's Bizarre Adventure",
            'is_scene': True
        },
        'expected': ([12], [2], [38]),
    },
    {
        'name': u"[HorribleSubs] JoJo's Bizarre Adventure - Stardust Crusaders - 12 [1080p].mkv",
        'indexer_id': 1,
        'indexer': 262954,
        'mocks': [
            ('medusa.scene_exceptions.get_season_from_name', 2),
            ('medusa.scene_numbering.get_indexer_abs_numbering', 38),
            ('medusa.helpers.get_all_episodes_from_absolute_number', (2, [12])),
        ],
        'series_info': {
            'name': u"JoJo's Bizarre Adventure",
            'is_scene': False
        },
        'expected': ([12], [2], [38]),
    },
    # Anime show, season scene name with two aliases because it's parsing the full path inc the show folder,
    # with scene numbering. Using the season scene name.
    {
        'name': u"JoJo's Bizarre Adventure (2012)\Season 02\[HorribleSubs] JoJo's Bizarre Adventure - Stardust Crusaders - 12 [1080p].mkv",
        'indexer_id': 1,
        'indexer': 262954,
        'mocks': [
            ('medusa.scene_exceptions.get_season_from_name', 2),
            ('medusa.scene_numbering.get_indexer_numbering', (2, 12)),
            ('medusa.scene_numbering.get_indexer_abs_numbering', 38),
        ],
        'series_info': {
            'name': u"JoJo's Bizarre Adventure",
            'is_scene': True
        },
        'expected': ([12], [2], [38]),
    },
    # Anime show, released as pseudo-absolute by scene
    {
        'name': u"One.Piece.S01E43.iTALiAN.PDTV.x264-iDiB",
        'indexer_id': 1,
        'indexer': 81797,
        'mocks': [
            ('medusa.scene_exceptions.get_season_from_name', None),
            ('medusa.scene_numbering.get_indexer_numbering', (3, 13)),
            ('medusa.scene_numbering.get_indexer_abs_numbering', 43),
        ],
        'series_info': {
            'name': u"One Piece",
            'is_scene': True
        },
        'expected': ([13], [3], [43]),
    },

])
def test_anime_parsing(p, create_tvshow, monkeypatch_function_return):
    """Test the function medusa.name_parser.NameParser().parser, for a number of (scene/non-scene) numbered
    anime shows.

    :p: List of parameters to test with.
    :create_tvshow: Fixture injected for creating a mock TvShow object. Found in conftest.py.
    :monkeypatch_function_return: Fixture to monkeypatch a list of tuples (configured through
    the pytest.mark.parameterize config)
    """
    monkeypatch_function_return(p['mocks'])

    parser = NameParser()
    guess = guessit.guessit(p['name'], dict(show_type='anime'))
    result = parser.to_parse_result(p['name'], guess)

    # confirm passed in show object indexer id matches result show object indexer id
    result.series = create_tvshow(name=p['series_info']['name'])
    result.series.scene = p['series_info']['is_scene']

    actual = parser._parse_anime(result)

    expected = p['expected']

    assert expected == actual
