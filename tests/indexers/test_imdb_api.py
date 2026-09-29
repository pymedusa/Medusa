# coding=utf-8
"""Tests for medusa/indexers/imdb/api.py."""
from __future__ import unicode_literals

from medusa.indexers.imdb.api import Imdb

from mock.mock import MagicMock, patch

import pytest


@pytest.fixture
def imdb_api():
    """Return an Imdb indexer whose session and imdbpie client are mocked out."""
    session = MagicMock()
    with patch('medusa.indexers.imdb.api.imdbpie.Imdb'):
        indexer = Imdb(session=session)
    indexer.imdb_api = MagicMock()
    return indexer


def test_get_episodes_does_not_scrape_imdb_html(imdb_api):
    """Get episode details from the imdb api only, never by scraping imdb.com.

    IMDb answers scripted requests to /title/{imdb_id}/episodes with a 403, and an
    empty WAF challenge when a browser user agent is used, so scraping it can only
    log a warning and waste a request per season on every show update.
    """
    # Given
    imdb_api.imdb_api.get_title_episodes.return_value = {
        'seasons': [{
            'season': 1,
            'episodes': [{
                'season': 1,
                'episode': 1,
                'id': '/title/tt0000002/',
                'title': 'Pilot',
                'year': 2023,
            }],
        }],
    }
    imdb_api.imdb_api.get_title_episodes_detailed.return_value = {'episodes': []}

    # When
    imdb_api._get_episodes(1, detailed=True)

    # Then
    assert not imdb_api.config['session'].get.called
