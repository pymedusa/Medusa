# coding=utf-8
"""Tests for numeric show titles that resemble episode ranges."""
from __future__ import unicode_literals

from medusa import app
from medusa.name_parser.parser import NameParser
from medusa.scene_exceptions import TitleException

import guessit
import pytest


NUMERIC_SHOW = "39-45 : L'Europe en guerre"
FILE_ONLY = "39-45 L'Europe en guerre - S01E07 - La bataille des Ardennes.mkv"
FULL_PATH = (
    "/tv/39-45 : L'Europe en guerre/Season 1/"
    "39-45 L'Europe en guerre - S01E07 - La bataille des Ardennes.mkv"
)


@pytest.fixture
def numeric_series(create_tvshow):
    return create_tvshow(indexerid=3945, name=NUMERIC_SHOW)


def test_full_path_without_series_keeps_generic_guessit_behavior(monkeypatch):
    """Without a known series, GuessIt may still treat the folder as an episode range."""
    monkeypatch.setattr(app, 'showList', [])

    actual = guessit.guessit(FULL_PATH, cached=False)

    assert actual.get('season') == 1
    assert actual.get('episode') == [39, 40, 41, 42, 43, 44, 45]


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
        r"E:\media\tv\39-45  L'Europe en Guerre (2019)"
        r"\39-45  L'Europe en guerre S01"
        r"\39-45  L'Europe en guerre - S01E07 - La bataille des Ardennes.mkv"
    )

    actual = guessit.guessit(release_name, cached=False)

    assert actual.get('season') == 1
    assert actual.get('episode') == 7
    assert actual.get('episode') != [39, 40, 41, 42, 43, 44, 45]


@pytest.mark.parametrize('title', [
    '11.22.63',
    '12 Monkeys',
    'The 100',
])
def test_flexible_expected_title_not_used_for_common_numeric_titles(title):
    from medusa.name_parser import guessit_parser as gp

    assert gp._flexible_expected_title(title) is None


def test_flexible_expected_title_used_for_numeric_range_title():
    from medusa.name_parser import guessit_parser as gp

    flexible = gp._flexible_expected_title(NUMERIC_SHOW)

    assert flexible == "re:39-+45-+L'Europe-+en-+guerre"


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
    assert "re:39-+45-+L'Europe-+en-+guerre" in expected


def test_alias_order_is_deterministic(create_tvshow):
    from medusa.name_parser import guessit_parser as gp

    series = create_tvshow(
        indexerid=30,
        name='Show Name',
        _aliases=[
            TitleException(title='Zeta 99 Alias', season=-1, indexer=1, series_id=30, custom=True),
            TitleException(title='Alpha 12 Alias', season=-1, indexer=1, series_id=30, custom=True),
            TitleException(title='Alpha 12 Alias', season=-1, indexer=1, series_id=30, custom=True),
            TitleException(title='beta 7 Alias', season=-1, indexer=1, series_id=30, custom=True),
            None,
            TitleException(title='', season=-1, indexer=1, series_id=30, custom=True),
        ],
    )

    first = gp.get_expected_titles([series])
    second = gp.get_expected_titles([series])
    numbered_aliases = [title for title in first if 'Alias' in title]

    assert first == second
    assert numbered_aliases == ['Alpha 12 Alias', 'beta 7 Alias', 'Zeta 99 Alias']
    assert len(numbered_aliases) == len(set(numbered_aliases))
    assert first == list(dict.fromkeys(first))


def test_guessit_does_not_mutate_show_list(numeric_series, monkeypatch):
    show_list = [numeric_series]
    monkeypatch.setattr(app, 'showList', show_list)

    guessit.guessit(FULL_PATH, {'series': numeric_series}, cached=False)

    assert app.showList is show_list
    assert app.showList == [numeric_series]
