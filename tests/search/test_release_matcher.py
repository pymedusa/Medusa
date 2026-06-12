# coding=utf-8
"""Tests for contextual release matching."""

from __future__ import unicode_literals

from mock.mock import Mock, patch

import pytest

from medusa.providers.generic_provider import GenericProvider
from medusa.search.release_matcher import (
    ReleaseMatcher,
    extract_strong_numbering,
    is_explicit_season_pack,
    normalize_release_text,
    normalize_to_tokens,
    tokens_contain_sequence,
)


SHOW_NAME = 'Alpha Chronicle'
OTHER_SHOW = 'Beta Chronicle'
EPISODE_TITLE = 'First Contact'
OTHER_EPISODE_TITLE = 'Second Wave'


def _episode(season, episode, name):
    ep = Mock()
    ep.season = season
    ep.episode = episode
    ep.name = name
    return ep


def _series(name, episodes):
    series = Mock()
    series.name = name
    series.is_anime = False
    series.get_all_episodes.return_value = episodes
    return series


def _matcher(series, episodes):
    return ReleaseMatcher(series, episodes)


@pytest.fixture
def alpha_series():
    return _series(SHOW_NAME, [
        _episode(1, 1, EPISODE_TITLE),
        _episode(1, 2, OTHER_EPISODE_TITLE),
    ])


@pytest.fixture
def alpha_matcher(alpha_series):
    return _matcher(alpha_series, [_episode(1, 1, EPISODE_TITLE)])


def test_normalize_and_token_sequence():
    assert normalize_release_text("Alpha Chronicle") == 'alpha chronicle'
    assert normalize_to_tokens('[Uploader] Alpha.Chronicle') == ['uploader', 'alpha', 'chronicle']
    assert tokens_contain_sequence(['alpha', 'chronicle', 'first', 'contact'], ['alpha', 'chronicle']) is True
    assert tokens_contain_sequence(['beta', 'chronicle'], ['alpha', 'chronicle']) is False


def test_extract_strong_numbering():
    assert extract_strong_numbering('Alpha.Chronicle.S01E02.Title') == (1, [2])
    assert extract_strong_numbering('Alpha.Chronicle.1x02.Title') == (1, [2])
    assert extract_strong_numbering('Alpha.Chronicle.site-1--group') is None


@patch('medusa.search.release_matcher.scene_exceptions.get_all_scene_exceptions', return_value={})
@patch('medusa.search.release_matcher.scene_exceptions.get_season_scene_exceptions', return_value=[])
def test_explicit_numbering_match(_season_exc, _all_exc, alpha_matcher):
    release = 'Alpha.Chronicle.S01E01.mkv'
    match = alpha_matcher.match(release)
    assert match.matched is True
    assert match.method == 'explicit_numbering'
    assert match.episodes == [1]


@patch('medusa.search.release_matcher.scene_exceptions.get_all_scene_exceptions', return_value={})
@patch('medusa.search.release_matcher.scene_exceptions.get_season_scene_exceptions', return_value=[])
def test_explicit_numbering_without_title(_season_exc, _all_exc, alpha_matcher):
    release = 'Alpha.Chronicle.S01E01.1080p.WEB.mkv'
    match = alpha_matcher.match(release)
    assert match.matched is True
    assert match.method == 'explicit_numbering'


@patch('medusa.search.release_matcher.scene_exceptions.get_all_scene_exceptions', return_value={})
@patch('medusa.search.release_matcher.scene_exceptions.get_season_scene_exceptions', return_value=[])
def test_explicit_numbering_conflict(_season_exc, _all_exc, alpha_matcher):
    release = 'Alpha.Chronicle.S01E02.First.Contact.mkv'
    match = alpha_matcher.match(release)
    assert match.matched is False
    assert match.reason == 'explicit_number_conflict'


@patch('medusa.search.release_matcher.scene_exceptions.get_all_scene_exceptions', return_value={})
@patch('medusa.search.release_matcher.scene_exceptions.get_season_scene_exceptions', return_value=[])
def test_title_match_without_numbering(_season_exc, _all_exc, alpha_matcher):
    release = 'Alpha.Chronicle.-.Segment.-.First.Contact.-.suffix.mkv'
    match = alpha_matcher.match(release)
    assert match.matched is True
    assert match.method == 'episode_title'
    assert match.season == 1
    assert match.episodes == [1]


@patch('medusa.search.release_matcher.scene_exceptions.get_all_scene_exceptions', return_value={})
@patch('medusa.search.release_matcher.scene_exceptions.get_season_scene_exceptions', return_value=[])
def test_prefix_before_series_title(_season_exc, _all_exc, alpha_matcher):
    release = '[Uploader] Alpha.Chronicle.-.First.Contact.mkv'
    match = alpha_matcher.match(release)
    assert match.matched is True
    assert match.method == 'episode_title'


@patch('medusa.search.release_matcher.scene_exceptions.get_all_scene_exceptions', return_value={})
@patch('medusa.search.release_matcher.scene_exceptions.get_season_scene_exceptions', return_value=[])
def test_suffix_after_episode_title(_season_exc, _all_exc, alpha_matcher):
    release = 'Alpha.Chronicle.-.First.Contact.-.website-1--group.mkv'
    parsed = Mock()
    parsed.episode_numbers = [1]
    parsed.guess = {'episode': [1]}
    match = alpha_matcher.match(release, parsed_result=parsed)
    assert match.matched is True
    assert match.method == 'weak_number_ignored'


