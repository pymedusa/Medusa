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
from __future__ import division
from __future__ import unicode_literals

import logging
import os.path
import warnings

from medusa import app
from medusa.helper.common import try_int
from medusa.helper.exceptions import ShowDirectoryNotFoundException
from medusa.helpers import copy_file, get_image_size
from medusa.logger.adapters.style import BraceAdapter
from medusa.metadata.generic import GenericMetadata

from six import itervalues, viewitems

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())

BANNER = 1
POSTER = 2
BANNER_THUMB = 3
POSTER_THUMB = 4
FANART = 5

IMAGE_TYPES = {
    BANNER: 'banner',
    POSTER: 'poster',
    BANNER_THUMB: 'banner_thumb',
    POSTER_THUMB: 'poster_thumb',
    FANART: 'fanart',
}

# TMDB aspect ratios and image sizes:
#   https://www.themoviedb.org/documentation/editing/images?language=en

# TVDB aspect ratios and image sizes:
#   https://www.thetvdb.com/wiki/index.php/Posters
#   https://www.thetvdb.com/wiki/index.php/Series_Banners
#   https://www.thetvdb.com/wiki/index.php/Fan_Art


# min, median, and max aspect ratios by type
ASPECT_RATIOS = {
    # most banner aspect ratios are ~5.4 (eg. 758/140)
    BANNER: [5, 5.4, 6],
    # most poster aspect ratios are ~0.68 (eg. 680/1000)
    POSTER: [0.55, 0.68, 0.8],
    # most fanart aspect ratios are ~1.777 (eg. 1280/720 and 1920/1080)
    FANART: [1.2, 1.777, 2.5],
}


def _cache_dir(series_obj):
    """Build path to the image cache directory."""
    return os.path.abspath(os.path.join(app.CACHE_DIR, 'images', series_obj.indexer_name))


def _thumbnails_dir(series_obj):
    """Build path to the thumbnail image cache directory."""
    return os.path.abspath(os.path.join(_cache_dir(series_obj), 'thumbnails'))


def get_path(img_type, series_obj):
    """
    Build path to a series cached artwork.

    :param img_type: integer constant representing an image type
    :param series_obj: the series object

    :return: full path and filename for artwork
    """
    image = IMAGE_TYPES[img_type]
    thumbnail = image.endswith('_thumb')
    if thumbnail:
        location = _thumbnails_dir(series_obj)
        image = image[:-len('_thumb')]  # strip `_thumb` from the end
    else:
        location = _cache_dir(series_obj)
    filename = '{series_obj.series_id}.{image}.jpg'.format(
        series_obj=series_obj,
        image=image,
    )
    return os.path.join(location, filename)


def get_artwork(img_type, series_obj):
    """
    Get path to cached artwork for a series.

    :param img_type: integer constant representing an image type
    :param series_obj: the series object

    :return: full path and filename for artwork if it exists
    """
    location = get_path(img_type, series_obj)
    if os.path.isfile(location):
        return location


def which_type(path):
    """
    Analyze image and attempt to determine its type.

    :param path: full path to the image
    :return: artwork type if detected, or None
    """
    if not os.path.isfile(path):
        log.warning('Could not check type, file does not exist: {0}', path)
        return

    if not try_int(os.path.getsize(path)):
        log.warning('Deleting 0 byte image: {0}', path)
        try:
            os.remove(path)
        except OSError as error:
            log.warning(
                'Failed to delete file: {path}. Please delete it manually.'
                ' Error: {msg}', {'path': path, 'msg': error})
            return

    image_dimension = get_image_size(path)
    if not image_dimension:
        log.debug('Skipping image. Unable to get metadata from {0}', path)
        return

    width, height = image_dimension
    if not width or not height:
        log.debug('Skipping image. zero width or height {0}', path)
        return

    aspect_ratio = width / height
    log.debug('Image aspect ratio: {0}', aspect_ratio)

    for img_type in ASPECT_RATIOS:
        min_ratio, median_ratio, max_ratio = ASPECT_RATIOS[img_type]
        if min_ratio < aspect_ratio < max_ratio:
            log.debug('{image} detected based on aspect ratio.',
                      {'image': IMAGE_TYPES[img_type]})
            return img_type
    else:
        log.warning('Aspect ratio ({0}) does not match any known types.',
                    aspect_ratio)
        return


