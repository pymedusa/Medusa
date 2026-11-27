# coding=utf-8
"""Tests for numeric show titles that resemble episode ranges."""
from __future__ import unicode_literals

from medusa import app
from medusa.name_parser.parser import NameParser, ParseResult, name_parser_cache
from medusa.scene_exceptions import TitleException

import guessit
import pytest


NUMERIC_SHOW = '39-45 Show Story'
FILE_ONLY = '39-45 Show Story - S01E07 - Episode Title.mkv'
FULL_PATH = (
    '/tv/39-45 Show Story/Season 1/'
    '39-45 Show Story - S01E07 - Episode Title.mkv'
)

# Synthetic releases for a show whose title starts with a numeric range.
# GuessIt alone may read that range as the episode range 39-45; with the
# series known it must stay SxxExx.
REAL_NUMERIC_RELEASES = [
    pytest.param(
        '39-45 Show Story - S01E03 - Episode Title.mp4',
        (1, [3]),
        id='s01e03',
    ),
    # No SxxExx in the name: the parser reports episode 3 without a season,
    # and the caller assumes the season (e.g. the Season 1 fallback).
    pytest.param(
        'Doc - 39-45 - Show Story - 03 - Episode Title (Channel 01 01 2020 Doc FR).mp4',
        (None, [3]),
        id='doc-prefix-episode-only',
    ),
    pytest.param(
        '39-45, Show Story - 1x02 - Episode Title (2019)_GRP.mkv',
        (1, [2]),
        id='1x02',
    ),
    pytest.param(
        '39-45 Show Story - S01E08 Episode Title 2019 French WEB-DL 720p x264-GRP.mkv',
        (1, [8]),
        id='s01e08',
    ),
]


@pytest.fixture
def numeric_series(create_tvshow):
    return create_tvshow(indexerid=3945, name=NUMERIC_SHOW)


def test_full_path_without_series_uses_current_guessit_behavior(monkeypatch):
    """GuessIt 4.1 already handles the canonical full-path form correctly."""
    monkeypatch.setattr(app, 'showList', [])

    actual = guessit.guessit(FULL_PATH, cached=False)

    assert actual.get('title') == NUMERIC_SHOW
    assert actual.get('season') == 1
    assert actual.get('episode') == 7


def test_file_only_parses_explicit_sxxexx_without_series(monkeypatch):
    monkeypatch.setattr(app, 'showList', [])

    actual = guessit.guessit(FILE_ONLY, cached=False)

    assert actual.get('season') == 1
    assert actual.get('episode') == 7


@pytest.mark.parametrize('release_name', [FILE_ONLY, FULL_PATH])
def test_known_series_protects_numeric_title(release_name, numeric_series, monkeypatch):
    monkeypatch.setattr(app, 'showList', [])

    actual = guessit.guessit(release_name, {'series': numeric_series}, cached=False)

    assert actual.get('season') == 1
    assert actual.get('episode') == 7
    assert actual.get('episode') != [39, 40, 41, 42, 43, 44, 45]


def test_name_parser_with_series_returns_episode_seven(numeric_series, monkeypatch):
    monkeypatch.setattr(app, 'showList', [])

    parser = NameParser(series=numeric_series)
    guess = guessit.guessit(FULL_PATH, {'series': numeric_series}, cached=False)
    result = parser.to_parse_result(FULL_PATH, guess)

    assert result.season_number == 1
    assert result.episode_numbers == [7]
    assert result.ab_episode_numbers == []
    assert set(result.episode_numbers).isdisjoint({39, 40, 41, 42, 43, 44, 45})


def test_parse_cache_accounts_for_series_context(numeric_series, monkeypatch):
    """A bare-name cache entry must not shadow series-aware parse()."""
    monkeypatch.setattr(app, 'showList', [])
    name_parser_cache.clear()

    cached_wrong = ParseResult(
        {'title': NUMERIC_SHOW, 'season': 1, 'episode': list(range(39, 46))},
        original_name=FILE_ONLY,
        series_name=NUMERIC_SHOW,
        season_number=1,
        episode_numbers=list(range(39, 46)),
    )
    cached_wrong.series = numeric_series
    name_parser_cache.add(FILE_ONLY, cached_wrong)

    # naming_pattern skips DB scene-numbering while still using parse()/cache.
    parser = NameParser(series=numeric_series, naming_pattern=True)
    result = parser.parse(FILE_ONLY)

    assert result is not cached_wrong
    assert result.season_number == 1
    assert result.episode_numbers == [7]
    assert set(result.episode_numbers).isdisjoint({39, 40, 41, 42, 43, 44, 45})


def test_parse_reuses_cache_for_same_series_context(numeric_series, monkeypatch):
    monkeypatch.setattr(app, 'showList', [])
    name_parser_cache.clear()

    parser = NameParser(series=numeric_series, naming_pattern=True)
    first = parser.parse(FILE_ONLY, use_cache=False)
    name_parser_cache.add(parser._cache_name(FILE_ONLY), first)

    second = parser.parse(FILE_ONLY, use_cache=True)

    assert first is second
    assert first.season_number == 1
    assert first.episode_numbers == [7]


