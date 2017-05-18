# coding=utf-8
"""Provider test code for Generic Provider."""
from __future__ import unicode_literals

from datetime import datetime, timedelta

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
        'expected': timedelta(seconds=60 * 12),
        'human_time': True
    },
    {  # p4: human time and hours
        'pubdate': '3hours',
        'expected': timedelta(seconds=60 * 60 * 3),
        'human_time': True
    },
    {  # p5: date, time and custom timezone
        'pubdate': '2017-05-18 16:19:33',
        'expected': datetime(2017, 5, 18, 16, 19, 33, tzinfo=tz.gettz('UTC')),
        'timezone': 'US/Eastern'
    },
])
def test_parse_pubdate(p):
    # Given
    parsed_date = p['pubdate']
    expected = p['expected']
    ht = p['human_time'] if p.get('human_time') else False
    tzone = p['timezone'] if p.get('timezone') else None

    # When
    actual = sut.parse_pubdate(parsed_date, human_time=ht, timezone=tzone)

    # Use a recent datetime for human date comparison
    if ht:
        expected = datetime.now(tz.tzlocal()) - p['expected']

    # Then
    assert expected == actual
