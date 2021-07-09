# coding=utf-8

from __future__ import unicode_literals

import datetime
import logging
import re


from babelfish import Country

from medusa import helpers
from medusa.app import TVDB_API_KEY
from medusa.helper.common import dateFormat, episode_num
from medusa.indexers.api import indexerApi
from medusa.indexers.config import INDEXER_TVDBV2
from medusa.indexers.exceptions import IndexerEpisodeNotFound, IndexerSeasonNotFound
from medusa.indexers.tvdbv2.api import API_BASE_TVDB
from medusa.logger.adapters.style import BraceAdapter
from medusa.metadata import generic

from six import string_types, text_type

try:
    import xml.etree.cElementTree as etree
except ImportError:
    import xml.etree.ElementTree as etree

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


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
    def _show_data(self, series_obj):
        """
        Creates an elementTree XML structure for an KODI-style tvshow.nfo and
        returns the resulting data object.

        show_obj: a Series instance to create the NFO for
        """

        my_show = self._get_show_data(series_obj)

        # If by any reason it couldn't get the shows indexer data let's not go throught the rest of this method
        # as that pretty useless.
        if not my_show:
            return False

        tv_node = etree.Element('tvshow')

        title = etree.SubElement(tv_node, 'title')
        title.text = my_show['seriesname']

        if getattr(my_show, 'rating', None):
            rating = etree.SubElement(tv_node, 'rating')
            rating.text = text_type(my_show['rating'])

        if getattr(my_show, 'firstaired', None):
            try:
                year_text = text_type(datetime.datetime.strptime(my_show['firstaired'], dateFormat).year)
                if year_text:
                    year = etree.SubElement(tv_node, 'year')
                    year.text = year_text
            except Exception:
                pass

        if getattr(my_show, 'overview', None):
            plot = etree.SubElement(tv_node, 'plot')
            plot.text = my_show['overview']

        # For now we're only using this for tvdb indexed shows. We should come with a proper strategy as how to use the
        # metadata for TMDB/TVMAZE shows. We could try to map it a tvdb show. Or keep mixing it.
        if series_obj.indexer == INDEXER_TVDBV2 and getattr(my_show, 'id', None):
            episode_guide = etree.SubElement(tv_node, 'episodeguide')
            episode_guide_url = etree.SubElement(episode_guide, 'url', cache='auth.json', post='yes')
            episode_guide_url.text = '{url}/login?{{"apikey":"{apikey}","id":{id}}}' \
                                     '|Content-Type=application/json'.format(url=API_BASE_TVDB,
                                                                             apikey=TVDB_API_KEY,
                                                                             id=my_show['id'])

        if getattr(my_show, 'contentrating', None):
            mpaa = etree.SubElement(tv_node, 'mpaa')
            mpaa.text = my_show['contentrating']

        if getattr(my_show, 'id', None):
            indexer_id = etree.SubElement(tv_node, 'id')
            indexer_id.text = text_type(my_show['id'])

            uniqueid = etree.SubElement(tv_node, 'uniqueid')
            uniqueid.set('type', series_obj.indexer_name)
            uniqueid.set('default', 'true')
            uniqueid.text = text_type(my_show['id'])

        if getattr(my_show, 'genre', None) and isinstance(my_show['genre'], string_types):
            for genre in self._split_info(my_show['genre']):
                cur_genre = etree.SubElement(tv_node, 'genre')
                cur_genre.text = genre

        if 'country_codes' in series_obj.imdb_info:
            for country in self._split_info(series_obj.imdb_info['country_codes']):
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
                    cur_actor_thumb = etree.SubElement(cur_actor, 'thumb')
                    cur_actor_thumb.text = actor['image'].strip()

        # Make it purdy
        helpers.indent_xml(tv_node)

        data = etree.ElementTree(tv_node)

        return data

    def _ep_data(self, ep_obj):
        """
        Creates an elementTree XML structure for an KODI-style episode.nfo and
        returns the resulting data object.

        show_obj: a Episode instance to create the NFO for
        """
        eps_to_write = [ep_obj] + ep_obj.related_episodes

        series_obj = self._get_show_data(ep_obj.series)
        if not series_obj:
            return None

        if len(eps_to_write) > 1:
            root_node = etree.Element('kodimultiepisode')
        else:
            root_node = etree.Element('episodedetails')

        # write an NFO containing info for all matching episodes
        for ep_to_write in eps_to_write:

            try:
                my_ep = series_obj[ep_to_write.season][ep_to_write.episode]
            except (IndexerEpisodeNotFound, IndexerSeasonNotFound):
                log.info(
                    u'Unable to find episode {ep_num} on {indexer}...'
                    u' has it been removed? Should I delete from db?', {
                        'ep_num': episode_num(ep_to_write.season, ep_to_write.episode),
                        'indexer': indexerApi(ep_obj.series.indexer).name,
                    }
                )
                return None

            if not getattr(my_ep, 'firstaired', None):
                my_ep['firstaired'] = text_type(datetime.date.fromordinal(1))

            if not getattr(my_ep, 'episodename', None):
                log.debug(u'Not generating nfo because the ep has no title')
                return None

            log.debug(u'Creating metadata for episode {0}',
                      episode_num(ep_obj.season, ep_obj.episode))

            if len(eps_to_write) > 1:
                episode = etree.SubElement(root_node, 'episodedetails')
            else:
                episode = root_node

            if getattr(my_ep, 'episodename', None):
                title = etree.SubElement(episode, 'title')
                title.text = my_ep['episodename']

            if getattr(series_obj, 'seriesname', None):
                showtitle = etree.SubElement(episode, 'showtitle')
                showtitle.text = series_obj['seriesname']

            season = etree.SubElement(episode, 'season')
            season.text = text_type(ep_to_write.season)

            episodenum = etree.SubElement(episode, 'episode')
            episodenum.text = text_type(ep_to_write.episode)

            uniqueid = etree.SubElement(episode, 'uniqueid')
            uniqueid.set('type', ep_obj.indexer_name)
            uniqueid.set('default', 'true')
            uniqueid.text = text_type(ep_to_write.indexerid)

            if ep_to_write.airdate != datetime.date.fromordinal(1):
                aired = etree.SubElement(episode, 'aired')
                aired.text = text_type(ep_to_write.airdate)

            if getattr(my_ep, 'overview', None):
                plot = etree.SubElement(episode, 'plot')
                plot.text = my_ep['overview']

            if ep_to_write.season and getattr(series_obj, 'runtime', None):
                runtime = etree.SubElement(episode, 'runtime')
                runtime.text = text_type(series_obj['runtime'])

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
                rating.text = text_type(my_ep['rating'])

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

            if getattr(series_obj, '_actors', None):
                for actor in series_obj['_actors']:
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
                        cur_actor_thumb = etree.SubElement(cur_actor, 'thumb')
                        cur_actor_thumb.text = actor['image'].strip()

        # Make it purdy
        helpers.indent_xml(root_node)

        data = etree.ElementTree(root_node)

        return data


# present a standard 'interface' from the module
metadata_class = KODI_12PlusMetadata
