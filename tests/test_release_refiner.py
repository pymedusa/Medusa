# coding=utf-8
"""Tests for medusa.refiners.release.py."""

import os

from medusa.refiners import release as sut
import pytest
from subliminal.video import Video


@pytest.fixture
def data():
    return {
        'release_name': 'Show.Name.2012.S01E02.Episode.Title.1080p.HDTV.x265.AC3-Group',
        'release_properties': {
            'series': 'Show Name',
            'season': 1,
            'episode': 2,
            'title': 'Episode Title',
            'year': 2012,
            'format': 'HDTV',
            'resolution': '1080p',
            'release_group': 'Group',
            'video_codec': 'H.265',
            'audio_codec': 'Dolby Digital'
        },
        'another_release_name': 'Different.Show.2013.S03E04.Another.Episode.720p.BluRay.x264-NoGroup',
        'video': Video.fromname('Show.Name.S01E02.mkv'),
        'video_properties': {
            'series': 'Show Name',
            'season': 1,
            'episode': 2,
            'title': None,
            'year': None,
            'format': None,
            'resolution': None,
            'release_group': None,
            'video_codec': None,
            'audio_codec': None,
        }
    }


def _to_properties(video):
    return {
        'series': video.series,
        'season': video.season,
        'episode': video.episode,
        'title': video.title,
        'year': video.year,
        'format': video.format,
        'resolution': video.resolution,
        'release_group': video.release_group,
        'video_codec': video.video_codec,
        'audio_codec': video.audio_codec,
    }


def test_refine__only_video(data):
    # Given
    video = data['video']
    expected = data['video_properties']

    # When
    sut.refine(video)

    # Then
    assert expected == _to_properties(video)


def test_refine__with_release_name(data):
    # Given
    video = data['video']
    release_name = data['release_name']
    expected = data['release_properties']

    # When
    sut.refine(video, release_name=release_name)

    # Then
    assert expected == _to_properties(video)


def test_refine__with_release_file(data, tmpdir):
    # Given
    video = data['video']
    release_name = data['release_name']
    release_file = tmpdir.ensure('somefile.ext')
    release_file.write(release_name)
    expected = data['release_properties']

    # When
    sut.refine(video, release_file=release_file.strpath)

    # Then
    assert expected == _to_properties(video)


def test_refine__with_release_file_with_no_content(data, tmpdir):
    # Given
    video = data['video']
    release_file = tmpdir.ensure('somefile.ext')
    expected = data['video_properties']

    # When
    sut.refine(video, release_file=release_file.strpath)

    # Then
    assert expected == _to_properties(video)


def test_refine__with_non_existent_release_file(data):
    # Given
    video = data['video']
    release_file = 'somefile.ext'
    expected = data['video_properties']

    # When
    sut.refine(video, release_file=release_file)

    # Then
    assert expected == _to_properties(video)


def test_refine__with_release_extension(data, tmpdir):
    # Given
    video = data['video']
    release_name = data['release_name']
    name, ext = os.path.splitext(os.path.basename(video.name))
    video.name = '{path}/{name}{ext}'.format(path=tmpdir.strpath, name=name, ext=ext)
    release_file = tmpdir.ensure('{name}.ext'.format(name=name))
    release_file.write(release_name)
    release_file = tmpdir.ensure('{name}.ttt'.format(name=name))
    release_file.write(data['another_release_name'])
    expected = data['release_properties']

    # When
    sut.refine(video, extension='ext')

    # Then
    assert expected == _to_properties(video)


def test_refine__precedence_with_release_file_and_release_name(data, tmpdir):
    # Given
    video = data['video']
    release_name = data['release_name']
    another_release_name = data['another_release_name']
    release_file = tmpdir.ensure('somefile.ext')
    release_file.write(release_name)
    expected = data['release_properties']

    # When
    sut.refine(video, release_name=another_release_name, release_file=release_file.strpath)

    # Then
    assert expected == _to_properties(video)


def test_refine__precedence_with_default_release_extension_and_release_name(data, tmpdir):
    # Given
    video = data['video']
    name, ext = os.path.splitext(os.path.basename(video.name))
    video.name = '{path}/{name}{ext}'.format(path=tmpdir.strpath, name=name, ext=ext)
    release_name = data['release_name']
    another_release_name = data['another_release_name']
    release_file = tmpdir.ensure('{name}.release'.format(name=name))
    release_file.write(release_name)
    expected = data['release_properties']

    # When
    sut.refine(video, release_name=another_release_name)

    # Then
    assert expected == _to_properties(video)
