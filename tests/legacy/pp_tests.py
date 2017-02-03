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
"""PP Tests."""

from __future__ import print_function

import unittest

from medusa import app
from medusa.name_cache import addNameToCache
from medusa.post_processor import PostProcessor
from medusa.tv import Episode, Series
from . import test_lib as test


class PPInitTests(unittest.TestCase):
    """Init tests."""

    def setUp(self):
        """Set up tests."""
        self.post_processor = PostProcessor(test.FILE_PATH)

    def test_init_file_name(self):
        self.assertEqual(self.post_processor.file_name, test.FILENAME)

    def test_init_folder_name(self):
        self.assertEqual(self.post_processor.rel_path, test.FILE_PATH)


class PPBasicTests(test.AppTestDBCase):
    """Basic tests."""

    def test_process(self):
        show = Series(1, 3)
        show.name = test.SHOW_NAME
        show.location = test.SHOW_DIR
        show.save_to_db()

        app.showList = [show]
        episode = Episode(show, test.SEASON, test.EPISODE)
        episode.name = "some episode name"
        episode.save_to_db()

        addNameToCache('show name', 3)
        app.PROCESS_METHOD = 'move'

        post_processor = PostProcessor(test.FILE_PATH)
        self.assertTrue(post_processor.process())
