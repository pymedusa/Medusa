# coding=utf-8
"""Tests for air-by-date post-processor numbering preference."""
from __future__ import unicode_literals

from datetime import date

from medusa.name_parser.parser import NameParser, ParseResult
from medusa.post_processor import PostProcessor

from mock.mock import Mock


def test_analyze_name_prefers_sxex_over_rebroadcast_date(monkeypatch, create_tvshow):
    series = create_tvshow()
    series.air_by_date = 1
    parse_result = ParseResult(
        guess={'title': 'Show Name', 'season': 2, 'episode': 4, 'date': date(2010, 1, 24)},
        series_name='Show Name',
        season_number=2,
        episode_numbers=[4],
        air_date=date(2010, 1, 24),
    )
    parse_result.series = series

    monkeypatch.setattr(NameParser, 'parse', Mock(return_value=parse_result))

    processor = PostProcessor('/tmp/Show.Name.02x04.Title.Fr5.2010-01-24.mkv')
    show, season, episodes, quality, version = processor._analyze_name(processor.file_path)

    assert show is series
    assert season == 2
    assert episodes == [4]


def test_analyze_name_uses_airdate_when_no_episode_numbers(monkeypatch, create_tvshow):
    series = create_tvshow()
    series.air_by_date = 1
    air = date(2008, 12, 27)
    parse_result = ParseResult(
        guess={'title': 'Show Name', 'date': air},
        series_name='Show Name',
        air_date=air,
    )
    parse_result.series = series

    monkeypatch.setattr(NameParser, 'parse', Mock(return_value=parse_result))

    processor = PostProcessor('/tmp/Show.Name.Title_Fr5.2008-12-27.mkv')
    show, season, episodes, quality, version = processor._analyze_name(processor.file_path)

    assert show is series
    assert season == -1
    assert episodes == [air]
