# coding=utf-8
"""Tests for medusa/test_list_associated_files.py."""
import os

import medusa.helpers
import medusa.scene_numbering
from medusa.name_parser.parser import NameParser

import pytest


@pytest.mark.parametrize('p', [
    {
        'name': '',
        'search_result': None,
        'expected': (),
    },
])
def test_series_parsing(p, create_structure, monkeypatch):

    def mock_get_indexer_numbering():
        return p['get_indexer_numbering']

    def mock_get_absolute_number_from_season_and_episode():
        return p['get_absolute_number_from_season_and_episode']

    monkeypatch.setattr(
        medusa.scene_numbering,
        'get_indexer_numbering',
        mock_get_indexer_numbering
    )

    monkeypatch.setattr(
        medusa.helpers,
        'absolute_number_from_season_and_episode',
        mock_get_absolute_number_from_season_and_episode
    )

    parser = NameParser()
    actual = parser._parse_series(p['search_result'])

    expected = p['expected']

    assert expected == actual

