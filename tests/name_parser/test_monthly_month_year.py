# coding=utf-8
"""Regression and coverage tests for monthly month/year release parsing."""
from __future__ import unicode_literals

from datetime import date

import pytest

import medusa.name_parser.guessit_parser as guessit_parser
from medusa import app


@pytest.fixture(autouse=True)
def _empty_show_list(monkeypatch):
    monkeypatch.setattr(app, 'showList', [])


MONTHLY_NAME_YEAR_CASES = [
    # French
    ('Show.Name.Janvier.2019.FRENCH.720p.HDTV.x264-GROUP', date(2019, 1, 1), 'Show Name'),
    ('Show.Name.Fevrier.2018.FRENCH.720p.HDTV.x264-GROUP', date(2018, 2, 1), 'Show Name'),
    ('Show.Name.Mars.2018.FRENCH.720p.HDTV.x264-GROUP', date(2018, 3, 1), 'Show Name'),
    ('Show.Name.Avril.2018.FRENCH.720p.HDTV.x264-GROUP', date(2018, 4, 1), 'Show Name'),
    ('Show.Name.Mai.2016.FRENCH.HDTV.x264-GROUP', date(2016, 5, 1), 'Show Name'),
    ('Show.Name.Juin.2018.FRENCH.720p.HDTV.x264-GROUP', date(2018, 6, 1), 'Show Name'),
    ('Show.Name.Juillet.2017.FRENCH.720p.HDTV.x264-GROUP', date(2017, 7, 1), 'Show Name'),
    ('Show.Name.Aout.2017.FRENCH.720p.HDTV.x264-GROUP', date(2017, 8, 1), 'Show Name'),
    ('Show.Name.Septembre.2018.FRENCH.720p.HDTV.x264-GROUP', date(2018, 9, 1), 'Show Name'),
    ('Show.Name.Octobre.2018.FRENCH.720p.HDTV.x264-GROUP', date(2018, 10, 1), 'Show Name'),
    ('Show.Name.Novembre.2019.FRENCH.720p.HDTV.x264-GROUP', date(2019, 11, 1), 'Show Name'),
    ('Show.Name.Decembre.2018.FRENCH.720p.HDTV.x264-GROUP', date(2018, 12, 1), 'Show Name'),
    # English
    ('Show.Name.January.2018.HDTV.x264-GROUP', date(2018, 1, 1), 'Show Name'),
    ('Show.Name.February.2018.HDTV.x264-GROUP', date(2018, 2, 1), 'Show Name'),
    ('Show.Name.March.2018.HDTV.x264-GROUP', date(2018, 3, 1), 'Show Name'),
    ('Show.Name.April.2018.HDTV.x264-GROUP', date(2018, 4, 1), 'Show Name'),
    ('Show.Name.May.2018.HDTV.x264-GROUP', date(2018, 5, 1), 'Show Name'),
    ('Show.Name.June.2018.HDTV.x264-GROUP', date(2018, 6, 1), 'Show Name'),
    ('Show.Name.July.2018.HDTV.x264-GROUP', date(2018, 7, 1), 'Show Name'),
    ('Show.Name.August.2017.HDTV.x264-GROUP', date(2017, 8, 1), 'Show Name'),
    ('Show.Name.September.2018.HDTV.x264-GROUP', date(2018, 9, 1), 'Show Name'),
    ('Show.Name.October.2018.HDTV.x264-GROUP', date(2018, 10, 1), 'Show Name'),
    ('Show.Name.November.2018.HDTV.x264-GROUP', date(2018, 11, 1), 'Show Name'),
    ('Show.Name.December.2018.HDTV.x264-GROUP', date(2018, 12, 1), 'Show Name'),
    ('Monthly.Show.Sep.2020.720p.WEB.h264-GROUP', date(2020, 9, 1), 'Monthly Show'),
    ('Show.Name.Oct.2019.720p.HDTV.x264-GROUP', date(2019, 10, 1), 'Show Name'),
    # Other Medusa languages
    ('Show.Name.Mayo.2016.HDTV.x264-GROUP', date(2016, 5, 1), 'Show Name'),  # es
    ('Show.Name.Maggio.2016.HDTV.x264-GROUP', date(2016, 5, 1), 'Show Name'),  # it
    ('Show.Name.Mei.2016.HDTV.x264-GROUP', date(2016, 5, 1), 'Show Name'),  # nl
    ('Show.Name.Maio.2016.HDTV.x264-GROUP', date(2016, 5, 1), 'Show Name'),  # pt
    ('Show.Name.Maj.2016.HDTV.x264-GROUP', date(2016, 5, 1), 'Show Name'),  # pl/sv/da
    ('Show.Name.Mai.2016.GERMAN.HDTV.x264-GROUP', date(2016, 5, 1), 'Show Name'),  # de
    ('Show.Name.Agustos.2018.HDTV.x264-GROUP', date(2018, 8, 1), 'Show Name'),  # tr
    ('Show.Name.Yanvar.2019.HDTV.x264-GROUP', date(2019, 1, 1), 'Show Name'),  # ru
    ('Show.Name.Kesakuu.2020.HDTV.x264-GROUP', date(2020, 6, 1), 'Show Name'),  # fi
    ('Show.Name.Desember.2021.HDTV.x264-GROUP', date(2021, 12, 1), 'Show Name'),  # no
    ('Show.Name.Marts.2017.HDTV.x264-GROUP', date(2017, 3, 1), 'Show Name'),  # da
    ('Show.Name.Augusti.2018.HDTV.x264-GROUP', date(2018, 8, 1), 'Show Name'),  # sv
    ('Show.Name.Styczen.2019.HDTV.x264-GROUP', date(2019, 1, 1), 'Show Name'),  # pl
    ('Show.Name.Sijecanj.2020.HDTV.x264-GROUP', date(2020, 1, 1), 'Show Name'),  # hr
    ('Show.Name.Ianuarie.2018.HDTV.x264-GROUP', date(2018, 1, 1), 'Show Name'),  # ro
    # Space-separated + trailing scene tag
    ('Show Name Mars 2012 TAG 03 2012 avi', date(2012, 3, 1), 'Show Name'),
    ('Show Name Fevrier 2012 TAG 02 2012 avi', date(2012, 2, 1), 'Show Name'),
    ('Show Name Juillet 2012 TAG 07 2012 avi', date(2012, 7, 1), 'Show Name'),
    ('Show Name Avril 2012 TAG 04 2012 avi', date(2012, 4, 1), 'Show Name'),
    ('Show Name Novembre 2012 FRENCH PDTV x264 GROUP', date(2012, 11, 1), 'Show Name'),
    ('Show Name Fevrier 2011 FRENCH 720p HDTV x264 GROUP', date(2011, 2, 1), 'Show Name'),
    ('Show Name Septembre 2012 FRENCH HDTV x264 GROUP', date(2012, 9, 1), 'Show Name'),
    ('Show Name Decembre 2012 FRENCH PDTV x264 GROUP', date(2012, 12, 1), 'Show Name'),
    (
        'Show Name Juin 2023 extra tags french more filler words here mp4',
        date(2023, 6, 1),
        'Show Name',
    ),
    # Month name + parenthesized year
    ('Show Name Aout (2017)', date(2017, 8, 1), 'Show Name'),
    ('Show Name Juin (2017)', date(2017, 6, 1), 'Show Name'),
    ('Show Name Avril (2018)', date(2018, 4, 1), 'Show Name'),
]