def replace_images(series_obj):
    """
    Replace cached images for a series based on image type.

    :param series_obj: Series object
    """
    remove_images(series_obj)
    fill_cache(series_obj)


def remove_images(series_obj, image_types=None):
    """
    Remove cached images for a series based on image type.

    :param series_obj: Series object
    :param image_types: iterable of integers for image types to remove
        if no image types passed, remove all images
    """
    image_types = image_types or IMAGE_TYPES
    series_name = series_obj.name

    for image_type in image_types:
        cur_path = get_path(image_type, series_obj)

        # see if image exists
        if not os.path.isfile(cur_path):
            continue

        # try to remove image
        try:
            os.remove(cur_path)
        except OSError as error:
            log.error(
                'Could not remove {img} for series {name} from cache'
                ' [{loc}]: {msg}', {
                    'img': IMAGE_TYPES[image_type],
                    'name': series_name,
                    'loc': cur_path,
                    'msg': error,
                }
            )
        else:
            log.info('Removed {img} for series {name}',
                     {'img': IMAGE_TYPES[image_type], 'name': series_name})


def _cache_image_from_file(image_path, img_type, series_obj):
    """
    Take the image provided and copy it to the cache folder.

    :param image_path: path to the image we're caching
    :param img_type: BANNER or POSTER or FANART
    :param series_obj: Series object
    :return: bool representing success
    """
    # generate the path based on the type and the indexer_id
    if img_type in (POSTER, BANNER, FANART):
        location = get_path(img_type, series_obj)
    else:
        type_name = IMAGE_TYPES.get(img_type, img_type)
        log.error('Invalid cache image type: {0}', type_name)
        return

    directories = {
        'image': _cache_dir(series_obj),
        'thumbnail': _thumbnails_dir(series_obj),
    }

    for cache in directories:
        cache_dir = directories[cache]
        if not os.path.isdir(cache_dir):
            log.info('Creating {0} cache directory: {1}', cache, cache_dir)
            os.makedirs(cache_dir)

    log.info('Copying from {origin} to {dest}',
             {'origin': image_path, 'dest': location})

    copy_file(image_path, location)

    return True


def _cache_image_from_indexer(series_obj, img_type):
    """
    Retrieve specified artwork from the indexer and save to the cache folder.

    :param series_obj: Series object that we want to cache an image for
    :param img_type: BANNER or POSTER or FANART
    :return: bool representing success
    """
    # generate the path based on the type and the indexer_id
    try:
        img_type_name = IMAGE_TYPES[img_type]
    except KeyError:
        log.error('Invalid cache image type: {0}', img_type)
        return

    location = get_path(img_type, series_obj)

    # retrieve the image from the indexer using the generic metadata class
    # TODO: refactor
    metadata_generator = GenericMetadata()
    img_data = metadata_generator._retrieve_show_image(img_type_name, series_obj)
    result = metadata_generator._write_image(img_data, location)

    return result


