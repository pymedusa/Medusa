# coding=utf-8
"""Tests for medusa/test_should_search.py."""
from __future__ import unicode_literals
from medusa.common import (ARCHIVED, DOWNLOADED, IGNORED, Quality, SKIPPED,
                           SNATCHED, SNATCHED_BEST, SNATCHED_PROPER, WANTED)
from medusa.tv import Series

import pytest


class TestTVShow(Series):
    """A test `Series` object that does not need DB access."""

    def __init__(self, indexer, indexer_id, lang, quality):
        """Initialize the object."""
        super(TestTVShow, self).__init__(indexer, indexer_id, lang, quality)

    def _load_from_db(self):
        """Override Series._load_from_db to avoid DB access during testing."""
        pass


@pytest.mark.parametrize('p', [
    {  # p0: Downloaded a quality not in quality system : yes
        'status': DOWNLOADED,
        'quality': Quality.SDTV,
        'show_obj': TestTVShow(indexer=1, indexer_id=1, lang='',
                               quality=Quality.combine_qualities([Quality.HDTV],  # Allowed Qualities
                                                                 [Quality.HDWEBDL])),  # Preferred Qualities
        'manually_searched': False,
        'expected': True
    },
    {  # p1: Current status is SKIPPED: no
        'status': SKIPPED,
        'quality': Quality.NA,
        'show_obj': TestTVShow(indexer=1, indexer_id=1, lang='',
                               quality=Quality.combine_qualities([Quality.HDTV],  # Allowed Qualities
                                                                 [Quality.HDWEBDL])),  # Preferred Qualities
        'manually_searched': False,
        'expected': False
    },
    {  # p2: Current status is IGNORED: no
        'status': IGNORED,
        'quality': Quality.NA,
        'show_obj': TestTVShow(indexer=1, indexer_id=1, lang='',
                               quality=Quality.combine_qualities([Quality.HDTV],  # Allowed Qualities
                                                                 [Quality.HDWEBDL])),  # Preferred Qualities
        'manually_searched': False,
        'expected': False
    },
    {  # p3: Current status is SNATCHED_BEST: no
        'status': SNATCHED_BEST,
        'quality': Quality.HDWEBDL,
        'show_obj': TestTVShow(indexer=1, indexer_id=1, lang='',
                               quality=Quality.combine_qualities([Quality.HDTV],  # Allowed Qualities
                                                                 [Quality.HDWEBDL])),  # Preferred Qualities
        'manually_searched': False,
        'expected': False
    },
    {  # p4: Current status is SNATCHED: yes
        'status': SNATCHED,
        'quality': Quality.HDTV,
        'show_obj': TestTVShow(indexer=1, indexer_id=1, lang='',
                               quality=Quality.combine_qualities([Quality.HDTV],  # Allowed Qualities
                                                                 [Quality.HDWEBDL])),  # Preferred Qualities
        'manually_searched': False,
        'expected': True
    },
    {  # p5: Current status is SNATCHED_PROPER: yes
        'status': SNATCHED_PROPER,
        'quality': Quality.HDTV,
        'show_obj': TestTVShow(indexer=1, indexer_id=1, lang='',
                               quality=Quality.combine_qualities([Quality.HDTV],  # Allowed Qualities
                                                                 [Quality.HDWEBDL])),  # Preferred Qualities
        'manually_searched': False,
        'expected': True
    },
    {  # p6: Status is DOWNLOADED: yes
        'status': DOWNLOADED,
        'quality': Quality.HDTV,
        'show_obj': TestTVShow(indexer=1, indexer_id=1, lang='',
                               quality=Quality.combine_qualities([Quality.HDTV, Quality.HDWEBDL],  # Allowed Qualities
                                                                 [Quality.HDBLURAY])),  # Preferred Qualities
        'manually_searched': False,
        'expected': True
    },
    {  # p7: Status is ARCHIVED: no
        'status': ARCHIVED,
        'quality': Quality.HDTV,
        'show_obj': TestTVShow(indexer=1, indexer_id=1, lang='',
                               quality=Quality.combine_qualities([Quality.HDTV, Quality.HDWEBDL],  # Allowed Qualities
                                                                 [Quality.HDBLURAY])),  # Preferred Qualities
        'manually_searched': False,
        'expected': False
    },
    {  # p8: Status WANTED: yes
        'status': WANTED,
        'quality': Quality.NA,
        'show_obj': TestTVShow(indexer=1, indexer_id=1, lang='',
                               quality=Quality.combine_qualities([Quality.HDWEBDL],  # Allowed Qualities
                                                                 [Quality.HDBLURAY])),  # Preferred Qualities
        'manually_searched': False,
        'expected': True
    },
    {  # p9: Episode was manually searched by user: no
        'status': DOWNLOADED,
        'quality': Quality.HDBLURAY,
        'show_obj': TestTVShow(indexer=1, indexer_id=1, lang='',
                               quality=Quality.combine_qualities([Quality.HDTV],  # Allowed Qualities
                                                                 [Quality.HDWEBDL])),  # Preferred Qualities
        'manually_searched': True,
        'expected': False
    },
    {  # p10: Downloaded an Allowed quality. Preferred not set: no
        'status': DOWNLOADED,
        'quality': Quality.HDTV,
        'show_obj': TestTVShow(indexer=1, indexer_id=1, lang='',
                               quality=Quality.combine_qualities([Quality.HDTV],  # Allowed Qualities
                                                                 [])),  # Preferred Qualities
        'manually_searched': False,
        'expected': False
    },
    {  # p11: Downloaded an Allowed quality but Preferred set: yes
        'status': DOWNLOADED,
        'quality': Quality.HDTV,
        'show_obj': TestTVShow(indexer=1, indexer_id=1, lang='',
                               quality=Quality.combine_qualities([Quality.HDTV],  # Allowed Qualities
                                                                 [Quality.HDWEBDL])),  # Preferred Qualities
        'manually_searched': False,
        'expected': True
    },
    {  # p12: Downloaded an Preferred quality. Allowed not set: no
        'status': DOWNLOADED,
        'quality': Quality.HDTV,
        'show_obj': TestTVShow(indexer=1, indexer_id=1, lang='',
                               quality=Quality.combine_qualities([],  # Allowed Qualities
                                                                 [Quality.SDTV, Quality.HDTV])),  # Preferred Qualities
        'manually_searched': False,
        'expected': False
    },
    {  # p13: Already have Preferred quality: no
        'status': SNATCHED,
        'quality': Quality.HDBLURAY,
        'show_obj': TestTVShow(indexer=1, indexer_id=1, lang='',
                               quality=Quality.combine_qualities([Quality.HDTV],  # Allowed Qualities
                                                                 [Quality.HDBLURAY])),  # Preferred Qualities
        'manually_searched': False,
        'expected': False
    },
    {  # p14: ´Downloaded UNKNOWN and its on Allowed. Preferred not set: no
        'status': DOWNLOADED,
        'quality': Quality.UNKNOWN,
        'show_obj': TestTVShow(indexer=1, indexer_id=1, lang='',
                               quality=Quality.combine_qualities([Quality.UNKNOWN, Quality.HDTV],  # Allowed Qualities
                                                                 [])),  # Preferred Qualities
        'manually_searched': False,
        'expected': False
    },
    {  # p15: ´Downloaded UNKNOWN and its not on Allowed: yes
        'status': DOWNLOADED,
        'quality': Quality.UNKNOWN,
        'show_obj': TestTVShow(indexer=1, indexer_id=1, lang='',
                               quality=Quality.combine_qualities([Quality.HDTV],  # Allowed Qualities
                                                                 [Quality.HDBLURAY])),  # Preferred Qualities
        'manually_searched': False,
        'expected': True
    },
    {  # p16: ´Downloaded NA (initial quality): yes
        'status': DOWNLOADED,
        'quality': Quality.NA,
        'show_obj': TestTVShow(indexer=1, indexer_id=1, lang='',
                               quality=Quality.combine_qualities([Quality.HDTV],  # Allowed Qualities
                                                                 [Quality.HDBLURAY])),  # Preferred Qualities
        'manually_searched': False,
        'expected': True
    },
    {  # p17: ´SNATCHED BEST but this quality is no longer wanted: yes
        'status': SNATCHED_BEST,
        'quality': Quality.SDTV,
        'show_obj': TestTVShow(indexer=1, indexer_id=1, lang='',
                               quality=Quality.combine_qualities([Quality.HDTV],  # Allowed Qualities
                                                                 [Quality.HDBLURAY])),  # Preferred Qualities
        'manually_searched': False,
        'expected': True
    },
    {  # p18: ´SNATCHED BEST but this quality is no longer in preferred but in allowed. Preferred set: yes
        'status': SNATCHED_BEST,
        'quality': Quality.SDTV,
        'show_obj': TestTVShow(indexer=1, indexer_id=1, lang='',
                               quality=Quality.combine_qualities([Quality.HDTV, Quality.SDTV],  # Allowed Qualities
                                                                 [Quality.HDBLURAY])),  # Preferred Qualities
        'manually_searched': False,
        'expected': True
    },
    {  # p19: ´SNATCHED BEST but this quality is no longer in preferred but in allowed. Preferred not set: no
        'status': SNATCHED_BEST,
        'quality': Quality.SDTV,
        'show_obj': TestTVShow(indexer=1, indexer_id=1, lang='',
                               quality=Quality.combine_qualities([Quality.HDTV, Quality.SDTV],  # Allowed Qualities
                                                                 [])),  # Preferred Qualities
        'manually_searched': False,
        'expected': False
    },
    {  # p20: ´SNATCHED BEST but this quality is no longer wanted. Preferred not set: yes
        'status': SNATCHED_BEST,
        'quality': Quality.SDTV,
        'show_obj': TestTVShow(indexer=1, indexer_id=1, lang='',
                               quality=Quality.combine_qualities([Quality.HDTV],  # Allowed Qualities
                                                                 [])),  # Preferred Qualities
        'manually_searched': False,
        'expected': True
    },
    {  # p21: Downloaded HDTV and it's in Allowed. Preferred is set (UNKNOWN): yes
        'status': DOWNLOADED,
        'quality': Quality.HDTV,
        'show_obj': TestTVShow(indexer=1, indexer_id=1, lang='',
                               quality=Quality.combine_qualities([Quality.HDTV],  # Allowed Qualities
                                                                 [Quality.UNKNOWN])),  # Preferred Qualities
        'manually_searched': False,
        'expected': True
    },
])
def test_should_search(p):
    """Run the test."""
    # Given
    status = p['status']
    quality = p['quality']
    show_obj = p['show_obj']
    manually_searched = p['manually_searched']
    expected = p['expected']

    # When
    replace, msg = Quality.should_search(status, quality, show_obj, manually_searched)
    actual = replace

    # Then
    if expected != actual:
        print(msg)
    assert expected == actual
