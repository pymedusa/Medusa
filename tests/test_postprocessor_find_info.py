# coding=utf-8
"""Tests for medusa/test_should_process.py."""
from medusa.common import Quality
from medusa.name_parser.parser import NameParser
from medusa.post_processor import PostProcessor

import pytest


class TestPP(PostProcessor):
    """Test PP class."""

    def __init__(self, file_path, nzb_name):
        """Initialize the object."""
        super(TestPP, self).__init__(file_path, nzb_name)

    def _analyze_name(self, name):
        """Override original name to only parse release name and not match show database."""
        to_return = (None, None, [], None, None)

        if not name:
            return to_return

        #  This was changed from original method and removed Try/Expect
        parse_result = NameParser()._parse_string(name)

        if parse_result.show and all([parse_result.show.air_by_date, parse_result.is_air_by_date]):
            season = -1
            episodes = [parse_result.air_date]
        else:
            season = parse_result.season_number
            episodes = parse_result.episode_numbers

        #  Change show to series_name
        to_return = (parse_result.series_name, season, episodes, parse_result.quality, parse_result.version)

        self._finalize(parse_result)
        return to_return


@pytest.mark.parametrize('p', [
    {  # Test file in PP folder root
        'pp_obj': TestPP(file_path='/media/postprocess/Arrow.S01E01.1080p.HDTV.X264-DIMENSION.mkv',
                         nzb_name=None,
                         ),
        'series_name': 'Arrow',
        'season': 1,
        'episodes': [1],
        'quality': Quality.FULLHDTV,
        'version': -1
    },
    {  # Test NZB Season pack
        'pp_obj': TestPP(file_path='/media/postprocess/Game.of.Thrones.S02.Season.2.1080p.BluRay.x264-PublicHD/'
                                   'game.of.thrones.s02e10.1080p.bluray.x264-rovers.mkv',
                         nzb_name='Game.of.Thrones.S02.Season.2.1080p.BluRay.x264-PublicHD',
                         ),
        'series_name': 'game of thrones',
        'season': 2,
        'episodes': [10],
        'quality': Quality.FULLHDBLURAY,
        'version': -1
    },
    {  # Test NZB single episode
        'pp_obj': TestPP(file_path='/media/postprocess/Gotham.S03E13.1080p.HDTV.X264-DIMENSION/'
                                   'Gotham.S03E13.1080p.HDTV.X264-DIMENSION.mkv',
                         nzb_name='Gotham.S03E13.1080p.HDTV.X264-DIMENSION',
                         ),
        'series_name': 'Gotham',
        'season': 3,
        'episodes': [13],
        'quality': Quality.FULLHDTV,
        'version': -1
    },
    {  # Test NZB single episode but random char name
        'pp_obj': TestPP(file_path='/media/postprocess/Bones.S12E02.The.Brain.In.The.Bot.1080p.WEB-DL.DD5.1.H.264-R2D2/'
                         '161219_06.mkv',
                         nzb_name='Bones.S12E02.The.Brain.In.The.Bot.1080p.WEB-DL.DD5.1.H.264-R2D2',
                         ),
        'series_name': 'Bones',
        'season': 12,
        'episodes': [2],
        'quality': Quality.FULLHDWEBDL,
        'version': -1
    },
    {  # Test NZB multi episode
        'pp_obj': TestPP(file_path='/media/postprocess/Under.the.Dome.S03E01E02.HDTV.x264-LOL/'
                                   'Under.the.Dome.S03E01E02.HDTV.x264-LOL.mkv',
                         nzb_name='Under.the.Dome.S03E01E02.HDTV.x264-LOL',
                         ),
        'series_name': 'Under the Dome',
        'season': 3,
        'episodes': [1, 2],
        'quality': Quality.SDTV,
        'version': -1
    },
])
def test_should_process(p):
    """Run the test."""
    # Given
    pp_obj = p['pp_obj']
    expected_series_name = p['series_name']
    expected_season = p['season']
    expected_episodes = p['episodes']
    expected_quality = p['quality']
    expected_version = p['version']

    # When
    (series_name, season, episodes, quality, version) = PostProcessor._find_info(pp_obj)

    # Then
    assert series_name == expected_series_name
    assert season == expected_season
    assert episodes == expected_episodes
    assert quality == expected_quality
    assert version == expected_version
