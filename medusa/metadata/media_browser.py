# coding=utf-8

from __future__ import unicode_literals

import datetime
import logging
import os
import re

from medusa import app, helpers
from medusa.helper.common import dateFormat, episode_num, replace_extension
from medusa.indexers.api import indexerApi
from medusa.indexers.exceptions import IndexerEpisodeNotFound, IndexerSeasonNotFound
from medusa.logger.adapters.style import BraceAdapter
from medusa.metadata import generic

from six import iteritems, string_types, text_type as str

try:
    import xml.etree.cElementTree as etree
except ImportError:
    import xml.etree.ElementTree as etree

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


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

        self.name = u'MediaBrowser'
        self._ep_nfo_extension = u'xml'
        self._show_metadata_filename = u'series.xml'
        self.fanart_name = u'backdrop.jpg'
        self.poster_name = u'folder.jpg'

        # web-ui metadata template
        self.eg_show_metadata = 'series.xml'
        self.eg_episode_metadata = 'Season##\\metadata\\<i>filename</i>.xml'
        self.eg_fanart = 'backdrop.jpg'
        self.eg_poster = 'folder.jpg'
        self.eg_banner = 'banner.jpg'
        self.eg_episode_thumbnails = 'Season##\\metadata\\<i>filename</i>.jpg'
        self.eg_season_posters = 'Season##\\folder.jpg'
        self.eg_season_banners = 'Season##\\banner.jpg'
        # self.eg_season_all_poster = '<i>not supported</i>'
        # self.eg_season_all_banner = '<i>not supported</i>'

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

        ep_obj: a Episode object to get the path for
        """

        if os.path.isfile(ep_obj.location):
            xml_file_name = replace_extension(os.path.basename(ep_obj.location), self._ep_nfo_extension)
            metadata_dir_name = os.path.join(os.path.dirname(ep_obj.location), u'metadata')
            xml_file_path = os.path.join(metadata_dir_name, xml_file_name)
        else:
            log.debug(u'Episode location missing: {path}',
                      {u'path': ep_obj.location})
            return ''

        return xml_file_path

    @staticmethod
    def get_episode_thumb_path(ep_obj):
        """
        Returns a full show dir/metadata/episode.jpg path for MediaBrowser
        episode thumbs.

        ep_obj: a Episode object to get the path from
        """

        if os.path.isfile(ep_obj.location):
            tbn_file_name = replace_extension(os.path.basename(ep_obj.location), u'jpg')
            metadata_dir_name = os.path.join(os.path.dirname(ep_obj.location), u'metadata')
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

        dir_list = [x for x in os.listdir(show_obj.validate_location) if
                    os.path.isdir(os.path.join(show_obj.validate_location, x))]

        season_dir_regex = r'^Season\s+(\d+)$'

        season_dir = None

        for cur_dir in dir_list:
            # MediaBrowser 1.x only supports 'Specials'
            # MediaBrowser 2.x looks to only support 'Season 0'
            # MediaBrowser 3.x looks to mimic KODI/Plex support
            if season == 0 and cur_dir == u'Specials':
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
            log.debug(u'Unable to find a season directory for season {0}', season)
            return None

        log.debug(u'Using {path}/folder.jpg as season directory for season {number}',
                  {u'path': season_dir, u'number': season})

        return os.path.join(show_obj.validate_location, season_dir, u'folder.jpg')

    @staticmethod
    def get_season_banner_path(show_obj, season):
        """
        Season thumbs for MediaBrowser go in Show Dir/Season X/banner.jpg

        If no season folder exists, None is returned
        """

        dir_list = [x for x in os.listdir(show_obj.validate_location) if
                    os.path.isdir(os.path.join(show_obj.validate_location, x))]

        season_dir_regex = r'^Season\s+(\d+)$'

        season_dir = None

        for cur_dir in dir_list:
            # MediaBrowser 1.x only supports 'Specials'
            # MediaBrowser 2.x looks to only support 'Season 0'
            # MediaBrowser 3.x looks to mimic KODI/Plex support
            if season == 0 and cur_dir == u'Specials':
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
            log.debug(u'Unable to find a season directory for season {0}', season)
            return None

        log.debug(u'Using {path}/banner.jpg as season directory for season {number}',
                  {u'path': season_dir, u'number': season})

        return os.path.join(show_obj.validate_location, season_dir, u'banner.jpg')

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

        tv_node = etree.Element(u'Series')

        if getattr(my_show, u'id', None):
            indexerid = etree.SubElement(tv_node, u'id')
            indexerid.text = str(my_show[u'id'])

        if getattr(my_show, u'seriesname', None):
            series_name = etree.SubElement(tv_node, u'SeriesName')
            series_name.text = my_show[u'seriesname']

        if getattr(my_show, u'status', None):
            status = etree.SubElement(tv_node, u'Status')
            status.text = my_show[u'status']

        if getattr(my_show, u'network', None):
            network = etree.SubElement(tv_node, u'Network')
            network.text = my_show[u'network']

        if getattr(my_show, u'airs_time', None):
            airs_time = etree.SubElement(tv_node, u'Airs_Time')
            airs_time.text = my_show[u'airs_time']

        if getattr(my_show, u'airs_dayofweek', None):
            airs_day_of_week = etree.SubElement(tv_node, u'Airs_DayOfWeek')
            airs_day_of_week.text = my_show[u'airs_dayofweek']

        first_aired = etree.SubElement(tv_node, u'FirstAired')
        if getattr(my_show, u'firstaired', None):
            first_aired.text = my_show[u'firstaired']

        if getattr(my_show, u'contentrating', None):
            content_rating = etree.SubElement(tv_node, u'ContentRating')
            content_rating.text = my_show[u'contentrating']

            mpaa = etree.SubElement(tv_node, u'MPAARating')
            mpaa.text = my_show[u'contentrating']

            certification = etree.SubElement(tv_node, u'certification')
            certification.text = my_show[u'contentrating']

        metadata_type = etree.SubElement(tv_node, u'Type')
        metadata_type.text = u'Series'

        if getattr(my_show, u'overview', None):
            overview = etree.SubElement(tv_node, u'Overview')
            overview.text = my_show[u'overview']

        if getattr(my_show, u'firstaired', None):
            premiere_date = etree.SubElement(tv_node, u'PremiereDate')
            premiere_date.text = my_show[u'firstaired']

        if getattr(my_show, u'rating', None):
            rating = etree.SubElement(tv_node, u'Rating')
            rating.text = str(my_show[u'rating'])

        if getattr(my_show, u'firstaired', None):
            try:
                year_text = str(datetime.datetime.strptime(my_show[u'firstaired'], dateFormat).year)
                if year_text:
                    production_year = etree.SubElement(tv_node, u'ProductionYear')
                    production_year.text = year_text
            except Exception:
                pass

        if getattr(my_show, u'runtime', None):
            running_time = etree.SubElement(tv_node, u'RunningTime')
            running_time.text = str(my_show[u'runtime'])

            runtime = etree.SubElement(tv_node, u'Runtime')
            runtime.text = str(my_show[u'runtime'])

        if getattr(my_show, u'imdb_id', None):
            imdb_id = etree.SubElement(tv_node, u'IMDB_ID')
            imdb_id.text = my_show[u'imdb_id']

            imdb_id = etree.SubElement(tv_node, u'IMDB')
            imdb_id.text = my_show[u'imdb_id']

            imdb_id = etree.SubElement(tv_node, u'IMDbId')
            imdb_id.text = my_show[u'imdb_id']

        if getattr(my_show, u'zap2it_id', None):
            zap2it_id = etree.SubElement(tv_node, u'Zap2ItId')
            zap2it_id.text = my_show[u'zap2it_id']

        if getattr(my_show, u'genre', None) and isinstance(my_show[u'genre'], string_types):
            genres = etree.SubElement(tv_node, u'Genres')
            for genre in my_show[u'genre'].split(u'|'):
                if genre.strip():
                    cur_genre = etree.SubElement(genres, u'Genre')
                    cur_genre.text = genre.strip()

            genre = etree.SubElement(tv_node, u'Genre')
            genre.text = u'|'.join([x.strip() for x in my_show[u'genre'].split(u'|') if x.strip()])

        if getattr(my_show, u'network', None):
            studios = etree.SubElement(tv_node, u'Studios')
            studio = etree.SubElement(studios, u'Studio')
            studio.text = my_show[u'network']

        if getattr(my_show, u'_actors', None):
            persons = etree.SubElement(tv_node, u'Persons')
            for actor in my_show[u'_actors']:
                if not (u'name' in actor and actor[u'name'].strip()):
                    continue

                cur_actor = etree.SubElement(persons, u'Person')

                cur_actor_name = etree.SubElement(cur_actor, u'Name')
                cur_actor_name.text = actor[u'name'].strip()

                cur_actor_type = etree.SubElement(cur_actor, u'Type')
                cur_actor_type.text = u'Actor'

                if u'role' in actor and actor[u'role'].strip():
                    cur_actor_role = etree.SubElement(cur_actor, u'Role')
                    cur_actor_role.text = actor[u'role'].strip()

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
            u'Director': [],
            u'GuestStar': [],
            u'Writer': []
        }

        my_show = self._get_show_data(ep_obj.series)
        if not my_show:
            return None

        root_node = etree.Element(u'Item')

        # write an MediaBrowser XML containing info for all matching episodes
        for ep_to_write in eps_to_write:

            try:
                my_ep = my_show[ep_to_write.season][ep_to_write.episode]
            except (IndexerEpisodeNotFound, IndexerSeasonNotFound):
                log.info(
                    u'Unable to find episode {number} on {indexer}... has it been removed? Should I delete from db?', {
                        u'number': episode_num(ep_to_write.season, ep_to_write.episode),
                        u'indexer': indexerApi(ep_obj.series.indexer).name
                    }
                )
                return None

            if ep_to_write == ep_obj:
                # root (or single) episode

                # default to today's date for specials if firstaired is not set
                if ep_to_write.season == 0 and not getattr(my_ep, u'firstaired', None):
                    my_ep[u'firstaired'] = str(datetime.date.fromordinal(1))

                if not (getattr(my_ep, u'episodename', None) and getattr(my_ep, u'firstaired', None)):
                    return None

                episode = root_node

                if ep_to_write.name:
                    episode_name = etree.SubElement(episode, u'EpisodeName')
                    episode_name.text = ep_to_write.name

                episode_number = etree.SubElement(episode, u'EpisodeNumber')
                episode_number.text = str(ep_obj.episode)

                if ep_obj.related_episodes:
                    episode_number_end = etree.SubElement(episode, u'EpisodeNumberEnd')
                    episode_number_end.text = str(ep_to_write.episode)

                season_number = etree.SubElement(episode, u'SeasonNumber')
                season_number.text = str(ep_to_write.season)

                if not ep_obj.related_episodes and getattr(my_ep, u'absolute_number', None):
                    absolute_number = etree.SubElement(episode, u'absolute_number')
                    absolute_number.text = str(my_ep[u'absolute_number'])

                if ep_to_write.airdate != datetime.date.fromordinal(1):
                    first_aired = etree.SubElement(episode, u'FirstAired')
                    first_aired.text = str(ep_to_write.airdate)

                metadata_type = etree.SubElement(episode, u'Type')
                metadata_type.text = u'Episode'

                if ep_to_write.description:
                    overview = etree.SubElement(episode, u'Overview')
                    overview.text = ep_to_write.description

                if not ep_obj.related_episodes:
                    if getattr(my_ep, u'rating', None):
                        rating = etree.SubElement(episode, u'Rating')
                        rating.text = str(my_ep[u'rating'])

                    if getattr(my_show, u'imdb_id', None):
                        IMDB_ID = etree.SubElement(episode, u'IMDB_ID')
                        IMDB_ID.text = my_show[u'imdb_id']

                        IMDB = etree.SubElement(episode, u'IMDB')
                        IMDB.text = my_show[u'imdb_id']

                        IMDbId = etree.SubElement(episode, u'IMDbId')
                        IMDbId.text = my_show[u'imdb_id']

                indexer_id = etree.SubElement(episode, u'id')
                indexer_id.text = str(ep_to_write.indexerid)

                persons = etree.SubElement(episode, u'Persons')

                if getattr(my_show, u'_actors', None):
                    for actor in my_show[u'_actors']:
                        if not (u'name' in actor and actor[u'name'].strip()):
                            continue

                        cur_actor = etree.SubElement(persons, u'Person')

                        cur_actor_name = etree.SubElement(cur_actor, u'Name')
                        cur_actor_name.text = actor[u'name'].strip()

                        cur_actor_type = etree.SubElement(cur_actor, u'Type')
                        cur_actor_type.text = u'Actor'

                        if u'role' in actor and actor[u'role'].strip():
                            cur_actor_role = etree.SubElement(cur_actor, u'Role')
                            cur_actor_role.text = actor[u'role'].strip()

                language = etree.SubElement(episode, u'Language')
                try:
                    language.text = my_ep[u'language']
                except Exception:
                    language.text = app.INDEXER_DEFAULT_LANGUAGE  # tvrage api doesn't provide language so we must assume a value here

                thumb = etree.SubElement(episode, u'filename')
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
            if getattr(my_ep, u'director', None):
                persons_dict[u'Director'] += [x.strip() for x in my_ep[u'director'].split(u'|') if x.strip()]
            if getattr(my_ep, u'gueststars', None):
                persons_dict[u'GuestStar'] += [x.strip() for x in my_ep[u'gueststars'].split(u'|') if x.strip()]
            if getattr(my_ep, u'writer', None):
                persons_dict[u'Writer'] += [x.strip() for x in my_ep[u'writer'].split(u'|') if x.strip()]

        # fill in Persons section with collected directors, guest starts and writers
        for person_type, names in iteritems(persons_dict):
            # remove doubles
            names = list(set(names))
            for cur_name in names:
                person = etree.SubElement(persons, u'Person')
                cur_person_name = etree.SubElement(person, u'Name')
                cur_person_name.text = cur_name
                cur_person_type = etree.SubElement(person, u'Type')
                cur_person_type.text = person_type

        # Make it purdy
        helpers.indent_xml(root_node)
        data = etree.ElementTree(root_node)

        return data


# present a standard interface from the module
metadata_class = MediaBrowserMetadata
