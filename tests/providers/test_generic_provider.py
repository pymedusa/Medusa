# coding=utf-8
"""Provider test code for Generic Provider."""
from __future__ import unicode_literals

from collections import namedtuple
from datetime import date, datetime

from dateutil import tz

from medusa.providers import generic_provider
from medusa.providers.generic_provider import GenericProvider

import pytest
ExceptionTitle = namedtuple('ExceptionTitle', 'title')

sut = GenericProvider('FakeProvider')

# Create a single static "now" reference in UTC.
# Using UTC avoids local DST offset shifts entirely.
NOW_UTC = datetime.now(tz=tz.gettz('UTC')).replace(microsecond=0)
TOLERANCE_SECONDS = 60  # Acceptable difference for human-time tests


@pytest.mark.parametrize('p', [
    {  # p0: None
        'pubdate': None,
        'expected': None
    },
    {  # p1: date and time
        'pubdate': '2017-05-18 15:00:15',
        'expected': datetime(2017, 5, 18, 15, 0, 15, tzinfo=tz.gettz('UTC'))
    },
    {  # p2: date, time and timezone
        'pubdate': '2017-05-16 17:12:25+02:00',
        'expected': datetime(2017, 5, 16, 17, 12, 25, tzinfo=tz.tzoffset(None, 7200))
    },
    {  # p3: human time and minutes
        'pubdate': '12 minutes ago',
        'expected': 720,  # difference in seconds
        'human_time': True
    },
    {  # p4: human time and hours
        'pubdate': '3hours',
        'expected': 10800,  # difference in seconds
        'human_time': True
    },
    {  # p5: date, time and custom timezone
        'pubdate': '2017-05-18 16:19:33',
        'expected': datetime(2017, 5, 18, 12, 19, 33, tzinfo=tz.gettz('US/Eastern')),
        'timezone': 'US/Eastern'
    },
    {  # p6: human time hours (full day)
        'pubdate': '24 hours ago',
        'expected': 86400,  # difference in seconds
        'human_time': True
    },
    {  # p7: human now variant
        'pubdate': 'right now',
        'expected': 0,  # difference in seconds
        'human_time': True
    },
    {  # p8: human now variant
        'pubdate': 'just now',
        'expected': 0,  # difference in seconds
        'human_time': True
    },
    {  # p9: human now variant
        'pubdate': 'Now',
        'expected': 0,  # difference in seconds
        'human_time': True
    },
    {  # p10: invalid human time string
        'pubdate': 'This is not a valid hum readable date format!',
        'expected': None,  # difference in seconds
        'human_time': True
    },
    {  # p11: human time 1 minute
        'pubdate': '1 minute ago',
        'expected': 60,  # difference in seconds
        'human_time': True
    },
    {  # p12: dayfirst
        'pubdate': '2017-04-10 01:36:00+00:00',
        'expected': datetime(2017, 10, 4, 1, 36, tzinfo=tz.gettz('UTC')),
        'dayfirst': True
    },
    {  # p13: yearfirst
        'pubdate': '07-04-10 12:54:00+00:00',
        'expected': datetime(2007, 4, 10, 12, 54, tzinfo=tz.gettz('UTC')),
        'yearfirst': True
    },
    {  # p14: dayfirst and yearfirst
        'pubdate': '07-04-10 17:22:00+00:00',
        'expected': datetime(2007, 10, 4, 17, 22, tzinfo=tz.gettz('UTC')),
        'dayfirst': True,
        'yearfirst': True
    },
    {  # p15: iptorrents test human date with decimal.
        'pubdate': '4.8 minutes ago',
        'expected': 288,
        'human_time': True
    },
    {  # p16: iptorrents test human date with decimal.
        'pubdate': '4.2 weeks ago',
        'expected': 2540160,
        'human_time': True
    },
    {  # p17: iptorrents test human date with decimal.
       # The parse method does not support decimals for the months granularity.
        'pubdate': '1.0 months ago',
        'expected': 2592000,
        'human_time': True
    },
    {  # p18: iptorrents test human date with decimal. (round down)
       # The parse method does not support decimals for the years granularity.
        'pubdate': '5.2 years ago',
        'expected': 157680000,
        'human_time': True
    },
    {  # p19: iptorrents test human date with decimal. (round up)
       # The parse method does not support decimals for the years granularity.
        'pubdate': '4.8 years ago',
        'expected': 157680000,
        'human_time': True
    },
    {  # p20: fromtimestamp (epoch time)
        'pubdate': 1516315053,
        'expected': datetime(2018, 1, 18, 22, 37, 33, tzinfo=tz.gettz('UTC')),
        'fromtimestamp': True
    },
    {  # p21: fromtimestamp (epoch time), with timezone
        'pubdate': 1516315053,
        'expected': datetime(2018, 1, 18, 17, 37, 33, tzinfo=tz.gettz('US/Eastern')),
        'timezone': 'US/Eastern',
        'fromtimestamp': True
    },
    {  # p22: hd-space test human date like 'yesterday at 12:00:00'
        'pubdate': 'yesterday at 23:52:26',
        'expected': datetime(2026, 11, 1, 23, 52, 26, tzinfo=tz.gettz('UTC')),
        'human_time': False,
        'fixed_now': datetime(2026, 11, 2, 0, 2, 51, tzinfo=tz.gettz('UTC'))
    },
    {  # p23: hd-space test human date like 'today at 12:00:00'
        'pubdate': 'today at 23:52:26',
        'expected': datetime(2026, 11, 2, 23, 52, 26, tzinfo=tz.gettz('UTC')),
        'human_time': False,
        'fixed_now': datetime(2026, 11, 2, 0, 2, 51, tzinfo=tz.gettz('UTC'))
    },
])
def test_parse_pubdate(p, monkeypatch):
    # Given
    parsed_date = p['pubdate']
    expected = p['expected']
    ht = p.get('human_time', False)
    tzone = p.get('timezone')
    df = p.get('dayfirst', False)
    yf = p.get('yearfirst', False)
    ft = p.get('fromtimestamp', False)

    fixed_now = p.get('fixed_now')
    if fixed_now:
        class FixedDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                if tz is None:
                    return fixed_now.replace(tzinfo=None)
                return fixed_now.astimezone(tz)

        monkeypatch.setattr(generic_provider, 'datetime', FixedDatetime)

    # When
    actual = sut.parse_pubdate(parsed_date, human_time=ht, timezone=tzone,
                               dayfirst=df, yearfirst=yf, fromtimestamp=ft)

    # Calculate the difference for human date comparison
    if ht and actual:
        # Use the same NOW_UTC reference to avoid DST drift
        actual = int((NOW_UTC - actual).total_seconds())

    # Then
    if ht and isinstance(expected, (int, float)):
        # Allow up to a few seconds difference due to test execution time
        assert abs(expected - actual) <= TOLERANCE_SECONDS, \
            f'Expected ~{expected}s, got {actual}s (diff {expected - actual}s)'
    else:
        assert expected == actual


