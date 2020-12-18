# coding=utf-8
"""Tests for medusa.subtitles.py."""
from __future__ import unicode_literals
import os
import subprocess
import sys

from babelfish.language import Language
import medusa.subtitles as sut
from medusa import app
from mock.mock import Mock
import pytest

from subliminal.core import ProviderPool
from subliminal.subtitle import Subtitle

from six import text_type


def test_sorted_service_list(monkeypatch):
    # Given
    monkeypatch.setattr(app, 'SUBTITLES_SERVICES_LIST', ['legendastv', 'trash', 'thesubdb', 'shooter'])
    monkeypatch.setattr(app, 'SUBTITLES_SERVICES_ENABLED', [1, 1, 1, 0])

    # When
    actual = sut.sorted_service_list()

    # Then
    expected = [
        {'name': 'legendastv', 'enabled': True},
        {'name': 'thesubdb', 'enabled': True},
        {'name': 'shooter', 'enabled': False},
        {'name': 'addic7ed', 'enabled': False},
        {'name': 'argenteam', 'enabled': False},
        {'name': 'napiprojekt', 'enabled': False},
        {'name': 'opensubtitles', 'enabled': False},
        {'name': 'opensubtitlesvip', 'enabled': False},
        {'name': 'podnapisi', 'enabled': False},
        {'name': 'subtitulamos', 'enabled': False},
        {'name': 'tvsubtitles', 'enabled': False},
        {'name': 'wizdom', 'enabled': False},
    ]
    assert expected == [{'name': a['name'], 'enabled': a['enabled']} for a in actual]


def test_enabled_service_list(monkeypatch):
    # Given
    monkeypatch.setattr(app, 'SUBTITLES_SERVICES_LIST', ['legendastv', 'a', 'tvsubtitles', 'shooter'])
    monkeypatch.setattr(app, 'SUBTITLES_SERVICES_ENABLED', [1, 1, 1, 0])

    # When
    actual = sut.enabled_service_list()

    # Then
    expected = ['legendastv', 'tvsubtitles']
    assert expected == actual


def test_wanted_languages__only_valid_3letter_codes(monkeypatch):
    # Given
    monkeypatch.setattr(app, 'SUBTITLES_LANGUAGES', ['pob', 'trash', 'eng', 'fre', 'abc', 'pt-BR'])

    # When
    actual = sut.wanted_languages()

    # Then
    assert {'pob', 'eng', 'fre'} == actual


def test_get_needed_languages__multi_enabled(monkeypatch):
    # Given
    monkeypatch.setattr(app, 'SUBTITLES_MULTI', True)
    monkeypatch.setattr(app, 'SUBTITLES_LANGUAGES', ['pob', 'trash', 'eng', 'fre', 'abc'])
    existing_subtitles = {'pob', 'eng'}

    # When
    actual = sut.get_needed_languages(existing_subtitles)

    # Then
    assert {Language.fromietf('fr')} == actual


def test_get_needed_languages__multi_disabled_and_und_present(monkeypatch):
    # Given
    monkeypatch.setattr(app, 'SUBTITLES_MULTI', False)
    monkeypatch.setattr(app, 'SUBTITLES_LANGUAGES', ['pob', 'trash', 'eng', 'fre', 'abc'])
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
    monkeypatch.setattr(app, 'SUBTITLES_LANGUAGES', [])
    existing_subtitles = {'pob', 'eng'}

    # When
    actual = sut.needs_subtitles(existing_subtitles)

    # Then
    assert actual is False


def test_needs_subtitles__multi_enabled(monkeypatch):
    # Given
    monkeypatch.setattr(app, 'SUBTITLES_MULTI', True)
    monkeypatch.setattr(app, 'SUBTITLES_LANGUAGES', ['pob', 'eng', 'fre'])
    existing_subtitles = {'pob', 'eng'}

    # When
    actual = sut.needs_subtitles(existing_subtitles)

    # Then
    assert actual is True


def test_needs_subtitles__multi_enabled_with_string(monkeypatch):
    # Given
    monkeypatch.setattr(app, 'SUBTITLES_MULTI', True)
    monkeypatch.setattr(app, 'SUBTITLES_LANGUAGES', ['pob', 'eng', 'fre'])
    existing_subtitles = 'pob,eng,fre'

    # When
    actual = sut.needs_subtitles(existing_subtitles)

    # Then
    assert actual is False


def test_needs_subtitles__multi_disabled_and_und_present(monkeypatch):
    # Given
    monkeypatch.setattr(app, 'SUBTITLES_MULTI', False)
    monkeypatch.setattr(app, 'SUBTITLES_LANGUAGES', ['pob', 'eng', 'fre'])
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


