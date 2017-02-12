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

"""Test shows."""

from __future__ import print_function

import unittest

from medusa import app
from medusa.common import Quality
from medusa.helper.exceptions import MultipleShowObjectsException
from medusa.show.show import Show
from medusa.tv import Series
from six import iteritems


class ShowTests(unittest.TestCase):
    """Test shows."""

    def test_find(self):
        app.QUALITY_DEFAULT = Quality.FULLHDTV

        app.showList = []

        show123 = TestTVShow(0, 123)
        show456 = TestTVShow(0, 456)
        show789 = TestTVShow(0, 789)
        shows = [show123, show456, show789]
        shows_duplicate = shows + shows

        test_cases = {
            (False, None): None,
            (False, ''): None,
            (False, '123'): None,
            (False, 123): None,
            (False, 12.3): None,
            (True, None): None,
            (True, ''): None,
            (True, '123'): None,
            (True, 123): show123,
            (True, 12.3): None,
            (True, 456): show456,
            (True, 789): show789,
        }

        unicode_test_cases = {
            (False, u''): None,
            (False, u'123'): None,
            (True, u''): None,
            (True, u'123'): None,
        }

        for tests in test_cases, unicode_test_cases:
            for ((use_shows, indexer_id), result) in iteritems(tests):
                if use_shows:
                    self.assertEqual(Show.find(shows, indexer_id), result)
                else:
                    self.assertEqual(Show.find(None, indexer_id), result)

        with self.assertRaises(MultipleShowObjectsException):
            Show.find(shows_duplicate, 456)

    def test_validate_indexer_id(self):
        app.QUALITY_DEFAULT = Quality.FULLHDTV

        app.showList = []

        show123 = TestTVShow(0, 123)
        show456 = TestTVShow(0, 456)
        show789 = TestTVShow(0, 789)
        app.showList = [
            show123,
            show456,
            show789,
        ]

        invalid_show_id = ('Invalid show ID', None)

        indexer_id_list = [
            None, '', u'', '123', u'123', '456', u'456', '789', u'789', 123, 456, 789, ['123', '456'], [u'123', u'456'],
            [123, 456]
        ]
        results_list = [
            invalid_show_id, invalid_show_id, invalid_show_id, (None, show123), (None, show123), (None, show456),
            (None, show456), (None, show789), (None, show789), (None, show123), (None, show456), (None, show789),
            invalid_show_id, invalid_show_id, invalid_show_id
        ]

        self.assertEqual(
            len(indexer_id_list), len(results_list),
            'Number of parameters (%d) and results (%d) does not match' % (len(indexer_id_list), len(results_list))
        )

        for (index, indexer_id) in enumerate(indexer_id_list):
            self.assertEqual(Show._validate_indexer_id(indexer_id), results_list[index])  # pylint: disable=protected-access


class TestTVShow(Series):
    """A test `Series` object that does not need DB access."""

    def __init__(self, indexer, indexer_id):
        super(TestTVShow, self).__init__(indexer, indexer_id)

    def _load_from_db(self):
        """Override Series._load_from_db to avoid DB access during testing."""
        pass
