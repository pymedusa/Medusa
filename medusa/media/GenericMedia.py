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

from abc import abstractmethod
from mimetypes import guess_type
from os.path import isfile, join, normpath

import medusa as app
from ..helper.common import try_int
from ..helper.exceptions import MultipleShowObjectsException
from ..show.Show import Show


class GenericMedia(object):
    def __init__(self, indexer_id, media_format='normal'):
        """
        :param indexer_id: The indexer id of the show
        :param media_format: The format of the media to get. Must be either 'normal' or 'thumb'
        """

        self.indexer_id = try_int(indexer_id, 0)

        if media_format in ('normal', 'thumb'):
            self.media_format = media_format
        else:
            self.media_format = 'normal'

    @abstractmethod
    def get_default_media_name(self):
        """
        :return: The name of the file to use as a fallback if the show media file is missing
        """

        return ''

    def get_media(self):
        """
        :return: The content of the desired media file
        """

        static_media_path = self.get_static_media_path()

        if isfile(static_media_path):
            with open(static_media_path, 'rb') as content:
                return content.read()

        return None

    @abstractmethod
    def get_media_path(self):
        """
        :return: The path to the media related to ``self.indexer_id``
        """

        return ''

    @staticmethod
    def get_media_root():
        """
        :return: The root folder containing the media
        """

        return join(app.PROG_DIR, 'static')

    def get_media_type(self):
        """
        :return: The mime type of the current media
        """

        static_media_path = self.get_static_media_path()

        if isfile(static_media_path):
            return guess_type(static_media_path)[0]

        return ''

    def get_show(self):
        """
        :return: The show object associated with ``self.indexer_id`` or ``None``
        """

        try:
            return Show.find(app.showList, self.indexer_id)
        except MultipleShowObjectsException:
            return None

    def get_static_media_path(self):
        """
        :return: The full path to the media
        """

        if self.get_show():
            media_path = self.get_media_path()

            if isfile(media_path):
                return normpath(media_path)

        image_path = join(self.get_media_root(), 'images', self.get_default_media_name())

        return image_path.replace('\\', '/')
