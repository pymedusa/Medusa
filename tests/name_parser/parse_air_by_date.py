# coding=utf-8
"""Tests for medusa/test_list_associated_files.py."""
from __future__ import unicode_literals

from medusa import helpers
import medusa.scene_numbering
import medusa.scene_exceptions
from medusa.name_parser.parser import NameParser
import guessit
import pytest


# FIXME: Create meaningful test parameters for air by date shows.
@pytest.mark.parametrize('p', [
])
def test_air_by_date_parsing(p, monkeypatch_function_return, create_tvshow):
    monkeypatch_function_return(p['mocks'])
    parser = NameParser()
    guess = guessit.guessit(p['name'])
    result = parser.to_parse_result(p['name'], guess)

    # confirm passed in show object indexer id matches result show object indexer id
    result.series = create_tvshow(name=p['series_info']['name'])

    actual = parser._parse_anime(result)

    expected = p['expected']

    assert expected == actual