MONTHLY_NUMERIC_CASES = [
    # 2-digit month
    ('Show.Name.08.1998', date(1998, 8, 1)),
    ('show.name.07.2024', date(2024, 7, 1)),
    ('Show.Name.10.2024', date(2024, 10, 1)),
    ('Show.Name.05.2016.HDTV.x264-GROUP', date(2016, 5, 1)),
    ('Show.Name.2016.05', date(2016, 5, 1)),
    ('group-show.name.2011.01.french.720p.hdtv', date(2011, 1, 1)),
    ('Show.Name.2016.12', date(2016, 12, 1)),
    ('Show.Name.01.2000', date(2000, 1, 1)),
    ('Show.Name.09.2024.HDTV.x264-GROUP', date(2024, 9, 1)),
    # Underscore MM_YYYY / YYYY_MM packs
    ('Show.Name.05_2025.mkv', date(2025, 5, 1)),
    ('Show.Name.2025_05.mkv', date(2025, 5, 1)),
    ('Show.Name.5_2025.mkv', date(2025, 5, 1)),
    ('Show.Name.2025_5.mkv', date(2025, 5, 1)),
    ('Show.Name.05_2025_720p.mkv', date(2025, 5, 1)),
    # YYYY-MM after title junk / truncated day
    ('Show Name 2012-02 TAG extra.avi', date(2012, 2, 1)),
    ('Show Name [2004-03-0].mpg', date(2004, 3, 1)),
    ('SN 2003-10.avi', date(2003, 10, 1)),
    ('SN 2004-04.avi', date(2004, 4, 1)),
    # 1-digit month
    ('Show.Name.5.2016.HDTV.x264-GROUP', date(2016, 5, 1)),
    ('Show.Name.2016.5', date(2016, 5, 1)),
    ('Show.Name.1.2024', date(2024, 1, 1)),
    ('Show.Name.2024.1', date(2024, 1, 1)),
    ('Show.Name.9.2018.720p.HDTV.x264-GROUP', date(2018, 9, 1)),
    ('Show.Name.2018.9.HDTV.x264-GROUP', date(2018, 9, 1)),
]


