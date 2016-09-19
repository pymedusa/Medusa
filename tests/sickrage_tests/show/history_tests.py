# coding=utf-8
# This file is part of SickRage.
#

# Git: https://github.com/PyMedusa/SickRage.git
#
# SickRage is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# SickRage is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with SickRage. If not, see <http://www.gnu.org/licenses/>.

"""
Test history
"""

from __future__ import print_function

import os
import sys
import unittest

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../lib')))
sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from six import iteritems
from medusa.common import Quality
from medusa.show.History import History


class HistoryTests(unittest.TestCase):
    """
    Test history
    """
    def test_get_actions(self):
        """
        Test get actions
        """
        test_cases = {
            None: [],
            '': [],
            'wrong': [],
            'downloaded': Quality.DOWNLOADED,
            'Downloaded': Quality.DOWNLOADED,
            'snatched': Quality.SNATCHED,
            'Snatched': Quality.SNATCHED,
        }

        unicode_test_cases = {
            u'': [],
            u'wrong': [],
            u'downloaded': Quality.DOWNLOADED,
            u'Downloaded': Quality.DOWNLOADED,
            u'snatched': Quality.SNATCHED,
            u'Snatched': Quality.SNATCHED,
        }

        for tests in test_cases, unicode_test_cases:
            for (action, result) in iteritems(tests):
                self.assertEqual(History._get_actions(action), result)  # pylint: disable=protected-access

if __name__ == '__main__':
    print('=====> Testing %s' % __file__)

    SUITE = unittest.TestLoader().loadTestsFromTestCase(HistoryTests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
