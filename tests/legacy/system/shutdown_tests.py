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

"""Test shutdown."""

from __future__ import print_function

import unittest

from medusa import app
from medusa.event_queue import Events
from medusa.system.shutdown import Shutdown
from six import iteritems


class ShutdownTests(unittest.TestCase):
    """Test shutdown."""

    def test_shutdown(self):
        app.PID = 123456
        app.events = Events(None)

        test_cases = {
            0: False,
            '0': False,
            123: False,
            '123': False,
            123456: True,
            '123456': True,
        }

        unicode_test_cases = {
            u'0': False,
            u'123': False,
            u'123456': True,
        }

        for tests in test_cases, unicode_test_cases:
            for (pid, result) in iteritems(tests):
                self.assertEqual(Shutdown.stop(pid), result)
