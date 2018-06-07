# coding=utf-8
"""Tests for medusa/search/core.py."""

from medusa.common import Quality
from medusa.search.core import filter_results, pick_result

from six import iteritems

import pytest


@pytest.mark.parametrize('p', [
    {  # p0
        'config': {
            'IGNORE_WORDS': ['dubbed'],
            'PREFERRED_WORDS': [],
            'UNDESIRED_WORDS': ['internal'],
            'REQUIRE_WORDS': [],
        },
        'series': {
            'qualities_allowed': [Quality.FULLHDTV, Quality.FULLHDWEBDL, Quality.FULLHDBLURAY],
            'qualities_preferred': [],
            'release_ignore_words': 'BadRobot',
            'release_required_words': 'h264',
        },
        'provider': {
            'minseed': 5,
            'minleech': 2,
        },
        'results': [
            {
                'expected': True,
                'name': 'Show.Name.S03E04.1080p.HDTV.h264-RlsGrp',
                'quality': Quality.FULLHDTV,
                'seeders': 100,
                'leechers': 300,
            },
            {
                'expected': False,  # Global ignored word: dubbed
                'name': 'Show.Name.S03E04.DUBBED.1080p.HDTV.h264-RlsGrp',
                'quality': Quality.FULLHDTV,
                'seeders': 10,
                'leechers': 20,
            },
            # {
            #     'expected': True,  # Global undesired word: internal
            #     'name': 'Show.Name.S03E04.1080p.iNTERNAL.WEB-DL.h264-RlsGrp',
            #     'quality': Quality.FULLHDWEBDL,
            #     'seeders': 20,
            #     'leechers': 70,
            # },
            {
                'expected': False,  # result seeders < provider minseed
                'name': 'Show.Name.S03E04.1080p.WEB-DL.h264-RlsGrp',
                'quality': Quality.FULLHDWEBDL,
                'seeders': 2,
                'leechers': 7,
            },
            {
                'expected': False,  # Series ignored word: BadRobot
                'name': 'Show.Name.S03E04.1080p.BluRay.h264-BadRobot',
                'quality': Quality.FULLHDBLURAY,
                'seeders': 20,
                'leechers': 17,
            },
            {
                'expected': False,  # Series required word: h264
                'name': 'Show.Name.S03E04.1080p.BluRay.h265-RlsGrp',
                'quality': Quality.FULLHDBLURAY,
                'seeders': 5,
                'leechers': 5,
            },
            {
                'expected': False,  # Quality
                'name': 'Show.Name.S03E04.720p.HDTV.h264-RlsGrp',
                'quality': Quality.HDTV,
                'seeders': 10,
                'leechers': 5,
            }
        ]
    },
])
def test_filter_results(p, app_config, create_search_result, search_provider, tvshow, tvepisode):
    # Given
    config_atts = p.get('config', {})
    for attr, value in iteritems(config_atts):
        app_config(attr, value)

    series_atts = p.get('series', {})
    for attr, value in iteritems(series_atts):
        setattr(tvshow, attr, value)

    provider_attrs = p.get('provider', {})

    results = []
    expected = []

    for item in p['results']:
        is_expected = item.pop('expected', False)

        result = create_search_result(
            provider=search_provider(**provider_attrs),
            series=tvshow,
            episodes=[tvepisode],
            url='http://dl.my/file.torrent',
            **item
        )

        results.append(result)
        if is_expected:
            expected.append(result)

    # When
    actual = filter_results(results)

    # Then
    assert expected == actual