def test_from_country_code_to_name__valid_code():
    # Given
    code = 'IT'

    # When
    actual = sut.from_country_code_to_name(code)

    # Then
    assert 'ITALY' == actual


def test_from_country_code_to_name__valid_lower_code():
    # Given
    code = 'fr'

    # When
    actual = sut.from_country_code_to_name(code)

    # Then
    assert 'FRANCE' == actual


def test_from_country_code_to_name__invalid_code():
    # Given
    code = 'XY'

    # When
    actual = sut.from_country_code_to_name(code)

    # Then
    assert None is actual


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
    monkeypatch.setattr(app, 'SUBTITLES_MULTI', True)
    subtitle = Subtitle(language=Language('por', 'BR'))
    video_path = '/folder/subfolder/video.mkv'
    subtitles_dir = None

    # When
    actual = sut.compute_subtitle_path(subtitle, video_path, subtitles_dir)

    # Then
    assert '/folder/subfolder/video.pt-BR.srt' == actual


def test_compute_subtitle_path__multi_with_und_language(monkeypatch):
    # Given
    monkeypatch.setattr(app, 'SUBTITLES_MULTI', True)
    subtitle = Subtitle(language=Language('und'))
    video_path = '/folder/subfolder/video.mkv'
    subtitles_dir = None

    # When
    actual = sut.compute_subtitle_path(subtitle, video_path, subtitles_dir)

    # Then
    assert '/folder/subfolder/video.srt' == actual


def test_compute_subtitle_path__single_with_valid_language(monkeypatch):
    # Given
    monkeypatch.setattr(app, 'SUBTITLES_MULTI', False)
    subtitle = Subtitle(language=Language('por', 'BR'))
    video_path = '/folder/subfolder/video.mkv'
    subtitles_dir = None

    # When
    actual = sut.compute_subtitle_path(subtitle, video_path, subtitles_dir)

    # Then
    assert '/folder/subfolder/video.srt' == actual


def test_compute_subtitle_path__single_with_valid_language_and_subs_folder(monkeypatch):
    # Given
    monkeypatch.setattr(app, 'SUBTITLES_MULTI', False)
    subtitle = Subtitle(language=Language('por', 'BR'))
    video_path = '/folder/subfolder/video.mkv'
    subtitles_dir = '/folder/subtitles'

    # When
    actual = sut.compute_subtitle_path(subtitle, video_path, subtitles_dir)

    # Then
    assert os.path.normpath('/folder/subtitles/video.srt') == os.path.normpath(actual)


def test_merge_subtitles__with_multi_enabled(monkeypatch):
    # Given
    monkeypatch.setattr(app, 'SUBTITLES_MULTI', True)
    existing_subtitles = ['pob', 'eng']
    new_subtitles = ['fre']

    # When
    actual = sut.merge_subtitles(existing_subtitles, new_subtitles)

    # Then
    assert ['eng', 'fre', 'pob'] == actual


def test_merge_subtitles__with_multi_disabled_and_multiple_new_languages(monkeypatch):
    # Given
    monkeypatch.setattr(app, 'SUBTITLES_MULTI', False)
    existing_subtitles = ['pob']
    new_subtitles = ['fre', 'eng']

    # When
    actual = sut.merge_subtitles(existing_subtitles, new_subtitles)

    # Then
    assert ['eng', 'fre', 'pob'] == actual


def test_merge_subtitles__with_multi_disabled_and_single_new_language(monkeypatch):
    # Given
    monkeypatch.setattr(app, 'SUBTITLES_MULTI', False)
    existing_subtitles = ['pob', 'eng']
    new_subtitles = ['fre']

    # When
    actual = sut.merge_subtitles(existing_subtitles, new_subtitles)

    # Then
    assert ['eng', 'pob', 'und'] == actual


def test_get_min_score__with_perfect_match_enabled(monkeypatch):
    # Given
    monkeypatch.setattr(app, 'SUBTITLES_PERFECT_MATCH', True)

    # When
    actual = sut.get_min_score()

    # Then
    assert 645 == actual


def test_get_min_score__with_perfect_match_disabled(monkeypatch):
    # Given
    monkeypatch.setattr(app, 'SUBTITLES_PERFECT_MATCH', False)

    # When
    actual = sut.get_min_score()

    # Then
    assert 630 == actual


def test_get_subtitles_dir__no_subtitles_dir(monkeypatch):
    # Given
    monkeypatch.setattr(app, 'SUBTITLES_DIR', '')
    video_path = '/somefolder/subfolder/video.mkv'
    expected = '/somefolder/subfolder'

    # When
    actual = sut.get_subtitles_dir(video_path)

    # Then
    assert expected == actual


