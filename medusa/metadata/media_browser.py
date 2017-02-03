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

from six import iteritems, string_types
from .. import app, helpers, logger
from ..helper.common import dateFormat, episode_num, replace_extension
from ..indexers.indexer_api import indexerApi
from ..indexers.indexer_exceptions import IndexerEpisodeNotFound, IndexerSeasonNotFound
from ..metadata import generic

try:
    import xml.etree.cElementTree as etree
except ImportError:
    import xml.etree.ElementTree as etree


class MediaBrowserMetadata(generic.GenericMetadata):
    """
    Metadata generation class for Media Browser 2.x/3.x - Standard Mode.

    The following file structure is used:

    show_root/series.xml                       (show metadata)
    show_root/folder.jpg                       (poster)
    show_root/backdrop.jpg                     (fanart)
    show_root/Season ##/folder.jpg             (season thumb)
    show_root/Season ##/filename.ext           (*)
    show_root/Season ##/metadata/filename.xml  (episode metadata)
    show_root/Season ##/metadata/filename.jpg  (episode thumb)
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

        self.name = 'MediaBrowser'

        self._ep_nfo_extension = 'xml'
        self._show_metadata_filename = 'series.xml'

        self.fanart_name = 'backdrop.jpg'
        self.poster_name = 'folder.jpg'

        # web-ui metadata template
        self.eg_show_metadata = 'series.xml'
        self.eg_episode_metadata = 'Season##\\metadata\\<i>filename</i>.xml'
        self.eg_fanart = 'backdrop.jpg'
        self.eg_poster = 'folder.jpg'
        self.eg_banner = 'banner.jpg'
        self.eg_episode_thumbnails = 'Season##\\metadata\\<i>filename</i>.jpg'
        self.eg_season_posters = 'Season##\\folder.jpg'
        self.eg_season_banners = 'Season##\\banner.jpg'
        self.eg_season_all_poster = '<i>not supported</i>'
        self.eg_season_all_banner = '<i>not supported</i>'

    # Override with empty methods for unsupported features
    def retrieveShowMetadata(self, folder):
        # while show metadata is generated, it is not supported for our lookup
        return None, None, None

    def create_season_all_poster(self, show_obj):
        pass

    def create_season_all_banner(self, show_obj):
        pass

    def get_episode_file_path(self, ep_obj):
        """
        Returns a full show dir/metadata/episode.xml path for MediaBrowser
        episode metadata files

        ep_obj: a TVEpisode object to get the path for
        """

        if os.path.isfile(ep_obj.location):
            xml_file_name = replace_extension(os.path.basename(ep_obj.location), self._ep_nfo_extension)
            metadata_dir_name = os.path.join(os.path.dirname(ep_obj.location), 'metadata')
            xml_file_path = os.path.join(metadata_dir_name, xml_file_name)
        else:
            logger.log(u'Episode location doesn\'t exist: {path}'.format
                       (path=ep_obj.location), logger.DEBUG)
            return ''

        return xml_file_path

    @staticmethod
    def get_episode_thumb_path(ep_obj):
        """
        Returns a full show dir/metadata/episode.jpg path for MediaBrowser
        episode thumbs.

        ep_obj: a TVEpisode object to get the path from
        """

        if os.path.isfile(ep_obj.location):
            tbn_file_name = replace_extension(os.path.basename(ep_obj.location), 'jpg')
            metadata_dir_name = os.path.join(os.path.dirname(ep_obj.location), 'metadata')
            tbn_file_path = os.path.join(metadata_dir_name, tbn_file_name)
        else:
            return None

        return tbn_file_path

    @staticmethod
    def get_season_poster_path(show_obj, season):
        """
        Season thumbs for MediaBrowser go in Show Dir/Season X/folder.jpg

        If no season folder exists, None is returned
        """

        dir_list = [x for x in os.listdir(show_obj.location) if
                    os.path.isdir(os.path.join(show_obj.location, x))]

        season_dir_regex = r'^Season\s+(\d+)$'

        season_dir = None

        for cur_dir in dir_list:
            # MediaBrowser 1.x only supports 'Specials'
            # MediaBrowser 2.x looks to only support 'Season 0'
            # MediaBrowser 3.x looks to mimic KODI/Plex support
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

    @staticmethod
    def get_season_banner_path(show_obj, season):
        """
        Season thumbs for MediaBrowser go in Show Dir/Season X/banner.jpg

        If no season folder exists, None is returned
        """

        dir_list = [x for x in os.listdir(show_obj.location) if
                    os.path.isdir(os.path.join(show_obj.location, x))]

        season_dir_regex = r'^Season\s+(\d+)$'

        season_dir = None

        for cur_dir in dir_list:
            # MediaBrowser 1.x only supports 'Specials'
            # MediaBrowser 2.x looks to only support 'Season 0'
            # MediaBrowser 3.x looks to mimic KODI/Plex support
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

        logger.log(u'Using {path}/banner.jpg as season dir for season {season_num}'.format
                   (path=season_dir, season_num=season), logger.DEBUG)

        return os.path.join(show_obj.location, season_dir, 'banner.jpg')

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

        tv_node = etree.Element('Series')

        if getattr(my_show, 'id', None):
            indexerid = etree.SubElement(tv_node, 'id')
            indexerid.text = str(my_show['id'])

        if getattr(my_show, 'seriesname', None):
            series_name = etree.SubElement(tv_node, 'SeriesName')
            series_name.text = my_show['seriesname']

        if getattr(my_show, 'status', None):
            status = etree.SubElement(tv_node, 'Status')
            status.text = my_show['status']

        if getattr(my_show, 'network', None):
            network = etree.SubElement(tv_node, 'Network')
            network.text = my_show['network']

        if getattr(my_show, 'airs_time', None):
            airs_time = etree.SubElement(tv_node, 'Airs_Time')
            airs_time.text = my_show['airs_time']

        if getattr(my_show, 'airs_dayofweek', None):
            airs_day_of_week = etree.SubElement(tv_node, 'Airs_DayOfWeek')
            airs_day_of_week.text = my_show['airs_dayofweek']

        first_aired = etree.SubElement(tv_node, 'FirstAired')
        if getattr(my_show, 'firstaired', None):
            first_aired.text = my_show['firstaired']

        if getattr(my_show, 'contentrating', None):
            content_rating = etree.SubElement(tv_node, 'ContentRating')
            content_rating.text = my_show['contentrating']

            mpaa = etree.SubElement(tv_node, 'MPAARating')
            mpaa.text = my_show['contentrating']

            certification = etree.SubElement(tv_node, 'certification')
            certification.text = my_show['contentrating']

        metadata_type = etree.SubElement(tv_node, 'Type')
        metadata_type.text = 'Series'

        if getattr(my_show, 'overview', None):
            overview = etree.SubElement(tv_node, 'Overview')
            overview.text = my_show['overview']

        if getattr(my_show, 'firstaired', None):
            premiere_date = etree.SubElement(tv_node, 'PremiereDate')
            premiere_date.text = my_show['firstaired']

        if getattr(my_show, 'rating', None):
            rating = etree.SubElement(tv_node, 'Rating')
            rating.text = my_show['rating']

        if getattr(my_show, 'firstaired', None):
            try:
                year_text = str(datetime.datetime.strptime(my_show['firstaired'], dateFormat).year)
                if year_text:
                    production_year = etree.SubElement(tv_node, 'ProductionYear')
                    production_year.text = year_text
            except Exception:
                pass

        if getattr(my_show, 'runtime', None):
            running_time = etree.SubElement(tv_node, 'RunningTime')
            running_time.text = my_show['runtime']

            runtime = etree.SubElement(tv_node, 'Runtime')
            runtime.text = my_show['runtime']

        if getattr(my_show, 'imdb_id', None):
            imdb_id = etree.SubElement(tv_node, 'IMDB_ID')
            imdb_id.text = my_show['imdb_id']

            imdb_id = etree.SubElement(tv_node, 'IMDB')
            imdb_id.text = my_show['imdb_id']

            imdb_id = etree.SubElement(tv_node, 'IMDbId')
            imdb_id.text = my_show['imdb_id']

        if getattr(my_show, 'zap2it_id', None):
            zap2it_id = etree.SubElement(tv_node, 'Zap2ItId')
            zap2it_id.text = my_show['zap2it_id']

        if getattr(my_show, 'genre', None) and isinstance(my_show['genre'], string_types):
            genres = etree.SubElement(tv_node, 'Genres')
            for genre in my_show['genre'].split('|'):
                if genre.strip():
                    cur_genre = etree.SubElement(genres, 'Genre')
                    cur_genre.text = genre.strip()

            genre = etree.SubElement(tv_node, 'Genre')
            genre.text = '|'.join([x.strip() for x in my_show['genre'].split('|') if x.strip()])

        if getattr(my_show, 'network', None):
            studios = etree.SubElement(tv_node, 'Studios')
            studio = etree.SubElement(studios, 'Studio')
            studio.text = my_show['network']

        if getattr(my_show, '_actors', None):
            persons = etree.SubElement(tv_node, 'Persons')
            for actor in my_show['_actors']:
                if not ('name' in actor and actor['name'].strip()):
                    continue

                cur_actor = etree.SubElement(persons, 'Person')

                cur_actor_name = etree.SubElement(cur_actor, 'Name')
                cur_actor_name.text = actor['name'].strip()

                cur_actor_type = etree.SubElement(cur_actor, 'Type')
                cur_actor_type.text = 'Actor'

                if 'role' in actor and actor['role'].strip():
                    cur_actor_role = etree.SubElement(cur_actor, 'Role')
                    cur_actor_role.text = actor['role'].strip()

        helpers.indent_xml(tv_node)

        data = etree.ElementTree(tv_node)

        return data

    def _ep_data(self, ep_obj):
        """
        Creates an elementTree XML structure for a MediaBrowser style episode.xml
        and returns the resulting data object.

        show_obj: a Series instance to create the NFO for
        """

        eps_to_write = [ep_obj] + ep_obj.related_episodes

        persons_dict = {
            'Director': [],
            'GuestStar': [],
            'Writer': []
        }

        my_show = self._get_show_data(ep_obj.show)
        if not my_show:
            return None

        root_node = etree.Element('Item')

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

                episode = root_node

                if ep_to_write.name:
                    episode_name = etree.SubElement(episode, 'EpisodeName')
                    episode_name.text = ep_to_write.name

                episode_number = etree.SubElement(episode, 'EpisodeNumber')
                episode_number.text = str(ep_obj.episode)

                if ep_obj.related_episodes:
                    episode_number_end = etree.SubElement(episode, 'EpisodeNumberEnd')
                    episode_number_end.text = str(ep_to_write.episode)

                season_number = etree.SubElement(episode, 'SeasonNumber')
                season_number.text = str(ep_to_write.season)

                if not ep_obj.related_episodes and getattr(my_ep, 'absolute_number', None):
                    absolute_number = etree.SubElement(episode, 'absolute_number')
                    absolute_number.text = str(my_ep['absolute_number'])

                if ep_to_write.airdate != datetime.date.fromordinal(1):
                    first_aired = etree.SubElement(episode, 'FirstAired')
                    first_aired.text = str(ep_to_write.airdate)

                metadata_type = etree.SubElement(episode, 'Type')
                metadata_type.text = 'Episode'

                if ep_to_write.description:
                    overview = etree.SubElement(episode, 'Overview')
                    overview.text = ep_to_write.description

                if not ep_obj.related_episodes:
                    if getattr(my_ep, 'rating', None):
                        rating = etree.SubElement(episode, 'Rating')
                        rating.text = my_ep['rating']

                    if getattr(my_show, 'imdb_id', None):
                        IMDB_ID = etree.SubElement(episode, 'IMDB_ID')
                        IMDB_ID.text = my_show['imdb_id']

                        IMDB = etree.SubElement(episode, 'IMDB')
                        IMDB.text = my_show['imdb_id']

                        IMDbId = etree.SubElement(episode, 'IMDbId')
                        IMDbId.text = my_show['imdb_id']

                indexer_id = etree.SubElement(episode, 'id')
                indexer_id.text = str(ep_to_write.indexerid)

                persons = etree.SubElement(episode, 'Persons')

                if getattr(my_show, '_actors', None):
                    for actor in my_show['_actors']:
                        if not ('name' in actor and actor['name'].strip()):
                            continue

                        cur_actor = etree.SubElement(persons, 'Person')

                        cur_actor_name = etree.SubElement(cur_actor, 'Name')
                        cur_actor_name.text = actor['name'].strip()

                        cur_actor_type = etree.SubElement(cur_actor, 'Type')
                        cur_actor_type.text = 'Actor'

                        if 'role' in actor and actor['role'].strip():
                            cur_actor_role = etree.SubElement(cur_actor, 'Role')
                            cur_actor_role.text = actor['role'].strip()

                language = etree.SubElement(episode, 'Language')
                try:
                    language.text = my_ep['language']
                except Exception:
                    language.text = app.INDEXER_DEFAULT_LANGUAGE  # tvrage api doesn't provide language so we must assume a value here

                thumb = etree.SubElement(episode, 'filename')
                # TODO: See what this is needed for.. if its still needed
                # just write this to the NFO regardless of whether it actually exists or not
                # note: renaming files after nfo generation will break this, tough luck
                thumb_text = self.get_episode_thumb_path(ep_obj)
                if thumb_text:
                    thumb.text = thumb_text

            else:
                # append data from (if any) related episodes
                episode_number_end.text = str(ep_to_write.episode)

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

            # collect all directors, guest stars and writers
            if getattr(my_ep, 'director', None):
                persons_dict['Director'] += [x.strip() for x in my_ep['director'].split('|') if x.strip()]
            if getattr(my_ep, 'gueststars', None):
                persons_dict['GuestStar'] += [x.strip() for x in my_ep['gueststars'].split('|') if x.strip()]
            if getattr(my_ep, 'writer', None):
                persons_dict['Writer'] += [x.strip() for x in my_ep['writer'].split('|') if x.strip()]

        # fill in Persons section with collected directors, guest starts and writers
        for person_type, names in iteritems(persons_dict):
            # remove doubles
            names = list(set(names))
            for cur_name in names:
                person = etree.SubElement(persons, 'Person')
                cur_person_name = etree.SubElement(person, 'Name')
                cur_person_name.text = cur_name
                cur_person_type = etree.SubElement(person, 'Type')
                cur_person_type.text = person_type

        # Make it purdy
        helpers.indent_xml(root_node)
        data = etree.ElementTree(root_node)

        return data


# present a standard 'interface' from the module
metadata_class = MediaBrowserMetadata
