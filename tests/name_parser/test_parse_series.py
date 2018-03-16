# coding=utf-8
"""Tests for medusa/test_list_associated_files.py."""

from medusa.name_parser.parser import NameParser
from six import iteritems
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
])
def test_series_parsing(p, create_tvshow, monkeypatch_function_return):

    monkeypatch_function_return(p['mocks'])

    parser = NameParser()
    guess = guessit.guessit(p['name'])
    result = parser.to_parse_result(p['name'], guess)

    # confirm passed in show object indexer id matches result show object indexer id
    result.series = create_tvshow(name=p['series_info']['name'])
    result.series.scene = p['series_info']['is_scene']

    actual = parser._parse_series(result)

    expected = p['expected']

    assert expected == actual