@pytest.mark.parametrize(('pubdate', 'expected'), [
    ('today at 19:42:35', datetime(2026, 8, 27, 19, 42, 35, tzinfo=tz.gettz('UTC'))),
    ('yesterday at 19:42:35', datetime(2026, 8, 26, 19, 42, 35, tzinfo=tz.gettz('UTC'))),
], ids=['today', 'yesterday'])
def test_parse_pubdate_relative_day_uses_utc_date(monkeypatch, pubdate, expected):
    """Deterministically verify UTC default handling for today/yesterday phrases."""
    local_now = datetime(2026, 8, 28, 5, 53, 0)
    utc_now = datetime(2026, 8, 27, 19, 53, 0, tzinfo=tz.gettz('UTC'))
    original_parse = generic_provider.parser.parse

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return local_now
            return utc_now.astimezone(tz)

    def fake_parse(*args, **kwargs):
        kwargs.setdefault('default', datetime(2026, 8, 28))
        return original_parse(*args, **kwargs)

    monkeypatch.setattr(generic_provider, 'datetime', FixedDatetime)
    monkeypatch.setattr(generic_provider.parser, 'parse', fake_parse)

    assert expected == sut.parse_pubdate(pubdate)


@pytest.mark.parametrize('p', [
    {  # p0: Standard series search string
        'series_name': 'My Series',
        'separator': '+',
        'series_alias': ['My Series S1', 'My Series Alternate title'],
        'add_string': 'add_string',
        'expected': [
            u'My Series+S01E12+add_string',
            u'My Series S1+S01E12+add_string',
            u'My Series Alternate title+S01E12+add_string'
        ]
    },
])
def test_create_search_string_default(p, create_tvshow, create_tvepisode):
    series_name = p['series_name']
    separator = p['separator']
    series_alias = p['series_alias']
    add_string = p['add_string']
    expected = p['expected']

    mock_series = create_tvshow(indexer=1, name=series_name)
    provider = GenericProvider('mock_provider')
    provider.series = mock_series
    provider.search_separator = separator

    episode = create_tvepisode(mock_series, 1, 12)
    episode.scene_season = 1
    episode.scene_episode = 12

    search_string = {
        'Episode': []
    }

    # Create search strings
    for alias in [series_name] + series_alias:
        provider._create_default_search_string(alias, episode, search_string, add_string=add_string)
    actual = search_string['Episode']

    assert expected == actual


