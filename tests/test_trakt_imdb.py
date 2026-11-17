# coding=utf-8
"""Regression tests for matching Trakt shows with optional IMDb identifiers."""
from __future__ import unicode_literals

from types import SimpleNamespace

from medusa.indexers.config import INDEXER_TVDBV2
from medusa.schedulers.trakt_checker import TraktChecker

import pytest


@pytest.mark.parametrize('imdb_id, trakt_imdb, expected', [
    ('garbage', None, False),
    ({'invalid': True}, None, False),
    (None, None, False),
    ('tt6135388', None, False),
    ('tt6135388', 'tt7654321', False),
    ('tt6135388', 'tt6135388', True),
    ('tt6135388/episodes/?season=2&ref_=ttep', 'tt6135388', True),
])
def test_watchlist_imdb_match_requires_a_valid_identifier(imdb_id, trakt_imdb, expected):
    """Match IMDb identifiers only when normalization supplies a usable value."""
    checker = TraktChecker()
    checker.show_watchlist = [SimpleNamespace(tvdb=123, imdb=trakt_imdb)]
    series = SimpleNamespace(indexer=INDEXER_TVDBV2, indexerid=457780, imdb_id=imdb_id)

    assert checker._check_list(show_obj=series, list_type='Show') is expected


def test_watchlist_primary_indexer_match_does_not_require_imdb():
    """Continue matching the primary indexer when optional IMDb metadata is absent."""
    checker = TraktChecker()
    checker.show_watchlist = [SimpleNamespace(tvdb=457780, imdb=None)]
    series = SimpleNamespace(indexer=INDEXER_TVDBV2, indexerid=457780, imdb_id=None)

    assert checker._check_list(show_obj=series, list_type='Show') is True
