# coding=utf-8
"""Provider search tests."""
from __future__ import unicode_literals

import os

from vcr import VCR


__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))


vcr = VCR(path_transformer=VCR.ensure_suffix('.yaml'),
          record_mode='once',
          match_on=['method', 'scheme', 'host', 'port', 'path', 'query', 'body'],
          cassette_library_dir=__location__)


def test_search_backlog(providers):

    # Given
    for provider in providers:

        with vcr.use_cassette(os.path.join(provider.type, provider.name, provider.name + '_backlog')):

            search_strings = {provider.data['backlog']['mode']: provider.data['backlog']['search_strings']}
            provider.klass.search(search_strings)


def test_search_daily(providers):

    # Given
    for provider in providers:

        with vcr.use_cassette(os.path.join(provider.type, provider.name, provider.name + '_daily')):

            search_strings = {provider.data['daily']['mode']: provider.data['daily']['search_strings']}
            provider.klass.search(search_strings)
