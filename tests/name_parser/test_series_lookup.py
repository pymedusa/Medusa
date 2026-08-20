# coding=utf-8
"""Tests for matching parsed series names to shows."""
from __future__ import unicode_literals

from medusa import helpers
from medusa.name_parser.parser import NameParser

import guessit
from mock.mock import Mock
import pytest


def test_year_alias_falls_back_to_matching_title(monkeypatch, create_tvshow):
    series = create_tvshow()
    series.start_year = 2026
    get_show = Mock(side_effect=[None, series])
    monkeypatch.setattr(helpers, 'get_show', get_show)
    monkeypatch.setattr(NameParser, '_parse_series', Mock(return_value=([1], [1], [])))

    result = NameParser()._parse_string('Lucky.2026.S01E01')

    assert result.series is series
    assert ['Lucky 2026', 'Lucky'] == [call[0][0] for call in get_show.call_args_list]


def test_year_alias_rejects_title_with_different_year(monkeypatch, create_tvshow):
    series = create_tvshow()
    series.start_year = 2012
    get_show = Mock(side_effect=[None, series])
    monkeypatch.setattr(helpers, 'get_show', get_show)

    result = NameParser()._parse_string('Lucky.2026.S01E01')

    assert result.series is None
    assert ['Lucky 2026', 'Lucky'] == [call[0][0] for call in get_show.call_args_list]


@pytest.mark.parametrize('parsed_guess', [
    {
        'title': 'The Office',
        'alias': 'The Office US',
        'country': 'US',
        'season': 1,
        'episode': 1,
    },
    {
        'title': 'Show Name',
        'alias': 'Show Name - Still Name',
        'alternative_title': 'Still Name',
        'season': 1,
        'episode': 1,
    },
])
def test_non_year_alias_does_not_fall_back_to_title(monkeypatch, parsed_guess):
    monkeypatch.setattr(guessit, 'guessit', Mock(return_value=parsed_guess))
    get_show = Mock(return_value=None)
    monkeypatch.setattr(helpers, 'get_show', get_show)

    result = NameParser()._parse_string('release-name')

    assert result.series is None
    assert 1 == get_show.call_count
    assert parsed_guess['alias'] == get_show.call_args[0][0]


def test_year_alias_match_remains_preferred(monkeypatch, create_tvshow):
    series = create_tvshow()
    get_show = Mock(return_value=series)
    monkeypatch.setattr(helpers, 'get_show', get_show)
    monkeypatch.setattr(NameParser, '_parse_series', Mock(return_value=([1], [1], [])))

    result = NameParser()._parse_string('Lucky.2026.S01E01')

    assert result.series is series
    assert 1 == get_show.call_count
    assert 'Lucky 2026' == get_show.call_args[0][0]
