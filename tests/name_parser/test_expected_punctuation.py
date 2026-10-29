# coding=utf-8
"""Tests for GuessIt expected_title / expected_group Medusa monkeypatch."""
from __future__ import unicode_literals

import pytest

from medusa import app
from medusa.name_parser import guessit_parser as sut


@pytest.fixture
def punctuated_shows(create_tvshow, monkeypatch):
    shows = [
        create_tvshow(indexerid=2, name='11.22.63'),
        create_tvshow(indexerid=9, name='R-15'),
        create_tvshow(indexerid=19, name='9-1-1'),
    ]
    monkeypatch.setattr(app, 'showList', shows)
    # Options include expected_title lists; clear so titles from this fixture apply.
    sut.guessit_cache.clear()
    return shows


@pytest.mark.parametrize('release_name,expected_title', [
    ('11.22.63.S01E06.720p', '11.22.63'),
    ('R-15.S03E04', 'R-15'),
    ('9-1-1.S01E01.720p.HDTV.x264-GROUP', '9-1-1'),
])
def test_expected_title_keeps_punctuation(punctuated_shows, release_name, expected_title):
    """GuessIt 4 must not space-collapse punctuated expected titles."""
    result = sut.guessit(release_name, cached=False)
    assert result.get('title') == expected_title


def test_expected_group_keeps_punctuation(punctuated_shows):
    """Numeric release groups like 20-40 must keep their hyphen."""
    result = sut.guessit(
        'Show.Name.Season.6.480p.HDTV.H264-20-40.WEB-DL',
        cached=False,
    )
    assert result.get('release_group') == '20-40'
