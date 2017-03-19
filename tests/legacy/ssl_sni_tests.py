# coding=UTF-8

"""SSL SNI Tests."""

from __future__ import print_function

import unittest

import certifi

import medusa.providers as providers
from medusa.helper.exceptions import ex

import requests


def generator(_provider):
    """Generate tests for each provider.

    :param test_strings: to generate tests from
    :return: test
    """
    def _connectivity_test():
        """Generate tests.

        :param self:
        :return: test to run
        """
        if not _provider.url:
            print('%s has no url set, skipping' % _provider.name)
            return

        try:
            requests.head(_provider.url, verify=certifi.old_where(), timeout=10)
        except requests.exceptions.SSLError as error:
            if 'certificate verify failed' in str(error):
                print('Cannot verify certificate for %s' % _provider.name)
            else:
                print('SSLError on %s: %s' % (_provider.name, ex(error.message)))
                raise
        except requests.exceptions.Timeout:
            print('Provider timed out')

    return _connectivity_test


class SniTests(unittest.TestCase):
    """Unittest class."""

    pass

if __name__ == "__main__":
    print("""
    ==================
    STARTING - Provider Connectivity TESTS and SSL/SNI
    ==================
    ######################################################################
    """)
    # Just checking all providers - we should make this error on non-existent urls.
    for provider in [p for p in providers.make_provider_list()]:
        test_name = 'test_%s' % provider.name
        test = generator(provider)
        setattr(SniTests, test_name, test)

    SUITE = unittest.TestLoader().loadTestsFromTestCase(SniTests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
