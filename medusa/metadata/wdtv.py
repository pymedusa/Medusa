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
import os
import re

from .. import helpers, logger
from ..helper.common import dateFormat, episode_num as ep_num, replace_extension
from ..indexers.indexer_api import indexerApi
from ..indexers.indexer_exceptions import IndexerEpisodeNotFound, IndexerSeasonNotFound
from ..metadata import generic

try:
    import xml.etree.cElementTree as etree
except ImportError:
    import xml.etree.ElementTree as etree


class WDTVMetadata(generic.GenericMetadata):
    """
    Metadata generation class for WDTV

    The following file structure is used:

    show_root/folder.jpg                    (poster)
    show_root/Season ##/folder.jpg          (season thumb)
    show_root/Season ##/filename.ext        (*)
    show_root/Season ##/filename.metathumb  (episode thumb)
    show_root/Season ##/filename.xml        (episode metadata)
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

        generic.GenericMetadata.__init__(self,
                                         show_metadata,
                                         episode_metadata,
                                         fanart,
                                         poster,
                                         banner,
                                         episode_thumbnails,
                                         season_posters,
                                         season_banners,
                                         season_all_poster,
                                         season_all_banner)

        self.name = 'WDTV'

        self._ep_nfo_extension = 'xml'

        self.poster_name = 'folder.jpg'

        # web-ui metadata template
        self.eg_show_metadata = '<i>not supported</i>'
        self.eg_episode_metadata = 'Season##\\<i>filename</i>.xml'
        self.eg_fanart = '<i>not supported</i>'
        self.eg_poster = 'folder.jpg'
        self.eg_banner = '<i>not supported</i>'
        self.eg_episode_thumbnails = 'Season##\\<i>filename</i>.metathumb'
        self.eg_season_posters = 'Season##\\folder.jpg'
        self.eg_season_banners = '<i>not supported</i>'
        self.eg_season_all_poster = '<i>not supported</i>'
        self.eg_season_all_banner = '<i>not supported</i>'

    # Override with empty methods for unsupported features
    def retrieveShowMetadata(self, folder):
        # no show metadata generated, we abort this lookup function
        return None, None, None

    def create_show_metadata(self, show_obj):
        pass

    def update_show_indexer_metadata(self, show_obj):
        pass

    def get_show_file_path(self, show_obj):
        pass

    def create_fanart(self, show_obj):
        pass

    def create_banner(self, show_obj):
        pass

    def create_season_banners(self, show_obj):
        pass

    def create_season_all_poster(self, show_obj):
        pass

    def create_season_all_banner(self, show_obj):
        pass

    @staticmethod
    def get_episode_thumb_path(ep_obj):
        """
        Returns the path where the episode thumbnail should be stored. Defaults to
        the same path as the episode file but with a .metathumb extension.

        ep_obj: a Episode instance for which to create the thumbnail
        """
        if os.path.isfile(ep_obj.location):
            tbn_filename = replace_extension(ep_obj.location, 'metathumb')
        else:
            return None

        return tbn_filename

    @staticmethod
    def get_season_poster_path(show_obj, season):
        """
        Season thumbs for WDTV go in Show Dir/Season X/folder.jpg

        If no season folder exists, None is returned
        """

        dir_list = [x for x in os.listdir(show_obj.location) if
                    os.path.isdir(os.path.join(show_obj.location, x))]

        season_dir_regex = r'^Season\s+(\d+)$'

        season_dir = None

        for cur_dir in dir_list:
            if season == 0 and cur_dir == 'Specials':
                season_dir = cur_dir
                break

            match = re.match(season_dir_regex, cur_dir, re.I)
            if not match:
                continue

            cur_season = int(match.group(1))

            if cur_season == season:
                season_dir = cur_dir
                break

        if not season_dir:
            logger.log(u'Unable to find a season directory for season {season_num}'.format
                       (season_num=season), logger.DEBUG)
            return None

        logger.log(u'Using {path}/folder.jpg as season dir for season {season_num}'.format
                   (path=season_dir, season_num=season), logger.DEBUG)

        return os.path.join(show_obj.location, season_dir, 'folder.jpg')

    def _ep_data(self, ep_obj):
        """
        Creates an elementTree XML structure for a WDTV style episode.xml
        and returns the resulting data object.

        ep_obj: a Series instance to create the NFO for
        """

        eps_to_write = [ep_obj] + ep_obj.related_episodes

        my_show = self._get_show_data(ep_obj.show)
        if not my_show:
            return None

        root_node = etree.Element('details')

        # write an WDTV XML containing info for all matching episodes
        for ep_to_write in eps_to_write:

            try:
                my_ep = my_show[ep_to_write.season][ep_to_write.episode]
            except (IndexerEpisodeNotFound, IndexerSeasonNotFound):
                logger.log(u'Unable to find episode {ep_num} on {indexer}... '
                           u'has it been removed? Should I delete from db?'.format
                           (ep_num=ep_num(ep_to_write.season, ep_to_write.episode),
                            indexer=indexerApi(ep_obj.show.indexer).name))
                return None

            if ep_obj.season == 0 and not getattr(my_ep, 'firstaired', None):
                my_ep['firstaired'] = str(datetime.date.fromordinal(1))

            if not (getattr(my_ep, 'episodename', None) and getattr(my_ep, 'firstaired', None)):
                return None

            if len(eps_to_write) > 1:
                episode = etree.SubElement(root_node, 'details')
            else:
                episode = root_node

            # TODO: get right EpisodeID
            episode_id = etree.SubElement(episode, 'id')
            episode_id.text = str(ep_to_write.indexerid)

            title = etree.SubElement(episode, 'title')
            title.text = ep_obj.pretty_name()

            if getattr(my_show, 'seriesname', None):
                series_name = etree.SubElement(episode, 'series_name')
                series_name.text = my_show['seriesname']

            if ep_to_write.name:
                episode_name = etree.SubElement(episode, 'episode_name')
                episode_name.text = ep_to_write.name

            season_number = etree.SubElement(episode, 'season_number')
            season_number.text = str(ep_to_write.season)

            episode_num = etree.SubElement(episode, 'episode_number')
            episode_num.text = str(ep_to_write.episode)

            first_aired = etree.SubElement(episode, 'firstaired')

            if ep_to_write.airdate != datetime.date.fromordinal(1):
                first_aired.text = str(ep_to_write.airdate)

            if getattr(my_show, 'firstaired', None):
                try:
                    year_text = str(datetime.datetime.strptime(my_show['firstaired'], dateFormat).year)
                    if year_text:
                        year = etree.SubElement(episode, 'year')
                        year.text = year_text
                except Exception:
                    pass

            if ep_to_write.season != 0 and getattr(my_show, 'runtime', None):
                runtime = etree.SubElement(episode, 'runtime')
                runtime.text = my_show['runtime']

            if getattr(my_show, 'genre', None):
                genre = etree.SubElement(episode, 'genre')
                genre.text = ' / '.join([x.strip() for x in my_show['genre'].split('|') if x.strip()])

            if getattr(my_ep, 'director', None):
                director = etree.SubElement(episode, 'director')
                director.text = my_ep['director']

            if getattr(my_show, '_actors', None):
                for actor in my_show['_actors']:
                    if not ('name' in actor and actor['name'].strip()):
                        continue

                    cur_actor = etree.SubElement(episode, 'actor')

                    cur_actor_name = etree.SubElement(cur_actor, 'name')
                    cur_actor_name.text = actor['name']

                    if 'role' in actor and actor['role'].strip():
                        cur_actor_role = etree.SubElement(cur_actor, 'role')
                        cur_actor_role.text = actor['role'].strip()

            if ep_to_write.description:
                overview = etree.SubElement(episode, 'overview')
                overview.text = ep_to_write.description

            # Make it purdy
            helpers.indent_xml(root_node)
            data = etree.ElementTree(root_node)

        return data


# present a standard 'interface' from the module
metadata_class = WDTVMetadata
