# coding=UTF-8
# Author: Dustyn Gibson <miigotu@gmail.com>
#
# This file is part of Medusa.
#
# Medusa is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Medusa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Medusa. If not, see <http://www.gnu.org/licenses/>.
"""SSL SNI Tests."""
from __future__ import unicode_literals

import unittest
import certifi
import medusa.providers as providers
from medusa.helper.exceptions import ex
import requests

from six import text_type


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
            requests.head(_provider.url, verify=certifi.where(), timeout=10)
        except requests.exceptions.SSLError as error:
            if 'certificate verify failed' in text_type(error):
                print('Cannot verify certificate for %s' % _provider.name)
            else:
                print('SSLError on %s: %s' % (_provider.name, ex(error)))
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