FULL_DATE_CASES = [
    # 2-digit month and day
    ('Show.Name.2016.01.03.FRENCH.720p.HDTV.x264-GROUP', date(2016, 1, 3)),
    ('Show.Name.2010.11.23.HDTV.720p.x264-Group', date(2010, 11, 23)),
    ('Show Name - 2010.11.23 - Episode Name', date(2010, 11, 23)),
    ('Show.Name.2016.05.07.HDTV.x264-GROUP', date(2016, 5, 7)),
    ('Show.Name.07.05.2016.HDTV.x264-GROUP', date(2016, 5, 7)),
    # European DD-MM-YYYY
    ('Show.Name.04-08-2018.FRENCH.HDTV.720p.x264-GROUP', date(2018, 8, 4)),
    ('Show.Name.07-07-2018.FRENCH.HDTV.720p.x264-GROUP', date(2018, 7, 7)),
    ('SN 05-03-2022--group.mp4', date(2022, 3, 5)),
    # French "Emission du DD month YYYY"
    ('Show Name Emission du 03 juin 2023.mp4', date(2023, 6, 3)),
    ('Show Name 03 juin 2023.mp4', date(2023, 6, 3)),
    ('Show Name 03 June 2023.mp4', date(2023, 6, 3)),
    # 1-digit month and/or day
    ('Show.Name.2016.5.7.HDTV.x264-GROUP', date(2016, 5, 7)),
    ('Show.Name.2016.5.07.HDTV.x264-GROUP', date(2016, 5, 7)),
    ('Show.Name.2016.05.7.HDTV.x264-GROUP', date(2016, 5, 7)),
    ('Show.Name.7.5.2016.HDTV.x264-GROUP', date(2016, 5, 7)),
    ('Show.Name.2016.1.3.HDTV.x264-GROUP', date(2016, 1, 3)),
    ('Show.Name.2016.01.3.HDTV.x264-GROUP', date(2016, 1, 3)),
    ('Show.Name.2016.1.03.HDTV.x264-GROUP', date(2016, 1, 3)),
]


# Dash (MM-YYYY) packs, often inside parentheses. guessit mis-parses these as
# SxxExx with season == year; they must resolve to a month-precision date.
DASH_MONTH_YEAR_CASES = [
    ('[GROUP] Show Name (02-2021) TVRIP/1080p/AVC', date(2021, 2, 1), 'Show Name'),
    ('[GROUP] Show Name (03-2021) TVRIP/1080p/AVC', date(2021, 3, 1), 'Show Name'),
    ('[GROUP] Show Name (06-2021) TVRIP/1080p/AVC', date(2021, 6, 1), 'Show Name'),
    ('[GROUP] Show Name (01-2023) TVRIP/1080P/MP4', date(2023, 1, 1), 'Show Name'),
    ('[GROUP] Show Name (10-2022) TVRIP/1080P/MP4', date(2022, 10, 1), 'Show Name'),
    ('[GROUP] Show Name (07-2023) WEB-DL/720P/MP4', date(2023, 7, 1), 'Show Name'),
    ('[GROUP] Show Name 07-2025 FRENCH 1080p WEB x264', date(2025, 7, 1), 'Show Name'),
    # Parenthesized month name + year
    ('Show Name (Avril-2021)', date(2021, 4, 1), 'Show Name'),
    # Two-digit year (dash only)
    ('SN-01-24', date(2024, 1, 1), 'SN'),
    ('SN-03-24', date(2024, 3, 1), 'SN'),
    ('SN-04-24-720p', date(2024, 4, 1), 'SN'),
    ('Show Name 09-24', date(2024, 9, 1), 'Show Name'),
    # Dot-separated MM.YY (year > 12) — same as dash form
    ('Show.Name.09.24', date(2024, 9, 1), 'Show Name'),
    ('Show.Name.09.24.mkv', date(2024, 9, 1), 'Show Name'),
    # Full post-process path (folder + file both contain MM-YYYY)
    (
        r'\\server\downloads\tv\SN\SN-01-2022\SN-01-2022.mp4',
        date(2022, 1, 1),
        'SN',
    ),
    # Directory components must not leak into the title
    (
        r'\\server\downloads\tv\Show\Show Name Novembre 2020\Show Name Novembre 2020.mp4',
        date(2020, 11, 1),
        'Show Name',
    ),
    # Leading bracketed release tags must not leak into the title
    ('[GROUP] Show Name - Juin 2021.mkv', date(2021, 6, 1), 'Show Name'),
    ('[GROUP] Show Name Janvier 2021.mp4', date(2021, 1, 1), 'Show Name'),
    ('[TAG] Show Name - Juillet 2022 WEBrip 2160p x265 AAC', date(2022, 7, 1), 'Show Name'),
    ('[TAG].Show.Name.2022.07.Juillet.2022.4KRip.H265.AAC', date(2022, 7, 1), 'Show Name'),
    # A season folder must not turn the file's month into an episode number
    (
        r'M:\media\tv\Show Name (1991)\Show Name S35\Show Name 01-2026.mkv',
        date(2026, 1, 1),
        'Show Name',
    ),
    (
        r'M:\media\tv\Show Name (1991)\Show Name S35\Show Name Janvier 2026.mkv',
        date(2026, 1, 1),
        'Show Name',
    ),
    (
        r'M:\media\tv\Show Name (1991)\Show Name S33\SN-04-24-720p',
        date(2024, 4, 1),
        'Show Name',
    ),
    (
        r'M:\media\tv\Show Name (1991)\Show Name S32\SN-03-23',
        date(2023, 3, 1),
        'Show Name',
    ),
    # Spaced separators inside parentheses (year - month)
    ('Show Name (2009 - 10).avi', date(2009, 10, 1), 'Show Name'),
]


