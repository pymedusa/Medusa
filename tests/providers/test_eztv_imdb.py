# coding=utf-8
"""Tests for EZTV IMDb identifier handling."""
from __future__ import unicode_literals

from types import SimpleNamespace

from medusa.indexers.utils import mappings
from medusa.providers.torrent.json import eztv

import pytest


class RecordingSession(object):
    """Record provider requests and return an empty result page."""

    def __init__(self):
        """Initialize an empty call log."""
        self.calls = []

    def get_json(self, url, params=None):
        """Record a request and return an empty result page."""
        self.calls.append((url, params.copy()))
        return {'torrents': []}


def make_provider(imdb_id=None):
    """Create a provider without initializing caches or other services."""
    provider = object.__new__(eztv.EztvProvider)
    provider.series = SimpleNamespace(externals={mappings[10]: imdb_id})
    provider.session = RecordingSession()
    provider.urls = {'api': 'https://eztvx.to/api/get-torrents'}
    provider.max_pages = 1
    return provider


@pytest.mark.parametrize('imdb_id', [None, '', 'garbage', 'https://example.com/title/tt1234567x'])
def test_search_skips_invalid_imdb_ids_without_request(imdb_id):
    """Skip malformed or missing IDs without making provider requests."""
    provider = make_provider(imdb_id)

    assert provider.search({'Episode': ['Show.S01E01']}) == []
    assert provider.session.calls == []


def test_search_skips_imdb_id_rejected_by_parser(monkeypatch):
    """Skip an ID that the identifier parser rejects."""
    provider = make_provider('legacy-invalid-value')
    monkeypatch.setattr(eztv, 'ImdbIdentifier', lambda value: SimpleNamespace(imdb_id=None))

    assert provider.search({'Episode': ['Show.S01E01']}) == []
    assert provider.session.calls == []


@pytest.mark.parametrize('imdb_id', [
    ('6135388', '6135388'),
    ('https://www.imdb.com/title/tt6135388/episodes/?season=2&ref_=ttep', '6135388'),
])
def test_search_uses_normalized_imdb_id(imdb_id):
    """Pass only the normalized numeric ID to the provider API."""
    raw_id, expected_id = imdb_id
    provider = make_provider(raw_id)

    assert provider.search({'Episode': ['Show.S01E01']}) == []
    assert len(provider.session.calls) == 1
    assert provider.session.calls[0][1]['imdb_id'] == expected_id


def test_rss_search_does_not_require_imdb_id():
    """Allow RSS searches with no IMDb ID."""
    provider = make_provider()

    assert provider.search({'RSS': ['']}) == []
    assert len(provider.session.calls) == 1
    assert 'imdb_id' not in provider.session.calls[0][1]
