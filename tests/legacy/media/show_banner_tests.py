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

"""Test ShowBanner."""

from __future__ import print_function

from medusa.media.ShowBanner import ShowBanner
from .generic_media_tests import GenericMediaTests


class ShowBannerTests(GenericMediaTests):
    """Test ShowBanner."""

    def test_get_default_media_name(self):
        self.assertEqual(ShowBanner(0, '').get_default_media_name(), 'banner.png')