def test_name_parser_passes_series_into_guessit(numeric_series, monkeypatch):
    captured = {}

    def fake_guessit(name, options=None, cached=True):
        captured['options'] = dict(options or {})
        return {
            'title': NUMERIC_SHOW,
            'season': 1,
            'episode': 7,
            'type': 'episode',
        }

    monkeypatch.setattr('medusa.name_parser.parser.guessit.guessit', fake_guessit)

    # naming_pattern avoids DB-backed scene numbering after GuessIt returns
    parser = NameParser(series=numeric_series, naming_pattern=True)
    parser._parse_string(FULL_PATH)

    assert captured['options'].get('series') is numeric_series
    assert captured['options'].get('show_type') == 'normal'


def test_name_parser_without_series_does_not_inject_series(monkeypatch):
    captured = {}

    def fake_guessit(name, options=None, cached=True):
        captured['options'] = dict(options or {})
        return {
            'title': 'Show Name',
            'season': 1,
            'episode': 7,
            'type': 'episode',
        }

    monkeypatch.setattr('medusa.name_parser.parser.guessit.guessit', fake_guessit)

    parser = NameParser()
    parser._parse_string('Show.Name.S01E07.mkv')

    assert 'series' not in captured['options']


def test_alias_is_used_as_expected_title(create_tvshow, monkeypatch):
    alias_title = '39-45 Alias Europe'
    series = create_tvshow(
        indexerid=22,
        name='Numeric Alias Show',
        _aliases=[TitleException(
            title=alias_title,
            season=-1,
            indexer=1,
            series_id=22,
            custom=True,
        )],
    )
    monkeypatch.setattr(app, 'showList', [])
    release_name = (
        '/tv/39-45 Alias Europe/Season 1/'
        '39-45 Alias Europe - S01E03 - Something.mkv'
    )

    actual = guessit.guessit(release_name, {'series': series}, cached=False)

    assert actual.get('title') == alias_title
    assert actual.get('season') == 1
    assert actual.get('episode') == 3


def test_the_100_still_parses_with_expected_title(create_tvshow, monkeypatch):
    series = create_tvshow(indexerid=12, name='The 100')
    monkeypatch.setattr(app, 'showList', [series])

    actual = guessit.guessit('The.100.S04E13.1080p.BluRay.x264-SPRINTER', cached=False)

    assert actual.get('title') == 'The 100'
    assert actual.get('season') == 4
    assert actual.get('episode') == 13


@pytest.mark.parametrize('release_name,expected_episode', [
    ('Show.Name.S01E07.HDTV.x264-GROUP', 7),
    ('Show.Name.S01E10-E12.HDTV.x264-GROUP', [10, 11, 12]),
    ('Show.Name.S01E07E08.HDTV.x264-GROUP', [7, 8]),
])
def test_classic_range_and_multi_episode_unchanged(release_name, expected_episode, monkeypatch):
    monkeypatch.setattr(app, 'showList', [])

    actual = guessit.guessit(release_name, cached=False)

    assert actual.get('title') == 'Show Name'
    assert actual.get('season') == 1
    assert actual.get('episode') == expected_episode


def test_real_folder_variant_with_double_space_and_year(numeric_series, monkeypatch):
    """Folder names often differ in punctuation from the official indexer title."""
    monkeypatch.setattr(app, 'showList', [numeric_series])
    release_name = (
        r"E:\media\tv\39-45  Show Story (2019)"
        r"\39-45  Show Story S01"
        r"\39-45  Show Story - S01E07 - Episode Title.mkv"
    )

    actual = guessit.guessit(release_name, cached=False)

    assert actual.get('season') == 1
    assert actual.get('episode') == 7
    assert actual.get('episode') != [39, 40, 41, 42, 43, 44, 45]


@pytest.mark.parametrize('title', [
    '11.22.63',
    '12 Monkeys',
    'The 100',
    '9-1-1',
    '9-1-1: Lone Star',
])
def test_flexible_expected_title_not_used_for_common_numeric_titles(title):
    from medusa.name_parser import guessit_parser as gp

    assert gp._flexible_expected_title(title) is None


@pytest.mark.parametrize('title', [
    NUMERIC_SHOW,
    '39-45 : Show Story',
])
def test_flexible_expected_title_used_for_numeric_range_title(title):
    from medusa.name_parser import guessit_parser as gp

    flexible = gp._flexible_expected_title(title)

    assert flexible == 're:39-+45-+Show-+Story'


@pytest.mark.parametrize('title', [
    '9-1-1',
    '9-1-1: Lone Star',
    '9-1 - 1',
])
def test_flexible_expected_title_rejects_third_numeric_segment(title):
    from medusa.name_parser import guessit_parser as gp

    assert gp._flexible_expected_title(title) is None


