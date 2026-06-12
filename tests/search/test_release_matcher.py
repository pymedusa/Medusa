# coding=utf-8
"""Tests for contextual release matching."""

from __future__ import unicode_literals

from mock.mock import Mock, patch

import pytest

from medusa.name_parser.parser import InvalidNameException
from medusa.providers.generic_provider import GenericProvider
from medusa.search.release_matcher import (
    ReleaseMatch,
    ReleaseMatcher,
    extract_strong_numbering,
    has_explicit_non_video_extension,
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


def _series(name, episodes, **kwargs):
    series = Mock()
    series.name = name
    series.is_anime = kwargs.get('is_anime', False)
    series.is_scene = kwargs.get('is_scene', False)
    series.indexer = kwargs.get('indexer', 1)
    series.series_id = kwargs.get('series_id', 100)
    series.get_all_episodes.return_value = episodes
    return series


def _scene_episode(season, episode, scene_season, scene_episode, name):
    ep = _episode(season, episode, name)
    ep.scene_season = scene_season
    ep.scene_episode = scene_episode
    return ep


@pytest.fixture(autouse=True)
def mock_scene_exceptions():
    with patch('medusa.search.release_matcher.scene_exceptions.get_season_scene_exceptions', return_value=[]):
        yield


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


def test_normalize_punctuation_variants():
    assert normalize_release_text('Alpha, Chronicle') == 'alpha chronicle'
    assert normalize_release_text('Alpha.Series') == 'alpha series'
    assert normalize_release_text('First Contact: Part One') == 'first contact part one'
    assert normalize_release_text('Alpha & Chronicle') == 'alpha chronicle'
    assert normalize_to_tokens('Alpha, Chronicle') == normalize_to_tokens('Alpha.Chronicle')


def test_extract_strong_numbering():
    assert extract_strong_numbering('Alpha.Chronicle.S01E02.Title') == (1, [2])
    assert extract_strong_numbering('Alpha.Chronicle.1x02.Title') == (1, [2])
    assert extract_strong_numbering('Alpha.Chronicle.site-1--group') is None


def test_explicit_numbering_match(alpha_matcher):
    release = 'Alpha.Chronicle.S01E01.mkv'
    match = alpha_matcher.match(release)
    assert match.matched is True
    assert match.method == 'explicit_numbering'
    assert match.episodes == [1]


def test_explicit_numbering_without_title(alpha_matcher):
    release = 'Alpha.Chronicle.S01E01.1080p.WEB.mkv'
    match = alpha_matcher.match(release)
    assert match.matched is True
    assert match.method == 'explicit_numbering'


def test_explicit_numbering_conflict(alpha_matcher):
    release = 'Alpha.Chronicle.S01E02.First.Contact.mkv'
    match = alpha_matcher.match(release)
    assert match.matched is False
    assert match.reason == 'explicit_number_conflict'


def test_title_match_without_numbering(alpha_matcher):
    release = 'Alpha.Chronicle.-.Segment.-.First.Contact.-.suffix.mkv'
    match = alpha_matcher.match(release)
    assert match.matched is True
    assert match.method == 'episode_title'
    assert match.season == 1
    assert match.episodes == [1]


def test_prefix_before_series_title(alpha_matcher):
    release = '[Uploader] Alpha.Chronicle.-.First.Contact.mkv'
    match = alpha_matcher.match(release)
    assert match.matched is True
    assert match.method == 'episode_title'


def test_suffix_after_episode_title(alpha_matcher):
    release = 'Alpha.Chronicle.-.First.Contact.-.website-1--group.mkv'
    parsed = Mock()
    parsed.episode_numbers = [1]
    parsed.guess = {'episode': [1]}
    match = alpha_matcher.match(release, parsed_result=parsed)
    assert match.matched is True
    assert match.method == 'weak_number_ignored'


def test_weak_number_without_title_rejected(alpha_matcher):
    release = 'Alpha.Chronicle.-.website-1--group.mkv'
    parsed = Mock()
    parsed.episode_numbers = [1]
    parsed.guess = {'episode': [1]}
    match = alpha_matcher.match(release, parsed_result=parsed)
    assert match.matched is False
    assert match.reason == 'episode_title_not_found'


def test_other_series_rejected():
    series = _series(OTHER_SHOW, [_episode(1, 1, EPISODE_TITLE)])
    matcher = _matcher(series, [_episode(1, 1, EPISODE_TITLE)])
    release = 'Beta.Chronicle.-.First.Contact.mkv'
    assert matcher.matches_series(release) is True
    matcher = _matcher(_series(SHOW_NAME, [_episode(1, 1, EPISODE_TITLE)]), [_episode(1, 1, EPISODE_TITLE)])
    match = matcher.match(release)
    assert match.matched is False
    assert match.reason == 'series_not_found'


def test_duplicate_episode_titles_rejected():
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


def test_short_series_title_not_matched_inside_unrelated_word():
    series = _series('Go', [_episode(1, 1, EPISODE_TITLE)])
    matcher = _matcher(series, [_episode(1, 1, EPISODE_TITLE)])
    release = 'Dragon.-.First.Contact.mkv'
    assert matcher.matches_series(release) is False


def test_unresolved_release_not_season_pack(alpha_matcher):
    release = 'Alpha.Chronicle.-.Unrelated.Segment.mkv'
    match = alpha_matcher.match(release)
    assert match.matched is False
    assert match.reason == 'episode_title_not_found'


def test_explicit_season_pack_marker_rejected_for_single_episode(alpha_matcher):
    release = 'Alpha.Chronicle.Season.1.Complete.mkv'
    assert is_explicit_season_pack(release) is True
    match = alpha_matcher.match(release)
    assert match.matched is False
    assert match.reason == 'implicit_season_pack'


def test_non_video_extension_has_dedicated_rejection_reason(alpha_matcher):
    match = alpha_matcher.match('Alpha Chronicle - First Contact.nfo')
    assert match.matched is False
    assert match.reason == 'non_video_extension'


def test_rar_extension_is_not_rejected_as_non_video():
    assert not has_explicit_non_video_extension('Alpha Chronicle - First Contact.rar')


def test_multipart_rar_extension_is_not_rejected_as_non_video():
    assert not has_explicit_non_video_extension(
        'Alpha Chronicle - First Contact.part01.rar'
    )


def test_contextual_match_accepts_processable_rar_release(alpha_matcher):
    result = alpha_matcher.match('Alpha Chronicle - First Contact.part01.rar')
    assert result.matched is True
    assert result.reason != 'non_video_extension'


def test_contextual_matching_gate():
    assert GenericProvider._use_contextual_matching(True, [Mock()], 'eponly', 'episode') is True
    assert GenericProvider._use_contextual_matching(True, [Mock(), Mock()], 'eponly', 'episode') is False
    assert GenericProvider._use_contextual_matching(True, [Mock()], 'sponly', 'episode') is False
    assert GenericProvider._use_contextual_matching(True, [Mock()], 'eponly', 'season') is False
    assert GenericProvider._use_contextual_matching(False, [Mock()], 'eponly', 'episode') is False


def test_non_manual_path_uses_strict_parser_only():
    provider = GenericProvider('TestProvider')
    episode = _episode(1, 1, EPISODE_TITLE)
    series = _series(SHOW_NAME, [episode])
    series.air_by_date = False
    series.sports = False

    search_result = Mock()
    search_result.name = 'Alpha.Chronicle.S01E01.mkv'
    search_result.add_cache_entry = False
    search_result.result_wanted = True
    search_result.quality = 0
    search_result.episode_number = 1
    search_result.update_search_result = Mock()
    search_result.add_result_to_cache = Mock(return_value=None)

    parsed = Mock()
    parsed.series = series
    parsed.quality = 1
    parsed.release_group = 'GROUP'
    parsed.version = -1
    parsed.season_number = 1
    parsed.episode_numbers = [1]

    with patch.object(provider, '_check_auth'), \
         patch.object(provider, '_get_episode_search_strings', return_value=['Alpha Chronicle S01E01']), \
         patch.object(provider, 'search', return_value=[Mock()]), \
         patch.object(provider, 'get_result', return_value=search_result), \
         patch.object(provider, '_apply_contextual_manual_parse') as contextual_parse, \
         patch('medusa.providers.generic_provider.NameParser') as parser_cls:
        parser_cls.return_value.parse.return_value = parsed
        provider.find_search_results(
            series,
            [episode],
            'eponly',
            manual_search=False,
            manual_search_type='episode',
        )

    contextual_parse.assert_not_called()
    parser_cls.return_value.parse.assert_called_once_with(search_result.name)
    assert search_result.actual_season == 1
    assert search_result.actual_episodes == [1]


def test_scene_numbering_explicit_match():
    target = _scene_episode(2, 5, 1, 5, EPISODE_TITLE)
    series = _series(SHOW_NAME, [target], is_scene=True)
    matcher = _matcher(series, [target])
    match = matcher.match('Alpha.Chronicle.S01E05.mkv')
    assert match.matched is True
    assert match.method == 'explicit_numbering'
    assert match.season == 2
    assert match.episodes == [5]


def test_season_exceptions_limited_to_target_season():
    season_five_alias = Mock(title='Season Five Alias')
    target = _episode(1, 1, EPISODE_TITLE)

    def season_exceptions(series, season):
        if season == 5:
            return [season_five_alias]
        return []

    with patch(
        'medusa.search.release_matcher.scene_exceptions.get_season_scene_exceptions',
        side_effect=season_exceptions,
    ):
        matcher = _matcher(_series(SHOW_NAME, [target]), [target])
        assert matcher.matches_series('Season.Five.Alias.-.First.Contact.mkv') is False


def test_contextual_strict_parse_disables_name_parser_cache():
    provider = GenericProvider('TestProvider')
    search_result = Mock()
    search_result.name = 'Alpha.Chronicle.S01E01.mkv'
    search_result.add_cache_entry = True
    search_result.result_wanted = True

    target = _episode(1, 1, EPISODE_TITLE)
    series = _series(SHOW_NAME, [target])

    parsed = Mock()
    parsed.series = series
    parsed.quality = 1
    parsed.release_group = 'GROUP'
    parsed.version = -1
    parsed.season_number = 1
    parsed.episode_numbers = [1]

    strict_parser = Mock()
    strict_parser.parse.return_value = parsed
    matcher = _matcher(series, [target])

    with patch('medusa.providers.generic_provider.NameParser') as parser_cls:
        parser_cls.return_value = strict_parser
        assert provider._apply_contextual_manual_parse(
            search_result, series, target, matcher) is True

    strict_parser.parse.assert_called_once_with(
        search_result.name,
        cache_result=False,
        use_cache=False,
    )


def test_contextual_manual_parse_title_fallback():
    provider = GenericProvider('TestProvider')
    search_result = Mock()
    search_result.name = 'Alpha Chronicle - First Contact - suffix.mkv'
    search_result.add_cache_entry = True
    search_result.result_wanted = True

    target = _episode(1, 1, EPISODE_TITLE)
    series = _series(SHOW_NAME, [target])

    strict_parser = Mock()
    strict_parser.parse.side_effect = InvalidNameException('strict parse failed')
    advisory_parser = Mock()
    advisory_parsed = Mock()
    advisory_parsed.episode_numbers = []
    advisory_parsed.guess = {}
    advisory_parser.parse.return_value = advisory_parsed

    matcher = _matcher(series, [target])
    with patch('medusa.providers.generic_provider.NameParser') as parser_cls:
        parser_cls.side_effect = [strict_parser, advisory_parser]
        assert provider._apply_contextual_manual_parse(
            search_result, series, target, matcher) is True

    assert search_result.actual_season == 1
    assert search_result.actual_episodes == [1]
    assert search_result.result_wanted is True


def test_contextual_manual_parse_explicit_conflict():
    provider = GenericProvider('TestProvider')
    search_result = Mock()
    search_result.name = 'Alpha.Chronicle.S01E02.First.Contact.mkv'
    search_result.add_cache_entry = True
    search_result.result_wanted = True

    target = _episode(1, 1, EPISODE_TITLE)
    series = _series(SHOW_NAME, [target, _episode(1, 2, OTHER_EPISODE_TITLE)])

    parsed = Mock()
    parsed.series = series
    parsed.quality = 1
    parsed.release_group = 'GROUP'
    parsed.version = -1
    parsed.season_number = 1
    parsed.episode_numbers = [2]

    matcher = _matcher(series, [target])
    with patch('medusa.providers.generic_provider.NameParser') as parser_cls:
        parser_cls.return_value.parse.return_value = parsed
        assert provider._apply_contextual_manual_parse(
            search_result, series, target, matcher) is False

    assert search_result.result_wanted is False
    assert search_result.add_cache_entry is False


def test_contextual_manual_parse_wrong_series_strict_path():
    provider = GenericProvider('TestProvider')
    search_result = Mock()
    search_result.name = 'Beta.Chronicle.S01E01.mkv'
    search_result.add_cache_entry = True
    search_result.result_wanted = True

    target = _episode(1, 1, EPISODE_TITLE)
    series = _series(SHOW_NAME, [target], series_id=100)

    other_series = Mock()
    other_series.indexer = 1
    other_series.series_id = 200

    parsed = Mock()
    parsed.series = other_series
    parsed.quality = 1
    parsed.release_group = 'GROUP'
    parsed.version = -1
    parsed.season_number = 1
    parsed.episode_numbers = [1]

    matcher = _matcher(series, [target])
    with patch('medusa.providers.generic_provider.NameParser') as parser_cls:
        parser_cls.return_value.parse.return_value = parsed
        assert provider._apply_contextual_manual_parse(
            search_result, series, target, matcher) is False

    assert search_result.result_wanted is False
    assert search_result.add_cache_entry is False


def test_contextual_manual_parse_rejects_non_video_extension():
    provider = GenericProvider('TestProvider')
    search_result = Mock()
    search_result.name = 'Alpha.Chronicle.-.First.Contact.nfo'
    search_result.add_cache_entry = True
    search_result.result_wanted = True

    target = _episode(1, 1, EPISODE_TITLE)
    series = _series(SHOW_NAME, [target])
    matcher = _matcher(series, [target])

    assert provider._apply_contextual_manual_parse(
        search_result, series, target, matcher) is False
    assert search_result.result_wanted is False
    assert search_result.add_cache_entry is False


def test_build_minimal_parse_result_uses_parse_method():
    series = _series(SHOW_NAME, [_episode(1, 1, EPISODE_TITLE)], is_anime=True)
    with patch('medusa.providers.generic_provider.NameParser') as parser_cls, \
         patch('medusa.providers.generic_provider.guessit.guessit', return_value={}) as guessit_mock:
        parser_instance = parser_cls.return_value
        parser_instance.to_parse_result.return_value = Mock()
        GenericProvider._build_minimal_parse_result('release.mkv', series, 'anime')

    guessit_mock.assert_called_once_with('release.mkv', dict(show_type='anime'))
    parser_cls.assert_called_once_with(series=series, parse_method='anime')


def test_find_search_results_reuses_single_contextual_matcher():
    provider = GenericProvider('TestProvider')
    episode = _episode(1, 1, EPISODE_TITLE)
    series = _series(SHOW_NAME, [episode])
    series.air_by_date = False
    series.sports = False

    search_result_one = Mock()
    search_result_one.name = 'Alpha.Chronicle.-.First.Contact.one.mkv'
    search_result_one.add_cache_entry = False
    search_result_one.result_wanted = True
    search_result_one.quality = 0
    search_result_one.episode_number = 1
    search_result_one.update_search_result = Mock()
    search_result_one.add_result_to_cache = Mock(return_value=None)

    search_result_two = Mock()
    search_result_two.name = 'Alpha.Chronicle.-.First.Contact.two.mkv'
    search_result_two.add_cache_entry = False
    search_result_two.result_wanted = True
    search_result_two.quality = 0
    search_result_two.episode_number = 1
    search_result_two.update_search_result = Mock()
    search_result_two.add_result_to_cache = Mock(return_value=None)

    match = ReleaseMatch(matched=True, season=1, episodes=[1], method='episode_title')
    matcher_instance = Mock()
    matcher_instance.match.return_value = match

    with patch.object(provider, '_check_auth'), \
         patch.object(provider, '_get_episode_search_strings', return_value=['Alpha Chronicle']), \
         patch.object(provider, 'search', return_value=[Mock(), Mock()]), \
         patch.object(provider, 'get_result', side_effect=[search_result_one, search_result_two]), \
         patch('medusa.providers.generic_provider.ReleaseMatcher', return_value=matcher_instance) as matcher_cls, \
         patch('medusa.providers.generic_provider.NameParser') as parser_cls:
        strict_parser = Mock()
        strict_parser.parse.side_effect = InvalidNameException('strict parse failed')
        advisory_parser = Mock()
        advisory_parsed = Mock()
        advisory_parsed.episode_numbers = []
        advisory_parsed.guess = {}
        advisory_parser.parse.return_value = advisory_parsed
        parser_cls.side_effect = [strict_parser, advisory_parser, strict_parser, advisory_parser]

        provider.find_search_results(
            series,
            [episode],
            'eponly',
            manual_search=True,
            manual_search_type='episode',
        )

    matcher_cls.assert_called_once_with(series, [episode])
    assert matcher_instance.match.call_count == 2
