# coding=utf-8
"""Tests for medusa/test_list_associated_files.py."""

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
        'mocks': {
            'get_scene_exceptions_by_name': [(70668, 2, 1)],
            'get_indexer_absolute_numbering': 78,
            'get_all_episodes_from_absolute_number': (4, [8])
        },
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
        'mocks': {
            'get_scene_exceptions_by_name': [(70668, 2, 1)],
            'get_indexer_absolute_numbering': 78,
            'get_all_episodes_from_absolute_number': (4, [8])
        },
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
        'mocks': {
            'get_scene_exceptions_by_name': [(None, None, None)],
            'get_indexer_absolute_numbering': 8,
            'get_all_episodes_from_absolute_number': (1, [8])
        },
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
        'mocks': {
            'get_scene_exceptions_by_name': [(None, None, None)],
            'get_indexer_absolute_numbering': 26,
            'get_all_episodes_from_absolute_number': (1, [26])
        },
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
        'mocks': {
            'get_scene_exceptions_by_name': [(262954, 3, 1)],
            'get_indexer_absolute_numbering': 52,
            'get_all_episodes_from_absolute_number': (2, [26])
        },
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
        'mocks': {
            'get_scene_exceptions_by_name': [(262954, 4, 1)],
            'get_indexer_absolute_numbering': 100,
            'get_all_episodes_from_absolute_number': (3, [26])
        },
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
        'mocks': {
            'get_scene_exceptions_by_name': [(None, None, None)],
            'get_absolute_number_from_season_and_episode': 26,
        },
        'series_info': {
            'name': u"JoJo's Bizarre Adventure",
            'is_scene': True
        },
        'expected': ([13], [2], [26]),
    },
    # Ajin season 2, ep 13 using a S0xE0x format.
    {
        'name': u'[DragsterPS].AJIN.Demi-Human.S02E13.[1080p].[Multi-Audio].[Multi-Subs].[B2041D7E]',
        'indexer_id': 1,
        'indexer': 300835,
        'mocks': {
            'get_scene_exceptions_by_name': [(None, None, None)],
            'get_absolute_number_from_season_and_episode': 26,
        },
        'series_info': {
            'name': u"JoJo's Bizarre Adventure",
            'is_scene': True
        },
        'expected': ([13], [2], [26]),
    },

])
def test_series_parsing(p, monkeypatch, create_tvshow):

    # Anime
    # a = scene_numbering.get_indexer_absolute_numbering(result.series, absolute_episode, True, scene_season)
    monkeypatch.setattr(
        'medusa.scene_numbering.get_indexer_absolute_numbering',
        lambda *args: p['mocks']['get_indexer_absolute_numbering']
    )

    # a = helpers.get_absolute_number_from_season_and_episode(result.series, season, episode)
    monkeypatch.setattr(
        'medusa.helpers.get_absolute_number_from_season_and_episode',
        lambda *args: p['mocks']['get_absolute_number_from_season_and_episode']
    )

    # scene_season = scene_exceptions.get_scene_exceptions_by_name(result.series_name)[0][1]
    monkeypatch.setattr(
        'medusa.scene_exceptions.get_scene_exceptions_by_name',
        lambda *args: p['mocks']['get_scene_exceptions_by_name']
    )

    # helpers.get_all_episodes_from_absolute_number(result.series, [a])
    monkeypatch.setattr(
        'medusa.helpers.get_all_episodes_from_absolute_number',
        lambda *args: p['mocks']['get_all_episodes_from_absolute_number']
    )

    parser = NameParser()
    guess = guessit.guessit(p['name'], dict(show_type='anime'))
    result = parser.to_parse_result(p['name'], guess)

    # confirm passed in show object indexer id matches result show object indexer id
    result.series = create_tvshow(name=p['series_info']['name'])
    result.scene = p['series_info']['is_scene']

    actual = parser._parse_anime(result)

    expected = p['expected']

    assert expected == actual

