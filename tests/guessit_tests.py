# coding=utf-8
"""
Guessit name parser tests
"""
import os
import unittest
import yaml
from yaml.constructor import ConstructorError
from yaml.nodes import MappingNode, SequenceNode

from nose_parameterized import parameterized
from sickbeard.name_parser.guessit_parser import parser


__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))


def construct_mapping(self, node, deep=False):
    """
    Custom yaml map constructor to allow lists to be key of a map
    :param self:
    :param node:
    :param deep:
    :return:
    """
    if not isinstance(node, MappingNode):
        raise ConstructorError(None, None,
                               "expected a mapping node, but found %s" % node.id,
                               node.start_mark)
    mapping = {}
    for key_node, value_node in node.value:
        is_sequence = isinstance(key_node, SequenceNode)
        key = self.construct_object(key_node, deep=deep or is_sequence)
        try:
            if is_sequence:
                key = tuple(key)
            hash(key)
        except TypeError, exc:
            raise ConstructorError("while constructing a mapping", node.start_mark,
                                   "found unacceptable key (%s)" % exc, key_node.start_mark)
        value = self.construct_object(value_node, deep=deep)
        mapping[key] = value
    return mapping


yaml.SafeLoader.add_constructor(u'tag:yaml.org,2002:map', construct_mapping)


class GuessitTests(unittest.TestCase):
    """
    Guessit Tests :-)
    """
    files = {
        'tvshows': 'tvshows.yml',
    }

    parameters = []

    for scenario_name, file_name in files.iteritems():
        with open(os.path.join(__location__, 'datasets', file_name), 'r') as stream:
            data = yaml.safe_load(stream)

        for release_names, expected in data.iteritems():
            expected = {k: v for k, v in expected.iteritems()}

            if not isinstance(release_names, tuple):
                release_names = (release_names, )

            for release_name in release_names:
                parameters.append([scenario_name, release_name, expected])

    @parameterized.expand(parameters)
    def test_guess(self, scenario_name, release_name, expected):
        """
        :param scenario_name:
        :type scenario_name: str
        :param release_name: the input release name
        :type release_name: str
        :param expected: the expected guessed dict
        :type expected: dict
        """
        self.maxDiff = None
        options = expected.pop('options', {})
        actual = parser.guess(release_name, show_type=options.get('show_type'))
        actual = {k: v for k, v in actual.iteritems()}

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
            print(u'Skipping {scenario}: {release_name}'.format(scenario=scenario_name, release_name=release_name))
        else:
            print(u'Testing {scenario}: {release_name}'.format(scenario=scenario_name, release_name=release_name))
            self.assertEqual(expected, actual)

    # for debugging purposes
    #def dump(self, scenario_name, release_name, values):
    #    print('')
    #    print('# {scenario_name}'.format(scenario_name=scenario_name))
    #    print('? {release_name}'.format(release_name=release_name))
    #    start = ':'
    #    for k, v in values.iteritems():
    #        print('{start} {k}: {v}'.format(start=start, k=k, v=v))
    #        start = ' '
