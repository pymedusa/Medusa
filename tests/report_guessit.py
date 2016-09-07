# coding=utf-8
"""Utility module to report guessit issues."""

import os
import sys

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), '../lib')))
sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from guessit import __version__ as guessit_version
from rebulk.__version__ import __version__ as rebulk_version
from sickbeard.name_parser.guessit_parser import guessit


def main(argv):
    if len(argv) != 2:
        print('Usage: python {} <input>'.format(__file__))
        sys.exit(1)

    actual = guessit(argv[1])
    results = ['# guessit: {}  rebulk: {}'.format(guessit_version, rebulk_version), '? {}'.format(argv[1])]
    for key, value in actual.items():
        fmt = ': {key}: {value}' if len(results) <= 2 else '  {key}: {value}'
        results.append(fmt.format(key=key, value=value))

    print('\n'.join(results))


if __name__ == "__main__":
    main(sys.argv)
