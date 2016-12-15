# coding=utf-8
"""Configuration for pytest."""
from __future__ import unicode_literals

import os
from collections import namedtuple

from medusa.providers.torrent import extratorrent

import pytest

import yaml


__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

__providers__ = (extratorrent,)


@pytest.fixture(scope='session')
def providers():

    Provider = namedtuple('Provider', 'name type klass data')
    providers = [Provider(name=provider.__name__.rpartition('.')[2],
                          type=provider.__name__.split('.', 3)[2],
                          klass=provider.__dict__.get('provider'),
                          data={})
                 for provider in __providers__]

    for provider in providers:

        # Load provider test config
        input_file = os.path.join(__location__, provider.type, provider.name, provider.name + '_test.yaml')
        with open(input_file, 'r') as stream:
            test_data = yaml.load(stream)

        # Update provider with test data
        provider.data.update(test_data)

    return providers
