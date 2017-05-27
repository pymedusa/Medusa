# coding=utf-8
"""Provider test code for Generic Provider."""
from __future__ import unicode_literals

from datetime import datetime

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
        'expected': datetime(2017, 5, 18, 15, 0, 15, tzinfo=tz.tzlocal())
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
        'expected': datetime(2017, 5, 18, 16, 19, 33, tzinfo=tz.tzlocal()),
        'timezone': 'US/Eastern'
    },
    {  # p6: human time hours
        'pubdate': '24 hours ago',
        'expected': 86400,  # difference in seconds
        'human_time': True
    },
    {  # p6: human time hours
        'pubdate': 'right now',
        'expected': 0,  # difference in seconds
        'human_time': True
    },
    {  # p6: human time hours
        'pubdate': 'just now',
        'expected': 0,  # difference in seconds
        'human_time': True
    },
    {  # p6: human time hours
        'pubdate': 'Now',
        'expected': None,  # difference in seconds
        'human_time': True
    },
    {  # p6: human time hours
        'pubdate': 'This is not a valid hum readable date format!',
        'expected': None,  # difference in seconds
        'human_time': True
    },
])
def test_parse_pubdate(p):
    # Given
    parsed_date = p['pubdate']
    expected = p['expected']
    tzone = p['timezone'] if p.get('timezone') else None
    ht = p.get('human_time', False)

    # When
    actual = sut.parse_pubdate(parsed_date, provided_timezone=tzone, human_time=ht)

    if ht and actual:
        actual = (datetime.now(tz.tzlocal()) - actual).total_seconds()

    # Then
    assert expected == actual