@pytest.mark.parametrize('p', [
    {  # p0: Standard series search string
        'series_name': 'My Series',
        'separator': '+',
        'series_alias': ['My Series S1', 'My Series Alternate title'],
        'add_string': 'add_string',
        'expected': [
            u'My Series+2018 01 10+add_string',
            u'My Series S1+2018 01 10+add_string',
            u'My Series Alternate title+2018 01 10+add_string'
        ]
    },
])
def test_create_search_string_air_by_date(p, create_tvshow, create_tvepisode):
    series_name = p['series_name']
    separator = p['separator']
    series_alias = p['series_alias']
    add_string = p['add_string']
    expected = p['expected']

    mock_series = create_tvshow(indexer=1, name=series_name)
    provider = GenericProvider('mock_provider')
    provider.series = mock_series
    provider.search_separator = separator

    episode = create_tvepisode(mock_series, 1, 12)
    episode.airdate = date(2018, 1, 10)

    search_string = {
        'Episode': []
    }

    # Create search strings
    for alias in [series_name] + series_alias:
        provider._create_air_by_date_search_string(alias, episode, search_string, add_string=add_string)
    actual = search_string['Episode']

    assert expected == actual


@pytest.mark.parametrize('p', [
    {  # p0: Standard series search string
        'series_name': 'My Series',
        'separator': '+',
        'series_alias': ['My Series S1', 'My Series Alternate title'],
        'add_string': 'add_string',
        'expected': [
            u'My Series+2018 01 10|Jan+add_string',
            u'My Series S1+2018 01 10|Jan+add_string',
            u'My Series Alternate title+2018 01 10|Jan+add_string'
        ]
    },
])
def test_create_search_string_sports(p, create_tvshow, create_tvepisode):
    series_name = p['series_name']
    separator = p['separator']
    series_alias = p['series_alias']
    add_string = p['add_string']
    expected = p['expected']

    mock_series = create_tvshow(indexer=1, name=series_name)
    provider = GenericProvider('mock_provider')
    provider.series = mock_series
    provider.search_separator = separator

    episode = create_tvepisode(mock_series, 1, 12)
    episode.airdate = date(2018, 1, 10)

    search_string = {
        'Episode': []
    }

    # Create search strings
    for alias in [series_name] + series_alias:
        provider._create_sports_search_string(alias, episode, search_string, add_string=add_string)
    actual = search_string['Episode']

    assert expected == actual


@pytest.mark.parametrize('p', [
    {  # p0: Standard series search string, with series config scene disabled
        'series_name': 'My Series',
        'series_scene': False,
        'separator': '+',
        # All series aliases included the season scene exceptions.
        'series_alias': [
            'My Series S1',
            'My Series alternative title',
            'My Series Season2',
            'My Series Season Scene title',
            'My Series S2'
        ],
        'add_string': 'add_string',
        'season': 2,
        'scene_season': 2,
        'episode': 6,
        'scene_episode': 6,
        'absolute_number': 12,
        'scene_absolute_number': 12,
        # These season_scene_name_exceptions should be returned when querying for the season exceptions for season 2.
        'season_scene_name_exceptions': [
            ExceptionTitle('My Series Season2'),
            ExceptionTitle('My Series Season Scene title'),
            ExceptionTitle('My Series S2')
        ],
        'expected': [
            u'My Series+12+add_string',
            u'My Series S1+12+add_string',
            u'My Series alternative title+12+add_string',
            u'My Series Season2+06+add_string',
            u'My Series Season Scene title+06+add_string',
            u'My Series S2+06+add_string'
        ]
    },
    {  # p1: Standard series search string, with series config scene enabled
        'series_name': 'My Series',
        'series_scene': True,
        'separator': '+',
        # All series aliases included the season scene exceptions.
        'series_alias': [
            'My Series S1',
            'My Series alternative title',
            'My Series Season2',
            'My Series Season Scene title',
            'My Series S2'
        ],
        'add_string': 'add_string',
        'season': 2,
        'scene_season': 2,
        'episode': 6,
        'scene_episode': 6,
        'absolute_number': 12,
        'scene_absolute_number': 13,
        # These season_scene_name_exceptions should be returned when querying for the season exceptions for season 2.
        'season_scene_name_exceptions': [
            ExceptionTitle('My Series Season2'),
            ExceptionTitle('My Series Season Scene title'),
            ExceptionTitle('My Series S2')
        ],
        'expected': [
            u'My Series+13+add_string',
            u'My Series S1+13+add_string',
            u'My Series alternative title+13+add_string',
            u'My Series Season2+06+add_string',
            u'My Series Season Scene title+06+add_string',
            u'My Series S2+06+add_string'
        ]
    },

])
def test_create_search_string_anime(p, create_tvshow, create_tvepisode, monkeypatch_function_return):

    series_name = p['series_name']
    separator = p['separator']
    series_alias = p['series_alias']
    add_string = p['add_string']
    expected = p['expected']

    monkeypatch_function_return([(
        'medusa.scene_exceptions.get_season_scene_exceptions',
        p['season_scene_name_exceptions']
    )])

    mock_series = create_tvshow(indexer=1, name=series_name)
    mock_series.scene = p['series_scene']
    provider = GenericProvider('mock_provider')
    provider.series = mock_series
    provider.search_separator = separator

    episode = create_tvepisode(mock_series, 1, 12)
    episode.scene_episode = p['scene_episode']
    episode.scene_season = p['scene_season']
    episode.absolute_number = p['absolute_number']
    episode.scene_absolute_number = p['scene_absolute_number']

    search_string = {
        'Episode': []
    }

    # Create search strings
    for alias in [series_name] + series_alias:
        provider._create_anime_search_string(alias, episode, search_string, add_string=add_string)
    actual = search_string['Episode']

    assert expected == actual