STANDARD_SXXEXX_CASES = [
    ('Show.Name.S01E05.HDTV.x264-GROUP', 1, 5),
    ('Show.Name.S03E08.REPACK.PROPER.HDTV.x264-GROUP', 3, 8),
    ('The.100.S01E01.720p.HDTV.x264-GROUP', 1, 1),
    ('Show.Name.S02E10.720p.BluRay.x264-GROUP', 2, 10),
]


@pytest.mark.parametrize('release_name,expected_date,expected_title', MONTHLY_NAME_YEAR_CASES)
def test_monthly_month_name_year_releases(release_name, expected_date, expected_title):
    result = guessit_parser.guessit(release_name, cached=False)
    assert result.get('date') == expected_date
    assert result.get('date_precision') == 'month'
    assert result.get('title') == expected_title
    assert 'season' not in result
    assert 'episode' not in result


@pytest.mark.parametrize('release_name,expected_date', MONTHLY_NUMERIC_CASES)
def test_monthly_numeric_month_year_releases(release_name, expected_date):
    result = guessit_parser.guessit(release_name, dict(air_by_date=True), cached=False)
    assert result.get('date') == expected_date
    assert result.get('date_precision') == 'month'
    assert 'season' not in result
    assert 'episode' not in result


@pytest.mark.parametrize('release_name,expected_date,expected_title', DASH_MONTH_YEAR_CASES)
def test_dash_month_year_releases(release_name, expected_date, expected_title):
    result = guessit_parser.guessit(release_name, dict(air_by_date=True), cached=False)
    assert result.get('date') == expected_date
    assert result.get('date_precision') == 'month'
    if expected_title is not None:
        assert result.get('title') == expected_title
    assert 'season' not in result
    assert 'episode' not in result


@pytest.mark.parametrize('release_name,expected_date,expected_title', [
    # Compact packs need the short title as a scene exception (expected_title).
    ('SN04-2022', date(2022, 4, 1), 'SN'),
    ('SN09-21', date(2021, 9, 1), 'SN'),
    ('SN122022', date(2022, 12, 1), 'SN'),
    ('SN-01-24', date(2024, 1, 1), 'SN'),
    ('SN-04-24-720p', date(2024, 4, 1), 'SN'),
])
def test_compact_scene_alias_month_year(release_name, expected_date, expected_title, monkeypatch, create_tvshow):
    from medusa.scene_exceptions import TitleException

    series = create_tvshow(name='Show Name', indexerid=99)
    series._aliases = {
        TitleException(title='SN', season=-1, indexer=1, series_id=99, custom=True),
    }
    monkeypatch.setattr(app, 'showList', [series])

    result = guessit_parser.guessit(release_name, dict(air_by_date=True), cached=False)
    assert result.get('date') == expected_date
    assert result.get('date_precision') == 'month'
    assert result.get('title') == expected_title
    assert 'season' not in result
    assert 'episode' not in result


def test_compact_alias_does_not_parse_glued_episode_number(monkeypatch, create_tvshow):
    from medusa.scene_exceptions import TitleException

    series = create_tvshow(name='Show Name', indexerid=99)
    series._aliases = {
        TitleException(title='SN', season=-1, indexer=1, series_id=99, custom=True),
    }
    monkeypatch.setattr(app, 'showList', [series])

    result = guessit_parser.guessit('SN106.hdtv-abc', cached=False)
    assert result.get('date') is None
    assert result.get('date_precision') is None


def test_expected_titles_keep_compact_acronyms_not_long_aliases(create_tvshow):
    from medusa.scene_exceptions import TitleException

    series = create_tvshow(name='Show Name', indexerid=99)
    series._aliases = {
        TitleException(title='SN', season=-1, indexer=1, series_id=99, custom=True),
        TitleException(title='Some Long Alternate Title', season=-1, indexer=1, series_id=99, custom=True),
        TitleException(title='Show-Name-2', season=-1, indexer=1, series_id=99, custom=True),
    }
    titles = guessit_parser.get_expected_titles([series])
    assert 'SN' in titles
    assert 'Show-Name-2' in titles
    assert 'Some Long Alternate Title' not in titles
    assert 'Show Name' not in titles


