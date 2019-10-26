# coding=utf-8

"""Test if a string contains specific words."""
from __future__ import unicode_literals


from medusa.show.naming import contains_words

import pytest


@pytest.mark.parametrize(
    'params', [
        {
            'item': 'Show.2012.S01E02.Episode.Title.1080p.HDTV.x265.AC3-Group',
            'words': ['german', 'french', 'group', 'core2hd', 'dutch', 'swedish',
                      'reenc', 'MrLss', 'ita-eng', 'x265']
        },
        {
            'item': 'Show.2013.S03E04.Another.Episode.720p.BluRay.x264-Group',
            'words': ['german', '720p', 'french', 'core2hd', 'dutch', 'swedish',
                      'reenc', 'MrLss', 'ita-eng', ]
        },
        pytest.param(
            {
                'item': 'Show.2012.S01E02.Episode.Title.1080p.HDTV.x265.AC3-Group',
                'words': ['german', 'french', 'core2hd', 'dutch', 'swedish',
                          'reenc', 'MrLss', 'ita-eng', ]
            },
            marks=pytest.mark.xfail
        )
    ]
)
def test_words(params):
    """Test if item contains words, both lazily and eagerly."""
    has_words(**params)
    has_words_lazy(**params)


def has_words(item, words):
    """Test if item contains words."""
    found_words = set(contains_words(item, words))
    assert found_words, (item, words)


def has_words_lazy(item, words):
    """Test if item contains words lazily."""
    found_words = any(contains_words(item, words))
    assert found_words, (item, words)


@pytest.mark.parametrize('p', [
    # The regular Show uses xem data. To map scene S06E29 to indexer S06E28
    {
        'series_info': {
            'name': u'Regular Show',
            'is_scene': False
        },
        'global': {
            'ignored': ['pref1', 'pref2', 'pref3'],
        },
        'series': {
            'ignored': 'pref1,pref5,pref6',
            'exclude_ignored': False,
        },
        'expected_ignored': [u'pref1', u'pref5', u'pref6', u'pref2', u'pref3'],
    },
    {
        'series_info': {
            'name': u'Regular Show',
            'is_scene': False
        },
        'global': {
            'ignored': ['pref1', 'pref2', 'pref3'],
        },
        'series': {
            'ignored': 'pref1,pref2',
            'exclude_ignored': True,
        },
        'expected_ignored': [u'pref3'],
    },

])
def test_combine_ignored_words(p, create_tvshow, app_config):
    app_config('IGNORE_WORDS', p['global']['ignored'])

    # confirm passed in show object indexer id matches result show object indexer id
    series = create_tvshow(name=p['series_info']['name'])
    series.rls_ignore_words = p['series']['ignored']
    series.rls_ignore_exclude = p['series']['exclude_ignored']

    actual = series.show_words()

    expected = p['expected_ignored']

    assert expected == actual.ignored_words


@pytest.mark.parametrize('p', [
    # The regular Show uses xem data. To map scene S06E29 to indexer S06E28
    {
        'series_info': {
            'name': u'Regular Show',
            'is_scene': False
        },
        'global': {
            'required': ['req1', 'req2', 'req3']
        },
        'series': {
            'required': 'req1,req2,req4',
            'exclude_required': False,
        },
        'expected_required': [u'req1', u'req2', u'req4', u'req3'],
    },
    {
        'series_info': {
            'name': u'Regular Show',
            'is_scene': False
        },
        'global': {
            'required': ['req1', 'req2', 'req3']
        },
        'series': {
            'required': 'req2',
            'exclude_required': True,
        },
        'expected_required': [u'req1', u'req3'],
    },

])
def test_combine_required_words(p, create_tvshow, app_config):
    app_config('REQUIRE_WORDS', p['global']['required'])

    # confirm passed in show object indexer id matches result show object indexer id
    series = create_tvshow(name=p['series_info']['name'])
    series.rls_require_words = p['series']['required']
    series.rls_require_exclude = p['series']['exclude_required']

    actual = series.show_words()

    expected = p['expected_required']

    assert expected == actual.required_words
