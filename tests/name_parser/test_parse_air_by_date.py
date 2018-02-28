# coding=utf-8
"""Tests for medusa/test_list_associated_files.py."""

from medusa import helpers
import medusa.scene_numbering
import medusa.scene_exceptions
from medusa.name_parser.parser import NameParser
import guessit
import pytest


# FIXME: Create meaningful test parameters for air by date shows.
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
            ('scene_numbering.get_indexer_numbering', None),
        ],
        'series_info':{
            'name': u'Cardcaptor Sakura'
        },
        'expected': ([8], [4], [78]),
    },

])
def test_air_by_date_parsing(p, monkeypatch_function_return, create_tvshow):
    monkeypatch_function_return(p['mocks'])
    parser = NameParser()
    guess = guessit.guessit(p['name'], dict(show_type='anime'))
    result = parser.to_parse_result(p['name'], guess)

    # confirm passed in show object indexer id matches result show object indexer id
    result.series = create_tvshow(name=p['series_info']['name'])

    actual = parser._parse_anime(result)

    expected = p['expected']

    assert expected == actual

