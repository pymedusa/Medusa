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

import io
import os
import re

from requests.exceptions import RequestException
from six import iterkeys
import tmdbsimple as tmdb
from .. import app, exception_handler, helpers, logger
from ..helper.common import replace_extension
from ..helper.exceptions import ex
from ..indexers.indexer_api import indexerApi
from ..indexers.indexer_config import INDEXER_TMDB, INDEXER_TVDBV2, INDEXER_TVMAZE
from ..indexers.indexer_exceptions import IndexerException, IndexerShowNotFound
from ..metadata import helpers as metadata_helpers
from ..show_name_helpers import allPossibleShowNames

try:
    import xml.etree.cElementTree as etree
except ImportError:
    import xml.etree.ElementTree as etree


# todo: Implement Fanart.tv v3 API


class GenericMetadata(object):
    """
    Base class for all metadata providers. Default behavior is meant to mostly
    follow KODI 12+ metadata standards. Has support for:
    - show metadata file
    - episode metadata file
    - episode thumbnail
    - show fanart
    - show poster
    - show banner
    - season thumbnails (poster)
    - season thumbnails (banner)
    - season all poster
    - season all banner
    """

    def __init__(self, show_metadata=False, episode_metadata=False, fanart=False,
                 poster=False, banner=False, episode_thumbnails=False,
                 season_posters=False, season_banners=False,
                 season_all_poster=False, season_all_banner=False):

        self.name = u"Generic"

        self._ep_nfo_extension = u"nfo"
        self._show_metadata_filename = u"tvshow.nfo"

        self.fanart_name = u"fanart.jpg"
        self.poster_name = u"poster.jpg"
        self.banner_name = u"banner.jpg"

        self.season_all_poster_name = u"season-all-poster.jpg"
        self.season_all_banner_name = u"season-all-banner.jpg"

        self.show_metadata = show_metadata
        self.episode_metadata = episode_metadata
        self.fanart = fanart
        self.poster = poster
        self.banner = banner
        self.episode_thumbnails = episode_thumbnails
        self.season_posters = season_posters
        self.season_banners = season_banners
        self.season_all_poster = season_all_poster
        self.season_all_banner = season_all_banner

        # Reuse indexer api, as it's crazy to hit the api with a full search, for every season search.
        self.indexer_api = None

    def get_config(self):
        config_list = [self.show_metadata, self.episode_metadata, self.fanart, self.poster, self.banner,
                       self.episode_thumbnails, self.season_posters, self.season_banners, self.season_all_poster,
                       self.season_all_banner]
        return u'|'.join([str(int(x)) for x in config_list])

    def get_id(self):
        return GenericMetadata.makeID(self.name)

    @staticmethod
    def makeID(name):
        name_id = re.sub(r"[+]", "plus", name)
        name_id = re.sub(r"[^\w\d_]", "_", name_id).lower()
        return name_id

    def set_config(self, string):
        config_list = [bool(int(x)) for x in string.split('|')]
        self.show_metadata = config_list[0]
        self.episode_metadata = config_list[1]
        self.fanart = config_list[2]
        self.poster = config_list[3]
        self.banner = config_list[4]
        self.episode_thumbnails = config_list[5]
        self.season_posters = config_list[6]
        self.season_banners = config_list[7]
        self.season_all_poster = config_list[8]
        self.season_all_banner = config_list[9]

    @staticmethod
    def _check_exists(location):
        if location:
            result = os.path.isfile(location)
            logger.log(u"Checking if " + location + " exists: " + str(result), logger.DEBUG)
            return result
        return False

    def _has_show_metadata(self, show_obj):
        return self._check_exists(self.get_show_file_path(show_obj))

    def has_episode_metadata(self, ep_obj):
        return self._check_exists(self.get_episode_file_path(ep_obj))

    def _has_fanart(self, show_obj):
        return self._check_exists(self.get_fanart_path(show_obj))

    def _has_poster(self, show_obj):
        return self._check_exists(self.get_poster_path(show_obj))

    def _has_banner(self, show_obj):
        return self._check_exists(self.get_banner_path(show_obj))

    def has_episode_thumb(self, ep_obj):
        return self._check_exists(self.get_episode_thumb_path(ep_obj))

    def _has_season_poster(self, show_obj, season):
        return self._check_exists(self.get_season_poster_path(show_obj, season))

    def _has_season_banner(self, show_obj, season):
        return self._check_exists(self.get_season_banner_path(show_obj, season))

    def _has_season_all_poster(self, show_obj):
        return self._check_exists(self.get_season_all_poster_path(show_obj))

    def _has_season_all_banner(self, show_obj):
        return self._check_exists(self.get_season_all_banner_path(show_obj))

    def get_show_file_path(self, show_obj):
        return os.path.join(show_obj.location, self._show_metadata_filename)

    def get_episode_file_path(self, ep_obj):
        return replace_extension(ep_obj.location, self._ep_nfo_extension)

    def get_fanart_path(self, show_obj):
        return os.path.join(show_obj.location, self.fanart_name)

    def get_poster_path(self, show_obj):
        return os.path.join(show_obj.location, self.poster_name)

    def get_banner_path(self, show_obj):
        return os.path.join(show_obj.location, self.banner_name)

    @staticmethod
    def get_episode_thumb_path(ep_obj):
        """
        Returns the path where the episode thumbnail should be stored.
        ep_obj: a Episode instance for which to create the thumbnail
        """
        if os.path.isfile(ep_obj.location):

            tbn_filename = ep_obj.location.rpartition(".")

            if tbn_filename[0] == "":
                tbn_filename = ep_obj.location + "-thumb.jpg"
            else:
                tbn_filename = tbn_filename[0] + "-thumb.jpg"
        else:
            return None

        return tbn_filename

    @staticmethod
    def get_season_poster_path(show_obj, season):
        """
        Returns the full path to the file for a given season poster.

        show_obj: a Series instance for which to generate the path
        season: a season number to be used for the path. Note that season 0
                means specials.
        """

        # Our specials thumbnail is, well, special
        if season == 0:
            season_poster_filename = 'season-specials'
        else:
            season_poster_filename = 'season' + str(season).zfill(2)

        return os.path.join(show_obj.location, season_poster_filename + '-poster.jpg')

    @staticmethod
    def get_season_banner_path(show_obj, season):
        """
        Returns the full path to the file for a given season banner.

        show_obj: a Series instance for which to generate the path
        season: a season number to be used for the path. Note that season 0
                means specials.
        """

        # Our specials thumbnail is, well, special
        if season == 0:
            season_banner_filename = 'season-specials'
        else:
            season_banner_filename = 'season' + str(season).zfill(2)

        return os.path.join(show_obj.location, season_banner_filename + '-banner.jpg')

    def get_season_all_poster_path(self, show_obj):
        return os.path.join(show_obj.location, self.season_all_poster_name)

    def get_season_all_banner_path(self, show_obj):
        return os.path.join(show_obj.location, self.season_all_banner_name)

    # pylint: disable=unused-argument,no-self-use
    def _show_data(self, show_obj):
        """
        This should be overridden by the implementing class. It should
        provide the content of the show metadata file.
        """
        return None

    # pylint: disable=unused-argument,no-self-use
    def _ep_data(self, ep_obj):
        """
        This should be overridden by the implementing class. It should
        provide the content of the episode metadata file.
        """
        return None

    def create_show_metadata(self, show_obj):
        if self.show_metadata and show_obj and not self._has_show_metadata(show_obj):
            logger.log(u"Metadata provider {metadata_provider} creating show metadata for {show_name}"
                       .format(metadata_provider=self.name, show_name=show_obj.name), logger.DEBUG)
            return self.write_show_file(show_obj)
        return False

    def create_episode_metadata(self, ep_obj):
        if self.episode_metadata and ep_obj and not self.has_episode_metadata(ep_obj):
            logger.log(u"Metadata provider " + self.name + " creating episode metadata for " + ep_obj.pretty_name(),
                       logger.DEBUG)
            return self.write_ep_file(ep_obj)
        return False

    def update_show_indexer_metadata(self, show_obj):
        if self.show_metadata and show_obj and self._has_show_metadata(show_obj):
            logger.log(
                u"Metadata provider " + self.name + " updating show indexer info metadata file for " + show_obj.name,
                logger.DEBUG)

            nfo_file_path = self.get_show_file_path(show_obj)

            try:
                with io.open(nfo_file_path, 'rb') as xmlFileObj:
                    showXML = etree.ElementTree(file=xmlFileObj)

                indexerid = showXML.find('id')

                root = showXML.getroot()
                if indexerid is not None:
                    indexerid.text = str(show_obj.indexerid)
                else:
                    etree.SubElement(root, "id").text = str(show_obj.indexerid)

                # Make it purdy
                helpers.indent_xml(root)

                showXML.write(nfo_file_path, encoding='UTF-8')
                helpers.chmod_as_parent(nfo_file_path)

                return True
            except etree.ParseError as error:
                logger.log('Received an invalid XML for {show}, try again later. Error: {error_msg}'.format
                           (show=show_obj.name, error_msg=error), logger.WARNING)
            except IOError as e:
                logger.log(
                    u"Unable to write file to " + nfo_file_path + " - are you sure the folder is writable? " + ex(e),
                    logger.ERROR)

    def create_fanart(self, show_obj):
        if self.fanart and show_obj and not self._has_fanart(show_obj):
            logger.log(u"Metadata provider " + self.name + " creating fanart for " + show_obj.name, logger.DEBUG)
            return self.save_fanart(show_obj)
        return False

    def create_poster(self, show_obj):
        if self.poster and show_obj and not self._has_poster(show_obj):
            logger.log(u"Metadata provider " + self.name + " creating poster for " + show_obj.name, logger.DEBUG)
            return self.save_poster(show_obj)
        return False

    def create_banner(self, show_obj):
        if self.banner and show_obj and not self._has_banner(show_obj):
            logger.log(u"Metadata provider " + self.name + " creating banner for " + show_obj.name, logger.DEBUG)
            return self.save_banner(show_obj)
        return False

    def create_episode_thumb(self, ep_obj):
        if self.episode_thumbnails and ep_obj and not self.has_episode_thumb(ep_obj):
            logger.log(u"Metadata provider " + self.name + " creating episode thumbnail for " + ep_obj.pretty_name(),
                       logger.DEBUG)
            return self.save_thumbnail(ep_obj)
        return False

    def create_season_posters(self, show_obj):
        if self.season_posters and show_obj:
            result = []
            for season in iterkeys(show_obj.episodes):
                if not self._has_season_poster(show_obj, season):
                    logger.log(u"Metadata provider " + self.name + " creating season posters for " + show_obj.name,
                               logger.DEBUG)
                    result.append(self.save_season_posters(show_obj, season))
            return all(result)
        return False

    def create_season_banners(self, show_obj):
        if self.season_banners and show_obj:
            result = []
            logger.log(u"Metadata provider " + self.name + " creating season banners for " + show_obj.name,
                       logger.DEBUG)
            for season in iterkeys(show_obj.episodes):  # @UnusedVariable
                if not self._has_season_banner(show_obj, season):
                    result += [self.save_season_banners(show_obj, season)]
            return all(result)
        return False

    def create_season_all_poster(self, show_obj):
        if self.season_all_poster and show_obj and not self._has_season_all_poster(show_obj):
            logger.log(u"Metadata provider " + self.name + " creating season all poster for " + show_obj.name,
                       logger.DEBUG)
            return self.save_season_all_poster(show_obj)
        return False

    def create_season_all_banner(self, show_obj):
        if self.season_all_banner and show_obj and not self._has_season_all_banner(show_obj):
            logger.log(u"Metadata provider " + self.name + " creating season all banner for " + show_obj.name,
                       logger.DEBUG)
            return self.save_season_all_banner(show_obj)
        return False

    def _get_episode_thumb_url(self, ep_obj):
        """
        Returns the URL to use for downloading an episode's thumbnail. Uses
        theTVDB.com data.

        ep_obj: a Episode object for which to grab the thumb URL
        """
        all_eps = [ep_obj] + ep_obj.related_episodes

        # validate show
        if not helpers.validate_show(ep_obj.show):
            return None

        # try all included episodes in case some have thumbs and others don't
        for cur_ep in all_eps:
            myEp = helpers.validate_show(cur_ep.show, cur_ep.season, cur_ep.episode)
            if not myEp:
                continue

            thumb_url = getattr(myEp, 'filename', None)
            if thumb_url:
                return thumb_url

        return None

    def write_show_file(self, show_obj):
        """
        Generates and writes show_obj's metadata under the given path to the
        filename given by get_show_file_path()

        show_obj: Series object for which to create the metadata

        path: An absolute or relative path where we should put the file. Note that
                the file name will be the default show_file_name.

        Note that this method expects that _show_data will return an ElementTree
        object. If your _show_data returns data in another format you'll need to
        override this method.
        """

        data = self._show_data(show_obj)

        if not data:
            return False

        nfo_file_path = self.get_show_file_path(show_obj)
        nfo_file_dir = os.path.dirname(nfo_file_path)

        try:
            if not os.path.isdir(nfo_file_dir):
                logger.log(u"Metadata dir didn't exist, creating it at " + nfo_file_dir, logger.DEBUG)
                os.makedirs(nfo_file_dir)
                helpers.chmod_as_parent(nfo_file_dir)

            logger.log(u"Writing show nfo file to " + nfo_file_path, logger.DEBUG)

            nfo_file = io.open(nfo_file_path, 'wb')
            data.write(nfo_file, encoding='UTF-8')
            nfo_file.close()
            helpers.chmod_as_parent(nfo_file_path)
        except IOError as e:
            exception_handler.handle(e, u'Unable to write file to {location}', location=nfo_file_path)
            return False

        return True

    def write_ep_file(self, ep_obj):
        """
        Generates and writes ep_obj's metadata under the given path with the
        given filename root. Uses the episode's name with the extension in
        _ep_nfo_extension.

        ep_obj: Episode object for which to create the metadata

        file_name_path: The file name to use for this metadata. Note that the extension
                will be automatically added based on _ep_nfo_extension. This should
                include an absolute path.

        Note that this method expects that _ep_data will return an ElementTree
        object. If your _ep_data returns data in another format you'll need to
        override this method.
        """

        data = self._ep_data(ep_obj)

        if not data:
            return False

        nfo_file_path = self.get_episode_file_path(ep_obj)
        nfo_file_dir = os.path.dirname(nfo_file_path)

        try:
            if not os.path.isdir(nfo_file_dir):
                logger.log(u"Metadata dir didn't exist, creating it at " + nfo_file_dir, logger.DEBUG)
                os.makedirs(nfo_file_dir)
                helpers.chmod_as_parent(nfo_file_dir)

            logger.log(u"Writing episode nfo file to " + nfo_file_path, logger.DEBUG)
            nfo_file = io.open(nfo_file_path, 'wb')
            data.write(nfo_file, encoding='UTF-8')
            nfo_file.close()
            helpers.chmod_as_parent(nfo_file_path)
        except IOError as e:
            exception_handler.handle(e, u'Unable to write file to {location}', location=nfo_file_path)
            return False

        return True

    def save_thumbnail(self, ep_obj):
        """
        Retrieves a thumbnail and saves it to the correct spot. This method should not need to
        be overridden by implementing classes, changing get_episode_thumb_path and
        _get_episode_thumb_url should suffice.

        ep_obj: a Episode object for which to generate a thumbnail
        """

        file_path = self.get_episode_thumb_path(ep_obj)

        if not file_path:
            logger.log(u"Unable to find a file path to use for this thumbnail, not generating it", logger.DEBUG)
            return False

        thumb_url = self._get_episode_thumb_url(ep_obj)

        # if we can't find one then give up
        if not thumb_url:
            logger.log(u"No thumb is available for this episode, not creating a thumb", logger.DEBUG)
            return False

        thumb_data = metadata_helpers.getShowImage(thumb_url)

        result = self._write_image(thumb_data, file_path)

        if not result:
            return False

        for cur_ep in [ep_obj] + ep_obj.related_episodes:
            cur_ep.hastbn = True

        return True

    def save_fanart(self, show_obj, which=None):
        """
        Downloads a fanart image and saves it to the filename specified by fanart_name
        inside the show's root folder.

        show_obj: a Series object for which to download fanart
        """

        # use the default fanart name
        fanart_path = self.get_fanart_path(show_obj)

        fanart_data = self._retrieve_show_image('fanart', show_obj, which)

        if not fanart_data:
            logger.log(u"No fanart image was retrieved, unable to write fanart", logger.DEBUG)
            return False

        return self._write_image(fanart_data, fanart_path)

    def save_poster(self, show_obj, which=None):
        """
        Downloads a poster image and saves it to the filename specified by poster_name
        inside the show's root folder.

        show_obj: a Series object for which to download a poster
        """

        # use the default poster name
        poster_path = self.get_poster_path(show_obj)

        poster_data = self._retrieve_show_image('poster', show_obj, which)

        if not poster_data:
            logger.log(u"No show poster image was retrieved, unable to write poster", logger.DEBUG)
            return False

        return self._write_image(poster_data, poster_path)

    def save_banner(self, show_obj, which=None):
        """
        Downloads a banner image and saves it to the filename specified by banner_name
        inside the show's root folder.

        show_obj: a Series object for which to download a banner
        """

        # use the default banner name
        banner_path = self.get_banner_path(show_obj)

        banner_data = self._retrieve_show_image('banner', show_obj, which)

        if not banner_data:
            logger.log(u"No show banner image was retrieved, unable to write banner", logger.DEBUG)
            return False

        return self._write_image(banner_data, banner_path)

    def save_season_posters(self, show_obj, season):
        """
        Saves all season posters to disk for the given show.

        show_obj: a Series object for which to save the season thumbs

        Cycles through all seasons and saves the season posters if possible. This
        method should not need to be overridden by implementing classes, changing
        _season_posters_dict and get_season_poster_path should be good enough.
        """

        season_dict = self._season_posters_dict(show_obj, season)
        result = []

        # Returns a nested dictionary of season art with the season
        # number as primary key. It's really overkill but gives the option
        # to present to user via ui to pick down the road.
        for cur_season in season_dict:

            cur_season_art = season_dict[cur_season]

            if not cur_season_art:
                continue

            # Just grab whatever's there for now
            _, season_url = cur_season_art.popitem()  # @UnusedVariable

            season_poster_file_path = self.get_season_poster_path(show_obj, cur_season)

            if not season_poster_file_path:
                logger.log(u"Path for season " + str(cur_season) + " came back blank, skipping this season",
                           logger.DEBUG)
                continue

            seasonData = metadata_helpers.getShowImage(season_url)

            if not seasonData:
                logger.log(u"No season poster data available, skipping this season", logger.DEBUG)
                continue

            result += [self._write_image(seasonData, season_poster_file_path)]

        if result:
            return all(result)
        else:
            return False

    def save_season_banners(self, show_obj, season):
        """
        Saves all season banners to disk for the given show.

        show_obj: a Series object for which to save the season thumbs

        Cycles through all seasons and saves the season banners if possible. This
        method should not need to be overridden by implementing classes, changing
        _season_banners_dict and get_season_banner_path should be good enough.
        """

        season_dict = self._season_banners_dict(show_obj, season)
        result = []

        # Returns a nested dictionary of season art with the season
        # number as primary key. It's really overkill but gives the option
        # to present to user via ui to pick down the road.
        for cur_season in season_dict:

            cur_season_art = season_dict[cur_season]

            if not cur_season_art:
                continue

            # Just grab whatever's there for now
            _, season_url = cur_season_art.popitem()  # @UnusedVariable

            season_banner_file_path = self.get_season_banner_path(show_obj, cur_season)

            if not season_banner_file_path:
                logger.log(u"Path for season " + str(cur_season) + " came back blank, skipping this season",
                           logger.DEBUG)
                continue

            seasonData = metadata_helpers.getShowImage(season_url)

            if not seasonData:
                logger.log(u"No season banner data available, skipping this season", logger.DEBUG)
                continue

            result += [self._write_image(seasonData, season_banner_file_path)]

        if result:
            return all(result)
        else:
            return False

    def save_season_all_poster(self, show_obj, which=None):
        # use the default season all poster name
        poster_path = self.get_season_all_poster_path(show_obj)

        poster_data = self._retrieve_show_image('poster', show_obj, which)

        if not poster_data:
            logger.log(u"No show poster image was retrieved, unable to write season all poster", logger.DEBUG)
            return False

        return self._write_image(poster_data, poster_path)

    def save_season_all_banner(self, show_obj, which=None):
        # use the default season all banner name
        banner_path = self.get_season_all_banner_path(show_obj)

        banner_data = self._retrieve_show_image('banner', show_obj, which)

        if not banner_data:
            logger.log(u"No show banner image was retrieved, unable to write season all banner", logger.DEBUG)
            return False

        return self._write_image(banner_data, banner_path)

    def _write_image(self, image_data, image_path, obj=None):
        """
        Saves the data in image_data to the location image_path. Returns True/False
        to represent success or failure.

        image_data: binary image data to write to file
        image_path: file location to save the image to
        """

        # don't bother overwriting it
        if os.path.isfile(image_path):
            logger.log(u"Image already exists, not downloading", logger.DEBUG)
            return False

        image_dir = os.path.dirname(image_path)

        if not image_data:
            logger.log(u"Unable to retrieve image to save in %s, skipping" % image_path, logger.DEBUG)
            return False

        try:
            if not os.path.isdir(image_dir):
                logger.log(u"Metadata dir didn't exist, creating it at " + image_dir, logger.DEBUG)
                os.makedirs(image_dir)
                helpers.chmod_as_parent(image_dir)

            outFile = io.open(image_path, 'wb')
            outFile.write(image_data)
            outFile.close()
            helpers.chmod_as_parent(image_path)
        except IOError as e:
            exception_handler.handle(e, u'Unable to write image to {location}', location=image_path)
            return False

        return True

    def _retrieve_show_image(self, image_type, show_obj, which=None):
        """
        Gets an image URL from theTVDB.com and TMDB.com, downloads it and returns the data.

        image_type: type of image to retrieve (currently supported: fanart, poster, banner)
        show_obj: a Series object to use when searching for the image
        which: optional, a specific numbered poster to look for

        Returns: the binary image data if available, or else None
        """
        image_url = None

        indexer_show_obj = self._get_show_data(show_obj)

        if image_type not in ('fanart', 'poster', 'banner', 'poster_thumb', 'banner_thumb'):
            logger.log(u"Invalid image type " + str(image_type) + ", couldn't find it in the " + indexerApi(
                show_obj.indexer).name + " object", logger.ERROR)
            return None

        if image_type == 'poster_thumb':
            if getattr(indexer_show_obj, 'poster', None):
                image_url = re.sub('posters', '_cache/posters', indexer_show_obj['poster'])
            if not image_url:
                # Try and get images from TMDB
                image_url = self._retrieve_show_images_from_tmdb(show_obj, image_type)
        elif image_type == 'banner_thumb':
            if getattr(indexer_show_obj, 'banner', None):
                image_url = re.sub('graphical', '_cache/graphical', indexer_show_obj['banner'])
        else:
            if getattr(indexer_show_obj, image_type, None):
                image_url = indexer_show_obj[image_type]
            if not image_url and show_obj.indexer != 4:
                # Try and get images from TMDB
                image_url = self._retrieve_show_images_from_tmdb(show_obj, image_type)

        if image_url:
            image_data = metadata_helpers.getShowImage(image_url, which)
            return image_data

        return None

    def _season_posters_dict(self, show_obj, season):
        """
        Should return a dict like:

        result = {<season number>:
                    {1: '<url 1>', 2: <url 2>, ...},}
        """

        # This holds our resulting dictionary of season art
        result = {}

        indexer_show_obj = self._get_show_data(show_obj)

        # if we have no season banners then just finish
        if not getattr(indexer_show_obj, '_banners', None):
            return result

        if ('season' not in indexer_show_obj['_banners'] or
                'original' not in indexer_show_obj['_banners']['season'] or
                season not in indexer_show_obj['_banners']['season']['original']):
            return result

        # Give us just the normal poster-style season graphics
        season_art_obj = indexer_show_obj['_banners']['season']

        # Returns a nested dictionary of season art with the season
        # number as primary key. It's really overkill but gives the option
        # to present to user via ui to pick down the road.

        # find the correct season in the TVDB object and just copy the dict into our result dict
        for season_art_id in season_art_obj['original'][season].keys():
            if season not in result:
                result[season] = {}
            result[season][season_art_id] = season_art_obj['original'][season][season_art_id]['_bannerpath']

        return result

    def _season_banners_dict(self, show_obj, season):
        """
        Should return a dict like:

        result = {<season number>:
                    {1: '<url 1>', 2: <url 2>, ...},}
        """

        # This holds our resulting dictionary of season art
        result = {}

        indexer_show_obj = self._get_show_data(show_obj)

        # if we have no seasonwide banners then just finish
        if not getattr(indexer_show_obj, '_banners', None):
            return result

        if ('seasonwide' not in indexer_show_obj['_banners'] or
                'original' not in indexer_show_obj['_banners']['season'] or
                season not in indexer_show_obj['_banners']['seasonwide']['original']):
            return result

        # Give us just the normal poster-style season graphics
        season_art_obj = indexer_show_obj['_banners']['seasonwide']

        # Returns a nested dictionary of season art with the season
        # number as primary key. It's really overkill but gives the option
        # to present to user via ui to pick down the road.

        # find the correct season in the TVDB object and just copy the dict into our result dict
        for season_art_id in season_art_obj['original'][season].keys():
            if season not in result:
                result[season] = {}
            result[season][season_art_id] = season_art_obj['original'][season][season_art_id]['_bannerpath']

        return result

    def _get_show_data(self, show_obj):
        """Retrieve show data from the indexer.

        Try to reuse the indexer_api class instance attribute.
        As we are reusing the indexers results, we need to do a full index including actors and images.

        :param show_obj: A TVshow object.
        :return: A re-indexed show object.
        """

        show_id = show_obj.indexerid

        try:
            if not (show_obj.indexer_api and all([show_obj.indexer_api.config['banners_enabled'],
                                                  show_obj.indexer_api.config['actors_enabled']])):
                show_obj.create_indexer(banners=True, actors=True)

            self.indexer_api = show_obj.indexer_api
            my_show = self.indexer_api[int(show_id)]
        except IndexerShowNotFound:
            logger.log(u'Unable to find {indexer} show {id}, skipping it'.format
                       (indexer=indexerApi(show_obj.indexer).name,
                        id=show_id), logger.WARNING)
            return False

        except (IndexerException, RequestException):
            logger.log(u"{indexer} is down, can't use its data to add this show".format
                       (indexer=indexerApi(show_obj.indexer).name), logger.WARNING)
            return False

        # check for title and id
        if not (getattr(my_show, 'seriesname', None) and getattr(my_show, 'id', None)):
            logger.log(u'Incomplete info for {indexer} show {id}, skipping it'.format
                       (indexer=indexerApi(show_obj.indexer).name,
                        id=show_id), logger.WARNING)
            return False

        return my_show

    def retrieveShowMetadata(self, folder):
        """
        Used only when mass adding Existing Shows, using previously generated Show metadata to reduce the need to query TVDB.
        """

        empty_return = (None, None, None)

        metadata_path = os.path.join(folder, self._show_metadata_filename)

        if not os.path.isdir(folder) or not os.path.isfile(metadata_path):
            logger.log(u"Can't load the metadata file from " + metadata_path + ", it doesn't exist", logger.DEBUG)
            return empty_return

        logger.log(u"Loading show info from metadata file in " + folder, logger.DEBUG)

        try:
            with io.open(metadata_path, 'rb') as xmlFileObj:
                showXML = etree.ElementTree(file=xmlFileObj)

            if (showXML.findtext('title') is None or
                    (showXML.findtext('tvdbid') is None and showXML.findtext('id') is None)):
                logger.log(u"Invalid info in tvshow.nfo (missing name or id): %s %s %s"
                           % (showXML.findtext('title'), showXML.findtext('tvdbid'), showXML.findtext('id')),
                           logger.DEBUG)
                return empty_return

            name = showXML.findtext('title')

            if showXML.findtext('tvdbid'):
                indexer_id = int(showXML.findtext('tvdbid'))
            elif showXML.findtext('id'):
                indexer_id = int(showXML.findtext('id'))
            else:
                logger.log(u"Empty <id> or <tvdbid> field in NFO, unable to find a ID", logger.WARNING)
                return empty_return

            if indexer_id is None:
                logger.log(u"Invalid Indexer ID (" + str(indexer_id) + "), not using metadata file", logger.WARNING)
                return empty_return

            indexer = None
            if showXML.findtext('episodeguide/url'):
                epg_url = showXML.findtext('episodeguide/url').lower()
                if str(indexer_id) in epg_url:
                    if 'thetvdb.com' in epg_url:
                        indexer = INDEXER_TVDBV2
                    elif 'tvmaze.com' in epg_url:
                        indexer = INDEXER_TVMAZE
                    elif 'themoviedb.org' in epg_url:
                        indexer = INDEXER_TMDB
                    elif 'tvrage' in epg_url:
                        logger.log(u"Invalid Indexer ID (" + str(
                            indexer_id) + "), not using metadata file because it has TVRage info", logger.WARNING)
                        return empty_return

        except Exception as e:
            logger.log(
                u"There was an error parsing your existing metadata file: '" + metadata_path + "' error: " + ex(e),
                logger.WARNING)
            return empty_return

        return indexer_id, name, indexer

    @staticmethod
    def _retrieve_show_images_from_tmdb(show, img_type):
        types = {'poster': 'poster_path',
                 'banner': None,
                 'fanart': 'backdrop_path',
                 'poster_thumb': 'poster_path',
                 'banner_thumb': None}

        # get TMDB configuration info
        tmdb.API_KEY = app.TMDB_API_KEY
        config = tmdb.Configuration()
        try:
            response = config.info()
        except RequestException as e:
            logger.log('Indexer TMDB is unavailable at this time. Cause: {cause}'.format(cause=e), logger.WARNING)
            return False

        base_url = response['images']['base_url']
        sizes = response['images']['poster_sizes']

        def size_str_to_int(x):
            return float("inf") if x == 'original' else int(x[1:])

        max_size = max(sizes, key=size_str_to_int)

        try:
            search = tmdb.Search()
            for show_name in allPossibleShowNames(show):
                for result in search.collection(query=show_name)['results'] + search.tv(query=show_name)['results']:
                    if types[img_type] and getattr(result, types[img_type]):
                        return "{0}{1}{2}".format(base_url, max_size, result[types[img_type]])

        except Exception:
            pass

        logger.log(u"Could not find any " + img_type + " images on TMDB for " + show.name, logger.INFO)
