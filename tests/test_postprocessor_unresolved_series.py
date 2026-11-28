# coding=utf-8
"""Tests for unresolved series error messaging during post-processing."""
from __future__ import unicode_literals

from medusa.name_parser.parser import InvalidNameException, InvalidShowException, NameParser, ParseResult
from medusa.post_processor import PostProcessor

from mock.mock import Mock
import pytest


def test_assert_supported_raises_unresolved_show_message():
    result = ParseResult(
        guess={'title': 'Show Name', 'season': 17, 'episode': 7},
        original_name='Show Name - 17x07 - Episode Title.ts',
        series_name='Show Name',
        season_number=17,
        episode_numbers=[7],
    )

    with pytest.raises(InvalidShowException) as exc_info:
        NameParser.assert_supported(result)

    error = exc_info.value
    assert error.series_name == 'Show Name'
    assert error.input_name == result.original_name
    assert str(error) == 'Unable to resolve parsed show "Show Name" to a series in Medusa'


def test_assert_supported_formats_list_title():
    result = ParseResult(
        guess={'title': ['Show Name', 'ALT']},
        original_name='folder/release.mkv',
        series_name=['Show Name', 'ALT'],
        season_number=4,
        episode_numbers=[2],
    )

    with pytest.raises(InvalidShowException) as exc_info:
        NameParser.assert_supported(result)

    assert exc_info.value.series_name == 'Show Name, ALT'
    assert 'Show Name, ALT' in str(exc_info.value)


def test_analyze_name_keeps_invalid_show_for_message(monkeypatch):
    processor = PostProcessor('/media/pp/show.mkv')
    error = InvalidShowException(
        'Unable to resolve parsed show "Show Name" to a series in Medusa',
        series_name='Show Name',
        input_name='Show Name - 17x07.ts',
    )
    monkeypatch.setattr(NameParser, 'parse', Mock(side_effect=error))

    show, season, episodes, quality, version = processor._analyze_name('Show Name - 17x07.ts')

    assert show is None
    assert season is None
    assert episodes == []
    assert processor._last_parse_error is error
    assert processor._unresolved_series_message() == (
        'Unable to resolve parsed show "Show Name" to a series in Medusa'
    )


def test_unresolved_message_for_invalid_name():
    processor = PostProcessor('/media/pp/show.mkv')
    processor._last_parse_error = InvalidNameException('bad numbering')

    assert processor._unresolved_series_message() == (
        'Unable to parse episode information from release'
    )


def test_unresolved_message_fallback_without_parse_error():
    processor = PostProcessor('/media/pp/show.mkv')

    assert processor._unresolved_series_message() == (
        'Unable to resolve release to a series in Medusa'
    )
