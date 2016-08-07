# coding=utf-8
"""Tests for sickbeard.subtitles.py."""
import os
import sys

from babelfish.language import Language
import sickbeard.subtitles as sut
from subliminal.subtitle import Subtitle


def test_sorted_service_list(monkeypatch):
    # Given
    monkeypatch.setattr('sickbeard.SUBTITLES_SERVICES_LIST', ['legendastv', 'trash', 'itasa', 'thesubdb', 'shooter'])
    monkeypatch.setattr('sickbeard.SUBTITLES_SERVICES_ENABLED', [1, 1, 0, 1, 0])

    # When
    actual = sut.sorted_service_list()

    # Then
    expected = [
        {'name': 'legendastv', 'enabled': True},
        {'name': 'itasa', 'enabled': False},
        {'name': 'thesubdb', 'enabled': True},
        {'name': 'shooter', 'enabled': False},
        {'name': 'addic7ed', 'enabled': False},
        {'name': 'napiprojekt', 'enabled': False},
        {'name': 'opensubtitles', 'enabled': False},
        {'name': 'podnapisi', 'enabled': False},
        {'name': 'subscenter', 'enabled': False},
        {'name': 'tvsubtitles', 'enabled': False},
    ]
    assert expected == [{'name': a['name'], 'enabled': a['enabled']} for a in actual]


def test_enabled_service_list(monkeypatch):
    # Given
    monkeypatch.setattr('sickbeard.SUBTITLES_SERVICES_LIST', ['legendastv', 'a', 'itasa', 'tvsubtitles', 'shooter'])
    monkeypatch.setattr('sickbeard.SUBTITLES_SERVICES_ENABLED', [1, 1, 0, 1, 0])

    # When
    actual = sut.enabled_service_list()

    # Then
    expected = ['legendastv', 'tvsubtitles']
    assert expected == actual


def test_wanted_languages__only_valid_3letter_codes(monkeypatch):
    # Given
    monkeypatch.setattr('sickbeard.SUBTITLES_LANGUAGES', ['pob', 'trash', 'eng', 'fre', 'abc', 'pt-BR'])

    # When
    actual = sut.wanted_languages()

    # Then
    assert {'pob', 'eng', 'fre'} == actual


def test_get_needed_languages__multi_enabled(monkeypatch):
    # Given
    monkeypatch.setattr('sickbeard.SUBTITLES_MULTI', True)
    monkeypatch.setattr('sickbeard.SUBTITLES_LANGUAGES', ['pob', 'trash', 'eng', 'fre', 'abc'])
    existing_subtitles = {'pob', 'eng'}

    # When
    actual = sut.get_needed_languages(existing_subtitles)

    # Then
    assert {Language.fromietf('fr')} == actual


def test_get_needed_languages__multi_disabled_and_und_present(monkeypatch):
    # Given
    monkeypatch.setattr('sickbeard.SUBTITLES_MULTI', False)
    monkeypatch.setattr('sickbeard.SUBTITLES_LANGUAGES', ['pob', 'trash', 'eng', 'fre', 'abc'])
    existing_subtitles = {'pob', 'eng', 'und'}

    # When
    actual = sut.get_needed_languages(existing_subtitles)

    # Then
    assert actual == set()

# TODO: Pending: what's expected? current behaviour?
# test_get_needed_languages__multi_disabled_and_und_not_present
# test_needs_subtitles__multi_disabled_and_und_present


def test_needs_subtitles__no_wanted_language(monkeypatch):
    # Given
    monkeypatch.setattr('sickbeard.SUBTITLES_LANGUAGES', [])
    existing_subtitles = {'pob', 'eng'}

    # When
    actual = sut.needs_subtitles(existing_subtitles)

    # Then
    assert actual is False


def test_needs_subtitles__multi_enabled(monkeypatch):
    # Given
    monkeypatch.setattr('sickbeard.SUBTITLES_MULTI', True)
    monkeypatch.setattr('sickbeard.SUBTITLES_LANGUAGES', ['pob', 'eng', 'fre'])
    existing_subtitles = {'pob', 'eng'}

    # When
    actual = sut.needs_subtitles(existing_subtitles)

    # Then
    assert actual is True


def test_needs_subtitles__multi_enabled_with_string(monkeypatch):
    # Given
    monkeypatch.setattr('sickbeard.SUBTITLES_MULTI', True)
    monkeypatch.setattr('sickbeard.SUBTITLES_LANGUAGES', ['pob', 'eng', 'fre'])
    existing_subtitles = 'pob,eng,fre'

    # When
    actual = sut.needs_subtitles(existing_subtitles)

    # Then
    assert actual is False


def test_needs_subtitles__multi_disabled_and_und_present(monkeypatch):
    # Given
    monkeypatch.setattr('sickbeard.SUBTITLES_MULTI', False)
    monkeypatch.setattr('sickbeard.SUBTITLES_LANGUAGES', ['pob', 'eng', 'fre'])
    existing_subtitles = {'pob', 'eng', 'und'}

    # When
    actual = sut.needs_subtitles(existing_subtitles)

    # Then
    assert actual is False


def test_from_code__valid_code():
    # Given
    code = 'pob'

    # When
    actual = sut.from_code(code)

    # Then
    assert Language.fromietf('pt-BR') == actual


def test_from_code__unknown_code():
    # Given
    code = 'trash'

    # When
    actual = sut.from_code(code)

    # Then
    assert Language('und') == actual


def test_from_code__unknown_code_returning_none():
    # Given
    code = 'trash'

    # When
    actual = sut.from_code(code, unknown=None)

    # Then
    assert actual is None


