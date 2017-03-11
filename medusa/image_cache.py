# coding=utf-8
# Author: Nic Wolfe <nic@wolfeden.ca>
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

from __future__ import unicode_literals

import os.path

from . import app, logger
from .helper.exceptions import ShowDirectoryNotFoundException
from .metadata.generic import GenericMetadata


class ImageCache(object):

    BANNER = 1
    POSTER = 2
    BANNER_THUMB = 3
    POSTER_THUMB = 4
    FANART = 5

    def __init__(self):
        pass

    def __del__(self):
        pass

    def _cache_dir(self):
        """Build up the full path to the image cache directory."""
        return os.path.abspath(os.path.join(app.CACHE_DIR, 'images'))

    def _thumbnails_dir(self):
        """Build up the full path to the thumbnails image cache directory."""
        return os.path.abspath(os.path.join(self._cache_dir(), 'thumbnails'))

    def poster_path(self, indexer_id):
        """
        Build up the path to a poster cache for a given Indexer ID.

        :param indexer_id: ID of the show to use in the file name
        :return: a full path to the cached poster file for the given Indexer ID
        """
        poster_file_name = '{0}.poster.jpg'.format(indexer_id)
        return os.path.join(self._cache_dir(), poster_file_name)

    def banner_path(self, indexer_id):
        """
        Build up the path to a banner cache for a given Indexer ID.

        :param indexer_id: ID of the show to use in the file name
        :return: a full path to the cached banner file for the given Indexer ID
        """
        banner_file_name = '{0}.banner.jpg'.format(indexer_id)
        return os.path.join(self._cache_dir(), banner_file_name)

    def fanart_path(self, indexer_id):
        """
        Build up the path to a fanart cache for a given Indexer ID.

        :param indexer_id: ID of the show to use in the file name
        :return: a full path to the cached fanart file for the given Indexer ID
        """
        fanart_file_name = '{0}.fanart.jpg'.format(indexer_id)
        return os.path.join(self._cache_dir(), fanart_file_name)

    def poster_thumb_path(self, indexer_id):
        """
        Build up the path to a poster thumb cache for a given Indexer ID.

        :param indexer_id: ID of the show to use in the file name
        :return: a full path to the cached poster thumb file for the given Indexer ID
        """
        posterthumb_file_name = '{0}.poster.jpg'.format(indexer_id)
        return os.path.join(self._thumbnails_dir(), posterthumb_file_name)

    def banner_thumb_path(self, indexer_id):
        """
        Build up the path to a banner thumb cache for a given Indexer ID.

        :param indexer_id: ID of the show to use in the file name
        :return: a full path to the cached banner thumb file for the given Indexer ID
        """
        bannerthumb_file_name = '{0}.banner.jpg'.format(indexer_id)
        return os.path.join(self._thumbnails_dir(), bannerthumb_file_name)

    def has_poster(self, indexer_id):
        """Return true if a cached poster exists for the given Indexer ID."""
        poster_path = self.poster_path(indexer_id)
        bool_result = os.path.isfile(poster_path)
        logger.log('Checking if file {0} exists: {1}'.format(poster_path, bool_result), logger.DEBUG)
        return bool_result

    def has_banner(self, indexer_id):
        """Return true if a cached banner exists for the given Indexer ID."""
        banner_path = self.banner_path(indexer_id)
        bool_result = os.path.isfile(banner_path)
        logger.log('Checking if file {0} exists: {1}'.format(banner_path, bool_result), logger.DEBUG)
        return bool_result

    def has_fanart(self, indexer_id):
        """Return true if a cached fanart exists for the given Indexer ID."""
        fanart_path = self.fanart_path(indexer_id)
        bool_result = os.path.isfile(fanart_path)
        logger.log('Checking if file {0} exists: {1}'.format(fanart_path, bool_result), logger.DEBUG)
        return bool_result

    def has_poster_thumbnail(self, indexer_id):
        """Return true if a cached poster thumbnail exists for the given Indexer ID."""
        poster_thumb_path = self.poster_thumb_path(indexer_id)
        bool_result = os.path.isfile(poster_thumb_path)
        logger.log('Checking if file {0} exists: {1}'.format(poster_thumb_path, bool_result), logger.DEBUG)
        return bool_result

    def has_banner_thumbnail(self, indexer_id):
        """Return true if a cached banner exists for the given Indexer ID."""
        banner_thumb_path = self.banner_thumb_path(indexer_id)
        bool_result = os.path.isfile(banner_thumb_path)
        logger.log('Checking if file {0} exists: {1}'.format(banner_thumb_path, bool_result), logger.DEBUG)
        return bool_result

    def which_type(self, image_path):
        """
        Analyze the image provided and attempt to determine whether it is a poster or a banner.

        :param image_path: full path to the image
        :return: BANNER, POSTER if it concluded one or the other, or None if the image was neither (or didn't exist)
        """
        from .helpers import get_image_size
        from .helper.common import try_int

        if not os.path.isfile(image_path):
            logger.log("Couldn't check the type of {image_path} because it doesn't exist".format
                       (image_path=image_path), logger.WARNING)
            return

        if try_int(os.path.getsize(image_path)) == 0:
            logger.log('Image has 0 bytes size. Deleting it: {image_path}'.format
                       (image_path=image_path), logger.WARNING)
            try:
                os.remove(image_path)
            except OSError as e:
                logger.log("Could't delete file: {image_path}. Please manually delete it. Error: {error_msg}".format
                           (image_path=image_path, error_msg=e), logger.WARNING)
            return

        image_dimension = get_image_size(image_path)
        if not image_dimension:
            logger.log('Unable to get metadata from {image_path}, not using your existing image'.format
                       (image_path=image_path), logger.DEBUG)
            return

        height, width = image_dimension
        img_ratio = float(width) / float(height)

        # most posters are around 0.68 width/height ratio (eg. 680/1000)
        if 0.55 < img_ratio < 0.8:
            return self.POSTER

        # most banners are around 5.4 width/height ratio (eg. 758/140)
        elif 5 < img_ratio < 6:
            return self.BANNER

        # most fanarts are around 1.77777 width/height ratio (eg. 1280/720 and 1920/1080)
        elif 1.7 < img_ratio < 1.8:
            return self.FANART
        else:
            logger.log('Image has size ratio of {img_ratio}, unknown type'.format(img_ratio=img_ratio), logger.WARNING)
            return

    def _cache_image_from_file(self, image_path, img_type, indexer_id):
        """
        Take the image provided and copy it to the cache folder.

        :param image_path: path to the image we're caching
        :param img_type: BANNER or POSTER or FANART
        :param indexer_id: id of the show this image belongs to
        :return: bool representing success
        """
        from . import helpers
        # generate the path based on the type and the indexer_id
        if img_type == self.POSTER:
            dest_path = self.poster_path(indexer_id)
        elif img_type == self.BANNER:
            dest_path = self.banner_path(indexer_id)
        elif img_type == self.FANART:
            dest_path = self.fanart_path(indexer_id)
        else:
            logger.log('Invalid cache image type: {0}'.format(img_type), logger.ERROR)
            return False

        # make sure the cache folder exists before we try copying to it
        if not os.path.isdir(self._cache_dir()):
            logger.log("Image cache dir doesn't exist, creating it at: {0}".format(self._cache_dir()))
            os.makedirs(self._cache_dir())

        if not os.path.isdir(self._thumbnails_dir()):
            logger.log("Thumbnails cache dir didn't exist, creating it at: {0}".format(self._thumbnails_dir()))
            os.makedirs(self._thumbnails_dir())

        logger.log('Copying from {origin} to {dest}'.format(origin=image_path, dest=dest_path))
        helpers.copy_file(image_path, dest_path)

        return True

    def _cache_image_from_indexer(self, show_obj, img_type):
        """
        Retrieve an image of the type specified from the indexer and save it to the cache folder.

        :param show_obj: Series object that we want to cache an image for
        :param img_type: BANNER or POSTER or FANART
        :return: bool representing success
        """
        # generate the path based on the type and the indexer_id
        if img_type == self.POSTER:
            img_type_name = 'poster'
            dest_path = self.poster_path(show_obj.indexerid)
        elif img_type == self.BANNER:
            img_type_name = 'banner'
            dest_path = self.banner_path(show_obj.indexerid)
        elif img_type == self.POSTER_THUMB:
            img_type_name = 'poster_thumb'
            dest_path = self.poster_thumb_path(show_obj.indexerid)
        elif img_type == self.BANNER_THUMB:
            img_type_name = 'banner_thumb'
            dest_path = self.banner_thumb_path(show_obj.indexerid)
        elif img_type == self.FANART:
            img_type_name = 'fanart'
            dest_path = self.fanart_path(show_obj.indexerid)
        else:
            logger.log('Invalid cache image type: {0}'.format(img_type), logger.ERROR)
            return False

        # retrieve the image from the indexer using the generic metadata class
        # TODO: refactor
        metadata_generator = GenericMetadata()
        img_data = metadata_generator._retrieve_show_image(img_type_name, show_obj)
        result = metadata_generator._write_image(img_data, dest_path)

        return result

    def fill_cache(self, show_obj):
        """
        Cache all images for the given show.

        Copies them from the show dir if possible, or downloads them from indexer if they aren't in the show dir.

        :param show_obj: Series object to cache images for
        """
        logger.log('Checking if we need any cache images for show: {0}'.format(show_obj.name), logger.DEBUG)

        # check if the images are already cached or not
        need_images = {self.POSTER: not self.has_poster(show_obj.indexerid),
                       self.BANNER: not self.has_banner(show_obj.indexerid),
                       self.POSTER_THUMB: not self.has_poster_thumbnail(show_obj.indexerid),
                       self.BANNER_THUMB: not self.has_banner_thumbnail(show_obj.indexerid),
                       self.FANART: not self.has_fanart(show_obj.indexerid)}

        should_continue = None
        for key in need_images:
            if need_images.get(key):
                should_continue = True
                break

        if not should_continue:
            logger.log('No new cache images needed, not retrieving new ones', logger.DEBUG)
            logger.log('Cache check done')
            return

        # check the show dir for poster, banner or fanart images and use them
        if any([need_images[self.POSTER], need_images[self.BANNER], need_images[self.FANART]]):
            try:
                for cur_provider in app.metadata_provider_dict.values():
                    logger.log('Checking if we can use the show image from the {provider} metadata'.format
                               (provider=cur_provider.name), logger.DEBUG)

                    if os.path.isfile(cur_provider.get_poster_path(show_obj)):
                        cur_file_name = os.path.abspath(cur_provider.get_poster_path(show_obj))
                        cur_file_type = self.which_type(cur_file_name)

                        if cur_file_type is None:
                            logger.log('Unable to retrieve image type, not using the image from: {0}'.format
                                       (cur_file_name), logger.WARNING)
                            continue

                        logger.log('Checking if image {0} (type {1}) needs metadata: {2}'.format
                                   (cur_file_name, cur_file_type, need_images[cur_file_type]), logger.DEBUG)

                        if cur_file_type in need_images and need_images[cur_file_type]:
                            logger.log("Found an image in the show dir that doesn't exist in the cache, "
                                       "caching it: {0} (type {1})".format(cur_file_name, cur_file_type), logger.DEBUG)

                            self._cache_image_from_file(cur_file_name, cur_file_type, show_obj.indexerid)
                            need_images[cur_file_type] = False

            except ShowDirectoryNotFoundException:
                logger.log("Unable to search for images in the show dir because it doesn't exist", logger.WARNING)

        # download missing images from indexer
        for cur_image_type in need_images:
            logger.log('Seeing if we still need an image of type {0}: {1}'.format
                       (cur_image_type, need_images[cur_image_type]), logger.DEBUG)

            if cur_image_type in need_images and need_images[cur_image_type]:
                self._cache_image_from_indexer(show_obj, cur_image_type)

        logger.log('Cache check done')
