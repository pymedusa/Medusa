# coding=utf-8
"""Tests for episode filename naming with special characters (#12244)."""
from __future__ import unicode_literals

from datetime import date

from medusa.common import Quality

import pytest


@pytest.fixture
def make_episode(create_tvshow, create_tvepisode, app_config):
    def _make(show_name, ep_name):
        app_config('NAMING_STRIP_YEAR', True)
        app_config('NAMING_MULTI_EP', 1)
        app_config('NAMING_ANIME', 3)
        app_config('NAMING_CUSTOM_ANIME', False)
        app_config('UNKNOWN_RELEASE_GROUP', 'Medusa')
        show = create_tvshow(
            indexerid=1, name=show_name, air_by_date=False, sports=False,
            anime=False, season_folders=1,
        )
        ep = create_tvepisode(
            series=show, season=1, episode=1, name=ep_name,
            airdate=date(2025, 1, 15), quality=Quality.FULLHDWEBDL,
            release_group='GROUP', release_name='', is_proper=False,
            absolute_number=0, scene_season=1, scene_episode=1,
            scene_absolute_number=0,
        )
        ep.related_episodes = []
        return ep
    return _make


@pytest.mark.parametrize('show_name,ep_name,pattern,expected', [
    # Apostrophe becomes a separator in dotted tokens (not glued).
    (
        "C'est pas sorcier",
        "L'\xe9mission de janvier",
        '%S.N.S%0SE%0E.%E.N',
        'C.est.pas.sorcier.S01E01.L.\xe9mission.de.janvier',
    ),
    (
        'Le journal du hard',
        "Et si la peur n\u2019existait pas ?",
        '%S.N.S%0SE%0E.%E.N',
        'Le.journal.du.hard.S01E01.Et.si.la.peur.n.existait.pas',
    ),
    # Plain tokens keep the apostrophe; colon/question use sanitize_filename.
    (
        'Alien theory : Les preuves ultimes',
        'Titre normal',
        '%SN - S%0SE%0E - %EN',
        'Alien theory - Les preuves ultimes - S01E01 - Titre normal',
    ),
])
def test_formatted_filename_special_chars(make_episode, show_name, ep_name, pattern, expected):
    episode = make_episode(show_name, ep_name)
    assert episode.formatted_filename(pattern=pattern) == expected


def test_sanitize_scene_name_unchanged_for_search():
    """Search/name-cache must keep deleting apostrophes (scene style)."""
    from medusa.helpers import sanitize_scene_name
    assert sanitize_scene_name("C'est pas sorcier") == 'Cest.pas.sorcier'
    assert sanitize_scene_name("L'\xe9mission") == 'L\xe9mission'
