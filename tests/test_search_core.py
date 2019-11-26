# coding=utf-8
"""Tests for medusa/search/core.py."""
from __future__ import unicode_literals

import functools
import logging

from medusa.common import HD1080p, Quality
from medusa.search.core import filter_results, pick_result

from mock.mock import Mock

import pytest

from six import iteritems


@pytest.mark.parametrize('p', [
    {  # p0 - No results
        'results': []
    },
    {  # p1
        'config': {
            'IGNORE_WORDS': ['dubbed', 'whatever'],
            'REQUIRE_WORDS': [],
        },
        'series': {
            'quality': HD1080p,
            'rls_ignore_words': 'BadRobot',  # Comma separated
            'rls_require_words': 'h264,x265',  # Comma separated
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
                'expected': True,
                'name': 'Show.Name.S03E04.1080p.BluRay.x265-RlsGrp',
                'quality': Quality.FULLHDBLURAY,
                'seeders': 5,
                'leechers': 5,
            },
            {
                'expected': False,  # Global ignored word: dubbed
                'name': 'Show.Name.S03E04.DUBBED.1080p.HDTV.h264-RlsGrp',
                'quality': Quality.FULLHDTV,
                'seeders': 10,
                'leechers': 20,
            },
            {
                'expected': False,  # Global ignored word: whatever + Series required word: x265
                'name': 'Show.Name.S03E04.whatever.1080p.HDTV.x265-RlsGrp',
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
                'expected': False,  # Series required words
                'name': 'Show.Name.S03E04.1080p.BluRay.h265-RlsGrp',
                'quality': Quality.FULLHDBLURAY,
                'seeders': 5,
                'leechers': 5,
            },
            {
                'expected': False,  # Unwanted quality
                'name': 'Show.Name.S03E04.720p.HDTV.h264-RlsGrp',
                'quality': Quality.HDTV,
                'seeders': 10,
                'leechers': 5,
            }
        ]
    },
])
def test_filter_results(p, app_config, create_search_result, search_provider, create_tvshow, create_tvepisode, caplog):

    caplog.set_level(logging.DEBUG, logger='medusa')

    # Given
    config_attrs = p.get('config', {})
    for attr, value in iteritems(config_attrs):
        app_config(attr, value)

    series_attrs = p.get('series', {})
    series = create_tvshow(**series_attrs)
    series.want_episode = Mock(return_value=True)
    episode = create_tvepisode(series, 3, 4)

    provider_attrs = p.get('provider', {})

    results = []
    expected = []

    for item in p['results']:
        is_expected = item.pop('expected', False)

        result = create_search_result(
            provider=search_provider(**provider_attrs),
            series=series,
            episode=episode,
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
    {  # p1 - same quality - proper tags / preferred words / undesired words
        'config': {
            'PREFERRED_WORDS': ['x265', 'h265'],
            'UNDESIRED_WORDS': ['internal', 'subbed'],
        },
        'series': {
            'quality': HD1080p,
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
                'name': 'Show.Name.S03E04.iNTERNAL.1080p.HDTV.h264-RlsGrp',
                'quality': Quality.FULLHDTV
            },
            {  # 3 - Global preferred word: x265
                'name': 'Show.Name.S03E04.1080p.HDTV.x265-RlsGrp',
                'quality': Quality.FULLHDTV
            },
        ]
    },
    {  # p2 - quality upgrades + proper tags + words
        'config': {
            'PREFERRED_WORDS': ['x265', 'h265'],
            'UNDESIRED_WORDS': ['internal', 'subbed'],
        },
        'series': {
            'quality': HD1080p,
        },
        'expected': 4,  # Index of the expected result
        'results': [
            {  # 0 - Preferred: x265 + Proper tag: PROPER
                'name': 'Show.Name.S03E04.PROPER.1080p.WEB-DL.x265-RlsGrp',
                'quality': Quality.FULLHDWEBDL,
                'proper_tags': ['PROPER']
            },
            {  # 1 - Preferred: x265 + Better quality
                'name': 'Show.Name.S03E04.1080p.BluRay.x265-RlsGrp',
                'quality': Quality.FULLHDBLURAY
            },
            {  # 2 - Better quality
                'name': 'Show.Name.S03E04.1080p.BluRay.h264-RlsGrp',
                'quality': Quality.FULLHDBLURAY
            },
            {  # 3 - Preferred: h265 + Better quality + Undesired: subbed
                'name': 'Show.Name.S03E04.1080p.BluRay.h265.SUBBED-RlsGrp',
                'quality': Quality.FULLHDBLURAY
            },
            {  # 4 - Preferred: h265 + Better quality + Proper tag: REPACK
                'name': 'Show.Name.S03E04.REPACK.1080p.BluRay.h265-RlsGrp',
                'quality': Quality.FULLHDBLURAY,
                'proper_tags': ['REPACK']
            },
            {  # 5 - Preferred: h265 + Undesired: subbed
                'name': 'Show.Name.S03E04.1080p.WEB-DL.h265.SUBBED-RlsGrp',
                'quality': Quality.FULLHDWEBDL
            },
        ]
    },
    {  # p3 - everything undesired
        'config': {
            'PREFERRED_WORDS': [],
            'UNDESIRED_WORDS': ['internal', 'subbed'],
        },
        'series': {
            'quality': HD1080p,
        },
        'expected': 2,  # Index of the expected result
        'results': [
            {  # 0
                'name': 'Show.Name.S03E04.iNTERNAL.1080p.HDTV.x264-RlsGrp',
                'quality': Quality.FULLHDTV
            },
            {  # 1
                'name': 'Show.Name.S03E04.1080p.HDTV.x264.SUBBED-RlsGrp',
                'quality': Quality.FULLHDTV
            },
            {  # 2
                'name': 'Show.Name.S03E04.iNTERNAL.1080p.WEB-DL.x264-RlsGrp',
                'quality': Quality.FULLHDWEBDL
            },
        ]
    },
    {  # p4 - preferred lower quality
        'config': {
            'PREFERRED_WORDS': [],
            'UNDESIRED_WORDS': [],
        },
        'series': {
            'quality': Quality.combine_qualities(
                [Quality.FULLHDTV, Quality.FULLHDWEBDL, Quality.FULLHDBLURAY],
                [Quality.HDTV]
            ),
        },
        'expected': 1,  # Index of the expected result
        'results': [
            {  # 0
                'name': 'Show.Name.S03E04.1080p.WEB-DL.x264-RlsGrp',
                'quality': Quality.FULLHDWEBDL
            },
            {  # 1
                'name': 'Show.Name.S03E04.720p.HDTV.x264-RlsGrp',
                'quality': Quality.HDTV
            },
            {  # 2
                'name': 'Show.Name.S03E04.1080p.HDTV.x264-RlsGrp',
                'quality': Quality.FULLHDTV
            },
            {  # 3
                'name': 'Show.Name.S03E04.1080p.BluRay.x264-RlsGrp',
                'quality': Quality.FULLHDBLURAY
            },
        ]
    },
    {  # p5 - higher quality, lower quality and proper lower quality
        'config': {
            'PREFERRED_WORDS': [],
            'UNDESIRED_WORDS': [],
        },
        'series': {
            'quality': HD1080p,
        },
        'expected': 1,  # Index of the expected result
        'results': [
            {  # 0
                'name': 'Show.Name.S03E04.720p.HDTV.x264-RlsGrp',
                'quality': Quality.HDTV
            },
            {  # 1
                'name': 'Show.Name.S03E04.1080p.HDTV.x264-RlsGrp',
                'quality': Quality.FULLHDTV
            },
            {  # 2
                'name': 'Show.Name.S03E04.PROPER.720p.HDTV.x264-RlsGrp',
                'quality': Quality.HDTV,
                'proper_tags': ['PROPER']
            },
        ]
    },
    {  # p6 - higher quality, preferred lower quality and proper lower quality
        'config': {
            'PREFERRED_WORDS': [],
            'UNDESIRED_WORDS': [],
        },
        'series': {
            'quality': Quality.combine_qualities([Quality.FULLHDTV], [Quality.HDTV]),
        },
        'expected': 2,  # Index of the expected result
        'results': [
            {  # 0
                'name': 'Show.Name.S03E04.PROPER.1080p.HDTV.x264-RlsGrp',
                'quality': Quality.FULLHDTV,
                'proper_tags': ['PROPER']
            },
            {  # 1
                'name': 'Show.Name.S03E04.720p.HDTV.x264-RlsGrp',
                'quality': Quality.HDTV,
            },

            {  # 2
                'name': 'Show.Name.S03E04.PROPER.720p.HDTV.x264-RlsGrp',
                'quality': Quality.HDTV,
                'proper_tags': ['PROPER']
            },
        ]
    },
    {  # p7 - higher quality, preferred lower quality, real proper lower quality
        'config': {
            'PREFERRED_WORDS': [],
            'UNDESIRED_WORDS': [],
        },
        'series': {
            'quality': Quality.combine_qualities([Quality.FULLHDTV], [Quality.HDTV]),
        },
        'expected': 2,  # Index of the expected result
        'results': [
            {  # 0
                'name': 'Show.Name.S03E04.PROPER.1080p.HDTV.x264-RlsGrp',
                'quality': Quality.FULLHDTV,
                'proper_tags': ['PROPER']
            },
            {  # 1
                'name': 'Show.Name.S03E04.720p.HDTV.x264-RlsGrp',
                'quality': Quality.HDTV,
            },
            {  # 2
                'name': 'Show.Name.S03E04.REAL.PROPER.720p.HDTV.x264-RlsGrp',
                'quality': Quality.HDTV,
                'proper_tags': ['REAL', 'PROPER']
            },
            {  # 3
                'name': 'Show.Name.S03E04.PROPER.720p.HDTV.x264-RlsGrp',
                'quality': Quality.HDTV,
                'proper_tags': ['PROPER']
            },
        ]
    },
    {  # p8 - real proper higher quality, preferred lower proper quality
        'config': {
            'PREFERRED_WORDS': [],
            'UNDESIRED_WORDS': [],
        },
        'series': {
            'quality': Quality.combine_qualities([Quality.FULLHDTV], [Quality.HDTV]),
        },
        'expected': 2,  # Index of the expected result
        'results': [
            {  # 0
                'name': 'Show.Name.S03E04.REAL.PROPER.1080p.HDTV.x264-RlsGrp',
                'quality': Quality.FULLHDTV,
                'proper_tags': ['REAL', 'PROPER']
            },
            {  # 1
                'name': 'Show.Name.S03E04.720p.HDTV.x264-RlsGrp',
                'quality': Quality.HDTV,
            },
            {  # 2
                'name': 'Show.Name.S03E04.PROPER.720p.HDTV.x264-RlsGrp',
                'quality': Quality.HDTV,
                'proper_tags': ['PROPER']
            },
        ]
    },
    {  # p9 - real proper over proper
        'config': {
            'PREFERRED_WORDS': [],
            'UNDESIRED_WORDS': [],
        },
        'series': {
            'quality': HD1080p,
        },
        'expected': 2,  # Index of the expected result
        'results': [
            {  # 0
                'name': 'Show.Name.S03E04.PROPER.1080p.HDTV.x264-RlsGrp',
                'quality': Quality.FULLHDTV,
                'proper_tags': ['PROPER']
            },
            {  # 1
                'name': 'Show.Name.S03E04.1080p.HDTV.x264-RlsGrp',
                'quality': Quality.FULLHDTV,
            },
            {  # 2
                'name': 'Show.Name.S03E04.REAL.PROPER.1080p.HDTV.x264-RlsGrp',
                'quality': Quality.FULLHDTV,
                'proper_tags': ['REAL', 'PROPER']
            },
        ]
    },
    {  # p10 - higher quality, proper higher quality, preferred quality
        'config': {
            'PREFERRED_WORDS': [],
            'UNDESIRED_WORDS': [],
        },
        'series': {
            'quality': Quality.combine_qualities([Quality.FULLHDTV], [Quality.HDTV]),
        },
        'expected': 2,  # Index of the expected result
        'results': [
            {  # 0
                'name': 'Show.Name.S03E04.1080p.HDTV.x264-RlsGrp',
                'quality': Quality.FULLHDTV,
            },
            {  # 1
                'name': 'Show.Name.S03E04.PROPER.1080p.HDTV.x264-RlsGrp',
                'quality': Quality.FULLHDTV,
                'proper_tags': ['PROPER']
            },
            {  # 2
                'name': 'Show.Name.S03E04.720p.HDTV.x264-RlsGrp',
                'quality': Quality.HDTV
            },
        ]
    }
])
def test_pick_result(p, app_config, create_search_result, search_provider, create_tvshow, create_tvepisode, caplog):

    caplog.set_level(logging.DEBUG, logger='medusa')

    # Given
    config_attrs = p.get('config', {})
    for attr, value in iteritems(config_attrs):
        app_config(attr, value)

    series_attrs = p.get('series', {})
    series = create_tvshow(**series_attrs)
    episode = create_tvepisode(series, 3, 4)

    provider_attrs = p.get('provider', {})

    make_result = functools.partial(
        create_search_result,
        provider=search_provider(**provider_attrs),
        series=series,
        episode=episode
    )

    results = [make_result(**item) for item in p['results']]
    expected = p['expected']
    if isinstance(expected, int):
        expected = results[expected]

    # When
    actual = pick_result(results)

    # Then
    assert expected == actual