@pytest.mark.parametrize('release_name,expected_date', FULL_DATE_CASES)
def test_full_air_date_releases_digit_widths(release_name, expected_date):
    result = guessit_parser.guessit(release_name, cached=False)
    assert result.get('date') == expected_date
    assert result.get('date_precision') is None


@pytest.mark.parametrize('release_name,expected_date,expected_title', [
    ('Show Name Emission du 03 juin 2023.mp4', date(2023, 6, 3), 'Show Name'),
    ('Show Name 03 juin 2023.mp4', date(2023, 6, 3), 'Show Name'),
    ('Show.Name_S01E01_Emission du 03 juin 2023.mp4', date(2023, 6, 3), 'Show Name'),
    (
        r'M:\media\tv\Show Name (1991)\Show Name S01\Show.Name_S01E01_Emission du 03 juin 2023.mp4',
        date(2023, 6, 3),
        'Show Name',
    ),
])
def test_french_emission_du_day_month_year(release_name, expected_date, expected_title):
    result = guessit_parser.guessit(release_name, cached=False)
    assert result.get('date') == expected_date
    assert result.get('date_precision') is None
    assert result.get('title') == expected_title
    assert 'season' not in result
    assert 'episode' not in result


@pytest.mark.parametrize('release_name,season,episode', STANDARD_SXXEXX_CASES)
def test_standard_sxxexx_not_converted_to_month_year(release_name, season, episode):
    result = guessit_parser.guessit(release_name, cached=False)
    assert result.get('date') is None
    assert result.get('season') == season
    assert result.get('episode') == episode


@pytest.mark.parametrize('release_name,season,episode', [
    (r'M:\media\tv\Show Name\Season 03\Show.Name.S03E05.1080p.mkv', 3, 5),
    (r'M:\media\tv\Show (2011)\Season 01\Show.Name.S01E02.mkv', 1, 2),
])
def test_sxxexx_in_library_path_not_converted(release_name, season, episode):
    result = guessit_parser.guessit(release_name, cached=False)
    assert result.get('date') is None
    assert result.get('season') == season
    assert result.get('episode') == episode


def test_year_as_season_sxxexx_not_converted():
    result = guessit_parser.guessit('Show.Name.S2016E08.HDTV.x264-GROUP', cached=False)
    assert result.get('date') is None
    assert result.get('season') == 2016
    assert result.get('episode') == 8


@pytest.mark.parametrize('release_name', [
    'Show.Name.12.13.HDTV.x264-GROUP',
    'Show.Name.09.10.HDTV.x264-GROUP',
])
def test_weak_episode_pairs_not_converted_to_month_year(release_name):
    result = guessit_parser.guessit(release_name, cached=False)
    assert result.get('date') is None
    assert result.get('episode') is not None


@pytest.mark.parametrize('release_name', [
    'Show.Name.-.07.(2016).[RH].[English.Dubbed][WEBRip]..[HD.1080p]',
    'Show!.Name.2.-.10.(2016).[HorribleSubs][WEBRip]..[HD.720p]',
    'VA_-_Redux_presents_The_Uplifting_Selection_Vol_1-2019-(RDXSEL026)-WEB-2019-ZzZz',
    'Show.Name.E02.2010',
])
def test_anime_volume_and_exx_year_not_converted_to_month_year(release_name):
    result = guessit_parser.guessit(release_name, cached=False)
    assert result.get('date') is None


@pytest.mark.parametrize('release_name', [
    # Truncated month tokens from bad display/encoding — ignored on purpose
    'Show Name Ao 2022 extra tags french mp4',
    'Show Name cembre 2023 extra tags french mp4',
    'Show Name vrier 2024 extra tags french mp4',
])
def test_truncated_display_month_glitches_are_ignored(release_name):
    result = guessit_parser.guessit(release_name, cached=False)
    assert result.get('date') is None
    assert result.get('date_precision') is None


def _fake_db_with_single_mid_month_episode(episode_airdate, season, episode):
    """DB stub: exact day-1 miss, unique later episode in the same month."""

    class FakeDB(object):
        def select(self, query, args=None):
            args = args or []
            if 'airdate = ?' in query and 'airdate >=' not in query:
                return []
            if 'airdate >= ?' in query and 'airdate < ?' in query:
                start, end = args[2], args[3]
                if start <= episode_airdate.toordinal() < end:
                    return [{'season': season, 'episode': episode}]
            return []

    return FakeDB


