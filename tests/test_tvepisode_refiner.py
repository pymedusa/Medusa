# coding=utf-8
"""Tests for medusa.refiners.tv_episode.py."""

from medusa.common import DOWNLOADED, Quality
from medusa.refiners import tv_episode as sut
import pytest
from subliminal.video import Video


@pytest.fixture
def data(create_tvshow, create_tvepisode):
    show_name = 'Enhanced Show Name'
    show_year = 2012
    tvshow = create_tvshow(indexerid=12, name='{0} ({1})'.format(show_name, show_year), imdbid='tt0000000')
    tvepisode = create_tvepisode(show=tvshow, indexer=34, season=3, episode=4, name='Episode Title',
                                 file_size=1122334455, status=Quality.composite_status(DOWNLOADED, Quality.FULLHDBLURAY),
                                 release_group='SuperGroup')
    return {
        'tvshow': tvshow,
        'tvshow_properties': {
            'series': show_name,
            'year': show_year,
            'series_tvdb_id': tvshow.tvdb_id,
            'series_imdb_id': tvshow.imdbid,
        },
        'tvepisode': tvepisode,
        'tvepisode_properties': {
            'season': tvepisode.season,
            'episode': tvepisode.episode,
            'title': tvepisode.name,
            'resolution': '1080p',
            'format': 'BluRay',
            'release_group': tvepisode.release_group,
            'size': tvepisode.file_size,
            'tvdb_id': tvepisode.tvdb_id,
        },
        'video': Video.fromname('Show.Name.S01E02.mkv'),
        'video_properties': {
            'series': 'Show Name',
            'season': 1,
            'episode': 2,
            'title': None,
            'year': None,
            'resolution': None,
            'format': None,
            'release_group': None,
            'size': None,
            'series_tvdb_id': None,
            'series_imdb_id': None,
            'tvdb_id': None,
        }
    }


def _to_properties(video):
    return {
        'series': video.series,
        'season': video.season,
        'episode': video.episode,
        'title': video.title,
        'year': video.year,
        'resolution': video.resolution,
        'format': video.format,
        'size': video.size,
        'release_group': video.release_group,
        'series_tvdb_id': video.series_tvdb_id,
        'series_imdb_id': video.series_imdb_id,
        'tvdb_id': video.tvdb_id,
    }


def test_refine__only_video(data):
    # Given
    video = data['video']
    expected = data['video_properties']

    # When
    sut.refine(video)

    # Then
    assert expected == _to_properties(video)


def test_refine__with_tvepisode(data):
    # Given
    video = data['video']
    tvepisode = data['tvepisode']
    expected = dict(data['tvshow_properties'], **data['tvepisode_properties'])
    expected.update({'season': video.season, 'episode': video.episode})

    # When
    sut.refine(video, tv_episode=tvepisode)

    # Then
    assert expected == _to_properties(video)


def test_refine__video_with_ids_skipping_tvepisode_info(data):
    # Given
    video = data['video']
    video.series_tvdb_id = 99
    video.tvdb_id = 88
    tvepisode = data['tvepisode']
    expected = dict(data['video_properties'], series_tvdb_id=video.series_tvdb_id, tvdb_id=video.tvdb_id)

    # When
    sut.refine(video, tv_episode=tvepisode)

    # Then
    assert expected == _to_properties(video)


def test_refine__with_tvepisode_not_overwriting_resolution_format_and_release_group(data):
    # Given
    video = data['video']
    video.resolution = '720p'
    video.format = 'HDTV'
    video.release_group = 'AnotherGroup'
    tvepisode = data['tvepisode']
    expected = dict(data['tvshow_properties'], **data['tvepisode_properties'])
    expected = dict(expected, resolution=video.resolution, format=video.format, release_group=video.release_group,
                    season=video.season, episode=video.episode)

    # When
    sut.refine(video, tv_episode=tvepisode)

    # Then
    assert expected == _to_properties(video)
