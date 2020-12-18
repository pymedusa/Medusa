# coding=utf-8
"""Guessit name parser tests."""
from __future__ import unicode_literals

import datetime
import os

import guessit
import medusa.name_parser.guessit_parser as sut
from medusa.scene_exceptions import TitleException
from medusa import app
import pytest
from six import binary_type, text_type, iteritems
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
                      exceptions=[TitleException(
                          title='Mobile Suit Gundam Unicorn RE 0096',
                          season=-1,
                          indexer=1,
                          series_id=8,
                          custom=False
                      )
                      ], anime=1),
        create_tvshow(indexerid=9, name='R-15'),
        create_tvshow(indexerid=10, name='Super Show (1999)'),
        create_tvshow(indexerid=11, name='The 10 Anime Show', anime=1),
        create_tvshow(indexerid=12, name='The 100'),
        create_tvshow(indexerid=13, name='The 123 Show'),
        create_tvshow(indexerid=14, name=r"The Someone's Show 2"),
        create_tvshow(indexerid=15, name='The Show (UK)'),
        create_tvshow(indexerid=16, name='3 Show på (abc2)'),  # unicode characters, numbers and parenthesis
        create_tvshow(indexerid=16, name="Show '70s Name"),
        create_tvshow(indexerid=17, name='An Anime Show 100', anime=1),
        create_tvshow(indexerid=17, name='Show! Name 2', anime=1),
        create_tvshow(indexerid=18, name='24'),  # expected titles shouldn't contain numbers
    ]


def _format_param(param):
    if isinstance(param, list):
        return [_format_param(p) for p in param]
    if isinstance(param, datetime.date):
        return param
    if isinstance(param, int):
        return param

    return text_type(param)


def _parameters(single_test=None):
    parameters = []
    input_file = os.path.join(__location__, __name__.split('.')[-1] + '.yml')
    with open(input_file, 'r') as stream:
        data = yaml.load(stream, Loader=yaml.Loader)

    for release_names, expected in iteritems(data):
        expected = {k: v for k, v in iteritems(expected)}
        for k, v in iteritems(expected):
            if isinstance(v, binary_type):
                expected[k] = text_type(v)

        if not isinstance(release_names, tuple):
            release_names = (release_names,)

        for release_name in release_names:
            parameters.append([release_name, expected])
            if single_test is not None and single_test == release_name:
                return [[release_name, expected]]

    return parameters


def test_pre_configured_guessit():
    assert sut.guessit == guessit.guessit


@pytest.mark.parametrize('release_name,expected', _parameters())
def test_guess(monkeypatch, show_list, release_name, expected):
    # Given
    monkeypatch.setattr(app, 'showList', show_list)
    options = expected.pop('options', {})

    # When
    actual = guessit.guessit(release_name, options=options)

    # Then
    actual = {k: _format_param(v) for k, v in iteritems(actual)}
    expected['release_name'] = release_name
    actual['release_name'] = release_name

    # mimetypes are not consistent therefore they are not compared
    if 'mimetype' in expected:
        del expected['mimetype']
    if 'mimetype' in actual:
        del actual['mimetype']

    del actual['parsing_time']

    if not expected.get('disabled'):
        assert expected == actual