def test_month_precision_matches_first_saturday_airdate(monkeypatch, create_tvshow):
    """Mai.2016 must match the episode airing on the first Saturday, not day 1."""
    from medusa.name_parser.parser import NameParser, ParseResult

    series = create_tvshow(name='Show Name', lang='fr')
    series.air_by_date = 1

    # 2016-05-01 was a Sunday; first Saturday of May 2016 is 2016-05-07
    first_saturday = date(2016, 5, 7)
    monkeypatch.setattr(
        'medusa.name_parser.parser.db.DBConnection',
        lambda: _fake_db_with_single_mid_month_episode(first_saturday, 2016, 5)(),
    )

    guess = guessit_parser.guessit(
        'Show.Name.Mai.2016.FRENCH.HDTV.x264-GROUP',
        cached=False,
    )
    assert guess.get('date_precision') == 'month'
    assert guess.get('date') == date(2016, 5, 1)

    parser = NameParser(series=series)
    result = ParseResult(
        guess,
        series_name='Show Name',
        air_date=guess.get('date'),
        date_precision=guess.get('date_precision'),
        original_name='Show.Name.Mai.2016.FRENCH.HDTV.x264-GROUP',
    )
    result.series = series
    episodes, seasons = parser._parse_air_by_date(result)
    assert seasons == [2016]
    assert episodes == [5]


def test_full_date_on_first_does_not_fall_back_to_month_range(monkeypatch, create_tvshow):
    """A real YYYY.MM.01 airdate must not steal a later episode in the same month."""
    from medusa.name_parser.parser import NameParser, ParseResult

    series = create_tvshow(name='Show Name', lang='fr')
    series.air_by_date = 1
    later_in_month = date(2026, 5, 15)
    monkeypatch.setattr(
        'medusa.name_parser.parser.db.DBConnection',
        lambda: _fake_db_with_single_mid_month_episode(later_in_month, 2026, 5)(),
    )

    guess = guessit_parser.guessit(
        'Show.Name.2026.05.01.FRENCH.HDTV.x264-GROUP',
        cached=False,
    )
    assert guess.get('date') == date(2026, 5, 1)
    assert guess.get('date_precision') is None

    parser = NameParser(series=series)
    result = ParseResult(
        guess,
        series_name='Show Name',
        air_date=guess.get('date'),
        date_precision=guess.get('date_precision'),
        original_name='Show.Name.2026.05.01.FRENCH.HDTV.x264-GROUP',
    )
    result.series = series

    # Exact day-1 miss must not expand into a month search.
    assert NameParser._get_episodes_by_air_date(result) == []

    episodes, seasons = parser._parse_air_by_date(result)
    assert seasons == []
    assert episodes == []


def test_month_precision_ambiguous_month_returns_empty(monkeypatch, create_tvshow):
    """Month-precision with 0 or 2+ episodes in the month must not guess."""
    from medusa.name_parser.parser import NameParser, ParseResult

    series = create_tvshow(name='Show Name', lang='fr')
    series.air_by_date = 1

    class FakeDB(object):
        def select(self, query, args=None):
            if 'airdate = ?' in query and 'airdate >=' not in query:
                return []
            if 'airdate >= ?' in query and 'airdate < ?' in query:
                return [
                    {'season': 2016, 'episode': 5},
                    {'season': 2016, 'episode': 6},
                ]
            return []

    monkeypatch.setattr('medusa.name_parser.parser.db.DBConnection', lambda: FakeDB())

    result = ParseResult(
        {},
        series_name='Show Name',
        air_date=date(2016, 5, 1),
        date_precision='month',
        original_name='Show.Name.Mai.2016',
    )
    result.series = series
    assert NameParser._get_episodes_by_air_date(result) == []


@pytest.mark.parametrize('release_name', [
    'Example.Show.-.Saison.19.-.Episode.Title_Channel.5_2025_07_18_21_00.mp4',
    'Example.Show.Saison.19.Title_Channel.5_2025_07_18_21_00.mp4',
    'Example.Show.Saison.19.Title_Channel.7_2025_07_18_21_00.mp4',
    'Example.Show.Saison.19.Title_Source.10_2023_11_15_14_30.mp4',
])
def test_channel_number_before_underscore_timestamp_is_not_month_year(release_name):
    """A channel/source digit glued into _YYYY_MM_DD_HH_MM is not MM_YYYY."""
    result = guessit_parser.guessit(release_name, cached=False)
    assert result.get('date_precision') != 'month'
    assert result.get('date') != date(2025, 5, 1)
    assert result.get('date') != date(2025, 7, 1)
    assert result.get('date') != date(2023, 10, 1)
    # GuessIt keeps the bare Season/Saison marker; do not strip it for a false pack.
    assert result.get('season') == 19
    assert result.get('title') == 'Example Show'


