# coding=utf-8
"""Tests for medusa/test_should_replace.py."""
from __future__ import unicode_literals
from medusa.common import ARCHIVED, DOWNLOADED, Quality, SKIPPED, SNATCHED, SNATCHED_BEST, SNATCHED_PROPER, WANTED
from medusa.search import DAILY_SEARCH, PROPER_SEARCH

import pytest


@pytest.mark.parametrize('p', [
    {  # p0: Downloaded 720p HDTV and found 720p BluRay: no
        'ep_status': DOWNLOADED,
        'cur_quality': Quality.HDTV,
        'new_quality': Quality.HDBLURAY,
        'allowed_qualities': [Quality.HDTV, Quality.HDWEBDL, Quality.HDBLURAY],
        'preferred_qualities': [],
        'download_current_quality': False,
        'force': False,
        'manually_searched': False,
        'expected': False
    },
    {  # p1: Downloaded 720p HDTV and found 720p BluRay, but episode status is invalid: no
        'ep_status': WANTED,
        'cur_quality': Quality.HDTV,
        'new_quality': Quality.HDBLURAY,
        'allowed_qualities': [Quality.HDTV, Quality.HDWEBDL, Quality.HDBLURAY],
        'preferred_qualities': [],
        'download_current_quality': False,
        'force': False,
        'manually_searched': False,
        'expected': False
    },
    {  # p2: Downloaded 720p BluRay and found 720p HDTV, not a better quality: no
        'ep_status': DOWNLOADED,
        'cur_quality': Quality.HDBLURAY,
        'new_quality': Quality.HDTV,
        'allowed_qualities': [Quality.HDTV, Quality.HDWEBDL, Quality.HDBLURAY],
        'preferred_qualities': [],
        'download_current_quality': False,
        'force': False,
        'manually_searched': False,
        'expected': False
    },
    {  # p3: Snatched 720p HDTV and found 720p BluRay: yes
        'ep_status': SNATCHED,
        'cur_quality': Quality.HDTV,
        'new_quality': Quality.HDBLURAY,
        'allowed_qualities': [Quality.HDTV, Quality.HDWEBDL],
        'preferred_qualities': [Quality.HDBLURAY],
        'download_current_quality': False,
        'force': False,
        'manually_searched': False,
        'expected': True
    },
    {  # p4: Snatched Proper 720p HDTV and found 720p BluRay, but 720p HDTV is preferred: no
        'ep_status': SNATCHED_PROPER,
        'cur_quality': Quality.HDTV,
        'new_quality': Quality.HDBLURAY,
        'allowed_qualities': [Quality.HDTV, Quality.HDWEBDL, Quality.HDBLURAY],
        'preferred_qualities': [Quality.HDTV],
        'download_current_quality': False,
        'force': False,
        'manually_searched': False,
        'expected': False
    },
    {  # p5: Snatched Proper 720p HDTV and found 720p BluRay, but 720p BluRay is not allowed or preferred: no
        'ep_status': SNATCHED_PROPER,
        'cur_quality': Quality.HDTV,
        'new_quality': Quality.HDBLURAY,
        'allowed_qualities': [Quality.HDTV, Quality.HDWEBDL],
        'preferred_qualities': [Quality.HDWEBDL],
        'download_current_quality': False,
        'force': False,
        'manually_searched': False,
        'expected': False
    },
    {  # p6: Snatched Proper 720p HDTV and found 720p BluRay, and 720p BluRay is not preferred but allowed: yes
        'ep_status': SNATCHED_PROPER,
        'cur_quality': Quality.HDTV,
        'new_quality': Quality.HDBLURAY,
        'allowed_qualities': [Quality.HDTV, Quality.HDWEBDL, Quality.HDBLURAY],
        'preferred_qualities': [Quality.HDWEBDL],
        'download_current_quality': False,
        'force': False,
        'manually_searched': False,
        'expected': True
    },
    {  # p7: Downloaded 720p HDTV and found 720p BluRay, 720p BluRay is not explicity allowed but it's preferred: yes
        'ep_status': DOWNLOADED,
        'cur_quality': Quality.HDTV,
        'new_quality': Quality.HDBLURAY,
        'allowed_qualities': [Quality.HDTV, Quality.HDWEBDL],
        'preferred_qualities': [Quality.HDBLURAY],
        'download_current_quality': False,
        'force': False,
        'manually_searched': False,
        'expected': True
    },
    {  # p8: Downloaded 720p HDTV and found 720p BluRay, 720p BluRay is allowed and it's preferred: yes
        'ep_status': DOWNLOADED,
        'cur_quality': Quality.HDTV,
        'new_quality': Quality.HDBLURAY,
        'allowed_qualities': [Quality.HDTV, Quality.HDWEBDL, Quality.HDBLURAY],
        'preferred_qualities': [Quality.HDBLURAY],
        'download_current_quality': False,
        'force': False,
        'manually_searched': False,
        'expected': True
    },
    {  # p9: Downloaded 720p BluRay and found 720p HDTV, 720p HDTV is preferred: yes
        'ep_status': DOWNLOADED,
        'cur_quality': Quality.HDBLURAY,
        'new_quality': Quality.HDTV,
        'allowed_qualities': [Quality.HDTV, Quality.HDWEBDL, Quality.HDBLURAY],
        'preferred_qualities': [Quality.HDTV],
        'download_current_quality': False,
        'force': False,
        'manually_searched': False,
        'expected': True
    },
    {  # p10: Downloaded 720p BluRay and found 720p HDTV, both are preferred but 720p BluRay is still better: no
        'ep_status': DOWNLOADED,
        'cur_quality': Quality.HDBLURAY,
        'new_quality': Quality.HDTV,
        'allowed_qualities': [Quality.HDTV, Quality.HDWEBDL],
        'preferred_qualities': [Quality.HDTV, Quality.HDBLURAY],
        'download_current_quality': False,
        'force': False,
        'manually_searched': False,
        'expected': False
    },
    {  # p11: Downloaded 720p WEB-DL and found 720p HDTV, 720p WEB-DL is not allowed or preferred and 720p HDTV is allowed: yes
        'ep_status': DOWNLOADED,
        'cur_quality': Quality.HDWEBDL,
        'new_quality': Quality.HDTV,
        'allowed_qualities': [Quality.HDTV, Quality.HDBLURAY],
        'preferred_qualities': [Quality.HDBLURAY],
        'download_current_quality': False,
        'force': False,
        'manually_searched': False,
        'expected': True
    },
    {  # p12: Snatched 720p HDTV and found 720p BluRay: no
        'ep_status': SNATCHED,
        'cur_quality': Quality.HDTV,
        'new_quality': Quality.HDBLURAY,
        'allowed_qualities': [],
        'preferred_qualities': [Quality.HDTV, Quality.HDBLURAY],
        'download_current_quality': False,
        'force': False,
        'manually_searched': False,
        'expected': False
    },
    {  # p13: Snatched 720p HDTV and found 720p BluRay: no
        'ep_status': SNATCHED,
        'cur_quality': Quality.HDTV,
        'new_quality': Quality.HDBLURAY,
        'allowed_qualities': [Quality.HDTV],
        'preferred_qualities': [Quality.HDTV, Quality.HDBLURAY],
        'download_current_quality': False,
        'force': False,
        'manually_searched': False,
        'expected': False
    },
    {  # p14: Downloaded 720p BluRay and found 720p HDTV: no
        'ep_status': DOWNLOADED,
        'cur_quality': Quality.HDBLURAY,
        'new_quality': Quality.HDTV,
        'allowed_qualities': [Quality.HDTV],
        'preferred_qualities': [Quality.HDTV, Quality.HDBLURAY],
        'download_current_quality': False,
        'force': False,
        'manually_searched': False,
        'expected': False
    },
    {  # p15: Snatched 720p BluRay and found 720p HDTV: no
        'ep_status': SNATCHED,
        'cur_quality': Quality.HDBLURAY,
        'new_quality': Quality.HDTV,
        'allowed_qualities': [],
        'preferred_qualities': [Quality.HDTV, Quality.HDBLURAY],
        'download_current_quality': False,
        'force': False,
        'manually_searched': False,
        'expected': False
    },
    {  # p16: Archived 720p HDTV and found 720p HDBLURAY: no
        'ep_status': ARCHIVED,
        'cur_quality': Quality.HDTV,
        'new_quality': Quality.HDBLURAY,
        'allowed_qualities': [],
        'preferred_qualities': [Quality.HDTV, Quality.HDBLURAY],
        'download_current_quality': False,
        'force': False,
        'manually_searched': False,
        'expected': False
    },
    {  # p17: Archived 720p HDTV and found 720p HDBLURAY: no
        'ep_status': ARCHIVED,
        'cur_quality': Quality.HDTV,
        'new_quality': Quality.HDBLURAY,
        'allowed_qualities': [Quality.HDTV, Quality.HDBLURAY],
        'preferred_qualities': [],
        'download_current_quality': False,
        'force': False,
        'manually_searched': False,
        'expected': False
    },
    {  # p18: Downloaded Unknown found 720p HDBLURAY: yes
        'ep_status': DOWNLOADED,
        'cur_quality': Quality.UNKNOWN,
        'new_quality': Quality.HDBLURAY,
        'allowed_qualities': [Quality.HDTV, Quality.HDBLURAY],
        'preferred_qualities': [],
        'download_current_quality': False,
        'force': False,
        'manually_searched': False,
        'expected': True
    },
    {  # p19: Downloaded SDTV (not in quality system) and found 720p HDTV: yes
        'ep_status': DOWNLOADED,
        'cur_quality': Quality.SDTV,
        'new_quality': Quality.HDTV,
        'allowed_qualities': [Quality.HDTV],
        'preferred_qualities': [],
        'download_current_quality': False,
        'force': False,
        'manually_searched': False,
        'expected': True
    },
    {  # p20: Downloaded SDTV (not in quality system) and found 720p HDBLURAY: no
        'ep_status': DOWNLOADED,
        'cur_quality': Quality.SDTV,
        'new_quality': Quality.HDBLURAY,
        'allowed_qualities': [Quality.HDTV],
        'preferred_qualities': [],
        'download_current_quality': False,
        'force': False,
        'manually_searched': False,
        'expected': False
    },
    {  # p21: Downloaded Unknown found 720p HDBLURAY and force search: yes
        'ep_status': DOWNLOADED,
        'cur_quality': Quality.UNKNOWN,
        'new_quality': Quality.HDBLURAY,
        'allowed_qualities': [Quality.HDTV, Quality.HDBLURAY],
        'preferred_qualities': [],
        'download_current_quality': False,
        'force': True,
        'manually_searched': False,
        'expected': True
    },
    {  # p22: Downloaded SDTV found SDTV and force search and download_current_quality: yes
        'ep_status': DOWNLOADED,
        'cur_quality': Quality.SDTV,
        'new_quality': Quality.SDTV,
        'allowed_qualities': [Quality.SDTV],
        'preferred_qualities': [],
        'download_current_quality': True,
        'force': True,
        'manually_searched': False,
        'expected': True
    },
    {  # p23: Downloaded SDTV found SDTV and not force search and not download_current_quality: no
        'ep_status': DOWNLOADED,
        'cur_quality': Quality.SDTV,
        'new_quality': Quality.SDTV,
        'allowed_qualities': [Quality.SDTV],
        'preferred_qualities': [],
        'download_current_quality': False,
        'force': False,
        'manually_searched': False,
        'expected': False
    },
    {  # p24: Downloaded SDTV and found SDTV. Not wanted anymore. Force search: no
        'ep_status': DOWNLOADED,
        'cur_quality': Quality.SDTV,
        'new_quality': Quality.SDTV,
        'allowed_qualities': [Quality.HDTV],
        'preferred_qualities': [],
        'download_current_quality': False,
        'force': True,
        'manually_searched': False,
        'expected': False
    },
    {  # p25: Downloaded SDTV and found SDTV. Not wanted anymore: no
        'ep_status': DOWNLOADED,
        'cur_quality': Quality.SDTV,
        'new_quality': Quality.SDTV,
        'allowed_qualities': [Quality.HDTV],
        'preferred_qualities': [],
        'download_current_quality': False,
        'force': False,
        'manually_searched': False,
        'expected': False
    },
    {  # p26: Downloaded SDTV and found SDTV. Still wanted. Force search and download_current_quality: yes
        'ep_status': DOWNLOADED,
        'cur_quality': Quality.SDTV,
        'new_quality': Quality.SDTV,
        'allowed_qualities': [Quality.SDTV],
        'preferred_qualities': [],
        'download_current_quality': True,
        'force': True,
        'manually_searched': False,
        'expected': True
    },
    {  # p27: Archived SDTV and found HDTV. Force search yes: yes
        'ep_status': ARCHIVED,
        'cur_quality': Quality.SDTV,
        'new_quality': Quality.HDTV,
        'allowed_qualities': [Quality.HDTV],
        'preferred_qualities': [],
        'download_current_quality': False,
        'force': True,
        'manually_searched': False,
        'expected': True
    },
    {  # p28: SKIPPED and found HDTV. Force search yes: yes
        'ep_status': SKIPPED,
        'cur_quality': SKIPPED,
        'new_quality': Quality.HDTV,
        'allowed_qualities': [Quality.HDTV],
        'preferred_qualities': [],
        'download_current_quality': False,
        'force': True,
        'manually_searched': False,
        'expected': True
    },
    {  # p29: SKIPPED and found HDTV. Force search no: no
        'ep_status': SKIPPED,
        'cur_quality': None,
        'new_quality': Quality.HDTV,
        'allowed_qualities': [Quality.HDTV],
        'preferred_qualities': [],
        'download_current_quality': False,
        'force': False,
        'manually_searched': False,
        'expected': False
    },
    {  # p30: DOWNLOADED and found 1080p HDBLURAY (not in wanted qualities). Force search yes: false
        'ep_status': DOWNLOADED,
        'cur_quality': Quality.HDTV,
        'new_quality': Quality.HDBLURAY,
        'allowed_qualities': [Quality.HDTV],
        'preferred_qualities': [],
        'download_current_quality': False,
        'force': True,
        'manually_searched': False,
        'expected': False
    },
    {  # p31: ARCHIVED and found 1080p HDBLURAY (not in wanted qualities). Force search yes: false
        'ep_status': ARCHIVED,
        'cur_quality': Quality.HDTV,
        'new_quality': Quality.HDBLURAY,
        'allowed_qualities': [Quality.HDTV],
        'preferred_qualities': [],
        'download_current_quality': False,
        'force': True,
        'manually_searched': False,
        'expected': False
    },
    {  # p32: ARCHIVED and found 1080p HDTV. Force search yes: true
        'ep_status': ARCHIVED,
        'cur_quality': Quality.HDTV,
        'new_quality': Quality.HDTV,
        'allowed_qualities': [Quality.HDTV],
        'preferred_qualities': [],
        'download_current_quality': True,
        'force': True,
        'manually_searched': False,
        'expected': True
    },
    {  # p33: DOWNLOADED and found 1080p HDTV. Manual searched yes: false
        'ep_status': DOWNLOADED,
        'cur_quality': Quality.HDBLURAY,
        'new_quality': Quality.HDTV,
        'allowed_qualities': [Quality.HDTV],
        'preferred_qualities': [],
        'download_current_quality': False,
        'force': False,
        'manually_searched': True,
        'expected': False
    },
    {  # p34: DOWNLOADED and found 1080p HDTV. Manual searched no: true
        'ep_status': DOWNLOADED,
        'cur_quality': Quality.HDBLURAY,
        'new_quality': Quality.HDTV,
        'allowed_qualities': [Quality.HDTV],
        'preferred_qualities': [],
        'download_current_quality': False,
        'force': False,
        'manually_searched': False,
        'expected': True
    },
    {  # p35: DOWNLOADED and found 1080p HDTV. Manual searched yes and force search yes: true
        'ep_status': DOWNLOADED,
        'cur_quality': Quality.HDBLURAY,
        'new_quality': Quality.HDTV,
        'allowed_qualities': [Quality.HDTV],
        'preferred_qualities': [],
        'download_current_quality': False,
        'force': True,
        'manually_searched': True,
        'expected': True
    },
    {  # p36: SNATCHED BEST and found HDBLURAY: no
        'ep_status': SNATCHED_BEST,
        'cur_quality': Quality.HDTV,
        'new_quality': Quality.HDBLURAY,
        'allowed_qualities': [Quality.SDTV],
        'preferred_qualities': [Quality.HDTV],
        'download_current_quality': False,
        'force': False,
        'manually_searched': False,
        'expected': False
    },
    {  # p37: Current quality is NA: yes
        'ep_status': SNATCHED,
        'cur_quality': Quality.NA,
        'new_quality': Quality.HDTV,
        'allowed_qualities': [Quality.SDTV],
        'preferred_qualities': [Quality.HDTV],
        'download_current_quality': False,
        'force': False,
        'manually_searched': False,
        'expected': True
    },
    {  # p38: Downloaded UNKNOWN and its on Allowed: no
        'ep_status': DOWNLOADED,
        'cur_quality': Quality.UNKNOWN,
        'new_quality': Quality.HDTV,
        'allowed_qualities': [Quality.UNKNOWN, Quality.SDTV],
        'preferred_qualities': [],
        'download_current_quality': False,
        'force': False,
        'manually_searched': False,
        'expected': False
    },
    {  # p39: Downloaded UNKNOWN and its on Allowed but found Preferred: yes
        'ep_status': DOWNLOADED,
        'cur_quality': Quality.UNKNOWN,
        'new_quality': Quality.HDTV,
        'allowed_qualities': [Quality.UNKNOWN],
        'preferred_qualities': [Quality.HDTV],
        'download_current_quality': False,
        'force': False,
        'manually_searched': False,
        'expected': True
    },
    {  # p40: Downloaded SDTV and found SDTV PROPER: yes
        'ep_status': DOWNLOADED,
        'cur_quality': Quality.SDTV,
        'new_quality': Quality.SDTV,
        'allowed_qualities': [Quality.SDTV],
        'preferred_qualities': [],
        'download_current_quality': False,
        'force': False,
        'manually_searched': False,
        'search_type': PROPER_SEARCH,
        'expected': True
    },
    {  # p41: Downloaded SDTV and found HDTV PROPER but only Allowed. Not proper search: no
        'ep_status': DOWNLOADED,
        'cur_quality': Quality.SDTV,
        'new_quality': Quality.HDTV,
        'allowed_qualities': [Quality.SDTV, Quality.HDTV],
        'preferred_qualities': [],
        'download_current_quality': False,
        'force': False,
        'manually_searched': False,
        'expected': False
    },
    {  # p42: Downloaded SDTV and found HDTV PROPER in Preferred. Not proper search: yes
        'ep_status': DOWNLOADED,
        'cur_quality': Quality.SDTV,
        'new_quality': Quality.HDTV,
        'allowed_qualities': [Quality.SDTV],
        'preferred_qualities': [Quality.HDTV],
        'download_current_quality': False,
        'force': False,
        'manually_searched': False,
        'expected': True
    },
    {  # p43: Downloaded SDTV and found SDTV PROPER: yes
        'ep_status': DOWNLOADED,
        'cur_quality': Quality.SDTV,
        'new_quality': Quality.SDTV,
        'allowed_qualities': [Quality.SDTV],
        'preferred_qualities': [Quality.HDTV],
        'download_current_quality': False,
        'force': False,
        'manually_searched': False,
        'search_type': PROPER_SEARCH,
        'expected': True
    },
    {  # p44: Downloaded SDTV and found HDTV PROPER. Proper search: no
        'ep_status': DOWNLOADED,
        'cur_quality': Quality.SDTV,
        'new_quality': Quality.HDTV,
        'allowed_qualities': [Quality.SDTV, Quality.HDTV],
        'preferred_qualities': [],
        'download_current_quality': False,
        'force': False,
        'manually_searched': False,
        'search_type': PROPER_SEARCH,
        'expected': False
    },
    {  # p45: Downloaded UNKNOWN and it's Preferred: yes
        'ep_status': DOWNLOADED,
        'cur_quality': Quality.HDTV,
        'new_quality': Quality.UNKNOWN,
        'allowed_qualities': [Quality.HDTV],
        'preferred_qualities': [Quality.UNKNOWN],
        'download_current_quality': False,
        'force': False,
        'manually_searched': False,
        'expected': True
    },
])
def test_should_replace(p):
    """Run the test."""
    # Given
    ep_status = p['ep_status']
    cur_quality = p['cur_quality']
    new_quality = p['new_quality']
    allowed_qualities = p['allowed_qualities']
    preferred_qualities = p['preferred_qualities']
    expected = p['expected']
    download_current_quality = p['download_current_quality']
    force = p['force']
    manually_searched = p['manually_searched']
    search_type = p.get('search_type', DAILY_SEARCH)

    # When
    replace, msg = Quality.should_replace(ep_status, cur_quality, new_quality, allowed_qualities, preferred_qualities,
                                          download_current_quality, force, manually_searched, search_type)
    actual = replace

    # Then
    if expected != actual:
        print(msg)
    assert expected == actual
