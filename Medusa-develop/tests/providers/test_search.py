# coding=utf-8
"""Provider parser tests."""
from __future__ import unicode_literals

import datetime
import functools
import os

from tests.providers.conftest import get_provider_data

import vcr

# Set this to True to record cassettes
record_cassettes = False

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
record_mode = 'once' if record_cassettes else 'none'


def search(search_type, provider):
    """Generate test for provider search of a specific type."""
    # Given
    test_case = provider.data[search_type]
    expected = test_case['results']
    limit = len(expected)

    # When
    cassette_filename = '{0}_{1}.yaml'.format(provider.name, search_type)
    cassette_path = os.path.join(__location__, provider.type, provider.name,
                                 cassette_filename)
    with vcr.use_cassette(cassette_path, record_mode=record_mode):
        actual = provider.klass.search(test_case['search_strings'])

    # Check if we got any results
    if record_cassettes:
        assert actual != []

    for i, result in enumerate(actual):
        # Only compare up to the info hash if we have magnets
        if expected[i]['link'].startswith('magnet:'):
            result['link'] = result['link'][:60]
        # Only verify that we got a datetime object for now
        pubdate = expected[i]['pubdate']
        if pubdate and isinstance(pubdate, datetime.datetime):
            result['pubdate'] = pubdate

        # Then
        assert result == expected[i]

        if i + 1 == limit:
            break


def generate_test_cases():
    for provider in get_provider_data():
        for search_type in ('daily', 'backlog'):
            test_name = 'test_{0}_{1}_search'.format(provider.name, search_type)
            generated_test = functools.partial(search, search_type, provider)
            globals()[test_name] = generated_test
            del generated_test


generate_test_cases()
