# coding=utf-8
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

"""Test history."""
from __future__ import unicode_literals

import unittest

from medusa.common import Quality
from medusa.show.history import History
from six import iteritems


class HistoryTests(unittest.TestCase):
    """Test history."""

    def test_get_actions(self):
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