def test_get_subtitles_dir__absolute_subtitles_dir(monkeypatch, tmpdir):
    # Given
    expected = text_type(tmpdir.ensure('subtitles'))
    monkeypatch.setattr(app, 'SUBTITLES_DIR', expected)
    video_path = '/somefolder/subfolder/video.mkv'

    # When
    actual = sut.get_subtitles_dir(video_path)

    # Then
    assert expected == actual


def test_get_subtitles_dir__relative_subtitles_dir(monkeypatch, tmpdir):
    # Given
    relative_folder = 'subtitles'
    monkeypatch.setattr(app, 'SYS_ENCODING', sys.getdefaultencoding())
    monkeypatch.setattr(app, 'SUBTITLES_DIR', relative_folder)
    video_path = text_type(tmpdir.ensure('video.mkv'))
    expected = os.path.join(text_type(tmpdir), 'subtitles')

    # When
    actual = sut.get_subtitles_dir(video_path)

    # Then
    assert expected == actual
    assert os.path.isdir(actual)


def test_delete_unwanted_subtitles__existing_subtitles_in_unwanted_languages(monkeypatch, tmpdir):
    # Given
    monkeypatch.setattr(app, 'SUBTITLES_MULTI', True)
    monkeypatch.setattr(app, 'SUBTITLES_KEEP_ONLY_WANTED', True)
    monkeypatch.setattr(app, 'SUBTITLES_LANGUAGES', ['pob', 'eng'])
    subtitle_pob = text_type(tmpdir.ensure('video.pt-BR.srt'))
    subtitle_eng = text_type(tmpdir.ensure('video.en.srt'))
    subtitle_fre = text_type(tmpdir.ensure('video.fr.srt'))
    some_file = text_type(tmpdir.ensure('video.fr.nfo'))

    # When
    sut.delete_unwanted_subtitles(text_type(tmpdir), subtitle_pob)
    sut.delete_unwanted_subtitles(text_type(tmpdir), subtitle_eng)
    sut.delete_unwanted_subtitles(text_type(tmpdir), subtitle_fre)

    # Then
    assert os.path.exists(subtitle_pob)
    assert os.path.exists(subtitle_eng)
    assert not os.path.exists(subtitle_fre)
    assert os.path.exists(some_file)


def test_delete_unwanted_subtitles__multi_disabled(monkeypatch, tmpdir):
    # Given
    monkeypatch.setattr(app, 'SUBTITLES_MULTI', False)
    monkeypatch.setattr(app, 'SUBTITLES_KEEP_ONLY_WANTED', True)
    monkeypatch.setattr(app, 'SUBTITLES_LANGUAGES', ['pob', 'eng'])
    subtitle_pob = text_type(tmpdir.ensure('video.pt-BR.srt'))
    subtitle_fre = text_type(tmpdir.ensure('video.fr.srt'))

    # When
    sut.delete_unwanted_subtitles(tmpdir, subtitle_pob)
    sut.delete_unwanted_subtitles(tmpdir, subtitle_fre)

    # Then
    assert os.path.exists(subtitle_pob)
    assert os.path.exists(subtitle_fre)


def test_delete_unwanted_subtitles__keep_only_wanted_disabled(monkeypatch, tmpdir):
    # Given
    monkeypatch.setattr(app, 'SUBTITLES_MULTI', True)
    monkeypatch.setattr(app, 'SUBTITLES_KEEP_ONLY_WANTED', False)
    monkeypatch.setattr(app, 'SUBTITLES_LANGUAGES', ['pob', 'eng'])
    subtitle_pob = text_type(tmpdir.ensure('video.pt-BR.srt'))
    subtitle_fre = text_type(tmpdir.ensure('video.fr.srt'))

    # When
    sut.delete_unwanted_subtitles(tmpdir, subtitle_pob)
    sut.delete_unwanted_subtitles(tmpdir, subtitle_fre)

    # Then
    assert os.path.exists(subtitle_pob)
    assert os.path.exists(subtitle_fre)