@patch('medusa.search.release_matcher.scene_exceptions.get_all_scene_exceptions', return_value={})
@patch('medusa.search.release_matcher.scene_exceptions.get_season_scene_exceptions', return_value=[])
def test_weak_number_without_title_rejected(_season_exc, _all_exc, alpha_matcher):
    release = 'Alpha.Chronicle.-.website-1--group.mkv'
    parsed = Mock()
    parsed.episode_numbers = [1]
    parsed.guess = {'episode': [1]}
    match = alpha_matcher.match(release, parsed_result=parsed)
    assert match.matched is False
    assert match.reason == 'episode_title_not_found'


@patch('medusa.search.release_matcher.scene_exceptions.get_all_scene_exceptions', return_value={})
@patch('medusa.search.release_matcher.scene_exceptions.get_season_scene_exceptions', return_value=[])
def test_other_series_rejected(_season_exc, _all_exc):
    series = _series(OTHER_SHOW, [_episode(1, 1, EPISODE_TITLE)])
    matcher = _matcher(series, [_episode(1, 1, EPISODE_TITLE)])
    release = 'Beta.Chronicle.-.First.Contact.mkv'
    assert matcher.matches_series(release) is True
    matcher = _matcher(_series(SHOW_NAME, [_episode(1, 1, EPISODE_TITLE)]), [_episode(1, 1, EPISODE_TITLE)])
    match = matcher.match(release)
    assert match.matched is False
    assert match.reason == 'series_not_found'


@patch('medusa.search.release_matcher.scene_exceptions.get_all_scene_exceptions', return_value={})
@patch('medusa.search.release_matcher.scene_exceptions.get_season_scene_exceptions', return_value=[])
def test_duplicate_episode_titles_rejected(_season_exc, _all_exc):
    episodes = [
        _episode(1, 1, 'Shared Title'),
        _episode(2, 1, 'Shared Title'),
    ]
    series = _series(SHOW_NAME, episodes)
    matcher = _matcher(series, [episodes[0]])
    release = 'Alpha.Chronicle.-.Shared.Title.mkv'
    match = matcher.match(release)
    assert match.matched is False
    assert match.reason == 'ambiguous_episode_title'


@patch('medusa.search.release_matcher.scene_exceptions.get_all_scene_exceptions', return_value={})
@patch('medusa.search.release_matcher.scene_exceptions.get_season_scene_exceptions', return_value=[])
def test_short_series_title_not_matched_inside_unrelated_word(_season_exc, _all_exc):
    series = _series('Go', [_episode(1, 1, EPISODE_TITLE)])
    matcher = _matcher(series, [_episode(1, 1, EPISODE_TITLE)])
    release = 'Dragon.-.First.Contact.mkv'
    assert matcher.matches_series(release) is False


@patch('medusa.search.release_matcher.scene_exceptions.get_all_scene_exceptions', return_value={})
@patch('medusa.search.release_matcher.scene_exceptions.get_season_scene_exceptions', return_value=[])
def test_unresolved_release_not_season_pack(_season_exc, _all_exc, alpha_matcher):
    release = 'Alpha.Chronicle.-.Unrelated.Segment.mkv'
    match = alpha_matcher.match(release)
    assert match.matched is False
    assert match.reason == 'episode_title_not_found'


@patch('medusa.search.release_matcher.scene_exceptions.get_all_scene_exceptions', return_value={})
@patch('medusa.search.release_matcher.scene_exceptions.get_season_scene_exceptions', return_value=[])
def test_explicit_season_pack_marker_rejected_for_single_episode(_season_exc, _all_exc, alpha_matcher):
    release = 'Alpha.Chronicle.Season.1.Complete.mkv'
    assert is_explicit_season_pack(release) is True
    match = alpha_matcher.match(release)
    assert match.matched is False
    assert match.reason == 'implicit_season_pack'


def test_contextual_matching_gate():
    assert GenericProvider._use_contextual_matching(True, [Mock()], 'eponly', 'episode') is True
    assert GenericProvider._use_contextual_matching(True, [Mock(), Mock()], 'eponly', 'episode') is False
    assert GenericProvider._use_contextual_matching(True, [Mock()], 'sponly', 'episode') is False
    assert GenericProvider._use_contextual_matching(True, [Mock()], 'eponly', 'season') is False
    assert GenericProvider._use_contextual_matching(False, [Mock()], 'eponly', 'episode') is False


def test_non_manual_path_uses_strict_parser_only():
    search_result = Mock()
    search_result.name = 'Alpha.Chronicle.S01E01.mkv'
    search_result.add_cache_entry = True
    search_result.result_wanted = True

    series = Mock()
    series.is_anime = False

    parsed = Mock()
    parsed.series = series
    parsed.quality = 1
    parsed.release_group = 'GROUP'
    parsed.version = -1
    parsed.season_number = 1
    parsed.episode_numbers = [1]

    provider = GenericProvider('TestProvider')
    with patch('medusa.providers.generic_provider.NameParser') as parser_cls:
        parser_cls.return_value.parse.return_value = parsed
        assert provider._use_contextual_matching(False, [Mock()], 'eponly', 'episode') is False
