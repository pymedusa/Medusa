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

"""Test GenericMedia."""
from __future__ import unicode_literals

import os
import unittest

from medusa import app
from medusa.media.generic import GenericMedia
from medusa.tv import Series


class GenericMediaTests(unittest.TestCase):
    """Test GenericMedia."""

    def test_default_media_name(self):
        series_obj = Series(1, 70726)
        self.assertEqual(GenericMedia(series_obj, '').default_media_name, '')

    def test_media_root(self):
        app.PROG_DIR = os.path.join('some', 'path', 'to', 'application')

        self.assertEqual(GenericMedia.get_media_root(), os.path.join('some', 'path', 'to', 'application', 'static'))
