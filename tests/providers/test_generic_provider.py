# coding=utf-8
"""Provider test code for Generic Provider."""
from __future__ import unicode_literals

from datetime import date, datetime, timedelta

from dateutil import tz

from medusa.providers.generic_provider import GenericProvider

import pytest


sut = GenericProvider('FakeProvider')


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
        'pubdate': 'yesterday at {0}'.format((datetime.now() - timedelta(minutes=10, seconds=25)).strftime('%H:%M:%S')),
        'expected': datetime.now().replace(microsecond=0, tzinfo=tz.gettz('UTC')) - timedelta(days=1, minutes=10, seconds=25),
        'human_time': False
    },
    {  # p23: hd-space test human date like 'today at 12:00:00'
        'pubdate': 'today at {0}'.format((datetime.now() - timedelta(minutes=10, seconds=25)).strftime('%H:%M:%S')),
        'expected': datetime.now().replace(microsecond=0, tzinfo=tz.gettz('UTC')) - timedelta(days=0, minutes=10, seconds=25),
        'human_time': False
    },
])
def test_parse_pubdate(p):
    # Given
    parsed_date = p['pubdate']
    expected = p['expected']
    ht = p.get('human_time', False)
    tzone = p.get('timezone')
    df = p.get('dayfirst', False)
    yf = p.get('yearfirst', False)
    ft = p.get('fromtimestamp', False)

    # When
    actual = sut.parse_pubdate(parsed_date, human_time=ht, timezone=tzone,
                               dayfirst=df, yearfirst=yf, fromtimestamp=ft)

    # Calculate the difference for human date comparison
    if ht and actual:
        actual = int((datetime.now(tz.tzlocal()) - actual).total_seconds())

    # Then
    assert expected == actual


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
        'season_scene_name_exceptions': {
            'My Series Season2',
            'My Series Season Scene title',
            'My Series S2'
        },
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
        'season_scene_name_exceptions': {
            'My Series Season2',
            'My Series Season Scene title',
            'My Series S2'
        },
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