class _MonthParseResult(object):
    def __init__(self, season_number, episode_numbers):
        self.season_number = season_number
        self.episode_numbers = episode_numbers


class _MonthSearchResult(object):
    def __init__(self, parsed_result):
        self.name = 'Show.Name.Mai.2016.FRENCH.HDTV.x264-GROUP'
        self.parsed_result = parsed_result
        self.actual_season = None
        self.actual_episodes = None


def test_month_precision_result_uses_episode_resolved_by_name_parser():
    """A month-only release resolved to an episode airing mid-month must not be rejected."""
    search_result = _MonthSearchResult(_MonthParseResult(2016, [5]))

    assert GenericProvider._resolve_month_precision_result(search_result) is True
    assert search_result.actual_season == 2016
    assert search_result.actual_episodes == [5]


@pytest.mark.parametrize('season_number,episode_numbers', [
    (None, [5]),
    (2016, []),
    (None, []),
])
def test_month_precision_result_without_resolved_episode_is_skipped(season_number, episode_numbers):
    search_result = _MonthSearchResult(_MonthParseResult(season_number, episode_numbers))

    assert GenericProvider._resolve_month_precision_result(search_result) is False
    assert search_result.actual_season is None
    assert search_result.actual_episodes is None


def test_find_search_results_keeps_numeric_month_year_for_air_by_date(
        monkeypatch, create_tvshow, create_tvepisode, search_provider):
    """Provider search opts into air-by-date parsing so 05.2016 resolves mid-month."""
    from medusa import app, name_cache

    series = create_tvshow(name='Show Name', indexerid=42, lang='en', air_by_date=1, anime=0, scene=0)
    episode = create_tvepisode(series, 2016, 5)
    release = 'Show.Name.05.2016.HDTV.x264-GROUP'
    # Unique episode aired after day 1 of the month (first Saturday of May 2016).
    first_saturday = date(2016, 5, 7)

    class FakeDB(object):
        def select(self, query, args=None):
            args = args or []
            if 'airdate = ?' in query and 'airdate >=' not in query:
                return []
            if 'airdate >= ?' in query and 'airdate < ?' in query:
                start, end = args[2], args[3]
                if start <= first_saturday.toordinal() < end:
                    return [{'season': 2016, 'episode': 5}]
            return []

        def mass_action(self, *_args, **_kwargs):
            return []

    monkeypatch.setattr(app, 'showList', [series])
    monkeypatch.setattr(name_cache, 'name_cache', {
        'show name': (series.indexer, series.indexerid),
    })
    monkeypatch.setattr(name_cache, 'addNameToCache', lambda *args, **kwargs: None)
    monkeypatch.setattr('medusa.name_parser.parser.db.DBConnection', FakeDB)
    monkeypatch.setattr('medusa.providers.generic_provider.DBConnection', FakeDB)

    provider = _provider_month_search_env(monkeypatch, search_provider, series, release, FakeDB)
    results = provider.find_search_results(series, [episode], 'eponly')
    assert 5 in results
    retained = results[5][0]
    assert retained.actual_season == 2016
    assert retained.actual_episodes == [5]
    assert retained.parsed_result.date_precision == 'month'
    assert retained.parsed_result.air_date == date(2016, 5, 1)


