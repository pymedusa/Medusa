# coding=UTF-8
# Author: Dennis Lutter <lad1337@gmail.com>
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

"""Test show database functionality."""
from __future__ import unicode_literals

import threading

from tests.legacy import test_lib as test


class DBBasicTests(test.AppTestDBCase):
    """Perform basic database tests."""

    def setUp(self):
        """Unittest set up."""
        super(DBBasicTests, self).setUp()
        self.db = test.db.DBConnection()

    def test_select(self):
        self.db.select("SELECT * FROM tv_episodes WHERE showid = ? AND location != ''", [0000])


class DBMultiTests(test.AppTestDBCase):
    """Perform multi-threaded test of the database."""

    def setUp(self):
        """Unittest set up."""
        super(DBMultiTests, self).setUp()
        self.db = test.db.DBConnection()

    def select(self):
        """Select from the database."""
        self.db.select("SELECT * FROM tv_episodes WHERE showid = ? AND location != ''", [0000])

    def test_threaded(self):
        """Test multi-threaded selection from the database."""
        for _ in list(range(4)):
            thread = threading.Thread(target=self.select)
            thread.start()
