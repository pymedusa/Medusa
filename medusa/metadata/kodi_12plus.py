# coding=utf-8

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
import re

from babelfish import Country
import medusa as app
from six import string_types
from . import generic
from .. import helpers, logger
from ..helper.common import dateFormat, episode_num
from ..helper.exceptions import ShowNotFoundException

try:
    import xml.etree.cElementTree as etree
except ImportError:
    import xml.etree.ElementTree as etree


class KODI_12PlusMetadata(generic.GenericMetadata):
    """
    Metadata generation class for KODI 12+.

    The following file structure is used:

    show_root/tvshow.nfo                    (show metadata)
    show_root/fanart.jpg                    (fanart)
    show_root/poster.jpg                    (poster)
    show_root/banner.jpg                    (banner)
    show_root/Season ##/filename.ext        (*)
    show_root/Season ##/filename.nfo        (episode metadata)
    show_root/Season ##/filename-thumb.jpg  (episode thumb)
    show_root/season##-poster.jpg           (season posters)
    show_root/season##-banner.jpg           (season banners)
    show_root/season-all-poster.jpg         (season all poster)
    show_root/season-all-banner.jpg         (season all banner)
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

        self.name = u'KODI 12+'

        self.poster_name = u'poster.jpg'
        self.season_all_poster_name = u'season-all-poster.jpg'

        # web-ui metadata template
        self.eg_show_metadata = u'tvshow.nfo'
        self.eg_episode_metadata = u'Season##\\<i>filename</i>.nfo'
        self.eg_fanart = u'fanart.jpg'
        self.eg_poster = u'poster.jpg'
        self.eg_banner = u'banner.jpg'
        self.eg_episode_thumbnails = u'Season##\\<i>filename</i>-thumb.jpg'
        self.eg_season_posters = u'season##-poster.jpg'
        self.eg_season_banners = u'season##-banner.jpg'
        self.eg_season_all_poster = u'season-all-poster.jpg'
        self.eg_season_all_banner = u'season-all-banner.jpg'

    @staticmethod
    def _split_info(info_string):
        return {x.strip().title() for x in re.sub(r'[,/]+', '|', info_string).split('|') if x.strip()}

    # SHOW DATA
    def _show_data(self, show_obj):
        """
        Creates an elementTree XML structure for an KODI-style tvshow.nfo and
        returns the resulting data object.

        show_obj: a TVShow instance to create the NFO for
        """

        show_id = show_obj.indexerid
        indexer_name = app.indexerApi(show_obj.indexer).name
        indexer_lang = show_obj.lang
        l_indexer_api_params = app.indexerApi(show_obj.indexer).api_params.copy()

        l_indexer_api_params['actors'] = True

        if indexer_lang and not indexer_lang == app.INDEXER_DEFAULT_LANGUAGE:
            l_indexer_api_params['language'] = indexer_lang

        if show_obj.dvdorder != 0:
            l_indexer_api_params['dvdorder'] = True

        t = app.indexerApi(show_obj.indexer).indexer(**l_indexer_api_params)

        tv_node = etree.Element('tvshow')

        try:
            my_show = t[int(show_id)]
        except app.IndexerShowNotFound:
            logger.log(u'Unable to find {indexer} show {id}, skipping it'.format
                       (indexer=indexer_name,
                        id=show_id), logger.ERROR)
            raise

        except app.IndexerError:
            logger.log(u'{indexer} is down, can\'t use its data to add this show'.format
                       (indexer=indexer_name), logger.ERROR)
            raise

        # check for title and id
        if not (getattr(my_show, 'seriesname', None) and getattr(my_show, 'id', None)):
            logger.log(u'Incomplete info for {indexer} show {id}, skipping it'.format
                       (indexer=indexer_name,
                        id=show_id), logger.ERROR)
            return False

        title = etree.SubElement(tv_node, 'title')
        title.text = my_show['seriesname']

        if getattr(my_show, 'rating', None):
            rating = etree.SubElement(tv_node, 'rating')
            rating.text = my_show['rating']

        if getattr(my_show, 'firstaired', None):
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

        if getattr(my_show, 'id', None):
            episode_guide = etree.SubElement(tv_node, 'episodeguide')
            episode_guide_url = etree.SubElement(episode_guide, 'url')
            episode_guide_url.text = '{url}{id}/all/en.zip'.format(
                url=app.indexerApi(show_obj.indexer).config['base_url'],
                id=my_show['id']
            )

        if getattr(my_show, 'contentrating', None):
            mpaa = etree.SubElement(tv_node, 'mpaa')
            mpaa.text = my_show['contentrating']

        if getattr(my_show, 'id', None):
            indexer_id = etree.SubElement(tv_node, 'id')
            indexer_id.text = str(my_show['id'])

        if getattr(my_show, 'genre', None) and isinstance(my_show['genre'], string_types):
            for genre in self._split_info(my_show['genre']):
                cur_genre = etree.SubElement(tv_node, 'genre')
                cur_genre.text = genre

        if 'country_codes' in show_obj.imdb_info:
            for country in self._split_info(show_obj.imdb_info['country_codes']):
                try:
                    cur_country_name = Country(country.upper()).name.title()
                except Exception:
                    continue

                cur_country = etree.SubElement(tv_node, 'country')
                cur_country.text = cur_country_name

        if getattr(my_show, 'firstaired', None):
            premiered = etree.SubElement(tv_node, 'premiered')
            premiered.text = my_show['firstaired']

        if getattr(my_show, 'network', None):
            studio = etree.SubElement(tv_node, 'studio')
            studio.text = my_show['network'].strip()

        if getattr(my_show, 'writer', None) and isinstance(my_show['writer'], string_types):
            for writer in self._split_info(my_show['writer']):
                cur_writer = etree.SubElement(tv_node, 'credits')
                cur_writer.text = writer

        if getattr(my_show, 'director', None) and isinstance(my_show['director'], string_types):
            for director in self._split_info(my_show['director']):
                cur_director = etree.SubElement(tv_node, 'director')
                cur_director.text = director

        if getattr(my_show, '_actors', None):
            for actor in my_show['_actors']:
                cur_actor = etree.SubElement(tv_node, 'actor')

                if 'name' in actor and actor['name'].strip():
                    cur_actor_name = etree.SubElement(cur_actor, 'name')
                    cur_actor_name.text = actor['name'].strip()
                else:
                    continue

                if 'role' in actor and actor['role'].strip():
                    cur_actor_role = etree.SubElement(cur_actor, 'role')
                    cur_actor_role.text = actor['role'].strip()

                if 'image' in actor and actor['image'].strip():
                    indexer_url = ''
                    if indexer_name == 'thetvdb':
                        indexer_url = 'http://thetvdb.com/banners/'
                    cur_actor_thumb = indexer_url + etree.SubElement(cur_actor, 'thumb')
                    cur_actor_thumb.text = actor['image'].strip()

        # Make it purdy
        helpers.indentXML(tv_node)

        data = etree.ElementTree(tv_node)

        return data

    def _ep_data(self, ep_obj):
        """
        Creates an elementTree XML structure for an KODI-style episode.nfo and
        returns the resulting data object.

        show_obj: a TVEpisode instance to create the NFO for
        """

        eps_to_write = [ep_obj] + ep_obj.related_episodes

        indexer_lang = ep_obj.show.lang
        indexer_name = app.indexerApi(ep_obj.show.indexer).name

        # There's gotta be a better way of doing this but we don't wanna
        # change the language value elsewhere
        l_indexer_api_params = app.indexerApi(ep_obj.show.indexer).api_params.copy()

        l_indexer_api_params[b'actors'] = True

        if indexer_lang and not indexer_lang == app.INDEXER_DEFAULT_LANGUAGE:
            l_indexer_api_params[b'language'] = indexer_lang

        if ep_obj.show.dvdorder != 0:
            l_indexer_api_params[b'dvdorder'] = True

        try:
            t = app.indexerApi(ep_obj.show.indexer).indexer(**l_indexer_api_params)
            my_show = t[ep_obj.show.indexerid]
        except app.IndexerShowNotFound as e:
            raise ShowNotFoundException(e.message)
        except app.IndexerError:
            logger.log(u'Unable to connect to {indexer} while creating meta files - skipping it.'.format
                       (indexer=indexer_name), logger.WARNING)
            return

        if len(eps_to_write) > 1:
            root_node = etree.Element('kodimultiepisode')
        else:
            root_node = etree.Element('episodedetails')

        # write an NFO containing info for all matching episodes
        for ep_to_write in eps_to_write:

            try:
                my_ep = my_show[ep_to_write.season][ep_to_write.episode]
            except (app.IndexerEpisodeNotFound, app.IndexerSeasonNotFound):
                logger.log(u'Unable to find episode {ep_num} on {indexer}... '
                           u'has it been removed? Should I delete from db?'.format
                           (ep_num=episode_num(ep_to_write.season, ep_to_write.episode),
                            indexer=indexer_name))
                return None

            if not getattr(my_ep, 'firstaired', None):
                my_ep['firstaired'] = str(datetime.date.fromordinal(1))

            if not getattr(my_ep, 'episodename', None):
                logger.log(u'Not generating nfo because the ep has no title', logger.DEBUG)
                return None

            logger.log(u'Creating metadata for episode {ep_num}'.format
                       (ep_num=episode_num(ep_obj.season, ep_obj.episode)), logger.DEBUG)

            if len(eps_to_write) > 1:
                episode = etree.SubElement(root_node, 'episodedetails')
            else:
                episode = root_node

            if getattr(my_ep, 'episodename', None):
                title = etree.SubElement(episode, 'title')
                title.text = my_ep['episodename']

            if getattr(my_show, 'seriesname', None):
                showtitle = etree.SubElement(episode, 'showtitle')
                showtitle.text = my_show['seriesname']

            season = etree.SubElement(episode, 'season')
            season.text = str(ep_to_write.season)

            episodenum = etree.SubElement(episode, 'episode')
            episodenum.text = str(ep_to_write.episode)

            uniqueid = etree.SubElement(episode, 'uniqueid')
            uniqueid.text = str(ep_to_write.indexerid)

            if ep_to_write.airdate != datetime.date.fromordinal(1):
                aired = etree.SubElement(episode, 'aired')
                aired.text = str(ep_to_write.airdate)

            if getattr(my_ep, 'overview', None):
                plot = etree.SubElement(episode, 'plot')
                plot.text = my_ep['overview']

            if ep_to_write.season and getattr(my_show, 'runtime', None):
                runtime = etree.SubElement(episode, 'runtime')
                runtime.text = my_show['runtime']

            if getattr(my_ep, 'airsbefore_season', None):
                displayseason = etree.SubElement(episode, 'displayseason')
                displayseason.text = my_ep['airsbefore_season']

            if getattr(my_ep, 'airsbefore_episode', None):
                displayepisode = etree.SubElement(episode, 'displayepisode')
                displayepisode.text = my_ep['airsbefore_episode']

            if getattr(my_ep, 'filename', None):
                thumb = etree.SubElement(episode, 'thumb')
                thumb.text = my_ep['filename'].strip()

            # watched = etree.SubElement(episode, 'watched')
            # watched.text = 'false'

            if getattr(my_ep, 'rating', None):
                rating = etree.SubElement(episode, 'rating')
                rating.text = my_ep['rating']

            if getattr(my_ep, 'writer', None) and isinstance(my_ep['writer'], string_types):
                for writer in self._split_info(my_ep['writer']):
                    cur_writer = etree.SubElement(episode, 'credits')
                    cur_writer.text = writer

            if getattr(my_ep, 'director', None) and isinstance(my_ep['director'], string_types):
                for director in self._split_info(my_ep['director']):
                    cur_director = etree.SubElement(episode, 'director')
                    cur_director.text = director

            if getattr(my_ep, 'gueststars', None) and isinstance(my_ep['gueststars'], string_types):
                for actor in self._split_info(my_ep['gueststars']):
                    cur_actor = etree.SubElement(episode, 'actor')
                    cur_actor_name = etree.SubElement(cur_actor, 'name')
                    cur_actor_name.text = actor

            if getattr(my_show, '_actors', None):
                for actor in my_show['_actors']:
                    cur_actor = etree.SubElement(episode, 'actor')

                    if 'name' in actor and actor['name'].strip():
                        cur_actor_name = etree.SubElement(cur_actor, 'name')
                        cur_actor_name.text = actor['name'].strip()
                    else:
                        continue

                    if 'role' in actor and actor['role'].strip():
                        cur_actor_role = etree.SubElement(cur_actor, 'role')
                        cur_actor_role.text = actor['role'].strip()

                    if 'image' in actor and actor['image'].strip():
                        indexer_url = ''
                        if indexer_name == 'thetvdb':
                            indexer_url = 'http://thetvdb.com/banners/'
                        cur_actor_thumb = indexer_url + etree.SubElement(cur_actor, 'thumb')
                        cur_actor_thumb.text = actor['image'].strip()

        # Make it purdy
        helpers.indentXML(root_node)

        data = etree.ElementTree(root_node)

        return data


# present a standard 'interface' from the module
metadata_class = KODI_12PlusMetadata
