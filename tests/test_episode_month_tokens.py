# coding=utf-8
"""Tests for the date tokens of episode naming / search patterns."""
from __future__ import unicode_literals

from datetime import date

import pytest


@pytest.fixture
def monthly_episode(create_tvshow, create_tvepisode):
    def create(lang='fr'):
        series = create_tvshow(indexerid=12, name='Show Name', lang=lang)
        return create_tvepisode(series=series, season=1, episode=5, name='Episode Name',
                                airdate=date(2016, 5, 7), release_name='', release_group='')
    return create


@pytest.mark.parametrize('pattern,expected', [
    # Uppercase tokens.
    ('%Y.%0M', '2016.05'),
    ('%MM %Y', 'May 2016'),
    ('%Mm.%Y', 'May.2016'),
    ('%0M-%YY', '05-16'),
    ('%0m-%yy', '05-16'),
    # Lowercase variants of existing tokens keep their historical meaning:
    # %y is the lowercase form of %Y (4-digit year), not a two-digit year.
    ('%s.n.%y.%0m.%0d', 'show.name.2016.05.07'),
    ('%y-%0m', '2016-05'),
])
def test_episode_date_tokens(monthly_episode, pattern, expected):
    assert monthly_episode()._format_pattern(pattern) == expected


@pytest.mark.parametrize('lang', ['fr', 'de', 'el', 'ja', 'zh', 'ru', 'he', ''])
def test_month_tokens_ignore_show_language(monthly_episode, lang):
    """%MM and %Mm render locale-independent month names, regardless of the show language."""
    episode = monthly_episode(lang=lang)
    assert episode._format_pattern('%MM %Y') == 'May 2016'
    assert episode._format_pattern('%Mm.%Y') == 'May.2016'
    assert episode._format_pattern('%MM %Mm %0M %YY') == 'May May 05 16'
