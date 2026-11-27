# coding=utf-8
"""Manual search heuristics must not affect ordinary release parsing."""
from unittest.mock import Mock

from medusa.name_parser.guessit_parser import guessit
from medusa.name_parser.parser import NameParser, ParseResult, name_parser_cache

import pytest


@pytest.mark.parametrize('release_name', [
    'Show Name - 01l12 - Episode Title (Fr.1997).mp4',
    'Show Name - 3x03bis - Long Episode Title.mkv',
    'Show Name - 11, 10 - Long Episode Title.mkv',
])
def test_broadcast_numbering_requires_manual_context(release_name):
    """Ordinary parsing retains GuessIt output before and after a manual parse."""
    ordinary = guessit(release_name, cached=False)
    manual = guessit(release_name, {'contextual_manual': True}, cached=False)
    repeated = guessit(release_name, cached=False)
    assert manual.get('episode') is not None
    assert (ordinary.get('season'), ordinary.get('episode')) != (manual.get('season'), manual.get('episode'))
    ordinary.pop('parsing_time')
    repeated.pop('parsing_time')
    assert ordinary == repeated


def test_broadcast_properties_require_manual_context():
    """Duration and channel patterns are disabled for automatic parsing."""
    release = 'Show Name - 1x02l10 - Episode Title - TF1 (41m20s) [720p] {GRP}.mkv'
    ordinary = guessit(release, cached=False)
    manual = guessit(release, {'contextual_manual': True}, cached=False)
    assert 'duration' not in ordinary
    assert manual['duration'] == '41m20s'
    assert manual['streaming_service'] == 'TF1'


def test_ordinary_parse_does_not_load_library_titles(create_tvshow, monkeypatch):
    """Even weak numbers remain unchanged outside manual episode search."""
    series = create_tvshow(name='Example Show')
    library_lookup = Mock(side_effect=AssertionError('ordinary parsing must not scan episode titles'))
    monkeypatch.setattr(series, 'get_all_episodes', library_lookup)
    monkeypatch.setattr('medusa.scene_exceptions.get_season_from_name', lambda *args: None)
    monkeypatch.setattr('medusa.scene_numbering.get_indexer_numbering', lambda *args: (None, None))
    result = ParseResult(guess={'episode_title': 'Episode Gamma'}, original_name='Example.Show.05.Episode.Gamma.mkv',
                         series_name=series.name, season_number=1, episode_numbers=[5])
    result.series = series
    assert NameParser._parse_series(result) == ([5], [1], [])
    library_lookup.assert_not_called()


def test_manual_parse_cannot_consume_or_populate_global_cache(monkeypatch):
    """Opting in cannot reuse an ordinary parse or contaminate its cache entry."""
    parser = NameParser(contextual_manual=True)
    ordinary = Mock()
    manual = Mock()
    monkeypatch.setattr(parser, '_parse_string', lambda name: manual)
    monkeypatch.setattr(parser, 'assert_supported', lambda result: None)
    name_parser_cache.clear()
    try:
        name_parser_cache.add('release.mkv', ordinary)
        assert parser.parse('release.mkv') is manual
        assert name_parser_cache.get('release.mkv') is ordinary
    finally:
        name_parser_cache.clear()


@pytest.mark.parametrize('contextual_manual', [False, True])
def test_titled_anime_retains_absolute_episode_mapping(create_tvshow, monkeypatch, contextual_manual):
    """Episode titles must not divert absolute numbering into season-pack parsing."""
    series = create_tvshow(name='Example Anime', anime=1, air_by_date=0, scene=0)
    release = 'Example.Anime.-.27.-.A.New.Journey.mkv'
    guess = {'title': series.name, 'episode_title': 'A New Journey', 'absolute_episode': 27}
    monkeypatch.setattr('medusa.name_parser.parser.guessit.guessit', lambda *args: guess)
    monkeypatch.setattr('medusa.helpers.get_show', lambda *args: series)
    monkeypatch.setattr('medusa.scene_exceptions.get_season_from_name', lambda *args: None)
    absolute_lookup = Mock(return_value=(2, [3]))
    monkeypatch.setattr('medusa.helpers.get_all_episodes_from_absolute_number', absolute_lookup)
    monkeypatch.setattr(NameParser, '_parse_series', Mock(side_effect=AssertionError('must use anime mapping')))

    result = NameParser(series=series, contextual_manual=contextual_manual).parse(
        release, use_cache=False, cache_result=False)

    absolute_lookup.assert_called_once_with(series, [27])
    assert result.season_number == 2
    assert result.episode_numbers == [3]
    assert result.ab_episode_numbers == [27]
