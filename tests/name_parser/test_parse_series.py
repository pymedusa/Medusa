# coding=utf-8
"""Tests for medusa/test_list_associated_files.py."""

from medusa import helpers
import medusa.scene_numbering
import medusa.scene_exceptions
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
            'name': u'Cardcaptor Sakura'
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
            'name': u'Cardcaptor Sakura'
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
            'name': u'Cardcaptor Sakura'
        },
        'expected': ([8], [1], [8]),
    },
])
def test_series_parsing(p, monkeypatch, create_tvshow):

    # _parse_air_by_date
    # (season, episode) = scene_numbering.get_indexer_numbering(result.series, season_number, episode_number)
    def mock_get_indexer_numbering():
        return p['mocks']['get_indexer_numbering']

    # Series
    # a = helpers.get_absolute_number_from_season_and_episode(result.series, season, episode)
    def mock_get_absolute_number_from_season_and_episode():
        return p['mocks']['get_absolute_number_from_season_and_episode']

    def mock_get_show():
        return p['mocks']['get_show']

    monkeypatch.setattr(
        medusa.scene_numbering,
        'get_indexer_numbering',
        mock_get_indexer_numbering
    )

    monkeypatch.setattr(
        helpers,
        'get_absolute_number_from_season_and_episode',
        mock_get_absolute_number_from_season_and_episode
    )

    parser = NameParser()
    guess = guessit.guessit(p['name'])
    result = parser.to_parse_result(p['name'], guess)

    # confirm passed in show object indexer id matches result show object indexer id
    result.series = create_tvshow(name=p['series_info']['name'])

    actual = parser._parse_series(result)

    expected = p['expected']

    assert expected == actual
