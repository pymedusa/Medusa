# coding=utf-8
"""Tests for medusa/test_list_associated_files.py."""

import medusa.scene_numbering
import medusa.scene_exceptions
from medusa.name_parser.parser import NameParser
import guessit
import pytest


@pytest.mark.parametrize('p', [
    # The regular Show uses xem data. To map scene S06E29 to indexer S06E28
    {
        'name': u'Regular.Show.S06E29.Dumped.at.the.Altar.720p.HDTV.x264-W4F',
        'indexer_id': 1,
        'indexer': 188401,
        'mocks': {
            'get_indexer_numbering': (6, 28),
        },
        'series_info':{
            'name': u'Regular.Show'
        },
        'expected': ([28], [6], []),
    },
])
def test_series_parsing(p, monkeypatch, create_tvshow):

    # _parse_air_by_date
    # (season, episode) = scene_numbering.get_indexer_numbering(result.series, season_number, episode_number)
    def mock_get_indexer_numbering():
        return p['mocks']['get_indexer_numbering']

    monkeypatch.setattr(
        medusa.scene_numbering,
        'get_indexer_numbering',
        mock_get_indexer_numbering
    )

    parser = NameParser()
    guess = guessit.guessit(p['name'])
    result = parser.to_parse_result(p['name'], guess)

    # confirm passed in show object indexer id matches result show object indexer id
    result.series = create_tvshow(name=p['series_info']['name'])

    actual = parser._parse_series(result)

    expected = p['expected']

    assert expected == actual
