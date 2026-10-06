# coding=utf-8
"""Tests for SDBits IMDb identifier handling."""
from __future__ import unicode_literals

from types import SimpleNamespace

from medusa.indexers.utils import mappings
from medusa.providers.torrent.html import sdbits

import pytest


class RecordingSession(object):
    """Record search requests and return an empty response."""

    def __init__(self):
        """Initialize an empty call log."""
        self.calls = []

    def get(self, url, params=None):
        """Record a request and return empty HTML."""
        self.calls.append((url, params.copy()))
        return SimpleNamespace(text='')


def make_provider(imdb_id=None):
    """Create a provider with login and HTTP isolated from external services."""
    provider = object.__new__(sdbits.SDBitsProvider)
    provider.series = SimpleNamespace(externals={mappings[10]: imdb_id})
    provider.session = RecordingSession()
    provider.urls = {'search': 'http://sdbits.org/browse.php'}
    provider.login = lambda: True
    return provider


@pytest.mark.parametrize('imdb_id', ['legacy-invalid-value', {'id': 'tt6135388'}])
def test_invalid_imdb_id_falls_back_to_title_search(imdb_id):
    """Search by title when an external value cannot be normalized."""
    provider = make_provider(imdb_id)

    assert provider.search({'Episode': ['Show.S01E01']}) == []
    assert len(provider.session.calls) == 1
    params = provider.session.calls[0][1]
    assert params['imdb'] == ''
    assert params['search'] == 'Show.S01E01'


def test_search_uses_canonical_imdb_id():
    """Pass a canonical IMDb identifier to the SDBits search."""
    provider = make_provider('6135388')

    assert provider.search({'Episode': ['Show.S01E01']}) == []
    assert len(provider.session.calls) == 1
    params = provider.session.calls[0][1]
    assert params['imdb'] == 'tt6135388'
    assert params['search'] == ''


def test_rss_search_preserves_default_search_params():
    """Keep RSS requests independent of IMDb metadata."""
    provider = make_provider('tt6135388')

    assert provider.search({'RSS': ['']}) == []
    assert len(provider.session.calls) == 1
    params = provider.session.calls[0][1]
    assert params['imdb'] == ''
    assert params['search'] == ''