def test_get_expected_titles_keeps_plain_titles_for_common_shows(create_tvshow):
    from medusa.name_parser import guessit_parser as gp

    shows = [
        create_tvshow(indexerid=2, name='11.22.63'),
        create_tvshow(indexerid=3, name='12 Monkeys'),
        create_tvshow(indexerid=12, name='The 100'),
        create_tvshow(indexerid=21, name=NUMERIC_SHOW),
    ]

    expected = gp.get_expected_titles(shows)

    assert '11.22.63' in expected
    assert '12 Monkeys' in expected
    assert 'The 100' in expected
    assert NUMERIC_SHOW in expected
    assert "re:11-+22-+63" not in expected
    assert "re:12-+Monkeys" not in expected
    assert "re:The-+100" not in expected
    assert 're:39-+45-+Show-+Story' in expected


def test_alias_order_is_deterministic(create_tvshow):
    from medusa.name_parser import guessit_parser as gp

    series = create_tvshow(
        indexerid=30,
        name='Show Name',
        _aliases=[
            TitleException(title='Zeta 99 Alias', season=-1, indexer=1, series_id=30, custom=True),
            TitleException(title='delta 5 Alias', season=-1, indexer=1, series_id=30, custom=True),
            TitleException(title='Alpha 12 Alias', season=-1, indexer=1, series_id=30, custom=True),
            TitleException(title='Alpha 12 Alias', season=-1, indexer=1, series_id=30, custom=True),
            TitleException(title='Delta 5 Alias', season=-1, indexer=1, series_id=30, custom=True),
            TitleException(title='beta 7 Alias', season=-1, indexer=1, series_id=30, custom=True),
            None,
            TitleException(title='', season=-1, indexer=1, series_id=30, custom=True),
        ],
    )

    first = gp.get_expected_titles([series])
    second = gp.get_expected_titles([series])
    numbered_aliases = [title for title in first if 'Alias' in title]

    assert first == second
    # casefold ties break on the original title so "Delta" precedes "delta".
    assert numbered_aliases == [
        'Alpha 12 Alias',
        'beta 7 Alias',
        'Delta 5 Alias',
        'delta 5 Alias',
        'Zeta 99 Alias',
    ]
    assert len(numbered_aliases) == len(set(numbered_aliases))
    assert first == list(dict.fromkeys(first))


def test_guessit_does_not_mutate_show_list(numeric_series, monkeypatch):
    show_list = [numeric_series]
    monkeypatch.setattr(app, 'showList', show_list)

    guessit.guessit(FULL_PATH, {'series': numeric_series}, cached=False)

    assert app.showList is show_list
    assert app.showList == [numeric_series]


@pytest.fixture
def public_parse_path(monkeypatch):
    """Mock the DB-backed scene lookups so NameParser.parse() runs end to end.

    The numbering passthrough mirrors the real behaviour for shows without
    scene numbering: the parsed season/episode are returned unchanged. That
    keeps the test honest about what GuessIt reported; a regression to the
    39-45 range would surface in the mapped episodes.
    """
    def passthrough_numbering(series_obj, episode, season=None):
        return season, episode

    monkeypatch.setattr('medusa.scene_numbering.get_indexer_numbering', passthrough_numbering)
    monkeypatch.setattr('medusa.scene_exceptions.get_season_from_name', lambda series, name: None)
    monkeypatch.setattr(app, 'showList', [])
    name_parser_cache.clear()


@pytest.mark.parametrize('release_name,expected', REAL_NUMERIC_RELEASES)
def test_real_numeric_releases_through_public_parse_path(
    release_name, expected, numeric_series, public_parse_path
):
    """Real filenames of the show must parse to their explicit SxxExx episode."""
    expected_season, expected_episodes = expected

    parser = NameParser(series=numeric_series)
    result = parser.parse(release_name)

    assert result.series is numeric_series
    assert result.season_number == expected_season
    assert result.episode_numbers == expected_episodes
    assert set(result.episode_numbers).isdisjoint(range(39, 46))


@pytest.mark.parametrize('series_name,series_id,release_name,expected', [
    pytest.param(
        '9-1-1',
        336926,
        '9-1-1.S01E01.Pilot.1080p.AMZN.WEB-DL.DDP5.1.H.264-NTb.mkv',
        (1, [1]),
        id='9-1-1-s01e01',
    ),
    pytest.param(
        '24',
        77744,
        '24.S01E01.1080p.BluRay.x264-SiNNERS.mkv',
        (1, [1]),
        id='24-s01e01',
    ),
    pytest.param(
        'Show Name',
        12,
        'Show.Name.S01E07.HDTV.x264-GROUP',
        (1, [7]),
        id='normal-show-s01e07',
    ),
])
def test_other_numbered_and_normal_shows_through_public_parse_path(
    series_name, series_id, release_name, expected, create_tvshow, public_parse_path
):
    """Numeric titles like 9-1-1 and 24, and normal shows, keep parsing as before."""
    expected_season, expected_episodes = expected
    series = create_tvshow(indexerid=series_id, name=series_name)

    parser = NameParser(series=series)
    result = parser.parse(release_name)

    assert result.series is series
    assert result.season_number == expected_season
    assert result.episode_numbers == expected_episodes
