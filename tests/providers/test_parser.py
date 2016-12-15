# coding=utf-8
"""Provider parser tests."""
from __future__ import unicode_literals

import os

import vcr


__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))


def test_parser_daily(providers, limit=3):

    # Given
    for provider in providers:

        # When
        html = os.path.join(__location__, provider.type, provider.name,
                            provider.name + '_daily.yaml')

        with vcr.use_cassette(html) as test:

            actual = provider.klass.parse(test.responses[0]['body']['string'],
                                          provider.data['daily']['mode'])

            # Then
            for i, result in enumerate(actual):
                assert result == provider.data['daily']['data'][i]
                if i + 1 == limit:
                    break


def test_parser_backlog(providers, limit=2):

    # Given
    for provider in providers:

        # When
        html = os.path.join(__location__, provider.type, provider.name,
                            provider.name + '_backlog.yaml')

        with vcr.use_cassette(html) as test:

            actual = provider.klass.parse(test.responses[0]['body']['string'],
                                          provider.data['backlog']['mode'])

        # Then
        for i, result in enumerate(actual):
            assert result == provider.data['backlog']['data'][i]
            if i + 1 == limit:
                break
