# coding=utf-8
"""Tests for medusa.tv.py."""

from medusa.common import DOWNLOADED, Quality, SNATCHED, SNATCHED_PROPER, WANTED
from medusa.tv import TVEpisode
import pytest


@pytest.mark.parametrize('p', [
    {  # p0: Downloaded 720p HDTV and found 720p BluRay: yes
        'ep_status': DOWNLOADED,
        'cur_quality': Quality.HDTV,
        'new_quality': Quality.HDBLURAY,
        'allowed_qualities': [Quality.HDTV, Quality.HDWEBDL, Quality.HDBLURAY],
        'preferred_qualities': [],
        'expected': True
    },
    {  # p1: Downloaded 720p HDTV and found 720p BluRay, but episode status is invalid: no
        'ep_status': WANTED,
        'cur_quality': Quality.HDTV,
        'new_quality': Quality.HDBLURAY,
        'allowed_qualities': [Quality.HDTV, Quality.HDWEBDL, Quality.HDBLURAY],
        'preferred_qualities': [],
        'expected': False
    },
    {  # p2: Downloaded 720p BluRay and found 720p HDTV, not a better quality: no
        'ep_status': DOWNLOADED,
        'cur_quality': Quality.HDBLURAY,
        'new_quality': Quality.HDTV,
        'allowed_qualities': [Quality.HDTV, Quality.HDWEBDL, Quality.HDBLURAY],
        'preferred_qualities': [],
        'expected': False
    },
    {  # p3: Snatched 720p HDTV and found 720p BluRay: yes
        'ep_status': SNATCHED,
        'cur_quality': Quality.HDTV,
        'new_quality': Quality.HDBLURAY,
        'allowed_qualities': [Quality.HDTV, Quality.HDWEBDL, Quality.HDBLURAY],
        'preferred_qualities': [],
        'expected': True
    },
    {  # p4: Snatched Proper 720p HDTV and found 720p BluRay, but 720p HDTV is preferred: no
        'ep_status': SNATCHED_PROPER,
        'cur_quality': Quality.HDTV,
        'new_quality': Quality.HDBLURAY,
        'allowed_qualities': [Quality.HDTV, Quality.HDWEBDL, Quality.HDBLURAY],
        'preferred_qualities': [Quality.HDTV],
        'expected': False
    },
    {  # p5: Snatched Proper 720p HDTV and found 720p BluRay, but 720p BluRay is not allowed or preferred: no
        'ep_status': SNATCHED_PROPER,
        'cur_quality': Quality.HDTV,
        'new_quality': Quality.HDBLURAY,
        'allowed_qualities': [Quality.HDTV, Quality.HDWEBDL],
        'preferred_qualities': [Quality.HDWEBDL],
        'expected': False
    },
    {  # p6: Snatched Proper 720p HDTV and found 720p BluRay, and 720p BluRay is not preferred but allowed: yes
        'ep_status': SNATCHED_PROPER,
        'cur_quality': Quality.HDTV,
        'new_quality': Quality.HDBLURAY,
        'allowed_qualities': [Quality.HDTV, Quality.HDWEBDL, Quality.HDBLURAY],
        'preferred_qualities': [Quality.HDWEBDL],
        'expected': True
    },
    {  # p7: Downloaded 720p HDTV and found 720p BluRay, 720p BluRay is not explicity allowed but it's preferred: yes
        'ep_status': DOWNLOADED,
        'cur_quality': Quality.HDTV,
        'new_quality': Quality.HDBLURAY,
        'allowed_qualities': [Quality.HDTV, Quality.HDWEBDL],
        'preferred_qualities': [Quality.HDBLURAY],
        'expected': True
    },
    {  # p8: Downloaded 720p HDTV and found 720p BluRay, 720p BluRay is allowed and it's preferred: yes
        'ep_status': DOWNLOADED,
        'cur_quality': Quality.HDTV,
        'new_quality': Quality.HDBLURAY,
        'allowed_qualities': [Quality.HDTV, Quality.HDWEBDL, Quality.HDBLURAY],
        'preferred_qualities': [Quality.HDBLURAY],
        'expected': True
    },
    {  # p9: Downloaded 720p BluRay and found 720p HDTV, 720p HDTV is preferred: yes
        'ep_status': DOWNLOADED,
        'cur_quality': Quality.HDBLURAY,
        'new_quality': Quality.HDTV,
        'allowed_qualities': [Quality.HDTV, Quality.HDWEBDL, Quality.HDBLURAY],
        'preferred_qualities': [Quality.HDTV],
        'expected': True
    },
    {  # p10: Downloaded 720p BluRay and found 720p HDTV, both are preferred but 720p BluRay is still better: no
        'ep_status': DOWNLOADED,
        'cur_quality': Quality.HDBLURAY,
        'new_quality': Quality.HDTV,
        'allowed_qualities': [Quality.HDTV, Quality.HDWEBDL],
        'preferred_qualities': [Quality.HDTV, Quality.HDBLURAY],
        'expected': False
    },
    {  # p11: Downloaded 720p WEB-DL and found 720p HDTV, 720p WEB-DL is not allowed or preferred and 720p HDTV is allowed: yes
        'ep_status': DOWNLOADED,
        'cur_quality': Quality.HDWEBDL,
        'new_quality': Quality.HDTV,
        'allowed_qualities': [Quality.HDTV, Quality.HDBLURAY],
        'preferred_qualities': [Quality.HDBLURAY],
        'expected': True
    }
])
def test_should_replace(p):
    # Given
    ep_status = p['ep_status']
    cur_quality = p['cur_quality']
    new_quality = p['new_quality']
    allowed_qualities = p['allowed_qualities']
    preferred_qualities = p['preferred_qualities']
    expected = p['expected']

    # When
    actual = TVEpisode.should_replace(ep_status, cur_quality, new_quality, allowed_qualities, preferred_qualities)

    # Then
    assert expected == actual