def _provider_month_search_env(monkeypatch, search_provider, series, release, fake_db):
    """Wire a provider that returns one release for find_search_results tests."""
    from medusa.name_parser.parser import name_parser_cache

    # Drop parser entries left by other tests (e.g. series=None under air_by_date:).
    name_parser_cache.clear()

    class ProviderCache(object):
        def add_cache_entry(self, *_args, **_kwargs):
            return None

        def _get_db(self):
            return fake_db()

    provider = search_provider()
    provider.cache = ProviderCache()
    monkeypatch.setattr(provider, '_check_auth', lambda: True)
    monkeypatch.setattr(
        provider, '_get_episode_search_strings',
        lambda ep: [{'Episode': [series.name]}],
    )
    monkeypatch.setattr(
        provider, 'search',
        lambda *args, **kwargs: [{'title': release, 'link': 'http://example/1'}],
    )
    monkeypatch.setattr(
        provider, '_get_title_and_url',
        lambda item: (item.get('title') or release, item.get('link') or ''),
    )
    monkeypatch.setattr(provider, '_get_result_info', lambda item: (0, 0))
    monkeypatch.setattr(provider, '_get_size', lambda item: 1000)
    monkeypatch.setattr(provider, '_get_pubdate', lambda item: None)
    return provider


def test_find_search_results_rejects_other_series_month_pack(
        monkeypatch, create_tvshow, create_tvepisode, search_provider):
    """A monthly pack that maps to another known series must not be kept."""
    from medusa import app, name_cache

    series = create_tvshow(name='Show Name', indexerid=42, air_by_date=1, anime=0, scene=0)
    other = create_tvshow(name='Other Show', indexerid=99, air_by_date=1, anime=0, scene=0)
    episode = create_tvepisode(series, 2016, 5)
    release = 'Other.Show.05.2016.HDTV.x264-GROUP'

    class FakeDB(object):
        def select(self, query, args=None):
            return []

        def mass_action(self, *_args, **_kwargs):
            return []

    monkeypatch.setattr(app, 'showList', [series, other])
    monkeypatch.setattr(name_cache, 'name_cache', {
        'show name': (series.indexer, series.indexerid),
        'other show': (other.indexer, other.indexerid),
    })
    monkeypatch.setattr(name_cache, 'addNameToCache', lambda *args, **kwargs: None)
    monkeypatch.setattr('medusa.name_parser.parser.db.DBConnection', FakeDB)
    monkeypatch.setattr('medusa.providers.generic_provider.DBConnection', FakeDB)

    provider = _provider_month_search_env(monkeypatch, search_provider, series, release, FakeDB)
    results = provider.find_search_results(series, [episode], 'eponly')
    assert results == {}


def test_find_search_results_rejects_unknown_series_month_pack(
        monkeypatch, create_tvshow, create_tvepisode, search_provider):
    """An unknown title must not be attributed to the searched air-by-date series."""
    from medusa import app, name_cache

    series = create_tvshow(name='Show Name', indexerid=42, air_by_date=1, anime=0, scene=0)
    episode = create_tvepisode(series, 2016, 5)
    release = 'Unknown.Show.05.2016.HDTV.x264-GROUP'
    first_saturday = date(2016, 5, 7)

    class FakeDB(object):
        def select(self, query, args=None):
            args = args or []
            if 'airdate >= ?' in query and 'airdate < ?' in query:
                start, end = args[2], args[3]
                if start <= first_saturday.toordinal() < end:
                    return [{'season': 2016, 'episode': 5}]
            return []

        def mass_action(self, *_args, **_kwargs):
            return []

    monkeypatch.setattr(app, 'showList', [series])
    monkeypatch.setattr(name_cache, 'name_cache', {
        'show name': (series.indexer, series.indexerid),
    })
    monkeypatch.setattr(name_cache, 'addNameToCache', lambda *args, **kwargs: None)
    monkeypatch.setattr('medusa.name_parser.parser.db.DBConnection', FakeDB)
    monkeypatch.setattr('medusa.providers.generic_provider.DBConnection', FakeDB)

    provider = _provider_month_search_env(monkeypatch, search_provider, series, release, FakeDB)
    results = provider.find_search_results(series, [episode], 'eponly')
    assert results == {}
