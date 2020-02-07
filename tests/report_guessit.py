# coding=utf-8
"""Utility module to report guessit issues."""
from __future__ import unicode_literals

import os
import sys

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), '../ext')))
sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from guessit import __version__ as guessit_version
from medusa import app, cache
from medusa.name_parser.guessit_parser import guessit
from rebulk.__version__ import __version__ as rebulk_version

from six import iteritems


class MockTvShow(object):
    def __init__(self, name):
        self.is_anime = name.startswith('a:')
        self.name = name[2:] if self.is_anime else name
        self.aliases = []


def main(argv):
    if len(argv) < 2:
        print('Usage: python {0} <input> <expected show names>'.format(__file__))
        sys.exit(1)

    show_list = argv[2:]
    for arg in show_list:
        app.showList.append(MockTvShow(arg))

    cache.fallback()
    actual = guessit(argv[1])
    results = ['# guessit: {}  rebulk: {}'.format(guessit_version, rebulk_version)]
    if show_list:
        results.append('# show list: {}'.format(argv[2:]))
    results.append('? {}'.format(argv[1]))
    for key, value in iteritems(actual):
        fmt = ': {key}: {value}' if len(results) <= 2 else '  {key}: {value}'
        results.append(fmt.format(key=key, value=value))

    print('\n'.join(results))


if __name__ == "__main__":
    main(sys.argv)
