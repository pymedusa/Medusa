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

"""Test tv."""

from __future__ import print_function

from medusa import app
from medusa.tv import Episode, Series
from . import test_lib as test


class TVShowTests(test.AppTestDBCase):
    """Test tv shows."""

    def setUp(self):
        """Set up tests."""
        super(TVShowTests, self).setUp()
        app.showList = []

    def test_init_indexerid(self):
        show = Series(1, 1, "en")
        self.assertEqual(show.indexerid, 1)

    def test_change_indexerid(self):
        show = Series(1, 1, "en")
        show.name = "show name"
        show.network = "cbs"
        show.genre = "crime"
        show.runtime = 40
        show.status = "Ended"
        show.default_ep_status = "5"
        show.airs = "monday"
        show.start_year = 1987

        show.save_to_db()
        show._load_from_db()

        show.indexerid = 2
        show.save_to_db()
        show._load_from_db()

        self.assertEqual(show.indexerid, 2)

    def test_set_name(self):
        show = Series(1, 1, "en")
        show.name = "newName"
        show.save_to_db()
        show._load_from_db()
        self.assertEqual(show.name, "newName")


class TVEpisodeTests(test.AppTestDBCase):
    """Test tv episode."""

    def setUp(self):
        """Set up."""
        super(TVEpisodeTests, self).setUp()
        app.showList = []

    def test_init_empty_db(self):
        show = Series(1, 1, "en")
        episode = Episode(show, 1, 1)
        episode.name = "asdasdasdajkaj"
        episode.save_to_db()
        episode.load_from_db(1, 1)
        self.assertEqual(episode.name, "asdasdasdajkaj")


class TVTests(test.AppTestDBCase):
    """Test tv."""

    def setUp(self):
        """Set up."""
        super(TVTests, self).setUp()
        app.showList = []

    @staticmethod
    def test_get_episode():
        show = Series(1, 1, "en")
        show.name = "show name"
        show.network = "cbs"
        show.genre = "crime"
        show.runtime = 40
        show.status = "Ended"
        show.default_ep_status = "5"
        show.airs = "monday"
        show.start_year = 1987
        show.save_to_db()
        app.showList = [show]
        # TODO: implement
