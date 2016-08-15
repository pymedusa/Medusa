# coding=utf-8
"""Guessit name parser tests."""
from __future__ import unicode_literals

import datetime
import os

import guessit
import pytest
import sickbeard.name_parser.guessit_parser as sut
from six import text_type
import yaml

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))


@pytest.fixture
def show_list(create_tvshow):
    # show names with numbers that are used in our test suite
    return [
        create_tvshow(indexerid=1, name='1.2.3'),
        create_tvshow(indexerid=2, name='11.22.63'),
        create_tvshow(indexerid=3, name='12 Monkeys'),
        create_tvshow(indexerid=4, name='222 Show (2010)'),
        create_tvshow(indexerid=5, name='500 Bus Stops'),
        create_tvshow(indexerid=6, name='60 Minutes'),
        create_tvshow(indexerid=7, name='Incredible Show 2007'),
        create_tvshow(indexerid=8, name='Mobile Suit Gundam UC RE:0096',
                      exceptions=['Mobile Suit Gundam Unicorn RE 0096'], anime=1),
        create_tvshow(indexerid=9, name='R-15'),
        create_tvshow(indexerid=10, name='Super Show (1999)'),
        create_tvshow(indexerid=11, name='The 10 Anime Show', anime=1),
        create_tvshow(indexerid=12, name='The 100'),
        create_tvshow(indexerid=13, name='The 123 Show'),
        create_tvshow(indexerid=14, name=r"The.Someone's.Show.**.2.**"),
        create_tvshow(indexerid=15, name='The Show (UK)'),
        create_tvshow(indexerid=16, name='3 Show på (abc2)'),  # unicode characters, numbers and parenthesis
        create_tvshow(indexerid=16, name="Show '70s Name"),
    ]


def _format_param(param):
    if isinstance(param, list):
        return [_format_param(p) for p in param]
    if isinstance(param, datetime.date):
        return param
    if isinstance(param, int):
        return param

    return text_type(param)


def _parameters(files, single_test=None):
    parameters = []
    for file_name in files:
        with open(os.path.join(__location__, 'datasets', file_name), 'r') as stream:
            data = yaml.load(stream)

        for release_names, expected in data.items():
            expected = {k: v for k, v in expected.items()}

            if not isinstance(release_names, tuple):
                release_names = (release_names,)

            for release_name in release_names:
                parameters.append([release_name, expected])
                if single_test is not None and single_test == release_name:
                    return [[release_name, expected]]

    return parameters


def test_pre_configured_guessit():
    assert sut.guessit == guessit.guessit


@pytest.mark.parametrize('release_name,expected', _parameters(['tvshows.yml']))
def test_guess(monkeypatch, show_list, release_name, expected):
    # Given
    monkeypatch.setattr('sickbeard.showList', show_list)
    options = expected.pop('options', {})

    # When
    actual = guessit.guessit(release_name, options=options)

    # Then
    actual = {k: _format_param(v) for k, v in actual.items()}
    expected['release_name'] = release_name
    actual['release_name'] = release_name

    if not expected.get('disabled'):
        assert expected == actual
