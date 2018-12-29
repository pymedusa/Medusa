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

"""Test coming episodes."""
from __future__ import unicode_literals

import unittest

from medusa.show.coming_episodes import ComingEpisodes
from six import iteritems


class ComingEpisodesTests(unittest.TestCase):
    """Test comping episodes."""

    def test_get_categories(self):
        categories_list = [
            None, [], ['A', 'B'], [u'A', u'B'], '', 'A|B', u'A|B',
        ]
        results_list = [
            [], [], ['A', 'B'], [u'A', u'B'], [], ['A', 'B'], ['A', 'B']
        ]

        self.assertEqual(
            len(categories_list), len(results_list),
            'Number of parameters (%d) and results (%d) does not match' % (len(categories_list), len(results_list))
        )

        for (index, categories) in enumerate(categories_list):
            self.assertEqual(ComingEpisodes._get_categories(categories), results_list[index])  # pylint: disable=protected-access

    def test_get_categories_map(self):
        categories_list = [
            None, [], ['A', 'B'], [u'A', u'B']
        ]
        results_list = [
            {}, {}, {'A': [], 'B': []}, {u'A': [], u'B': []}
        ]

        self.assertEqual(
            len(categories_list), len(results_list),
            'Number of parameters (%d) and results (%d) does not match' % (len(categories_list), len(results_list))
        )

        for (index, categories) in enumerate(categories_list):
            self.assertEqual(ComingEpisodes._get_categories_map(categories), results_list[index])  # pylint: disable=protected-access

    def test_get_sort(self):
        test_cases = {
            None: 'date',
            '': 'date',
            'wrong': 'date',
            'date': 'date',
            'Date': 'date',
            'network': 'network',
            'NetWork': 'network',
            'show': 'show',
            'Show': 'show',
        }

        unicode_test_cases = {
            u'': 'date',
            u'wrong': 'date',
            u'date': 'date',
            u'Date': 'date',
            u'network': 'network',
            u'NetWork': 'network',
            u'show': 'show',
            u'Show': 'show',
        }

        for tests in test_cases, unicode_test_cases:
            for (sort, result) in iteritems(tests):
                self.assertEqual(ComingEpisodes._get_sort(sort), result)  # pylint: disable=protected-access