def test_from_ietf_code__valid_code():
    # Given
    code = 'pt-BR'

    # When
    actual = sut.from_ietf_code(code)

    # Then
    assert Language('por', 'BR') == actual


def test_from_ietf_code__unknown_code():
    # Given
    code = 'trash'

    # When
    actual = sut.from_ietf_code(code)

    # Then
    assert Language('und') == actual


def test_from_ietf_code__unknown_code_returning_none():
    # Given
    code = 'trash'

    # When
    actual = sut.from_ietf_code(code, unknown=None)

    # Then
    assert actual is None


def test_name_from_code__valid_code():
    # Given
    code = 'pob'

    # When
    actual = sut.name_from_code(code)

    # Then
    assert 'Portuguese' == actual


def test_name_from_code__unknown_code():
    # Given
    code = 'trash'

    # When
    actual = sut.name_from_code(code)

    # Then
    assert 'Undetermined' == actual


def test_code_from_code__valid_2letter_code():
    # Given
    code = 'en'

    # When
    actual = sut.code_from_code(code)

    # Then
    assert 'eng' == actual


def test_compute_subtitle_path__multi_with_valid_language(monkeypatch):
    # Given
    monkeypatch.setattr('sickbeard.SUBTITLES_MULTI', True)
    subtitle = Subtitle(language=Language('por', 'BR'))
    video_path = '/folder/subfolder/video.mkv'
    subtitles_dir = None

    # When
    actual = sut.compute_subtitle_path(subtitle, video_path, subtitles_dir)

    # Then
    assert '/folder/subfolder/video.pt-BR.srt' == actual


def test_compute_subtitle_path__multi_with_und_language(monkeypatch):
    # Given
    monkeypatch.setattr('sickbeard.SUBTITLES_MULTI', True)
    subtitle = Subtitle(language=Language('und'))
    video_path = '/folder/subfolder/video.mkv'
    subtitles_dir = None

    # When
    actual = sut.compute_subtitle_path(subtitle, video_path, subtitles_dir)

    # Then
    assert '/folder/subfolder/video.srt' == actual


def test_compute_subtitle_path__single_with_valid_language(monkeypatch):
    # Given
    monkeypatch.setattr('sickbeard.SUBTITLES_MULTI', False)
    subtitle = Subtitle(language=Language('por', 'BR'))
    video_path = '/folder/subfolder/video.mkv'
    subtitles_dir = None

    # When
    actual = sut.compute_subtitle_path(subtitle, video_path, subtitles_dir)

    # Then
    assert '/folder/subfolder/video.srt' == actual


def test_compute_subtitle_path__single_with_valid_language_and_subs_folder(monkeypatch):
    # Given
    monkeypatch.setattr('sickbeard.SUBTITLES_MULTI', False)
    subtitle = Subtitle(language=Language('por', 'BR'))
    video_path = '/folder/subfolder/video.mkv'
    subtitles_dir = '/folder/subtitles'

    # When
    actual = sut.compute_subtitle_path(subtitle, video_path, subtitles_dir)

    # Then
    assert '/folder/subtitles/video.srt' == actual


def test_merge_subtitles__with_multi_enabled(monkeypatch):
    # Given
    monkeypatch.setattr('sickbeard.SUBTITLES_MULTI', True)
    existing_subtitles = ['pob', 'eng']
    new_subtitles = ['fre']

    # When
    actual = sut.merge_subtitles(existing_subtitles, new_subtitles)

    # Then
    assert ['eng', 'fre', 'pob'] == actual


def test_merge_subtitles__with_multi_disabled_and_multiple_new_languages(monkeypatch):
    # Given
    monkeypatch.setattr('sickbeard.SUBTITLES_MULTI', False)
    existing_subtitles = ['pob']
    new_subtitles = ['fre', 'eng']

    # When
    actual = sut.merge_subtitles(existing_subtitles, new_subtitles)

    # Then
    assert ['eng', 'fre', 'pob'] == actual


def test_merge_subtitles__with_multi_disabled_and_single_new_language(monkeypatch):
    # Given
    monkeypatch.setattr('sickbeard.SUBTITLES_MULTI', False)
    existing_subtitles = ['pob', 'eng']
    new_subtitles = ['fre']

    # When
    actual = sut.merge_subtitles(existing_subtitles, new_subtitles)

    # Then
    assert ['eng', 'pob', 'und'] == actual


def test_get_subtitles_dir__no_subtitles_dir(monkeypatch):
    # Given
    monkeypatch.setattr('sickbeard.SUBTITLES_DIR', '')
    video_path = '/somefolder/subfolder/video.mkv'
    expected = '/somefolder/subfolder'

    # When
    actual = sut.get_subtitles_dir(video_path)

    # Then
    assert expected == actual


def test_get_subtitles_dir__absolute_subtitles_dir(monkeypatch, tmpdir):
    # Given
    expected = str(tmpdir.ensure('subtitles'))
    monkeypatch.setattr('sickbeard.SUBTITLES_DIR', expected)
    video_path = '/somefolder/subfolder/video.mkv'

    # When
    actual = sut.get_subtitles_dir(video_path)

    # Then
    assert expected == actual


def test_get_subtitles_dir__relative_subtitles_dir(monkeypatch, tmpdir):
    # Given
    relative_folder = 'subtitles'
    monkeypatch.setattr('sickbeard.SYS_ENCODING', sys.getdefaultencoding())
    monkeypatch.setattr('sickbeard.SUBTITLES_DIR', relative_folder)
    video_path = str(tmpdir.ensure('video.mkv'))
    expected = os.path.join(str(tmpdir), 'subtitles')

    # When
    actual = sut.get_subtitles_dir(video_path)

    # Then
    assert expected == actual
    assert os.path.isdir(actual)
