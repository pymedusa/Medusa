# coding=utf-8
"""Tests for FixLeadingDashEpisodeTitle span handling."""
from __future__ import unicode_literals

from medusa import app
from medusa.name_parser import guessit_parser as sut
from medusa.name_parser.rules import default_api


def test_fix_leading_dash_episode_title_span():
    """Series title span must be valid and stop before the NNxNN token."""
    release = "Rugrats Season 1/Rugrats - 01x01 - Tommy's First Birthday[JM].avi"
    result = sut.guessit(release, cached=False)

    assert result.get('title') == 'Rugrats'
    assert result.get('episode_title') == "Tommy's First Birthday"
    assert result.get('season') == 1
    assert result.get('episode') == 1

    matches = default_api.rebulk.matches(
        release,
        {
            'type': 'episode',
            'implicit': True,
            'expected_title': sut.get_expected_titles(app.showList),
            'expected_group': sut.expected_groups,
        },
    )
    series_titles = [
        match for match in matches.named('title')
        if match.value == 'Rugrats'
    ]
    assert series_titles
    for match in series_titles:
        assert match.start <= match.end
        span_text = release[match.start:match.end]
        assert span_text == 'Rugrats'
        assert '01x01' not in span_text
        assert not span_text.endswith('-')
        assert not span_text.endswith(' ')
