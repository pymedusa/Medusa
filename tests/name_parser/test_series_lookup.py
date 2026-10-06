# coding=utf-8
"""Tests for matching parsed series names to shows."""
from __future__ import unicode_literals

from medusa import app, helpers
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


def test_year_alias_accepts_numeric_string_imdb_year(monkeypatch, create_tvshow):
    series = create_tvshow()
    series.imdb_info['year'] = '2026'
    series.start_year = None
    get_show = Mock(side_effect=[None, series])
    monkeypatch.setattr(helpers, 'get_show', get_show)
    monkeypatch.setattr(NameParser, '_parse_series', Mock(return_value=([1], [1], [])))

    result = NameParser()._parse_string('Lucky.2026.S01E01')

    assert result.series is series


def test_year_alias_accepts_int_imdb_year(monkeypatch, create_tvshow):
    series = create_tvshow()
    series.imdb_info['year'] = 2026
    series.start_year = None
    get_show = Mock(side_effect=[None, series])
    monkeypatch.setattr(helpers, 'get_show', get_show)
    monkeypatch.setattr(NameParser, '_parse_series', Mock(return_value=([1], [1], [])))

    result = NameParser()._parse_string('Lucky.2026.S01E01')

    assert result.series is series


def test_year_alias_non_numeric_imdb_year_does_not_crash(monkeypatch, create_tvshow):
    """Non-numeric imdb_year must not raise; basename year still blocks the match."""
    series = create_tvshow()
    series.imdb_info['year'] = 'N/A'
    series.start_year = None
    get_show = Mock(side_effect=[None, series])
    monkeypatch.setattr(helpers, 'get_show', get_show)

    result = NameParser()._parse_string('Lucky.2026.S01E01')

    assert result.series is None


def test_year_alias_falls_back_to_start_year_when_imdb_year_is_non_numeric(monkeypatch, create_tvshow):
    series = create_tvshow()
    series.imdb_info['year'] = 'N/A'
    series.start_year = 2026
    get_show = Mock(side_effect=[None, series])
    monkeypatch.setattr(helpers, 'get_show', get_show)
    monkeypatch.setattr(NameParser, '_parse_series', Mock(return_value=([1], [1], [])))

    result = NameParser()._parse_string('Lucky.2026.S01E01')

    assert result.series is series


def test_folder_year_alias_accepts_despite_non_numeric_imdb_year(monkeypatch, create_tvshow):
    """Folder-only year mismatch path must still accept when imdb_year is not numeric."""
    series = create_tvshow()
    series.name = "Les Chemins de l'aventure"
    series.imdb_info['year'] = 'unknown'
    series.start_year = None
    get_show = Mock(side_effect=[None, series])
    monkeypatch.setattr(helpers, 'get_show', get_show)
    monkeypatch.setattr(NameParser, '_parse_series', Mock(return_value=([1], [17], [])))

    release = (
        r"D:\Media\TV\Les Chemins de l'aventure (2001)"
        r"\Les.Chemins.de.laventure.S17"
        r"\Les.Chemins.De.L.Aventure.S17E01.Title.2023.WEBRip.1080p.x264-Group.mkv"
    )
    result = NameParser()._parse_string(release)

    assert result.series is series


def test_folder_year_alias_accepts_title_despite_year_mismatch(monkeypatch, create_tvshow):
    """Parent-folder (2001) must not block matching when indexer year differs."""
    series = create_tvshow()
    series.name = "Les Chemins de l'aventure"
    series.start_year = 2007
    get_show = Mock(side_effect=[None, series])
    monkeypatch.setattr(helpers, 'get_show', get_show)
    monkeypatch.setattr(NameParser, '_parse_series', Mock(return_value=([1], [17], [])))

    release = (
        r"D:\Media\TV\Les Chemins de l'aventure (2001)"
        r"\Les.Chemins.de.laventure.S17"
        r"\Les.Chemins.De.L.Aventure.S17E01.Title.2023.WEBRip.1080p.x264-Group.mkv"
    )
    result = NameParser()._parse_string(release)

    assert result.series is series
    assert get_show.call_args_list[0][0][0].endswith('2001')
    assert get_show.call_args_list[1][0][0] == "Les Chemins de l'aventure"


def test_air_by_date_prefers_explicit_season_episode(monkeypatch, create_tvshow):
    series = create_tvshow()
    series.air_by_date = 1
    get_show = Mock(return_value=series)
    monkeypatch.setattr(helpers, 'get_show', get_show)
    parse_series = Mock(return_value=([4], [2], []))
    parse_air = Mock(return_value=([], []))
    monkeypatch.setattr(NameParser, '_parse_series', parse_series)
    monkeypatch.setattr(NameParser, '_parse_air_by_date', parse_air)

    result = NameParser()._parse_string(
        "Show Name - 02x04 - Episode Title (Fr.2009)_Fr5.2010-01-24_clo2.avi"
    )

    assert result.series is series
    assert parse_series.called
    assert not parse_air.called


def test_non_anime_bare_episode_number_uses_series_parser(monkeypatch, create_tvshow):
    """Bare `` - 01 - `` must not force anime parsing on non-anime shows."""
    series = create_tvshow(anime=0)
    series.name = 'Show Name'
    get_show = Mock(return_value=series)
    monkeypatch.setattr(helpers, 'get_show', get_show)
    parse_series = Mock(return_value=([1], [1], []))
    parse_anime = Mock(return_value=([], [], []))
    monkeypatch.setattr(NameParser, '_parse_series', parse_series)
    monkeypatch.setattr(NameParser, '_parse_anime', parse_anime)

    result = NameParser()._parse_string(
        'Show Name - 01 - Guest Name (13-10-1990).avi'
    )

    assert result.series is series
    assert parse_series.called
    assert not parse_anime.called
    assert result.episode_numbers == [1]
    assert result.season_number == 1


def test_spin_off_full_name_in_release_beats_parent_show(monkeypatch, create_tvshow):
    """``Parent(s), Subtitle - 01 - Title`` must resolve to the spin-off, not the parent."""
    parent = create_tvshow(indexerid=1)
    parent.name = 'Show Name(s)'
    spin_off = create_tvshow(indexerid=2)
    spin_off.name = 'Show Name(s), côté nature'
    monkeypatch.setattr(app, 'showList', [parent, spin_off])
    get_show = Mock(return_value=parent)
    monkeypatch.setattr(helpers, 'get_show', get_show)
    monkeypatch.setattr(NameParser, '_parse_series', Mock(return_value=([1], [1], [])))

    result = NameParser()._parse_string(
        'Show Name(s), côté nature - 01 - Episode Title (Fr.2021)[720p]_ARTE.2021-09-06_grp.mkv'
    )

    assert result.series is spin_off
    assert get_show.call_args[0][0] == 'Show Name'


def test_longer_library_name_not_in_release_keeps_parent(monkeypatch, create_tvshow):
    parent = create_tvshow(indexerid=1)
    parent.name = 'Show Name(s)'
    spin_off = create_tvshow(indexerid=2)
    spin_off.name = 'Show Name(s), côté nature'
    monkeypatch.setattr(app, 'showList', [parent, spin_off])
    monkeypatch.setattr(helpers, 'get_show', Mock(return_value=parent))
    monkeypatch.setattr(NameParser, '_parse_series', Mock(return_value=([1], [1], [])))

    result = NameParser()._parse_string('Show Name(s) - 01 - Episode Title.mkv')

    assert result.series is parent


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