def test_underscore_month_year_pack_still_accepted():
    result = guessit_parser.guessit('Example.Show.05_2025.mkv', dict(air_by_date=True), cached=False)
    assert result.get('date') == date(2025, 5, 1)
    assert result.get('date_precision') == 'month'
    assert result.get('title') == 'Example Show'


def test_underscore_year_month_pack_still_accepted():
    result = guessit_parser.guessit('Example.Show.2025_05.mkv', dict(air_by_date=True), cached=False)
    assert result.get('date') == date(2025, 5, 1)
    assert result.get('date_precision') == 'month'
    assert result.get('title') == 'Example Show'


@pytest.mark.parametrize('release_name,season,episode', [
    ('Show.Name.05.2016.HDTV.x264-GROUP', 2016, 5),
    ('Show.Name.2016.05.HDTV.x264-GROUP', 2016, 5),
    ('Show.Name.5.2016.HDTV.x264-GROUP', 2016, 5),
])
def test_numeric_month_year_keeps_develop_numbering_without_air_by_date(release_name, season, episode):
    """Ambiguous MM.YYYY stays SyyyyEmm unless an air-by-date series is known."""
    result = guessit_parser.guessit(release_name, cached=False)
    assert result.get('date') is None
    assert result.get('date_precision') is None
    assert result.get('season') == season
    assert result.get('episode') == episode


def test_name_parser_numeric_month_year_for_air_by_date_series(create_tvshow, monkeypatch):
    """Public parse() converts MM.YYYY only when the known series is air-by-date."""
    from medusa.name_parser.parser import NameParser

    series = create_tvshow(name='Show Name', lang='fr')
    series.air_by_date = 1
    monkeypatch.setattr('medusa.name_parser.parser.helpers.get_show', lambda *args, **kwargs: series)
    monkeypatch.setattr('medusa.name_parser.parser.NameParser.assert_supported', staticmethod(lambda result: None))

    result = NameParser(series=series, naming_pattern=True).parse(
        'Show.Name.05.2016.HDTV.x264-GROUP', cache_result=False, use_cache=False,
    )
    assert result.air_date == date(2016, 5, 1)
    assert result.date_precision == 'month'
    assert not result.episode_numbers


def test_name_parser_numeric_month_year_keeps_develop_for_unknown_series(create_tvshow, monkeypatch):
    """Without a known series, MM.YYYY keeps develop season/episode numbering."""
    from medusa.name_parser.parser import NameParser

    monkeypatch.setattr('medusa.name_parser.parser.helpers.get_show', lambda *args, **kwargs: None)
    monkeypatch.setattr('medusa.name_parser.parser.NameParser.assert_supported', staticmethod(lambda result: None))

    result = NameParser(naming_pattern=True).parse(
        'Show.Name.05.2016.HDTV.x264-GROUP', cache_result=False, use_cache=False,
    )
    assert result.air_date is None
    assert result.date_precision is None
    assert result.season_number == 2016
    assert result.episode_numbers == [5]


def test_name_parser_numeric_month_year_keeps_develop_for_non_air_by_date(create_tvshow, monkeypatch):
    """A known non–air-by-date series must not reinterpret MM.YYYY as a month."""
    from medusa.name_parser.parser import NameParser

    series = create_tvshow(name='Show Name')
    series.air_by_date = 0
    monkeypatch.setattr('medusa.name_parser.parser.helpers.get_show', lambda *args, **kwargs: series)
    monkeypatch.setattr('medusa.name_parser.parser.NameParser.assert_supported', staticmethod(lambda result: None))

    result = NameParser(series=series, naming_pattern=True).parse(
        'Show.Name.05.2016.HDTV.x264-GROUP', cache_result=False, use_cache=False,
    )
    assert result.air_date is None
    assert result.date_precision is None
    assert result.season_number == 2016
    assert result.episode_numbers == [5]


def test_name_parser_air_by_date_flag_without_forcing_series_identity(create_tvshow, monkeypatch):
    """air_by_date=True enables MM.YYYY conversion; title resolution still binds the series."""
    from medusa.name_parser.parser import NameParser

    series = create_tvshow(name='Show Name', lang='fr')
    series.air_by_date = 1
    monkeypatch.setattr('medusa.name_parser.parser.helpers.get_show', lambda *args, **kwargs: series)
    monkeypatch.setattr('medusa.name_parser.parser.NameParser.assert_supported', staticmethod(lambda result: None))

    result = NameParser(air_by_date=True, naming_pattern=True).parse(
        'Show.Name.05.2016.HDTV.x264-GROUP', cache_result=False, use_cache=False,
    )
    assert result.air_date == date(2016, 5, 1)
    assert result.date_precision == 'month'
    # naming_pattern returns before series assignment from get_show; identity is not forced.
    assert result.series is None


