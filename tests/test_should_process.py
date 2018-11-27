# coding=utf-8
"""Tests for medusa/test_should_process.py."""
from __future__ import unicode_literals
from medusa.common import Quality
from medusa.post_processor import PostProcessor

import pytest


@pytest.mark.parametrize('p', [
    {  # p0: New allowed quality higher than current allowed: yes
        'cur_quality': Quality.HDTV,
        'new_quality': Quality.HDBLURAY,
        'allowed_qualities': [Quality.HDTV, Quality.HDWEBDL, Quality.HDBLURAY],
        'preferred_qualities': [],
        'expected': True
    },
    {  # p1: New quality not in allowed qualities: no
        'cur_quality': Quality.HDTV,
        'new_quality': Quality.HDBLURAY,
        'allowed_qualities': [Quality.HDTV, Quality.HDWEBDL],
        'preferred_qualities': [],
        'expected': False
    },
    {  # p2: New allowed quality lower than current allowed: no
        'cur_quality': Quality.HDBLURAY,
        'new_quality': Quality.HDTV,
        'allowed_qualities': [Quality.HDTV, Quality.HDWEBDL, Quality.HDBLURAY],
        'preferred_qualities': [],
        'expected': False
    },
    {  # p3: Preferred quality replacing current allowed: yes
        'cur_quality': Quality.HDTV,
        'new_quality': Quality.HDBLURAY,
        'allowed_qualities': [Quality.HDTV, Quality.HDWEBDL],
        'preferred_qualities': [Quality.HDBLURAY],
        'expected': True
    },
    {  # p4: Preferred quality better than current preferred: yes
        'cur_quality': Quality.HDWEBDL,
        'new_quality': Quality.HDBLURAY,
        'allowed_qualities': [Quality.HDTV],
        'preferred_qualities': [Quality.HDWEBDL, Quality.HDBLURAY],
        'expected': True
    },
    {  # p5: New quality not in quality system: no
        'cur_quality': Quality.HDTV,
        'new_quality': Quality.SDTV,
        'allowed_qualities': [Quality.HDTV],
        'preferred_qualities': [Quality.HDWEBDL, Quality.HDBLURAY],
        'expected': False
    },
    {  # p6: Preferred lower quality replacing current higher allowed: yes
        'cur_quality': Quality.HDWEBDL,
        'new_quality': Quality.HDTV,
        'allowed_qualities': [Quality.HDWEBDL],
        'preferred_qualities': [Quality.HDTV],
        'expected': True
    },
    {  # p7: Current quality is NA: yes
        'cur_quality': Quality.NA,
        'new_quality': Quality.HDTV,
        'allowed_qualities': [Quality.HDWEBDL],
        'preferred_qualities': [Quality.HDTV],
        'expected': True
    },
])
def test_should_process(p):
    """Run the test."""
    # Given
    current_quality = p['cur_quality']
    new_quality = p['new_quality']
    allowed_qualities = p['allowed_qualities']
    preferred_qualities = p['preferred_qualities']
    expected = p['expected']

    # When
    replace, msg = PostProcessor._should_process(current_quality, new_quality, allowed_qualities, preferred_qualities)
    actual = replace

    # Then
    if expected != actual:
        print(msg)
    assert expected == actual
