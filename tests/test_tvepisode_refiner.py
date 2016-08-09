# coding=utf-8
"""Tests for sickbeard.refiners.tvepisode.py."""

import pytest

from sickbeard.common import DOWNLOADED, Quality
from sickbeard.indexers.indexer_config import INDEXER_TVDB
from sickbeard.refiners import tvepisode as sut
from sickbeard.tv import TVEpisode, TVShow
from subliminal.video import Video


@pytest.fixture
def data(monkeypatch):
    monkeypatch.setattr('sickbeard.tv.TVShow._load_from_db', lambda method: None)
    monkeypatch.setattr('sickbeard.tv.TVEpisode._specify_episode', lambda method, season, episode: None)

    show_name = 'Enhanced Show Name'
    show_year = 2012

    tvshow = TVShow(indexer=INDEXER_TVDB, indexerid=12, quality=Quality.UNKNOWN, flatten_folders=0, enabled_subtitles=0)
    tvshow.name = '{name} ({year})'.format(name=show_name, year=show_year)
    tvshow.imdbid = 'tt0000000'

    tvepisode = TVEpisode(show=tvshow, season=3, episode=4)
    tvepisode.indexer = 34
    tvepisode.file_size = 1122334455
    tvepisode.name = 'Episode Title'
    tvepisode.status = Quality.compositeStatus(DOWNLOADED, Quality.FULLHDBLURAY)
    tvepisode.release_group = 'SuperGroup'

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
    expected = dict(expected, resolution=video.resolution, format=video.format, release_group=video.release_group)

    # When
    sut.refine(video, tv_episode=tvepisode)

    # Then
    assert expected == _to_properties(video)