def test_name_parser_cache_separates_air_by_date_context(monkeypatch):
    """A develop-style cache entry must not shadow an air-by-date parse of the same name."""
    from medusa.name_parser.parser import NameParser, name_parser_cache

    release = 'Show.Name.05.2016.HDTV.x264-GROUP'
    name_parser_cache.clear()
    monkeypatch.setattr('medusa.name_parser.parser.helpers.get_show', lambda *args, **kwargs: None)
    monkeypatch.setattr('medusa.name_parser.parser.NameParser.assert_supported', staticmethod(lambda result: None))

    try:
        develop_parser = NameParser()
        develop = develop_parser.parse(release, cache_result=True, use_cache=False)
        name_parser_cache.add(develop_parser._cache_name(release), develop)
        assert develop.air_date is None
        assert develop.season_number == 2016

        monthly_parser = NameParser(air_by_date=True)
        monthly = monthly_parser.parse(release, cache_result=True, use_cache=True)
        assert monthly is not develop
        assert monthly.air_date == date(2016, 5, 1)
        assert monthly.date_precision == 'month'

        # Both contexts remain addressable under distinct keys.
        assert name_parser_cache.get(develop_parser._cache_name(release)) is develop
        assert name_parser_cache.get(monthly_parser._cache_name(release)) is monthly
    finally:
        # series=None fixtures must not leak into later provider parses.
        name_parser_cache.clear()


@pytest.mark.parametrize('release_name,season,episode', [
    # Title ending with a month name: the explicit SxxExx is the episode
    ('Life.on.Mars.2008.S01E05.720p.HDTV.x264-GROUP', 1, 5),
    ('Show.Name.Mai.2016.S01E05.HDTV.x264-GROUP', 1, 5),
    # Month/year only in an ancestor folder: the file name numbering wins
    ('/tv/Show Name/Show Name Mai 2016/Show.Name.S01E05.HDTV.x264-GROUP.mkv', 1, 5),
    (r'M:\media\tv\Show Name\Show Name 05.2016\Show.Name.1x05.HDTV.x264-GROUP.mkv', 1, 5),
    (r'M:\media\tv\Show Name\Show Name Emission du 03 juin 2023\Show.Name.S01E05.mkv', 1, 5),
])
def test_explicit_episode_numbers_are_not_replaced_by_month_year(release_name, season, episode):
    result = guessit_parser.guessit(release_name, cached=False)
    assert result.get('date') is None
    assert result.get('date_precision') is None
    assert result.get('season') == season
    assert result.get('episode') == episode


def test_explicit_episode_without_season_keeps_ancestor_month_out():
    result = guessit_parser.guessit('/tv/Show Name/Show Name Mai 2016/Show.Name.E05.HDTV.mkv', cached=False)
    assert result.get('date') is None
    assert result.get('date_precision') is None
    assert result.get('episode') == 5


def test_ancestor_month_year_still_used_when_file_has_no_numbering():
    result = guessit_parser.guessit('/tv/Show Name/Show Name Mai 2016/Show.Name.HDTV.mkv', cached=False)
    assert result.get('date') == date(2016, 5, 1)
    assert result.get('date_precision') == 'month'
    assert 'episode' not in result


@pytest.mark.parametrize('release_name,show_type', [
    ('[Group] Show Name - 01-24 [1080p]', 'anime'),
    ('[Group] Show Name 01-24 (BD 1080p)', 'anime'),
    ('[Group] Show Name - 01-24 [1080p]', 'normal'),
    ('[Group] Show Name - 13-26 [BD 1080p]', 'anime'),
])
def test_anime_absolute_episode_ranges_are_not_month_year(release_name, show_type):
    result = guessit_parser.guessit(release_name, dict(show_type=show_type), cached=False)
    assert result.get('date') is None
    assert result.get('date_precision') is None
    absolute = result.get('absolute_episode')
    assert isinstance(absolute, list)
    assert absolute[0] in (1, 13)
    assert absolute[-1] in (24, 26)


@pytest.mark.parametrize('release_name,season,episode', [
    # A number introduced by a season/episode keyword is explicit numbering,
    # not the month of a MM.YYYY monthly pack.
    ('Show.Name.Season.12.2023.720p.HDTV.x264-GROUP', 12, None),
    ('Show.Name.Season.5.2016.720p.HDTV.x264-GROUP', 5, None),
    ('Show.Name.Saison.05.2016.FRENCH.720p.HDTV.x264-GROUP', 5, None),
    ('Show.Name.Season.12.Episode.3.2023.720p.HDTV.x264-GROUP', 12, 3),
    ('Show Name Season 2 Episode 11 2019 720p HDTV x264-GROUP', 2, 11),
])
def test_keyword_numbering_is_not_replaced_by_month_year(release_name, season, episode):
    result = guessit_parser.guessit(release_name, cached=False)
    assert result.get('date') is None
    assert result.get('date_precision') is None
    assert result.get('season') == season
    assert result.get('episode') == episode
