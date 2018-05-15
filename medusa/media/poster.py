# coding=utf-8
# This file is part of Medusa.
#

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

from __future__ import unicode_literals

from medusa import image_cache
from medusa.media.generic import GenericMedia


class ShowPoster(GenericMedia):
    """Get the poster of a show."""

    default_media_name = 'poster.png'

    @property
    def img_type(self):
        """Get the image type (normal or thumbnail)."""
        if self.media_format == 'normal':
            return image_cache.POSTER
        elif self.media_format == 'thumb':
            return image_cache.POSTER_THUMB
        else:
            raise ValueError('Invalid media format')
