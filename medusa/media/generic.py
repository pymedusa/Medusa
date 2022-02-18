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

from builtins import object
from mimetypes import guess_type
from os.path import isfile, join, normpath

from medusa import app, image_cache
from medusa.helper.exceptions import MultipleShowObjectsException


class GenericMedia(object):
    """Base class for series media."""

    img_type = None
    default_media_name = ''

    def __init__(self, series_obj, media_format='normal', fallback=True):
        """
        Initialize media for a series.

        :param series_obj: The series object.
        :param media_format: The format of the media to get. Must be either 'normal' or 'thumb'
        :param fallback: Fallback to the default media if requested media doesn't exist
        """

        self.series_obj = series_obj
        self.series_id = series_obj.series_id

        if media_format in ('normal', 'thumb'):
            self.media_format = media_format
        else:
            self.media_format = 'normal'

        self.fallback = fallback

    @property
    def indexerid(self):
        return self.series_id

    @indexerid.setter
    def indexerid(self, value):
        self.series_id = value

    @property
    def media(self):
        """Get the contents of the desired media file."""

        static_media_path = self.static_media_path

        if isfile(static_media_path):
            with open(static_media_path, 'rb') as content:
                return content.read()

        return None

    @property
    def media_path(self):
        """Get the relative path to the media."""
        if self.series:
            return image_cache.get_path(self.img_type, self.series_obj)
        else:
            return ''

    @staticmethod
    def get_media_root():
        """Get the root folder containing the media."""
        return join(app.THEME_DATA_ROOT, 'assets')

    @property
    def media_type(self):
        """Get the mime type of the current media."""
        static_media_path = self.static_media_path

        if isfile(static_media_path):
            return guess_type(static_media_path)[0]

        return ''

    @property
    def series(self):
        """Find the series by indexer id."""
        try:
            return self.series_obj
        except MultipleShowObjectsException:
            return None

    @property
    def static_media_path(self):
        """Get the full path to the media."""
        if self.series:
            media_path = self.media_path

            if isfile(media_path):
                return normpath(media_path)
            elif not self.fallback:
                return ''

        image_path = join(self.get_media_root(), 'img', self.default_media_name)

        return image_path.replace('\\', '/')
