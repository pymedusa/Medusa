# coding=utf-8

"""Test if a string contains specific words."""


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
