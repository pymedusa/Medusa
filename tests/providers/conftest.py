# coding=utf-8
"""Configuration for pytest."""
from __future__ import unicode_literals

import os
from collections import namedtuple

import pytest

import yaml


__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))


def get_providers():
    from medusa.providers.torrent import (anidex, btdb, limetorrents, nyaa,
                                          rarbg, shanaproject, thepiratebay,
                                          tokyotoshokan, torrentz2, zooqle)
    from medusa.providers.nzb import anizb, binsearch

    return (anidex, btdb, limetorrents, nyaa, rarbg, shanaproject,
            thepiratebay, tokyotoshokan, torrentz2, zooqle, anizb, binsearch)


def get_provider_data():
    Provider = namedtuple('Provider', 'name type klass data')
    providers = [Provider(name=provider.__name__.rpartition('.')[2],
                          type=provider.__name__.split('.', 3)[2],
                          klass=provider.__dict__.get('provider'),
                          data={})
                 for provider in get_providers()]

    for provider in providers:
        # Load provider test config
        input_file = os.path.join(__location__, provider.type, provider.name, provider.name + '_test.yaml')
        with open(input_file, 'r') as stream:
            test_data = yaml.safe_load(stream)

        # Update provider with test data
        provider.data.update(test_data)

    return providers


@pytest.fixture(scope='session')
def providers():
    return get_provider_data()
