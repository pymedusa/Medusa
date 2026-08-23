# coding=utf-8
"""Tests for the legacy TVDB Plex fallback."""
from __future__ import unicode_literals

import datetime
from types import SimpleNamespace

from medusa import app
from medusa.indexers.exceptions import IndexerShowNotFound
from medusa.indexers.tvdbv2.api import API_BASE_TVDB, TVDBv2
from medusa.indexers.tvdbv2.fallback import PlexFallback

from mock.mock import Mock
import pytest
from tvdbapiv2.exceptions import ApiException


def create_session(host=API_BASE_TVDB):
    """Create a minimal TVDB session with Plex fallback configuration."""
    return SimpleNamespace(
        api_client=SimpleNamespace(host=host),
        fallback_config={
            'plex_fallback_time': datetime.datetime.now(),
            'api_base_url': host,
            'fallback_plex_enable': True,
            'fallback_plex_timeout': 3,
            'fallback_plex_notifications': False,
        },
    )


class FakeIndexer(object):
    """Minimal indexer used to exercise the fallback decorator."""

    def __init__(self, session, fail_on_plex=False):
        self.config = {'session': session}
        self.calls = 0
        self.fail_on_plex = fail_on_plex

    @PlexFallback
    def search(self):
        """Return a result from Plex after simulating a legacy TVDB 404."""
        self.calls += 1
        if self.config['session'].api_client.host == API_BASE_TVDB or self.fail_on_plex:
            raise IndexerShowNotFound('Legacy TVDB endpoint returned 404')
        return 'plex result'


def test_show_not_found_from_legacy_tvdb_falls_back_to_plex(monkeypatch):
    session = create_session()
    indexer = FakeIndexer(session)
    auth = Mock()
    monkeypatch.setattr('medusa.indexers.tvdbv2.fallback.TVDBAuth', auth)

    assert 'plex result' == indexer.search()
    assert 2 == indexer.calls
    assert app.FALLBACK_PLEX_API_URL == session.api_client.host
    auth.assert_called_once_with(api_key=app.TVDB_API_KEY, api_base=app.FALLBACK_PLEX_API_URL)


def test_show_not_found_from_plex_is_not_retried():
    session = create_session(app.FALLBACK_PLEX_API_URL)
    indexer = FakeIndexer(session, fail_on_plex=True)

    with pytest.raises(IndexerShowNotFound):
        indexer.search()

    assert 1 == indexer.calls


def test_episode_404_from_legacy_tvdb_falls_back_to_plex(monkeypatch):
    session = create_session()
    session.series_api = Mock()
    session.series_api.series_id_episodes_query_get.side_effect = [
        ApiException(status=404, reason='Not found'),
        ApiException(status=404, reason='Not found'),
    ]
    monkeypatch.setattr('medusa.indexers.tvdbv2.fallback.TVDBAuth', Mock())

    indexer = TVDBv2(session=session, cache=False)
    indexer.shows[123] = {'seriesname': 'Test Show', 'firstaired': '2026-01-01'}

    assert {'episode': []} == indexer._query_series(123)
    assert 2 == session.series_api.series_id_episodes_query_get.call_count
    assert app.FALLBACK_PLEX_API_URL == session.api_client.host
