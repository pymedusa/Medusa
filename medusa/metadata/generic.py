# coding=utf-8

from __future__ import unicode_literals

import errno
import io
import logging
import os
import re
from builtins import object
from builtins import str

from medusa import app, exception_handler, helpers
from medusa.helper.common import replace_extension
from medusa.helper.exceptions import ex
from medusa.helper.metadata import get_image
from medusa.indexers.config import INDEXER_TMDB, INDEXER_TVDBV2, INDEXER_TVMAZE
from medusa.indexers.exceptions import (IndexerEpisodeNotFound, IndexerException,
                                        IndexerSeasonNotFound, IndexerShowNotFound)
from medusa.logger.adapters.style import BraceAdapter

from requests.exceptions import RequestException

from six import iterkeys

import tmdbsimple as tmdb

try:
    import xml.etree.cElementTree as etree
except ImportError:
    import xml.etree.ElementTree as etree

# todo: Implement Fanart.tv v3 API

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())

BANNER = 1
POSTER = 2
BANNER_THUMB = 3
POSTER_THUMB = 4
FANART = 5


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

        self.name = u'Generic'
        self._ep_nfo_extension = u'nfo'
        self._show_metadata_filename = u'tvshow.nfo'
        self.fanart_name = u'fanart.jpg'
        self.poster_name = u'poster.jpg'
        self.banner_name = u'banner.jpg'
        self.season_all_poster_name = u'season-all-poster.jpg'
        self.season_all_banner_name = u'season-all-banner.jpg'
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

        # Web UI metadata template (override when subclassing)
        self.eg_show_metadata = '<i>not supported</i>'
        self.eg_episode_metadata = '<i>not supported</i>'
        self.eg_fanart = '<i>not supported</i>'
        self.eg_poster = '<i>not supported</i>'
        self.eg_banner = '<i>not supported</i>'
        self.eg_episode_thumbnails = '<i>not supported</i>'
        self.eg_season_posters = '<i>not supported</i>'
        self.eg_season_banners = '<i>not supported</i>'
        self.eg_season_all_poster = '<i>not supported</i>'
        self.eg_season_all_banner = '<i>not supported</i>'

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
        name_id = re.sub(r'[+]', 'plus', name)
        name_id = re.sub(r'[^\w\d_]', '_', name_id).lower()
        return name_id

    def set_config(self, provider_options):
        config_list = [bool(int(x)) for x in provider_options]
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
            log.debug(u'Checking if {location} exists: {result}',
                      {u'location': location, u'result': result})
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
        return os.path.join(show_obj.validate_location, self._show_metadata_filename)

    def get_episode_file_path(self, ep_obj):
        return replace_extension(ep_obj.location, self._ep_nfo_extension)

    def get_fanart_path(self, show_obj):
        return os.path.join(show_obj.validate_location, self.fanart_name)

    def get_poster_path(self, show_obj):
        return os.path.join(show_obj.validate_location, self.poster_name)

    def get_banner_path(self, show_obj):
        return os.path.join(show_obj.validate_location, self.banner_name)

    def get_image_path(self, show_obj, image_type):
        """Based on the image_type (banner, poster, fanart) call the correct method, and return the path."""
        banner_path = {
            BANNER: self.get_banner_path,
            POSTER: self.get_poster_path,
            FANART: self.get_fanart_path
        }
        if banner_path.get(image_type):
            return banner_path[image_type](show_obj)

    @staticmethod
    def get_episode_thumb_path(ep_obj):
        """
        Returns the path where the episode thumbnail should be stored.

        ep_obj: a Episode instance for which to create the thumbnail
        """
        if os.path.isfile(ep_obj.location):

            tbn_filename = ep_obj.location.rpartition('.')

            if tbn_filename[0] == '':
                tbn_filename = ep_obj.location + '-thumb.jpg'
            else:
                tbn_filename = tbn_filename[0] + '-thumb.jpg'
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
            season_poster_filename = u'season-specials'
        else:
            season_poster_filename = u'season' + str(season).zfill(2)

        return os.path.join(show_obj.validate_location, season_poster_filename + u'-poster.jpg')

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
            season_banner_filename = u'season-specials'
        else:
            season_banner_filename = u'season' + str(season).zfill(2)

        return os.path.join(show_obj.validate_location, season_banner_filename + u'-banner.jpg')

    def get_season_all_poster_path(self, show_obj):
        return os.path.join(show_obj.validate_location, self.season_all_poster_name)

    def get_season_all_banner_path(self, show_obj):
        return os.path.join(show_obj.validate_location, self.season_all_banner_name)

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
            log.debug(
                u'Metadata provider {name} creating series metadata for {series}',
                {u'name': self.name, u'series': show_obj.name}
            )
            return self.write_show_file(show_obj)
        return False

    def create_episode_metadata(self, ep_obj):
        if self.episode_metadata and ep_obj and not self.has_episode_metadata(ep_obj):
            log.debug(
                u'Metadata provider {name} creating episode metadata for {episode}',
                {u'name': self.name, u'episode': ep_obj.pretty_name()}
            )
            return self.write_ep_file(ep_obj)
        return False

    def update_show_indexer_metadata(self, show_obj):
        if self.show_metadata and show_obj and self._has_show_metadata(show_obj):
            log.debug(
                u'Metadata provider {name} updating series indexer info metadata file for {series}',
                {u'name': self.name, u'series': show_obj.name}
            )

            nfo_file_path = self.get_show_file_path(show_obj)

            try:
                with io.open(nfo_file_path, u'rb') as xmlFileObj:
                    showXML = etree.ElementTree(file=xmlFileObj)

                indexerid = showXML.find(u'id')

                root = showXML.getroot()
                if indexerid is not None:
                    indexerid.text = str(show_obj.indexerid)
                else:
                    etree.SubElement(root, u'id').text = str(show_obj.indexerid)

                # Make it purdy
                helpers.indent_xml(root)

                showXML.write(nfo_file_path, encoding=u'UTF-8')
                helpers.chmod_as_parent(nfo_file_path)

                return True
            except etree.ParseError as error:
                log.warning(
                    u'Received an invalid XML for {series}, try again later. Error: {error}',
                    {u'series': show_obj.name, u'error': error}
                )
            except IOError as error:
                if error.errno == errno.EACCES:
                    log.warning(
                        u'Unable to write metadata file to {location} - verify that the path is writeable',
                        {u'location': nfo_file_path}
                    )
                else:
                    log.error(
                        u'Unable to write metadata file to {location}. Error: {error!r}',
                        {u'location': nfo_file_path, u'error': error}
                    )

    def create_fanart(self, show_obj):
        if self.fanart and show_obj and not self._has_fanart(show_obj):
            log.debug(
                u'Metadata provider {name} creating fanart for {series}',
                {u'name': self.name, u'series': show_obj.name}
            )
            return self.save_fanart(show_obj)
        return False

    def create_poster(self, show_obj):
        if self.poster and show_obj and not self._has_poster(show_obj):
            log.debug(
                u'Metadata provider {name} creating poster for {series}',
                {u'name': self.name, u'series': show_obj.name}
            )
            return self.save_poster(show_obj)
        return False

    def create_banner(self, show_obj):
        if self.banner and show_obj and not self._has_banner(show_obj):
            log.debug(
                u'Metadata provider {name} creating banner for {series}',
                {u'name': self.name, u'series': show_obj.name}
            )
            return self.save_banner(show_obj)
        return False

    def create_episode_thumb(self, ep_obj):
        if self.episode_thumbnails and ep_obj and not self.has_episode_thumb(ep_obj):
            log.debug(
                u'Metadata provider {name} creating episode thumbnail for {episode}',
                {u'name': self.name, u'episode': ep_obj.pretty_name()}
            )
            if self.indexer_api:
                ep_obj.set_indexer_data(season=ep_obj.season, indexer_api=self.indexer_api)
            return self.save_thumbnail(ep_obj)
        return False

    def create_season_posters(self, show_obj):
        if self.season_posters and show_obj:
            result = []
            for season in iterkeys(show_obj.episodes):
                if not self._has_season_poster(show_obj, season):
                    log.debug(
                        u'Metadata provider {name} creating season posters for {series}',
                        {u'name': self.name, u'series': show_obj.name}
                    )
                    result.append(self.save_season_posters(show_obj, season))
            return all(result)
        return False

    def create_season_banners(self, show_obj):
        if self.season_banners and show_obj:
            result = []
            log.debug(
                u'Metadata provider {name} creating season banners for {series}',
                {u'name': self.name, u'series': show_obj.name}
            )
            for season in iterkeys(show_obj.episodes):  # @UnusedVariable
                if not self._has_season_banner(show_obj, season):
                    result += [self.save_season_banners(show_obj, season)]
            return all(result)
        return False

    def create_season_all_poster(self, show_obj):
        if self.season_all_poster and show_obj and not self._has_season_all_poster(show_obj):
            log.debug(
                u'Metadata provider {name} creating season all poster for {series}',
                {u'name': self.name, u'series': show_obj.name}
            )
            return self.save_season_all_poster(show_obj)
        return False

    def create_season_all_banner(self, show_obj):
        if self.season_all_banner and show_obj and not self._has_season_all_banner(show_obj):
            log.debug(
                u'Metadata provider {name} creating season all banner for {series}',
                {u'name': self.name, u'series': show_obj.name}
            )
            return self.save_season_all_banner(show_obj)
        return False

    def _get_episode_thumb_url(self, indexer_series, episode):
        """
        Returns the URL to use for downloading an episode's thumbnail.

        :param indexer_series: Indexer series object of the episode
        :param episode: Episode object for which to grab the thumbnail URL
        """
        episodes = [episode] + episode.related_episodes

        for ep in episodes:

            try:
                indexer_episode = indexer_series[ep.season][ep.episode]
            except (IndexerEpisodeNotFound, IndexerSeasonNotFound) as error:
                log.debug(u'Unable to find season or episode. Reason: {0!r}', error)
                continue

            thumb_url = getattr(indexer_episode, 'filename', None)
            if thumb_url:
                return thumb_url

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
                log.debug(u'Metadata directory missing, creating it at {location}',
                          {u'location': nfo_file_dir})
                os.makedirs(nfo_file_dir)
                helpers.chmod_as_parent(nfo_file_dir)

            log.debug(u'Writing show nfo file to {location}',
                      {u'location': nfo_file_path})

            nfo_file = io.open(nfo_file_path, u'wb')
            data.write(nfo_file, encoding=u'UTF-8')
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

        if not (nfo_file_path and nfo_file_dir):
            log.debug(u'Unable to write episode nfo file because episode location is missing.')
            return False

        try:
            if not os.path.isdir(nfo_file_dir):
                log.debug(u'Metadata directory missing, creating it at {location}',
                          {u'location': nfo_file_dir})
                os.makedirs(nfo_file_dir)
                helpers.chmod_as_parent(nfo_file_dir)

            log.debug(u'Writing episode nfo file to {location}',
                      {u'location': nfo_file_path})
            nfo_file = io.open(nfo_file_path, u'wb')
            data.write(nfo_file, encoding=u'UTF-8')
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

        ep_obj: Episode object for which to generate a thumbnail
        """
        thumb_path = self.get_episode_thumb_path(ep_obj)
        if not thumb_path:
            log.debug(u'Unable to find a file path to use for this thumbnail, not generating it')
            return False

        thumb_data = self._retrieve_show_image(u'thumbnail', ep_obj.series, ep_obj)
        if not thumb_data:
            log.debug(u'No thumb is available for this episode, not creating a thumbnail')
            return False

        result = self._write_image(thumb_data, thumb_path)
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

        fanart_data = self._retrieve_show_image(u'fanart', show_obj, which=which)

        if not fanart_data:
            log.debug(u'No fanart image was retrieved, unable to write fanart')
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

        poster_data = self._retrieve_show_image(u'poster', show_obj, which=which)

        if not poster_data:
            log.debug(u'No show poster image was retrieved, unable to write poster')
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

        banner_data = self._retrieve_show_image(u'banner', show_obj, which=which)

        if not banner_data:
            log.debug(u'No show banner image was retrieved, unable to write banner')
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
                log.debug(
                    u'Path for season {number} came back blank, skipping this season',
                    {u'number': cur_season}
                )
                continue

            seasonData = get_image(season_url)

            if not seasonData:
                log.debug(u'No season poster data available, skipping this season')
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
                log.debug(
                    u'Path for season {number} came back blank, skipping this season',
                    {u'number': cur_season}
                )
                continue

            seasonData = get_image(season_url)

            if not seasonData:
                log.debug(u'No season banner data available, skipping this season')
                continue

            result += [self._write_image(seasonData, season_banner_file_path)]

        if result:
            return all(result)
        else:
            return False

    def save_season_all_poster(self, show_obj, which=None):
        # use the default season all poster name
        poster_path = self.get_season_all_poster_path(show_obj)

        poster_data = self._retrieve_show_image(u'poster', show_obj, which=which)

        if not poster_data:
            log.debug(u'No show poster image was retrieved, unable to write season all poster')
            return False

        return self._write_image(poster_data, poster_path)

    def save_season_all_banner(self, show_obj, which=None):
        # use the default season all banner name
        banner_path = self.get_season_all_banner_path(show_obj)

        banner_data = self._retrieve_show_image(u'banner', show_obj, which=which)

        if not banner_data:
            log.debug(u'No show banner image was retrieved, unable to write season all banner')
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
            log.debug(u'Image already exists, not downloading')
            return False

        image_dir = os.path.dirname(image_path)

        if not image_data:
            log.debug(u'Unable to retrieve image to save in {location}, skipping',
                      {u'location': image_path})
            return False

        try:
            if not os.path.isdir(image_dir):
                log.debug(u'Metadata directory missing, creating it at {location}',
                          {u'location': image_path})
                os.makedirs(image_dir)
                helpers.chmod_as_parent(image_dir)

            outFile = io.open(image_path, u'wb')
            outFile.write(image_data)
            outFile.close()
            helpers.chmod_as_parent(image_path)
        except IOError as e:
            exception_handler.handle(e, u'Unable to write image to {location}', location=image_path)
            return False

        return True

    def _retrieve_show_image(self, image_type, show_obj, episode=None, which=None):
        """
        Get an image URL from theTVDB.com and TMDB.com, download it and returns the data.

        :param image_type: type of image to retrieve (currently supported: fanart, poster, banner)
        :param show_obj: a Series object to use when searching for the image
        :param episode: Episode object (only needed for episode thumbnails)
        :param which: optional, a specific numbered poster to look for
        :return: the binary image data if available, or else None
        """
        image_url = None

        indexer_show_obj = self._get_show_data(show_obj)
        if not indexer_show_obj:
            return None

        if image_type not in (u'fanart', u'poster', u'banner', u'thumbnail', u'poster_thumb', u'banner_thumb'):
            log.error(
                u'Invalid {image}, unable to find it in the {indexer}',
                {u'image': image_type, u'indexer': show_obj.indexer_name}
            )
            return None

        if image_type == u'thumbnail' and episode:
            image_url = self._get_episode_thumb_url(indexer_show_obj, episode)

        elif image_type == u'poster_thumb':
            if getattr(indexer_show_obj, u'poster', None):
                if show_obj.indexer == INDEXER_TVDBV2:
                    image_url = indexer_show_obj[u'poster'].replace('.jpg', '_t.jpg')
                else:
                    image_url = re.sub(u'posters', u'_cache/posters', indexer_show_obj[u'poster'])

            if not image_url:
                # Try and get images from TMDB
                image_url = self._retrieve_show_images_from_tmdb(show_obj, image_type)

        elif image_type == u'banner_thumb':
            if getattr(indexer_show_obj, u'banner', None):
                if show_obj.indexer == INDEXER_TVDBV2:
                    image_url = indexer_show_obj[u'banner'].replace('.jpg', '_t.jpg')
                else:
                    image_url = re.sub(u'graphical', u'_cache/graphical', indexer_show_obj[u'banner'])
        else:
            if getattr(indexer_show_obj, image_type, None):
                image_url = indexer_show_obj[image_type]

            if not image_url and show_obj.indexer != INDEXER_TMDB:
                # Try and get images from TMDB
                image_url = self._retrieve_show_images_from_tmdb(show_obj, image_type)

        if image_url:
            image_data = get_image(image_url, which)
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
        if not getattr(indexer_show_obj, u'_banners', None):
            return result

        if (u'season' not in indexer_show_obj[u'_banners'] or
                u'original' not in indexer_show_obj[u'_banners'][u'season'] or
                season not in indexer_show_obj[u'_banners'][u'season'][u'original']):
            return result

        # Give us just the normal poster-style season graphics
        season_art_obj = indexer_show_obj[u'_banners'][u'season']

        # Returns a nested dictionary of season art with the season
        # number as primary key. It's really overkill but gives the option
        # to present to user via ui to pick down the road.

        # find the correct season in the TVDB object and just copy the dict into our result dict
        for season_art_id in season_art_obj[u'original'][season]:
            if season not in result:
                result[season] = {}
            result[season][season_art_id] = season_art_obj[u'original'][season][season_art_id][u'_bannerpath']

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
        if not getattr(indexer_show_obj, u'_banners', None):
            return result

        if (u'seasonwide' not in indexer_show_obj[u'_banners'] or
                u'original' not in indexer_show_obj[u'_banners'][u'seasonwide'] or
                season not in indexer_show_obj[u'_banners'][u'seasonwide'][u'original']):
            return result

        # Give us just the normal poster-style season graphics
        season_art_obj = indexer_show_obj[u'_banners'][u'seasonwide']

        # Returns a nested dictionary of season art with the season
        # number as primary key. It's really overkill but gives the option
        # to present to user via ui to pick down the road.

        # find the correct season in the TVDB object and just copy the dict into our result dict
        for season_art_id in season_art_obj[u'original'][season]:
            if season not in result:
                result[season] = {}
            result[season][season_art_id] = season_art_obj[u'original'][season][season_art_id][u'_bannerpath']

        return result

    def _get_show_data(self, series_obj):
        """
        Retrieve show data from the indexer.

        Try to reuse the indexer_api class instance attribute.
        As we are reusing the indexers results, we need to do a full index including actors and images.

        :param series_obj: A TVshow object.
        :return: A re-indexed show object.
        """
        series_id = series_obj.series_id

        try:
            if not (series_obj.indexer_api and all([series_obj.indexer_api.config[u'banners_enabled'],
                                                    series_obj.indexer_api.config[u'actors_enabled']])):
                series_obj.create_indexer(banners=True, actors=True)

            self.indexer_api = series_obj.indexer_api
            my_show = self.indexer_api[int(series_id)]
        except IndexerShowNotFound:
            log.warning(
                u'Unable to find {indexer} show {id}, skipping it',
                {u'indexer': series_obj.indexer_name, u'id': series_id}
            )
            return False

        except (IndexerException, RequestException):
            log.warning(
                u'{indexer} is down, cannot use its data to add this show',
                {u'indexer': series_obj.indexer_name}
            )
            return False

        # check for title and id
        if not (getattr(my_show, u'seriesname', None) and getattr(my_show, u'id', None)):
            log.warning(
                u'Incomplete info for {indexer} show {id}, skipping it',
                {u'indexer': series_obj.indexer_name, u'id': series_id}
            )
            return False

        return my_show

    def retrieveShowMetadata(self, folder):
        """
        Used only when mass adding Existing Shows, using previously generated
        Show metadata to reduce the need to query TVDB.
        """
        empty_return = (None, None, None)

        metadata_path = os.path.join(folder, self._show_metadata_filename)

        if not os.path.isdir(folder) or not os.path.isfile(metadata_path):
            log.debug(
                u'Cannot load the {name} metadata file from {location}, it does not exist',
                {u'name': self.name, u'location': metadata_path}
            )
            return empty_return

        log.debug(u'Loading show info from {name} metadata file in {location}',
                  {u'name': self.name, u'location': folder})

        try:
            with io.open(metadata_path, u'rb') as xmlFileObj:
                showXML = etree.ElementTree(file=xmlFileObj)

            if (showXML.findtext(u'title') is None or
                    (showXML.findtext(u'tvdbid') is None and showXML.findtext(u'id') is None)):
                log.debug(
                    u'Invalid info in tvshow.nfo (missing name or id): {0} {1} {2}',
                    showXML.findtext(u'title'), showXML.findtext(u'tvdbid'), showXML.findtext(u'id'),
                )
                return empty_return

            name = showXML.findtext(u'title')

            if showXML.findtext(u'tvdbid'):
                indexer_id = int(showXML.findtext(u'tvdbid'))
            elif showXML.findtext(u'id'):
                indexer_id = int(showXML.findtext(u'id'))
            else:
                log.warning(u'Empty <id> or <tvdbid> field in NFO, unable to find a ID')
                return empty_return

            if indexer_id is None:
                log.warning(u'Invalid Indexer ID ({0}), not using metadata file',
                            indexer_id)
                return empty_return

            indexer = None
            if showXML.findtext(u'episodeguide/url'):
                epg_url = showXML.findtext(u'episodeguide/url').lower()
                if str(indexer_id) in epg_url:
                    if u'thetvdb.com' in epg_url:
                        indexer = INDEXER_TVDBV2
                    elif u'tvmaze.com' in epg_url:
                        indexer = INDEXER_TVMAZE
                    elif u'themoviedb.org' in epg_url:
                        indexer = INDEXER_TMDB
                    elif u'tvrage' in epg_url:
                        log.warning(
                            u'Invalid Indexer ID ({0}), not using metadata file because it has TVRage info',
                            indexer_id
                        )
                        return empty_return

        except Exception as error:
            log.warning(
                u'There was an error parsing your existing metadata file: {location} error: {error}',
                {u'location': metadata_path, u'error': ex(error)}
            )
            return empty_return

        return indexer_id, name, indexer

    @staticmethod
    def _retrieve_show_images_from_tmdb(show, img_type):
        types = {u'poster': u'poster_path',
                 u'banner': None,
                 u'fanart': u'backdrop_path',
                 u'poster_thumb': u'poster_path',
                 u'banner_thumb': None}

        # get TMDB configuration info
        tmdb.API_KEY = app.TMDB_API_KEY
        config = tmdb.Configuration()
        try:
            response = config.info()
        except RequestException as error:
            log.warning(u'Indexer TMDB is unavailable at this time: {reason}',
                        {u'reason': error})
            return False

        base_url = response[u'images'][u'base_url']
        sizes = response[u'images'][u'poster_sizes']

        def size_str_to_int(x):
            return float(u'inf') if x == u'original' else int(x[1:])

        max_size = max(sizes, key=size_str_to_int)

        try:
            search = tmdb.Search()
            for show_name in show.get_all_possible_names():
                for result in search.collection(query=show_name)[u'results'] + search.tv(query=show_name)[u'results']:
                    if types[img_type] and result.get(types[img_type]):
                        return u'{0}{1}{2}'.format(base_url, max_size, result[types[img_type]])

        except Exception:
            pass

        log.info(
            u'Could not find any {type} images on TMDB for {series}',
            {u'type': img_type, u'series': show.name}
        )

    def to_json(self):
        """Return JSON representation."""
        data = {}
        data['id'] = self.get_id()
        data['name'] = self.name
        data['showMetadata'] = self.show_metadata
        data['episodeMetadata'] = self.episode_metadata
        data['fanart'] = self.fanart
        data['poster'] = self.poster
        data['banner'] = self.banner
        data['episodeThumbnails'] = self.episode_thumbnails
        data['seasonPosters'] = self.season_posters
        data['seasonBanners'] = self.season_banners
        data['seasonAllPoster'] = self.season_all_poster
        data['seasonAllBanner'] = self.season_all_banner

        data['example'] = {}
        data['example']['banner'] = self.eg_banner
        data['example']['episodeMetadata'] = self.eg_episode_metadata
        data['example']['episodeThumbnails'] = self.eg_episode_thumbnails
        data['example']['fanart'] = self.eg_fanart
        data['example']['poster'] = self.eg_poster
        data['example']['seasonAllBanner'] = self.eg_season_all_banner
        data['example']['seasonAllPoster'] = self.eg_season_all_poster
        data['example']['seasonBanners'] = self.eg_season_banners
        data['example']['seasonPosters'] = self.eg_season_posters
        data['example']['showMetadata'] = self.eg_show_metadata

        return data
