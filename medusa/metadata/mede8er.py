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


import datetime
import io
import os

from six import string_types
from .. import helpers, logger
from ..helper.common import dateFormat, episode_num, replace_extension
from ..helper.exceptions import ex
from ..indexers.indexer_api import indexerApi
from ..indexers.indexer_exceptions import IndexerEpisodeNotFound, IndexerSeasonNotFound
from ..metadata import media_browser

try:
    import xml.etree.cElementTree as etree
except ImportError:
    import xml.etree.ElementTree as etree


class Mede8erMetadata(media_browser.MediaBrowserMetadata):
    """
    Metadata generation class for Mede8er based on the MediaBrowser.

    The following file structure is used:

    show_root/series.xml                    (show metadata)
    show_root/folder.jpg                    (poster)
    show_root/fanart.jpg                    (fanart)
    show_root/Season ##/folder.jpg          (season thumb)
    show_root/Season ##/filename.ext        (*)
    show_root/Season ##/filename.xml        (episode metadata)
    show_root/Season ##/filename.jpg        (episode thumb)
    """

    def __init__(self,
                 show_metadata=False,
                 episode_metadata=False,
                 fanart=False,
                 poster=False,
                 banner=False,
                 episode_thumbnails=False,
                 season_posters=False,
                 season_banners=False,
                 season_all_poster=False,
                 season_all_banner=False):

        media_browser.MediaBrowserMetadata.__init__(
            self, show_metadata, episode_metadata, fanart,
            poster, banner, episode_thumbnails, season_posters,
            season_banners, season_all_poster, season_all_banner
        )

        self.name = 'Mede8er'

        self.fanart_name = 'fanart.jpg'

        # web-ui metadata template
        # self.eg_show_metadata = 'series.xml'
        self.eg_episode_metadata = 'Season##\\<i>filename</i>.xml'
        self.eg_fanart = 'fanart.jpg'
        # self.eg_poster = 'folder.jpg'
        # self.eg_banner = 'banner.jpg'
        self.eg_episode_thumbnails = 'Season##\\<i>filename</i>.jpg'
        # self.eg_season_posters = 'Season##\\folder.jpg'
        # self.eg_season_banners = 'Season##\\banner.jpg'
        # self.eg_season_all_poster = '<i>not supported</i>'
        # self.eg_season_all_banner = '<i>not supported</i>'

    def get_episode_file_path(self, ep_obj):
        return replace_extension(ep_obj.location, self._ep_nfo_extension)

    @staticmethod
    def get_episode_thumb_path(ep_obj):
        return replace_extension(ep_obj.location, 'jpg')

    # SHOW DATA
    def _show_data(self, show_obj):
        """
        Creates an elementTree XML structure for a MediaBrowser-style series.xml
        returns the resulting data object.

        show_obj: a Series instance to create the NFO for
        """
        my_show = self._get_show_data(show_obj)

        # If by any reason it couldn't get the shows indexer data let's not go throught the rest of this method
        # as that pretty useless.
        if not my_show:
            return False

        root_node = etree.Element('details')
        tv_node = etree.SubElement(root_node, 'movie')
        tv_node.attrib['isExtra'] = 'false'
        tv_node.attrib['isSet'] = 'false'
        tv_node.attrib['isTV'] = 'true'

        title = etree.SubElement(tv_node, 'title')
        title.text = my_show['seriesname']

        if getattr(my_show, 'genre', None):
            genres = etree.SubElement(tv_node, 'genres')
            for genre in my_show['genre'].split('|'):
                if genre and genre.strip():
                    cur_genre = etree.SubElement(genres, 'Genre')
                    cur_genre.text = genre.strip()

        if getattr(my_show, 'firstaired', None):
            first_aired = etree.SubElement(tv_node, 'premiered')
            first_aired.text = my_show['firstaired']
            try:
                year_text = str(datetime.datetime.strptime(my_show['firstaired'], dateFormat).year)
                if year_text:
                    year = etree.SubElement(tv_node, 'year')
                    year.text = year_text
            except Exception:
                pass

        if getattr(my_show, 'overview', None):
            plot = etree.SubElement(tv_node, 'plot')
            plot.text = my_show['overview']

        if getattr(my_show, 'rating', None):
            try:
                rating = int(float(my_show['rating']) * 10)
            except ValueError:
                rating = 0

            if rating:
                rating = etree.SubElement(tv_node, 'rating')
                rating.text = str(rating)

        if getattr(my_show, 'status', None):
            status = etree.SubElement(tv_node, 'status')
            status.text = my_show['status']

        if getattr(my_show, 'contentrating', None):
            mpaa = etree.SubElement(tv_node, 'mpaa')
            mpaa.text = my_show['contentrating']

        if getattr(my_show, 'imdb_id', None):
            imdb_id = etree.SubElement(tv_node, 'id')
            imdb_id.attrib['moviedb'] = 'imdb'
            imdb_id.text = my_show['imdb_id']

        if getattr(my_show, 'id', None):
            indexer_id = etree.SubElement(tv_node, 'indexerid')
            indexer_id.text = my_show['id']

        if getattr(my_show, 'runtime', None):
            runtime = etree.SubElement(tv_node, 'runtime')
            runtime.text = my_show['runtime']

        if getattr(my_show, '_actors', None):
            cast = etree.SubElement(tv_node, 'cast')
            for actor in my_show['_actors']:
                if 'name' in actor and actor['name'].strip():
                    cur_actor = etree.SubElement(cast, 'actor')
                    cur_actor.text = actor['name'].strip()

        helpers.indent_xml(root_node)

        data = etree.ElementTree(root_node)

        return data

    def _ep_data(self, ep_obj):
        """
        Creates an elementTree XML structure for a MediaBrowser style episode.xml
        and returns the resulting data object.

        show_obj: a Series instance to create the NFO for
        """

        eps_to_write = [ep_obj] + ep_obj.related_episodes

        my_show = self._get_show_data(ep_obj.show)
        if not my_show:
            return None

        root_node = etree.Element('details')
        movie = etree.SubElement(root_node, 'movie')

        movie.attrib['isExtra'] = 'false'
        movie.attrib['isSet'] = 'false'
        movie.attrib['isTV'] = 'true'

        # write an MediaBrowser XML containing info for all matching episodes
        for ep_to_write in eps_to_write:

            try:
                my_ep = my_show[ep_to_write.season][ep_to_write.episode]
            except (IndexerEpisodeNotFound, IndexerSeasonNotFound):
                logger.log(u'Unable to find episode {ep_num} on {indexer}... '
                           u'has it been removed? Should I delete from db?'.format
                           (ep_num=episode_num(ep_to_write.season, ep_to_write.episode),
                            indexer=indexerApi(ep_obj.show.indexer).name))
                return None

            if ep_to_write == ep_obj:
                # root (or single) episode

                # default to today's date for specials if firstaired is not set
                if ep_to_write.season == 0 and not getattr(my_ep, 'firstaired', None):
                    my_ep['firstaired'] = str(datetime.date.fromordinal(1))

                if not (getattr(my_ep, 'episodename', None) and getattr(my_ep, 'firstaired', None)):
                    return None

                episode = movie

                if ep_to_write.name:
                    episode_name = etree.SubElement(episode, 'title')
                    episode_name.text = ep_to_write.name

                season_number = etree.SubElement(episode, 'season')
                season_number.text = str(ep_to_write.season)

                episode_number = etree.SubElement(episode, 'episode')
                episode_number.text = str(ep_to_write.episode)

                if getattr(my_show, 'firstaired', None):
                    try:
                        year_text = str(datetime.datetime.strptime(my_show['firstaired'], dateFormat).year)
                        if year_text:
                            year = etree.SubElement(episode, 'year')
                            year.text = year_text
                    except Exception:
                        pass

                if getattr(my_show, 'overview', None):
                    plot = etree.SubElement(episode, 'plot')
                    plot.text = my_show['overview']

                if ep_to_write.description:
                    overview = etree.SubElement(episode, 'episodeplot')
                    overview.text = ep_to_write.description

                if getattr(my_show, 'contentrating', None):
                    mpaa = etree.SubElement(episode, 'mpaa')
                    mpaa.text = my_show['contentrating']

                if not ep_obj.related_episodes and getattr(my_ep, 'rating', None):
                    try:
                        rating = int((float(my_ep['rating']) * 10))
                    except ValueError:
                        rating = 0

                    if rating:
                        rating = etree.SubElement(episode, 'rating')
                        rating.text = str(rating)

                if getattr(my_ep, 'director', None):
                    director = etree.SubElement(episode, 'director')
                    director.text = my_ep['director']

                if getattr(my_ep, 'writer', None):
                    writer = etree.SubElement(episode, 'credits')
                    writer.text = my_ep['writer']

                if getattr(my_show, '_actors', None) or getattr(my_ep, 'gueststars', None):
                    cast = etree.SubElement(episode, 'cast')
                    if getattr(my_ep, 'gueststars', None) and isinstance(my_ep['gueststars'], string_types):
                        for actor in (x.strip() for x in my_ep['gueststars'].split('|') if x.strip()):
                            cur_actor = etree.SubElement(cast, 'actor')
                            cur_actor.text = actor

                    if getattr(my_show, '_actors', None):
                        for actor in my_show['_actors']:
                            if 'name' in actor and actor['name'].strip():
                                cur_actor = etree.SubElement(cast, 'actor')
                                cur_actor.text = actor['name'].strip()

            else:
                # append data from (if any) related episodes

                if ep_to_write.name:
                    if not episode_name.text:
                        episode_name.text = ep_to_write.name
                    else:
                        episode_name.text = u', '.join([episode_name.text, ep_to_write.name])

                if ep_to_write.description:
                    if not overview.text:
                        overview.text = ep_to_write.description
                    else:
                        overview.text = u'\r'.join([overview.text, ep_to_write.description])

        # Make it purdy
        helpers.indent_xml(root_node)

        data = etree.ElementTree(root_node)

        return data

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
                logger.log(u'Metadata directory did not exist, creating it at {path}'.format
                           (path=nfo_file_dir), logger.DEBUG)
                os.makedirs(nfo_file_dir)
                helpers.chmod_as_parent(nfo_file_dir)

            logger.log(u'Writing show nfo file to {path}'.format
                       (path=nfo_file_path), logger.DEBUG)

            nfo_file = io.open(nfo_file_path, 'wb')

            data.write(nfo_file, encoding='utf-8', xml_declaration=True)
            nfo_file.close()
            helpers.chmod_as_parent(nfo_file_path)
        except IOError as e:
            logger.log(u'Unable to write file to {path} - '
                       u'are you sure the folder is writable? {exception}'.format
                       (path=nfo_file_path, exception=ex(e)),
                       logger.ERROR)
            return False

        return True

    def write_ep_file(self, ep_obj):
        """
        Generates and writes ep_obj's metadata under the given path with the
        given filename root. Uses the episode's name with the extension in
        _ep_nfo_extension.

        ep_obj: TVEpisode object for which to create the metadata

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
                logger.log(u'Metadata directory did not exist, creating it at {path}'.format
                           (path=nfo_file_dir), logger.DEBUG)
                os.makedirs(nfo_file_dir)
                helpers.chmod_as_parent(nfo_file_dir)

            logger.log(u'Writing episode nfo file to {path}'.format
                       (path=nfo_file_path), logger.DEBUG)

            with io.open(nfo_file_path, 'wb') as nfo_file:
                # Calling encode directly, b/c often descriptions have wonky characters.
                data.write(nfo_file, encoding='utf-8', xml_declaration=True)

            helpers.chmod_as_parent(nfo_file_path)

        except IOError as e:
            logger.log(u'Unable to write file to {path} - '
                       u'are you sure the folder is writable? {exception}'.format
                       (path=nfo_file_path, exception=ex(e)), logger.ERROR)
            return False

        return True


# present a standard 'interface' from the module
metadata_class = Mede8erMetadata
