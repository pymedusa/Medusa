# coding=utf-8
"""Guessit name parser tests."""
from __future__ import unicode_literals

import os
import unittest

try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock
import yaml
from yaml.constructor import ConstructorError
from yaml.nodes import MappingNode, SequenceNode

import guessit

import sickbeard
import sickbeard.name_parser.guessit_parser as sut
from nose_parameterized import parameterized
from six import iteritems

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))


def construct_mapping(self, node, deep=False):
    """Custom yaml map constructor to allow lists to be key of a map.

    :param self:
    :param node:
    :param deep:
    :return:
    """
    if not isinstance(node, MappingNode):
        raise ConstructorError(None, None, 'expected a mapping node, but found %s' % node.id, node.start_mark)
    mapping = {}
    for key_node, value_node in node.value:
        is_sequence = isinstance(key_node, SequenceNode)
        key = self.construct_object(key_node, deep=deep or is_sequence)
        try:
            if is_sequence:
                key = tuple(key)
            hash(key)
        except TypeError as exc:
            raise ConstructorError('while constructing a mapping', node.start_mark,
                                   'found unacceptable key (%s)' % exc, key_node.start_mark)
        value = self.construct_object(value_node, deep=deep)
        mapping[key] = value
    return mapping


yaml.Loader.add_constructor('tag:yaml.org,2002:map', construct_mapping)


def _mock_tv_show(name, is_anime=False):
    tvshow = Mock(is_anime=is_anime)
    tvshow.configure_mock(name=name)
    return tvshow


class GuessitTests(unittest.TestCase):
    """Guessit Tests."""

    files = {
        'tvshows': 'tvshows.yml',
    }

    # show names with numbers that are used in our test suite
    show_list = [
            _mock_tv_show('12 Monkeys'),
            _mock_tv_show('500 Bus Stops'),
            _mock_tv_show('60 Minutes'),
            _mock_tv_show('Mobile Suit Gundam Unicorn RE 0096', is_anime=True),
            _mock_tv_show('The 100'),
        ]

    parameters = []

    for scenario_name, file_name in iteritems(files):
        with open(os.path.join(__location__, 'datasets', file_name), 'r') as stream:
            data = yaml.load(stream)

        for release_names, expected in iteritems(data):
            expected = {k: v for k, v in iteritems(expected)}

            if not isinstance(release_names, tuple):
                release_names = (release_names,)

            for release_name in release_names:
                parameters.append([scenario_name, release_name, expected])

    def test_get_expected_titles(self):
        """Assert expect titles only returns regexes for titles containing numbers."""
        # Given
        regular_format = r're:(?<![^/\\]){name}\b'
        anime_format = r're:\b{name}\b'
        sickbeard.showList = [
            _mock_tv_show('Super Show (1999)'),
            _mock_tv_show('Incredible Show 2007'),
            _mock_tv_show('The Show (UK)'),
            _mock_tv_show('The 123 Show'),
            _mock_tv_show('222 Show (2010)'),
            _mock_tv_show('The 10 Anime Show', is_anime=True),
        ]

        # When
        actual = sut.get_expected_titles()

        # Then
        expected = list(sut.fixed_expected_titles)
        expected.extend([
            regular_format.format(name='The 123 Show'),
            regular_format.format(name='222 Show'),
            anime_format.format(name='The 10 Anime Show'),
        ])
        self.assertEqual(expected, actual)

    def test_pre_configured_guessit(self):
        """Assert that guessit.guessit() uses the pre-configured hook."""
        self.assertEqual(sut.guessit, guessit.guessit)

    @parameterized.expand(parameters)
    def test_guess(self, scenario_name, release_name, expected):
        """Test the given release name.

        :param scenario_name:
        :type scenario_name: str
        :param release_name: the input release name
        :type release_name: str
        :param expected: the expected guessed dict
        :type expected: dict
        """
        self.maxDiff = None
        sickbeard.showList = self.show_list
        options = expected.pop('options', {})
        actual = guessit.guessit(release_name, options=options)
        actual = {k: v for k, v in iteritems(actual)}

        def format_param(param):
            if isinstance(param, list):
                result = []
                for p in param:
                    result.append(str(p))
                return result

            return str(param)

        if 'country' in actual:
            actual['country'] = format_param(actual['country'])
        if 'language' in actual:
            actual['language'] = format_param(actual['language'])
        if 'subtitle_language' in actual:
            actual['subtitle_language'] = format_param(actual['subtitle_language'])

        expected['release_name'] = release_name
        actual['release_name'] = release_name

        if expected.get('disabled'):
            print('Skipping {scenario}: {release_name}'.format(scenario=scenario_name, release_name=release_name))
        else:
            print('Testing {scenario}: {release_name}'.format(scenario=scenario_name, release_name=release_name))
            self.assertEqual(expected, actual)
