# coding=utf-8
"""Tests for medusa/imdb.py."""
from __future__ import unicode_literals

import os.path

from medusa import imdb


def test_imdb_cache_dir(app_config):
    # Given
    cache_dir = app_config('CACHE_DIR', '/opt/medusa/data/cache')

    # When
    instance = imdb.Imdb()
    expected = os.path.join(cache_dir, 'diskcache')

    # Then
    assert instance._cachedir, expected
