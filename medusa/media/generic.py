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

from mimetypes import guess_type
from os.path import isfile, join, normpath

from medusa import app, image_cache
from medusa.helper.common import try_int
from medusa.helper.exceptions import MultipleShowObjectsException
from medusa.show.show import Show


class GenericMedia(object):
    """Base class for series media."""

    img_type = None
    default_media_name = ''

    def __init__(self, indexer_id, media_format='normal'):
        """
        Initialize media for a series.

        :param indexer_id: The indexer id of the show
        :param media_format: The format of the media to get. Must be either 'normal' or 'thumb'
        """

        self.indexer_id = try_int(indexer_id, 0)

        if media_format in ('normal', 'thumb'):
            self.media_format = media_format
        else:
            self.media_format = 'normal'

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
            return image_cache.get_path(self.img_type, self.indexer_id)
        else:
            return ''

    @staticmethod
    def get_media_root():
        """Get the root folder containing the media."""
        return join(app.PROG_DIR, 'static')

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
            return Show.find(app.showList, self.indexer_id)
        except MultipleShowObjectsException:
            return None

    @property
    def static_media_path(self):
        """Get the full path to the media."""
        if self.series:
            media_path = self.media_path

            if isfile(media_path):
                return normpath(media_path)

        image_path = join(self.get_media_root(), 'images', self.default_media_name)

        return image_path.replace('\\', '/')
