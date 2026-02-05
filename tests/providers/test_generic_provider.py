# coding=utf-8
"""Provider test code for Generic Provider."""
from __future__ import unicode_literals

from collections import namedtuple
from datetime import date, datetime, timedelta

from dateutil import tz

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
        'pubdate': 'yesterday at {0}'.format((NOW_UTC - timedelta(minutes=10, seconds=25)).strftime('%H:%M:%S')),
        'expected': NOW_UTC - timedelta(days=1, minutes=10, seconds=25),
        'human_time': False
    },
    {  # p23: hd-space test human date like 'today at 12:00:00'
        'pubdate': 'today at {0}'.format((NOW_UTC - timedelta(minutes=10, seconds=25)).strftime('%H:%M:%S')),
        'expected': NOW_UTC - timedelta(days=0, minutes=10, seconds=25),
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
        # Use the same NOW_UTC reference to avoid DST drift
        actual = int((NOW_UTC - actual).total_seconds())

    # Then
    if ht and isinstance(expected, (int, float)):
        # Allow up to a few seconds difference due to test execution time
        assert abs(expected - actual) <= TOLERANCE_SECONDS, \
            f"Expected ~{expected}s, got {actual}s (diff {expected - actual}s)"
    else:
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


@pytest.mark.parametrize('p', [
    {  # p0: Episode search with default template (year should be preserved)
        'series_name': 'My Series',
        'start_year': 2020,
        'templates': [
            # Default template - year should NOT be stripped
            {'id': 1, 'template': '{title} S{season:02d}E{episode:02d}', 'title': 'My Series (2020)',
             'series': 1, 'season': -1, 'enabled': 1, 'default': 1, 'season_search': 0},
        ],
        'expected': ['My Series (2020) S01E05']
    },
    {  # p1: Episode search with custom template (year should be stripped)
        'series_name': 'My Series',
        'start_year': 2020,
        'templates': [
            # Custom template - year SHOULD be stripped
            {'id': 2, 'template': '{title} S{season:02d}E{episode:02d}', 'title': 'My Series (2020)',
             'series': 1, 'season': -1, 'enabled': 1, 'default': 0, 'season_search': 0},
        ],
        'expected': ['My Series S01E05']
    },
    {  # p2: Episode search with mixed templates (default and custom)
        'series_name': 'My Series',
        'start_year': 2020,
        'templates': [
            # Default template - year should NOT be stripped
            {'id': 1, 'template': '{title} S{season:02d}E{episode:02d}', 'title': 'My Series (2020)',
             'series': 1, 'season': -1, 'enabled': 1, 'default': 1, 'season_search': 0},
            # Custom template - year SHOULD be stripped
            {'id': 2, 'template': '{title}.{season:02d}x{episode:02d}', 'title': 'My Series (2020)',
             'series': 1, 'season': -1, 'enabled': 1, 'default': 0, 'season_search': 0},
        ],
        'expected': ['My Series (2020) S01E05', 'My Series.01x05']
    },
    {  # p3: Episode search with custom template without year
        'series_name': 'My Series',
        'start_year': 2020,
        'templates': [
            # Custom template without year - title should remain unchanged
            {'id': 3, 'template': '{title} S{season:02d}E{episode:02d}', 'title': 'My Series',
             'series': 1, 'season': -1, 'enabled': 1, 'default': 0, 'season_search': 0},
        ],
        'expected': ['My Series S01E05']
    },
    {  # p4: Episode search filtering by season
        'series_name': 'My Series',
        'start_year': 2020,
        'templates': [
            # Season 1 template - should be included
            {'id': 1, 'template': '{title} S{season:02d}E{episode:02d}', 'title': 'My Series (2020)',
             'series': 1, 'season': 1, 'enabled': 1, 'default': 0, 'season_search': 0},
            # Season 2 template - should be excluded
            {'id': 2, 'template': '{title} S{season:02d}E{episode:02d}', 'title': 'Other Title',
             'series': 1, 'season': 2, 'enabled': 1, 'default': 0, 'season_search': 0},
        ],
        'expected': ['My Series S01E05']
    },
    {  # p5: Episode search with disabled templates excluded
        'series_name': 'My Series',
        'start_year': 2020,
        'templates': [
            # Enabled template
            {'id': 1, 'template': '{title} S{season:02d}E{episode:02d}', 'title': 'My Series (2020)',
             'series': 1, 'season': -1, 'enabled': 1, 'default': 0, 'season_search': 0},
            # Disabled template - should be excluded
            {'id': 2, 'template': '{title}.{season:02d}x{episode:02d}', 'title': 'My Series (2020)',
             'series': 1, 'season': -1, 'enabled': 0, 'default': 0, 'season_search': 0},
        ],
        'expected': ['My Series S01E05']
    },
])
def test_create_search_string_with_templates_episode(p, create_tvshow, create_tvepisode, monkeypatch):
    from medusa.search_templates import SearchTemplate

    series_name = p['series_name']
    start_year = p['start_year']
    templates_data = p['templates']
    expected = p['expected']

    # Create mock series
    mock_series = create_tvshow(indexer=1, name=series_name, start_year=start_year)
    
    # Create SearchTemplate namedtuples
    templates = [SearchTemplate(**t) for t in templates_data]
    
    # Mock search_templates object with a templates list
    mock_search_templates = type('obj', (object,), {'templates': templates})()
    
    # Mock the search_templates property getter instead of setting it
    monkeypatch.setattr(type(mock_series), 'search_templates', 
                        property(lambda self: mock_search_templates), raising=False)
    mock_series.templates = True  # Enable use_templates
    
    # Create provider and episode
    provider = GenericProvider('mock_provider')
    provider.series = mock_series
    
    episode = create_tvepisode(mock_series, 1, 5)
    episode.scene_season = 1
    episode.scene_episode = 5
    
    # Mock formatted_search_string to return predictable output
    def mock_formatted_search_string(template, title=None):
        return template.format(title=title or series_name, season=1, episode=5)
    
    monkeypatch.setattr(episode, 'formatted_search_string', mock_formatted_search_string)
    
    # Call _get_episode_search_strings
    result = provider._get_episode_search_strings(episode)
    actual = result[0]['Episode']
    
    assert expected == actual


@pytest.mark.parametrize('p', [
    {  # p0: Season search with default template (year should be preserved)
        'series_name': 'My Series',
        'start_year': 2020,
        'templates': [
            # Default template - year should NOT be stripped
            {'id': 1, 'template': '{title} S{season:02d}', 'title': 'My Series (2020)',
             'series': 1, 'season': -1, 'enabled': 1, 'default': 1, 'season_search': 1},
        ],
        'expected': ['My Series (2020) S01']
    },
    {  # p1: Season search with custom template (year should be stripped)
        'series_name': 'My Series',
        'start_year': 2020,
        'templates': [
            # Custom template - year SHOULD be stripped
            {'id': 2, 'template': '{title} S{season:02d}', 'title': 'My Series (2020)',
             'series': 1, 'season': -1, 'enabled': 1, 'default': 0, 'season_search': 1},
        ],
        'expected': ['My Series S01']
    },
    {  # p2: Season search with mixed templates (default and custom)
        'series_name': 'My Series',
        'start_year': 2020,
        'templates': [
            # Default template - year should NOT be stripped
            {'id': 1, 'template': '{title} S{season:02d}', 'title': 'My Series (2020)',
             'series': 1, 'season': -1, 'enabled': 1, 'default': 1, 'season_search': 1},
            # Custom template - year SHOULD be stripped
            {'id': 2, 'template': '{title} Season {season}', 'title': 'My Series (2020)',
             'series': 1, 'season': -1, 'enabled': 1, 'default': 0, 'season_search': 1},
        ],
        'expected': ['My Series (2020) S01', 'My Series Season 1']
    },
    {  # p3: Season search with custom template without year
        'series_name': 'My Series',
        'start_year': 2020,
        'templates': [
            # Custom template without year - title should remain unchanged
            {'id': 3, 'template': '{title} S{season:02d}', 'title': 'My Series',
             'series': 1, 'season': -1, 'enabled': 1, 'default': 0, 'season_search': 1},
        ],
        'expected': ['My Series S01']
    },
    {  # p4: Season search filtering by season
        'series_name': 'My Series',
        'start_year': 2020,
        'templates': [
            # Season 1 template - should be included
            {'id': 1, 'template': '{title} S{season:02d}', 'title': 'My Series (2020)',
             'series': 1, 'season': 1, 'enabled': 1, 'default': 0, 'season_search': 1},
            # Season 2 template - should be excluded
            {'id': 2, 'template': '{title} S{season:02d}', 'title': 'Other Title',
             'series': 1, 'season': 2, 'enabled': 1, 'default': 0, 'season_search': 1},
        ],
        'expected': ['My Series S01']
    },
    {  # p5: Season search with disabled templates excluded
        'series_name': 'My Series',
        'start_year': 2020,
        'templates': [
            # Enabled template
            {'id': 1, 'template': '{title} S{season:02d}', 'title': 'My Series (2020)',
             'series': 1, 'season': -1, 'enabled': 1, 'default': 0, 'season_search': 1},
            # Disabled template - should be excluded
            {'id': 2, 'template': '{title} Season {season}', 'title': 'My Series (2020)',
             'series': 1, 'season': -1, 'enabled': 0, 'default': 0, 'season_search': 1},
        ],
        'expected': ['My Series S01']
    },
])
def test_create_search_string_with_templates_season(p, create_tvshow, create_tvepisode, monkeypatch):
    from medusa.search_templates import SearchTemplate

    series_name = p['series_name']
    start_year = p['start_year']
    templates_data = p['templates']
    expected = p['expected']

    # Create mock series
    mock_series = create_tvshow(indexer=1, name=series_name, start_year=start_year)
    
    # Create SearchTemplate namedtuples
    templates = [SearchTemplate(**t) for t in templates_data]
    
    # Mock search_templates object with a templates list
    mock_search_templates = type('obj', (object,), {'templates': templates})()
    
    # Mock the search_templates property getter instead of setting it
    monkeypatch.setattr(type(mock_series), 'search_templates', 
                        property(lambda self: mock_search_templates), raising=False)
    mock_series.templates = True  # Enable use_templates
    
    # Create provider and episode
    provider = GenericProvider('mock_provider')
    provider.series = mock_series
    
    episode = create_tvepisode(mock_series, 1, 5)
    episode.scene_season = 1
    episode.scene_episode = 5
    
    # Mock formatted_search_string to return predictable output
    def mock_formatted_search_string(template, title=None):
        return template.format(title=title or series_name, season=1)
    
    monkeypatch.setattr(episode, 'formatted_search_string', mock_formatted_search_string)
    
    # Call _get_season_search_strings
    result = provider._get_season_search_strings(episode)
    actual = result[0]['Season']
    
    assert expected == actual