def fill_cache(series_obj):
    """
    Cache artwork for the given show.

    Copy artwork from series directory if possible, or download from indexer.

    :param series_obj: Series object to cache images for
    """
    # get expected paths for artwork
    images = {
        img_type: get_path(img_type, series_obj)
        for img_type in IMAGE_TYPES
    }
    # check if artwork is cached
    needed = {
        img_type: location
        for img_type, location in viewitems(images)
        if not os.path.exists(location)
    }

    if not needed:
        log.debug('No new cache images needed')
        log.info('Cache check completed')
        return

    log.debug('Searching for images for series id {0}', series_obj.series_id)

    # check the show for poster, banner or fanart
    for img_type in BANNER, POSTER, FANART:
        if not needed.get(img_type):
            continue
        try:
            for provider in itervalues(app.metadata_provider_dict):
                log.debug('Checking {provider.name} metadata for {img}',
                          {'provider': provider, 'img': IMAGE_TYPES[img_type]})

                path = provider.get_image_path(series_obj, img_type)
                if os.path.isfile(path):
                    filename = os.path.abspath(path)
                    file_type = which_type(filename)

                    if not file_type:
                        log.warning('Unable to determine image type for {0}',
                                    filename)
                        continue

                    desired = needed.get(file_type)
                    type_name = IMAGE_TYPES[file_type]
                    log.debug(
                        'Wanted {img} {path}: {status}', {
                            'img': type_name,
                            'path': filename,
                            'status': bool(desired)
                        }
                    )

                    if desired:
                        # cache the image
                        _cache_image_from_file(filename, file_type, series_obj)
                        log.debug('Cached {img} from series folder: {path}',
                                  {'img': type_name, 'path': filename})
                        # remove it from the needed image types
                        needed.pop(file_type)

        except ShowDirectoryNotFoundException:
            log.warning('Path does not exist. Unable to search it for images.')

    # download missing images from indexer
    for img_type in needed:
        log.debug('Searching for {img} for series {x}',
                  {'img': IMAGE_TYPES[img_type], 'x': series_obj.series_id})
        _cache_image_from_indexer(series_obj, img_type)

    log.info('Cache check completed')


def banner_path(indexer_id):
    """DEPRECATED: Build path to a series cached artwork. Use `get_path`."""
    warnings.warn('Deprecated use get_path instead', DeprecationWarning)
    return get_path(BANNER, indexer_id)


def banner_thumb_path(indexer_id):
    """DEPRECATED: Build path to a series cached artwork. Use `get_path`."""
    warnings.warn('Deprecated use get_path instead', DeprecationWarning)
    return get_path(BANNER_THUMB, indexer_id)


def fanart_path(indexer_id):
    """DEPRECATED: Build path to a series cached artwork. Use `get_path`."""
    warnings.warn('Deprecated use get_path instead', DeprecationWarning)
    return get_path(FANART, indexer_id)


def poster_path(indexer_id):
    """DEPRECATED: Build path to a series cached artwork. Use `get_path`."""
    warnings.warn('Deprecated use get_path instead', DeprecationWarning)
    return get_path(POSTER, indexer_id)


def poster_thumb_path(indexer_id):
    """DEPRECATED: Build path to a series cached artwork. Use `get_path`."""
    warnings.warn('Deprecated use get_path instead', DeprecationWarning)
    return get_path(POSTER_THUMB, indexer_id)


def has_poster(indexer_id):
    """DEPRECATED: Check if artwork exists for series. Use `get_artwork`."""
    warnings.warn('Deprecated use get_artwork instead', DeprecationWarning)
    return get_artwork(POSTER, indexer_id)


def has_banner(indexer_id):
    """DEPRECATED: Check if artwork exists for series. Use `get_artwork`."""
    warnings.warn('Deprecated use get_artwork instead', DeprecationWarning)
    return get_artwork(BANNER, indexer_id)


def has_fanart(indexer_id):
    """DEPRECATED: Check if artwork exists for series. Use `get_artwork`."""
    warnings.warn('Deprecated use get_artwork instead', DeprecationWarning)
    return get_artwork(FANART, indexer_id)


def has_poster_thumbnail(indexer_id):
    """DEPRECATED: Check if artwork exists for series. Use `get_artwork`."""
    warnings.warn('Deprecated use get_artwork instead', DeprecationWarning)
    return get_artwork(POSTER_THUMB, indexer_id)


def has_banner_thumbnail(indexer_id):
    """DEPRECATED: Check if artwork exists for series. Use `get_artwork`."""
    warnings.warn('Deprecated use get_artwork instead', DeprecationWarning)
    return get_artwork(BANNER_THUMB, indexer_id)
