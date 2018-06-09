# coding=utf-8
"""Tests for medusa/search/core.py."""

import functools
import logging

from medusa.common import Quality
from medusa.search.core import filter_results, pick_result

from six import iteritems

import pytest


@pytest.mark.parametrize('p', [
    {  # p0 - No results
        'results': []
    },
    {  # p1
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
def test_filter_results(p, app_config, create_search_result, search_provider, tvshow, tvepisode, caplog):

    caplog.set_level(logging.DEBUG, logger='medusa')

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
            **item
        )

        results.append(result)
        if is_expected:
            expected.append(result)

    # When
    actual = filter_results(results)

    # Then
    assert expected == actual


@pytest.mark.parametrize('p', [
    {  # p0 - No results
        'results': [],
        'expected': None
    },
    {  # p1
        'config': {
            'PREFERRED_WORDS': ['x265'],
            'UNDESIRED_WORDS': ['internal'],
        },
        'series': {
            'qualities_allowed': [Quality.FULLHDTV, Quality.FULLHDWEBDL, Quality.FULLHDBLURAY],
            'qualities_preferred': []
        },
        'expected': 3,  # Index of the expected result
        'results': [
            {  # 0
                'name': 'Show.Name.S03E04.1080p.HDTV.h264-RlsGrp',
                'quality': Quality.FULLHDTV
            },
            {  # 1 - Proper tag: REPACK
                'name': 'Show.Name.S03E04.REPACK.1080p.HDTV.h264-RlsGrp',
                'quality': Quality.FULLHDTV,
                'proper_tags': ['REPACK']
            },
            {  # 2 - Global undesired word: internal
                'name': 'Show.Name.S03E04.1080p.iNTERNAL.WEB-DL.h264-RlsGrp',
                'quality': Quality.FULLHDWEBDL
            },
            {  # 3 - Global preferred word: x265
                'name': 'Show.Name.S03E04.1080p.WEB-DL.x265-RlsGrp',
                'quality': Quality.FULLHDWEBDL
            }
        ]
    },
])
def test_pick_result(p, app_config, create_search_result, search_provider, tvshow, tvepisode, caplog):

    caplog.set_level(logging.DEBUG, logger='medusa')

    # Given
    config_atts = p.get('config', {})
    for attr, value in iteritems(config_atts):
        app_config(attr, value)

    series_atts = p.get('series', {})
    for attr, value in iteritems(series_atts):
        setattr(tvshow, attr, value)

    provider_attrs = p.get('provider', {})

    make_result = functools.partial(
        create_search_result,
        provider=search_provider(**provider_attrs),
        series=tvshow,
        episodes=[tvepisode]
    )

    results = [make_result(**item) for item in p['results']]
    expected = p['expected']
    if isinstance(expected, int):
        expected = results[expected]

    # When
    actual = pick_result(results)

    # Then
    assert expected == actual
