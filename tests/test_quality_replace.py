# coding=utf-8
"""Tests for medusa/test_quality_replace.py."""
from medusa.common import ARCHIVED, DOWNLOADED, Quality, SKIPPED, SNATCHED, SNATCHED_PROPER, WANTED

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
        'expected': False
    },
    {  # p18: Downloaded Unknown found 720p HDBLURAY: no
        'ep_status': DOWNLOADED,
        'cur_quality': Quality.UNKNOWN,
        'new_quality': Quality.HDBLURAY,
        'allowed_qualities': [Quality.HDTV, Quality.HDBLURAY],
        'preferred_qualities': [],
        'download_current_quality': False,
        'force': False,
        'expected': False
    },
    {  # p19: Downloaded SDTV (not in quality system) and found 720p HDTV: yes
        'ep_status': DOWNLOADED,
        'cur_quality': Quality.SDTV,
        'new_quality': Quality.HDTV,
        'allowed_qualities': [Quality.HDTV],
        'preferred_qualities': [],
        'download_current_quality': False,
        'force': False,
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
        'expected': False
    },
    {  # p24: Downloaded SDTV and found SDTV. Not wanted anymore. Force search: yes
        'ep_status': DOWNLOADED,
        'cur_quality': Quality.SDTV,
        'new_quality': Quality.SDTV,
        'allowed_qualities': [Quality.HDTV],
        'preferred_qualities': [],
        'download_current_quality': False,
        'force': True,
        'expected': True
    },
    {  # p25: Downloaded SDTV and found SDTV. Not wanted anymore: no
        'ep_status': DOWNLOADED,
        'cur_quality': Quality.SDTV,
        'new_quality': Quality.SDTV,
        'allowed_qualities': [Quality.HDTV],
        'preferred_qualities': [],
        'download_current_quality': False,
        'force': False,
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
        'expected': False
    },
    {  # p30: DOWNLOADED and found 1080p HDBLURAY (not in wanted qualities). Force search yes: yes
        'ep_status': DOWNLOADED,
        'cur_quality': Quality.HDTV,
        'new_quality': Quality.HDBLURAY,
        'allowed_qualities': [Quality.HDTV],
        'preferred_qualities': [],
        'download_current_quality': False,
        'force': True,
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
    download_current_quality = p['download_current_quality']
    force = p['force']

    # When
    replace, msg = Quality.should_replace(ep_status, cur_quality, new_quality, allowed_qualities, preferred_qualities,
                                          download_current_quality, force)
    actual = replace

    # Then
    if expected != actual:
        print msg
    assert expected == actual
