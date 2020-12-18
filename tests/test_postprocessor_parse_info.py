# coding=utf-8
"""Tests for medusa/post_processor.py."""
from __future__ import unicode_literals
from medusa.common import Quality
from medusa.name_parser.parser import NameParser
from medusa.post_processor import PostProcessor

import pytest


@pytest.mark.parametrize('p', [
    {  # Test file in PP folder root
        'file_path': '/media/postprocess/Show.Name.S01E01.1080p.HDTV.X264-DIMENSION.mkv',
        'nzb_name': None,
        'expected': {
            'show': 'Show Name',
            'season': 1,
            'episodes': [1],
            'quality': Quality.FULLHDTV,
            'version': -1
        }
    },
    {  # Test NZB Season pack
        'file_path': '/media/postprocess/Show.Name.S02.Season.2.1080p.BluRay.x264-PublicHD/show.name.s02e10.1080p.bluray.x264-rovers.mkv',
        'nzb_name': 'Show.Name.S02.Season.2.1080p.BluRay.x264-PublicHD',
        'expected': {
            'show': 'show name',
            'season': 2,
            'episodes': [10],
            'quality': Quality.FULLHDBLURAY,
            'version': -1
        }
    },
    {  # Test NZB single episode
        'file_path': '/media/postprocess/Show.Name.S03E13.1080p.HDTV.X264-DIMENSION/Show.Name.S03E13.1080p.HDTV.X264-DIMENSION.mkv',
        'nzb_name': 'Show.Name.S03E13.1080p.HDTV.X264-DIMENSION',
        'expected': {
            'show': 'Show Name',
            'season': 3,
            'episodes': [13],
            'quality': Quality.FULLHDTV,
            'version': -1
        }
    },
    {  # Test NZB single episode but random char name
        'file_path': '/media/postprocess/Show.Name.S12E02.The.Brain.In.The.Bot.1080p.WEB-DL.DD5.1.H.264-R2D2/161219_06.mkv',
        'nzb_name': 'Show.Name.S12E02.The.Brain.In.The.Bot.1080p.WEB-DL.DD5.1.H.264-R2D2',
        'expected': {
            'show': 'Show Name',
            'season': 12,
            'episodes': [2],
            'quality': Quality.FULLHDWEBDL,
            'version': -1
        }
    },
    {  # Test NZB multi episode
        'file_path': '/media/postprocess/Show.Name.S03E01E02.HDTV.x264-LOL/Show.Name.S03E01E02.HDTV.x264-LOL.mkv',
        'nzb_name': 'Show.Name.S03E01E02.HDTV.x264-LOL',
        'expected': {
            'show': 'Show Name',
            'season': 3,
            'episodes': [1, 2],
            'quality': Quality.SDTV,
            'version': -1
        }
    },
    {  # Quality from parent folder with source
        'file_path': 'tvs-americansDETE507/The.Americans.2013.S05E07.Hoehere.Ziele.German.DD+51.WEBDL.1080p.NetflixHD.AVC-TVS/tvs-the-americans-2013-dd51-dl-18p-nfhd-avc-507.mkv',
        'nzb_name': 'tvs-the-americans-2013-dd51-dl-18p-nfhd-avc-507.mkv',
        'expected': {
            'show': 'The Americans 2013',
            'season': 5,
            'episodes': [7],
            'quality': Quality.FULLHDWEBDL,
            'version': -1
        }
    },
    {  # Quality from parent folder with origin
        'file_path': 'tvs-americansDETE507/The.Americans.2013.S05E07.Hoehere.Ziele.German.DD+51.DL.1080p.NetflixHD.AVC-TVS/tvs-the-americans-2013-dd51-dl-18p-nfhd-avc-507.mkv',
        'nzb_name': 'tvs-the-americans-2013-dd51-dl-18p-nfhd-avc-507.mkv',
        'expected': {
            'show': 'The Americans 2013',
            'season': 5,
            'episodes': [7],
            'quality': Quality.FULLHDWEBDL,
            'version': -1
        }
    },
    {  # Quality from parent folder without source/origin
        'file_path': 'tvs-americansDETE507/The.Americans.2013.S05E07.Hoehere.Ziele.German.DD+51.DL.1080p.AVC-TVS/tvs-the-americans-2013-dd51-dl-18p-nfhd-avc-507.mkv',
        'nzb_name': 'tvs-the-americans-2013-dd51-dl-18p-nfhd-avc-507.mkv',
        'expected': {
            'show': 'The Americans 2013',
            'season': 5,
            'episodes': [7],
            'quality': Quality.FULLHDTV,
            'version': -1
        }
    }
])
def test_parse_info(p, monkeypatch, parse_method):
    """Run the test."""
    # Given
    monkeypatch.setattr(NameParser, 'parse', parse_method)
    sut = PostProcessor(file_path=p['file_path'], nzb_name=p['nzb_name'])

    # When
    show, season, episodes, quality, version, airdate = sut._parse_info()

    # Then
    assert show is not None
    assert p['expected'] == {
        'show': show.name,
        'season': season,
        'episodes': episodes,
        'quality': quality,
        'version': version,
    }