@pytest.mark.parametrize('p', [
    {  # multi subs and needed languages: download needed
        'multiple_subtitles': True,
        'wanted_languages': ['pob', 'eng', 'fre'],
        'existing_subtitles': ['eng'],
        'external_subtitles': True,
        'embedded_subtitles': False,
        'hearing_impaired': False,
        'pre_scripts': ['pre.py'],
        'post_scripts': ['post.py'],
        'list_subtitles': [(1, 'pob', 'content'), (0, 'pob', 'poor content'), (1, 'fre', 'content')],
        'best_subtitles': [(1, 'pob', 'content'), (1, 'fre', 'content')],
        'expected': ['fre', 'pob']
    },
    {  # multi subs, needed languages, but already have all: download needed
        'multiple_subtitles': True,
        'wanted_languages': ['pob', 'eng'],
        'existing_subtitles': ['eng', 'pob'],
        'external_subtitles': False,
        'embedded_subtitles': True,
        'hearing_impaired': True,
        'pre_scripts': ['pre.py'],
        'post_scripts': ['post.py', 'post2.py'],
        'list_subtitles': [(1, 'pob', 'content'), (0, 'pob', 'poor content')],
        'best_subtitles': [(1, 'pob', 'content')],
        'expected': []
    },
    {  # multi subs, needed languages, no content: download needed
        'multiple_subtitles': True,
        'wanted_languages': ['pob', 'eng'],
        'existing_subtitles': ['eng'],
        'external_subtitles': False,
        'embedded_subtitles': True,
        'hearing_impaired': True,
        'pre_scripts': ['pre.py', 'pre2.py'],
        'post_scripts': ['post.py', 'post2.py'],
        'list_subtitles': [(1, 'pob', None), (0, 'pob', 'poor content')],
        'best_subtitles': [(1, 'pob', None)],
        'expected': []
    },
    {  # single subs and 'und' in subtitles: no download needed
        'multiple_subtitles': False,
        'wanted_languages': ['pob', 'eng'],
        'existing_subtitles': ['und'],
        'external_subtitles': True,
        'embedded_subtitles': False,
        'hearing_impaired': False,
        'pre_scripts': [],
        'post_scripts': [],
        'list_subtitles': [(1, 'pob', 'content'), (0, 'pob', 'poor content')],
        'best_subtitles': [(1, 'pob', 'content')],
        'expected': []
    },
    {  # single subs and 'und' not in subtitles: download needed
        'multiple_subtitles': False,
        'wanted_languages': ['pob', 'eng'],
        'existing_subtitles': ['pob'],
        'external_subtitles': True,
        'embedded_subtitles': None,
        'hearing_impaired': False,
        'pre_scripts': [],
        'post_scripts': [],
        'list_subtitles': [(1, 'eng', 'content'), (0, 'eng', 'poor content')],
        'best_subtitles': [(1, 'eng', 'content')],
        'expected': ['eng']
    }
])
def test_download_subtitles(monkeypatch, tmpdir, video, tvshow, create_sub, create_file, create_tvepisode, p):
    # Given
    subtitles = [create_sub(language=code, id=sid, content=content) for sid, code, content in p['list_subtitles']]
    best_subtitles = [create_sub(language=code, id=sid, content=content) for sid, code, content in p['best_subtitles']]
    video_path = text_type(tmpdir.ensure(video.name))
    tvepisode = create_tvepisode(series=tvshow, season=3, episode=4, subtitles=p['existing_subtitles'])
    external_subtitles = p['external_subtitles']
    embedded_subtitles = p['embedded_subtitles'] if p['embedded_subtitles'] is not None else True
    refine = Mock()
    compute_score = Mock(return_value=1)
    list_subtitles = Mock(return_value=subtitles)
    download_best_subtitles = Mock(return_value=best_subtitles)
    popen = Mock()
    monkeypatch.setattr(app, 'SYS_ENCODING', 'utf-8')
    monkeypatch.setattr(app, 'SUBTITLES_MULTI', p['multiple_subtitles'])
    monkeypatch.setattr(app, 'SUBTITLES_LANGUAGES', p['wanted_languages'])
    monkeypatch.setattr(app, 'SUBTITLES_PRE_SCRIPTS', [create_file(f, size=42) for f in p['pre_scripts']])
    monkeypatch.setattr(app, 'SUBTITLES_EXTRA_SCRIPTS', [create_file(f, size=42) for f in p['post_scripts']])
    monkeypatch.setattr(app, 'SUBTITLES_HEARING_IMPAIRED', p['hearing_impaired'])
    monkeypatch.setattr(sut, 'refine', refine)
    monkeypatch.setattr(sut, 'compute_score', compute_score)
    monkeypatch.setattr(ProviderPool, 'list_subtitles', list_subtitles)
    monkeypatch.setattr(ProviderPool, 'download_best_subtitles', download_best_subtitles)
    monkeypatch.setattr(subprocess, 'Popen', popen)

    # When
    actual = sut.download_subtitles(tv_episode=tvepisode, video_path=video_path,
                                    subtitles=external_subtitles, embedded_subtitles=embedded_subtitles)

    # Then
    assert p['expected'] == actual
    if p['expected']:
        assert len(p['pre_scripts']) + len(p['post_scripts']) * len(p['best_subtitles']) == popen.call_count
    if refine.called:
        assert embedded_subtitles == refine.call_args[1]['embedded_subtitles']
        assert tvepisode == refine.call_args[1]['tv_episode']
