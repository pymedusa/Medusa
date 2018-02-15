# coding=utf-8
"""Tests for medusa/test_should_search.py."""
import pytest

from medusa.common import (
    ARCHIVED, DOWNLOADED, IGNORED, Quality, SKIPPED,
    SNATCHED, SNATCHED_BEST, SNATCHED_PROPER, WANTED,
)
from medusa.tv import Series


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
        'status': Quality.composite_status(DOWNLOADED, Quality.SDTV),
        'show_obj': TestTVShow(indexer=1, indexer_id=1, lang='',
                               quality=Quality.combine_qualities([Quality.HDTV],  # Allowed Qualities
                                                                 [Quality.HDWEBDL])),  # Preferred Qualities
        'manually_searched': False,
        'expected': True
    },
    {  # p1: Current status is SKIPPED: no
        'status': Quality.composite_status(SKIPPED, None),
        'show_obj': TestTVShow(indexer=1, indexer_id=1, lang='',
                               quality=Quality.combine_qualities([Quality.HDTV],  # Allowed Qualities
                                                                 [Quality.HDWEBDL])),  # Preferred Qualities
        'manually_searched': False,
        'expected': False
    },
    {  # p2: Current status is IGNORED: no
        'status': Quality.composite_status(IGNORED, None),
        'show_obj': TestTVShow(indexer=1, indexer_id=1, lang='',
                               quality=Quality.combine_qualities([Quality.HDTV],  # Allowed Qualities
                                                                 [Quality.HDWEBDL])),  # Preferred Qualities
        'manually_searched': False,
        'expected': False
    },
    {  # p3: Current status is SNATCHED_BEST: no
        'status': Quality.composite_status(SNATCHED_BEST, Quality.HDWEBDL),
        'show_obj': TestTVShow(indexer=1, indexer_id=1, lang='',
                               quality=Quality.combine_qualities([Quality.HDTV],  # Allowed Qualities
                                                                 [Quality.HDWEBDL])),  # Preferred Qualities
        'manually_searched': False,
        'expected': False
    },
    {  # p4: Current status is SNATCHED: yes
        'status': Quality.composite_status(SNATCHED, Quality.HDTV),
        'show_obj': TestTVShow(indexer=1, indexer_id=1, lang='',
                               quality=Quality.combine_qualities([Quality.HDTV],  # Allowed Qualities
                                                                 [Quality.HDWEBDL])),  # Preferred Qualities
        'manually_searched': False,
        'expected': True
    },
    {  # p5: Current status is SNATCHED_PROPER: yes
        'status': Quality.composite_status(SNATCHED_PROPER, Quality.HDTV),
        'show_obj': TestTVShow(indexer=1, indexer_id=1, lang='',
                               quality=Quality.combine_qualities([Quality.HDTV],  # Allowed Qualities
                                                                 [Quality.HDWEBDL])),  # Preferred Qualities
        'manually_searched': False,
        'expected': True
    },
    {  # p6: Status is DOWNLOADED: yes
        'status': Quality.composite_status(DOWNLOADED, Quality.HDTV),
        'show_obj': TestTVShow(indexer=1, indexer_id=1, lang='',
                               quality=Quality.combine_qualities([Quality.HDTV, Quality.HDWEBDL],  # Allowed Qualities
                                                                 [Quality.HDBLURAY])),  # Preferred Qualities
        'manually_searched': False,
        'expected': True
    },
    {  # p7: Status is ARCHIVED: no
        'status': Quality.composite_status(ARCHIVED, Quality.HDTV),
        'show_obj': TestTVShow(indexer=1, indexer_id=1, lang='',
                               quality=Quality.combine_qualities([Quality.HDTV, Quality.HDWEBDL],  # Allowed Qualities
                                                                 [Quality.HDBLURAY])),  # Preferred Qualities
        'manually_searched': False,
        'expected': False
    },
    {  # p8: Status WANTED: yes
        'status': Quality.composite_status(WANTED, None),
        'show_obj': TestTVShow(indexer=1, indexer_id=1, lang='',
                               quality=Quality.combine_qualities([Quality.HDWEBDL],  # Allowed Qualities
                                                                 [Quality.HDBLURAY])),  # Preferred Qualities
        'manually_searched': False,
        'expected': True
    },
    {  # p9: Episode was manually searched by user: no
        'status': Quality.composite_status(DOWNLOADED, Quality.HDBLURAY),
        'show_obj': TestTVShow(indexer=1, indexer_id=1, lang='',
                               quality=Quality.combine_qualities([Quality.HDTV],  # Allowed Qualities
                                                                 [Quality.HDWEBDL])),  # Preferred Qualities
        'manually_searched': True,
        'expected': False
    },
    {  # p10: Downloaded an Allowed quality. Preferred not set: no
        'status': Quality.composite_status(DOWNLOADED, Quality.HDTV),
        'show_obj': TestTVShow(indexer=1, indexer_id=1, lang='',
                               quality=Quality.combine_qualities([Quality.HDTV],  # Allowed Qualities
                                                                 [])),  # Preferred Qualities
        'manually_searched': False,
        'expected': False
    },
    {  # p11: Downloaded an Allowed quality but Preferred set: yes
        'status': Quality.composite_status(DOWNLOADED, Quality.HDTV),
        'show_obj': TestTVShow(indexer=1, indexer_id=1, lang='',
                               quality=Quality.combine_qualities([Quality.HDTV],  # Allowed Qualities
                                                                 [Quality.HDWEBDL])),  # Preferred Qualities
        'manually_searched': False,
        'expected': True
    },
    {  # p12: Downloaded an Preferred quality. Allowed not set: no
        'status': Quality.composite_status(DOWNLOADED, Quality.HDTV),
        'show_obj': TestTVShow(indexer=1, indexer_id=1, lang='',
                               quality=Quality.combine_qualities([],  # Allowed Qualities
                                                                 [Quality.SDTV, Quality.HDTV])),  # Preferred Qualities
        'manually_searched': False,
        'expected': False
    },
    {  # p13: Already have Preferred quality: no
        'status': Quality.composite_status(SNATCHED, Quality.HDBLURAY),
        'show_obj': TestTVShow(indexer=1, indexer_id=1, lang='',
                               quality=Quality.combine_qualities([Quality.HDTV],  # Allowed Qualities
                                                                 [Quality.HDBLURAY])),  # Preferred Qualities
        'manually_searched': False,
        'expected': False
    },
    {  # p14: ´Downloaded UNKNOWN and its on Allowed. Preferred not set: no
        'status': Quality.composite_status(DOWNLOADED, Quality.UNKNOWN),
        'show_obj': TestTVShow(indexer=1, indexer_id=1, lang='',
                               quality=Quality.combine_qualities([Quality.UNKNOWN, Quality.HDTV],  # Allowed Qualities
                                                                 [])),  # Preferred Qualities
        'manually_searched': False,
        'expected': False
    },
    {  # p15: ´Downloaded UNKNOWN and its not on Allowed: yes
        'status': Quality.composite_status(DOWNLOADED, Quality.UNKNOWN),
        'show_obj': TestTVShow(indexer=1, indexer_id=1, lang='',
                               quality=Quality.combine_qualities([Quality.HDTV],  # Allowed Qualities
                                                                 [Quality.HDBLURAY])),  # Preferred Qualities
        'manually_searched': False,
        'expected': True
    },
    {  # p16: ´Downloaded NONE (invalid quality): yes
        'status': Quality.composite_status(DOWNLOADED, Quality.NONE),
        'show_obj': TestTVShow(indexer=1, indexer_id=1, lang='',
                               quality=Quality.combine_qualities([Quality.HDTV],  # Allowed Qualities
                                                                 [Quality.HDBLURAY])),  # Preferred Qualities
        'manually_searched': False,
        'expected': True
    },
    {  # p17: ´SNATCHED BEST but this quality is no longer wanted: yes
        'status': Quality.composite_status(SNATCHED_BEST, Quality.SDTV),
        'show_obj': TestTVShow(indexer=1, indexer_id=1, lang='',
                               quality=Quality.combine_qualities([Quality.HDTV],  # Allowed Qualities
                                                                 [Quality.HDBLURAY])),  # Preferred Qualities
        'manually_searched': False,
        'expected': True
    },
    {  # p18: ´SNATCHED BEST but this quality is no longer in preferred but in allowed. Preferred set: yes
        'status': Quality.composite_status(SNATCHED_BEST, Quality.SDTV),
        'show_obj': TestTVShow(indexer=1, indexer_id=1, lang='',
                               quality=Quality.combine_qualities([Quality.HDTV, Quality.SDTV],  # Allowed Qualities
                                                                 [Quality.HDBLURAY])),  # Preferred Qualities
        'manually_searched': False,
        'expected': True
    },
    {  # p19: ´SNATCHED BEST but this quality is no longer in preferred but in allowed. Preferred not set: no
        'status': Quality.composite_status(SNATCHED_BEST, Quality.SDTV),
        'show_obj': TestTVShow(indexer=1, indexer_id=1, lang='',
                               quality=Quality.combine_qualities([Quality.HDTV, Quality.SDTV],  # Allowed Qualities
                                                                 [])),  # Preferred Qualities
        'manually_searched': False,
        'expected': False
    },
    {  # p20: ´SNATCHED BEST but this quality is no longer wanted. Preferred not set: yes
        'status': Quality.composite_status(SNATCHED_BEST, Quality.SDTV),
        'show_obj': TestTVShow(indexer=1, indexer_id=1, lang='',
                               quality=Quality.combine_qualities([Quality.HDTV],  # Allowed Qualities
                                                                 [])),  # Preferred Qualities
        'manually_searched': False,
        'expected': True
    },
])
def test_should_search(p):
    """Run the test."""
    # Given
    status = p['status']
    show_obj = p['show_obj']
    manually_searched = p['manually_searched']
    expected = p['expected']

    # When
    replace, msg = Quality.should_search(status, show_obj, manually_searched)
    actual = replace

    # Then
    if expected != actual:
        print msg
    assert expected == actual
