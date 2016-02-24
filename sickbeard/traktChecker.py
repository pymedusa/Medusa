# coding=utf-8
# Author: Frank Fenton
# URL: http://code.google.com/p/sickbeard/
#
# This file is part of SickRage.
#
# SickRage is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# SickRage is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with SickRage. If not, see <http://www.gnu.org/licenses/>.

import os
import traceback
import datetime
from libtrakt.exceptions import TraktException # pylint: disable=import-error
from libtrakt.trakt import TraktApi # pylint: disable=import-error

import sickbeard
from sickbeard import logger
from sickbeard import helpers
from sickbeard import search_queue
from sickbeard import db
from sickbeard.common import SKIPPED, UNKNOWN, WANTED, Quality

from sickrage.helper.common import episode_num
from sickrage.helper.encoding import ek
from sickrage.helper.exceptions import ex
from sickrage.show.Show import Show


def setEpisodeToWanted(show, s, e):
    """
    Sets an episode to wanted, only if it is currently skipped
    """
    ep_obj = show.getEpisode(s, e)
    if ep_obj:

        with ep_obj.lock:
            if ep_obj.status != SKIPPED or ep_obj.airdate == datetime.date.fromordinal(1):
                return

            logger.log(u"Setting episode {show} {ep} to wanted".format
                       (show=show.name, ep=episode_num(s, e)))
            # figure out what segment the episode is in and remember it so we can backlog it

            ep_obj.status = WANTED
            ep_obj.saveToDB()

        cur_backlog_queue_item = search_queue.BacklogQueueItem(show, [ep_obj])
        sickbeard.searchQueueScheduler.action.add_item(cur_backlog_queue_item)

        logger.log(u"Starting backlog search for {show} {ep} because some episodes were set to wanted".format
                   (show=show.name, ep=episode_num(s, e)))


class TraktChecker(object):
    def __init__(self):
        self.trakt_api = TraktApi(sickbeard.SSL_VERIFY, sickbeard.TRAKT_TIMEOUT)
        self.todoWanted = []
        self.show_watchlist = {}
        self.episode_watchlist = {}
        self.collection_list = {}
        self.amActive = False

    def run(self, force=False): # pylint: disable=unused-argument
        self.amActive = True

        # add shows from Trakt watchlist
        if sickbeard.TRAKT_SYNC_WATCHLIST:
            self.todoWanted = []  # its about to all get re-added
            if len(sickbeard.ROOT_DIRS.split('|')) < 2:
                logger.log(u"No default root directory", logger.WARNING)
                return

            try:
                self.sync_watchlist()
            except Exception:
                logger.log(traceback.format_exc(), logger.DEBUG)

            try:
                # sync Trakt library with medusa library
                self.sync_library()
            except Exception:
                logger.log(traceback.format_exc(), logger.DEBUG)

        self.amActive = False

    def find_show(self, indexerid):

        try:
            trakt_library = self.trakt_api.traktRequest("sync/collection/shows") or []
            if not trakt_library:
                logger.log(u"No shows found in your library, aborting library update", logger.DEBUG)
                return

            trakt_show = [x for x in trakt_library if int(indexerid) in [int(x['show']['ids']['tvdb'] or 0), int(x['show']['ids']['tvrage'] or 0)]]
        except TraktException as e:
            logger.log(u"Could not connect to Trakt. Aborting library check. Error: {}".format(repr(e)), logger.WARNING)

        return trakt_show if trakt_show else None

    def remove_show_trakt_library(self, show_obj):
        if self.find_show(show_obj.indexerid):
            trakt_id = sickbeard.indexerApi(show_obj.indexer).config['trakt_id']

            # URL parameters
            data = {
                'shows': [
                    {
                        'title': show_obj.name,
                        'year': show_obj.startyear,
                        'ids': {}
                    }
                ]
            }

            if trakt_id == 'tvdb_id':
                data['shows'][0]['ids']['tvdb'] = show_obj.indexerid
            else:
                data['shows'][0]['ids']['tvrage'] = show_obj.indexerid

            logger.log(u"Removing '{}' from Trakt library".format(show_obj.name), logger.DEBUG)

            try:
                self.trakt_api.traktRequest("sync/collection/remove", data, method='POST')
            except TraktException as e:
                logger.log(u"Could not connect to Trakt. Aborting removing show '{}' from Trakt library. Error: {}".format(show_obj.name, repr(e)), logger.WARNING)

    def add_show_trakt_library(self, show_obj):
        """
        Sends a request to trakt indicating that the given show and all its episodes is part of our library.

        show_obj: The TVShow object to add to trakt
        """
        data = {}

        if not self.find_show(show_obj.indexerid):
            trakt_id = sickbeard.indexerApi(show_obj.indexer).config['trakt_id']
            # URL parameters
            data = {
                'shows': [
                    {
                        'title': show_obj.name,
                        'year': show_obj.startyear,
                        'ids': {}
                    }
                ]
            }

            if trakt_id == 'tvdb_id':
                data['shows'][0]['ids']['tvdb'] = show_obj.indexerid
            else:
                data['shows'][0]['ids']['tvrage'] = show_obj.indexerid

        if data:
            logger.log(u"Adding '{}' to Trakt library".format(show_obj.name), logger.DEBUG)

            try:
                self.trakt_api.traktRequest("sync/collection", data, method='POST')
            except TraktException as e:
                logger.log(u"Could not connect to Trakt. Aborting adding show '{}' to Trakt library. Error: {}".format(show_obj.name, repr(e)), logger.WARNING)
                return

    def sync_library(self):
        if sickbeard.TRAKT_SYNC and sickbeard.USE_TRAKT:
            logger.log(u"Starting to sync Medusa with Trakt collection", logger.DEBUG)

            if self._get_show_collection():
                self.add_episode_trakt_collection()
                if sickbeard.TRAKT_SYNC_REMOVE:
                    self.remove_episode_trakt_collection()

    def remove_episode_trakt_collection(self):
        if sickbeard.TRAKT_SYNC_REMOVE and sickbeard.TRAKT_SYNC and sickbeard.USE_TRAKT:

            main_db_con = db.DBConnection()
            sql_selection = 'select tv_shows.indexer, tv_shows.startyear, showid, show_name, season, episode, tv_episodes.status, tv_episodes.location from tv_episodes,tv_shows where tv_shows.indexer_id = tv_episodes.showid'
            episodes = main_db_con.select(sql_selection)

            if episodes:
                trakt_data = []

                for cur_episode in episodes:
                    trakt_id = sickbeard.indexerApi(cur_episode["indexer"]).config['trakt_id']

                    if self._check_list(trakt_id, cur_episode["showid"], cur_episode["season"], cur_episode["episode"], List='Collection'):
                        if cur_episode["location"] == '':
                            logger.log(u"Removing Episode {show} {ep} from collection".format
                                       (show=cur_episode["show_name"],
                                        ep=episode_num(cur_episode["season"], cur_episode["episode"])),
                                       logger.DEBUG)
                            trakt_data.append((cur_episode["showid"], cur_episode["indexer"], cur_episode["show_name"], cur_episode["startyear"], cur_episode["season"], cur_episode["episode"]))

                if trakt_data:
                    try:
                        data = self.trakt_bulk_data_generate(trakt_data)
                        self.trakt_api.traktRequest("sync/collection/remove", data, method='POST')
                        self._get_show_collection()
                    except TraktException as e:
                        logger.log(u"Could not connect to Trakt. Error: {}".format(ex(e)), logger.WARNING)


    def add_episode_trakt_collection(self):
        if sickbeard.TRAKT_SYNC and sickbeard.USE_TRAKT:

            main_db_con = db.DBConnection()
            sql_selection = 'select tv_shows.indexer, tv_shows.startyear, showid, show_name, season, episode from tv_episodes,tv_shows where tv_shows.indexer_id = tv_episodes.showid and tv_episodes.status in (' + ','.join([str(x) for x in Quality.DOWNLOADED + Quality.ARCHIVED]) + ')'
            episodes = main_db_con.select(sql_selection)

            if episodes:
                trakt_data = []

                for cur_episode in episodes:
                    trakt_id = sickbeard.indexerApi(cur_episode["indexer"]).config['trakt_id']

                    if not self._check_list(trakt_id, cur_episode["showid"], cur_episode["season"], cur_episode["episode"], List='Collection'):
                        logger.log(u"Adding Episode {show} {ep} to collection".format
                                   (show=cur_episode["show_name"],
                                    ep=episode_num(cur_episode["season"], cur_episode["episode"])),
                                   logger.DEBUG)
                        trakt_data.append((cur_episode["showid"], cur_episode["indexer"], cur_episode["show_name"], cur_episode["startyear"], cur_episode["season"], cur_episode["episode"]))

                if trakt_data:
                    try:
                        data = self.trakt_bulk_data_generate(trakt_data)
                        self.trakt_api.traktRequest("sync/collection", data, method='POST')
                        self._get_show_collection()
                    except TraktException as e:
                        logger.log(u"Could not connect to Trakt. Error: {}".format(ex(e)), logger.WARNING)


    def sync_watchlist(self):
        if sickbeard.TRAKT_SYNC_WATCHLIST and sickbeard.USE_TRAKT:
            logger.log(u"Starting to sync Medusa with Trakt Watchlist", logger.DEBUG)

            self.remove_from_library()

            if self._get_show_watchlist():
                logger.log(u"Syncing shows with Trakt watchlist", logger.DEBUG)
                self.add_show_watchlist()
                self.fetch_trakt_shows()

            if self._get_episode_watchlist():
                logger.log(u"Syncing episodes with Trakt watchlist", logger.DEBUG)
                self.remove_episode_watchlist()
                self.add_episode_watchlist()
                self.fetch_trakt_episodes()

            logger.log(u"Medusa is synced with Trakt watchlist", logger.DEBUG)

    def remove_episode_watchlist(self):
        if sickbeard.TRAKT_SYNC_WATCHLIST and sickbeard.USE_TRAKT:

            main_db_con = db.DBConnection()
            sql_selection = 'select tv_shows.indexer, tv_shows.startyear, showid, show_name, season, episode, tv_episodes.status from tv_episodes,tv_shows where tv_shows.indexer_id = tv_episodes.showid'
            episodes = main_db_con.select(sql_selection)

            if episodes:
                trakt_data = []

                for cur_episode in episodes:
                    trakt_id = sickbeard.indexerApi(cur_episode["indexer"]).config['trakt_id']

                    if self._check_list(trakt_id, cur_episode["showid"], cur_episode["season"], cur_episode["episode"]):
                        if cur_episode["status"] not in Quality.SNATCHED + Quality.SNATCHED_PROPER + [UNKNOWN] + [WANTED]:
                            logger.log(u"Removing Episode {show} {ep} from watchlist".format
                                       (show=cur_episode["show_name"],
                                        ep=episode_num(cur_episode["season"], cur_episode["episode"])),
                                       logger.DEBUG)
                            trakt_data.append((cur_episode["showid"], cur_episode["indexer"], cur_episode["show_name"], cur_episode["startyear"], cur_episode["season"], cur_episode["episode"]))

                if trakt_data:
                    try:
                        data = self.trakt_bulk_data_generate(trakt_data)
                        self.trakt_api.traktRequest("sync/watchlist/remove", data, method='POST')
                        self._get_episode_watchlist()
                    except TraktException as e:
                        logger.log(u"Could not connect to Trakt. Error: {}".format(ex(e)), logger.WARNING)


    def add_episode_watchlist(self):
        if sickbeard.TRAKT_SYNC_WATCHLIST and sickbeard.USE_TRAKT:

            main_db_con = db.DBConnection()
            sql_selection = 'select tv_shows.indexer, tv_shows.startyear, showid, show_name, season, episode from tv_episodes,tv_shows where tv_shows.indexer_id = tv_episodes.showid and tv_episodes.status in (' + ','.join([str(x) for x in Quality.SNATCHED + Quality.SNATCHED_PROPER + [WANTED]]) + ')'
            episodes = main_db_con.select(sql_selection)

            if episodes:
                trakt_data = []

                for cur_episode in episodes:
                    trakt_id = sickbeard.indexerApi(cur_episode["indexer"]).config['trakt_id']

                    if not self._check_list(trakt_id, cur_episode["showid"], cur_episode["season"], cur_episode["episode"]):
                        logger.log(u"Adding Episode {show} {ep} to watchlist".format
                                   (show=cur_episode["show_name"],
                                    ep=episode_num(cur_episode["season"], cur_episode["episode"])),
                                   logger.DEBUG)
                        trakt_data.append((cur_episode["showid"], cur_episode["indexer"], cur_episode["show_name"], cur_episode["startyear"], cur_episode["season"],
                                           cur_episode["episode"]))

                if trakt_data:
                    try:
                        data = self.trakt_bulk_data_generate(trakt_data)
                        self.trakt_api.traktRequest("sync/watchlist", data, method='POST')
                        self._get_episode_watchlist()
                    except TraktException as e:
                        logger.log(u"Could not connect to Trakt. Error: {}".format(ex(e)), logger.WARNING)



    def add_show_watchlist(self):
        if sickbeard.TRAKT_SYNC_WATCHLIST and sickbeard.USE_TRAKT:
            logger.log(u"Syncing shows to Trakt watchlist", logger.DEBUG)

            if sickbeard.showList:
                trakt_data = []

                for show_obj in sickbeard.showList:
                    trakt_id = sickbeard.indexerApi(show_obj.indexer).config['trakt_id']

                    if not self._check_list(trakt_id, show_obj.indexerid, 0, 0, List='Show'):
                        logger.log(u"Adding Show '{}' with ID: '{}' to Trakt watchlist".format(show_obj.name, show_obj.indexerid), logger.DEBUG)
                        show_el = {'title': show_obj.name, 'year': show_obj.startyear, 'ids': {}}
                        if trakt_id == 'tvdb_id':
                            show_el['ids']['tvdb'] = show_obj.indexerid
                        else:
                            show_el['ids']['tvrage'] = show_obj.indexerid
                        trakt_data.append(show_el)

                if trakt_data:
                    try:
                        data = {'shows': trakt_data}
                        self.trakt_api.traktRequest("sync/watchlist", data, method='POST')
                        self._get_show_watchlist()
                    except TraktException as e:
                        logger.log(u"Could not connect to Trakt. Error: {}".format(ex(e)), logger.WARNING)


    def remove_from_library(self):
        if sickbeard.TRAKT_SYNC_WATCHLIST and sickbeard.USE_TRAKT and sickbeard.TRAKT_REMOVE_SHOW_FROM_SICKRAGE:
            logger.log(u"Retrieving ended/completed shows to remove from Medusa", logger.DEBUG)

            if sickbeard.showList:
                for show in sickbeard.showList:
                    if show.status == "Ended":
                        if not show.imdbid:
                            logger.log(u'Could not check trakt progress for {0} because the imdb id is missing from tvdb data, skipping'.format
                                       (show.name), logger.WARNING)
                            continue

                        try:
                            progress = self.trakt_api.traktRequest("shows/" + show.imdbid + "/progress/watched") or []
                        except TraktException as e:
                            logger.log(u"Could not connect to Trakt. Aborting removing show '{}' from Medusa. Error: {}".format(show.name, repr(e)), logger.WARNING)
                            continue

                        if not progress:
                            continue

                        if progress.get('aired', True) == progress.get('completed', False):
                            sickbeard.showQueueScheduler.action.removeShow(show, full=True)
                            logger.log(u"Show '{}' has been removed from Medusa".format(show.name), logger.DEBUG)


    def fetch_trakt_shows(self):

        if not self.show_watchlist:
            logger.log(u"No shows found in your watchlist, aborting watchlist update", logger.DEBUG)
        else:
            indexer = int(sickbeard.TRAKT_DEFAULT_INDEXER)
            trakt_id = sickbeard.indexerApi(indexer).config['trakt_id']

            for watchlisted_show in self.show_watchlist[trakt_id]:
                indexer_id = int(watchlisted_show)
                show_obj = self.show_watchlist[trakt_id][watchlisted_show]
                if show_obj['year'] and show_obj['slug'].endswith(str(show_obj['year'])):
                    show_name = '{} ({})'.format(show_obj['title'], show_obj['year'])
                else:
                    show_name = show_obj['title']

                if int(sickbeard.TRAKT_METHOD_ADD) != 2:
                    self.add_show(indexer, indexer_id, show_name, SKIPPED)
                else:
                    self.add_show(indexer, indexer_id, show_name, WANTED)

                if int(sickbeard.TRAKT_METHOD_ADD) == 1:
                    new_show = Show.find(sickbeard.showList, indexer_id)

                    if new_show:
                        setEpisodeToWanted(new_show, 1, 1)
                    else:
                        self.todoWanted.append(indexer_id, 1, 1)


    def fetch_trakt_episodes(self):
        """
        Sets episodes to wanted that are in trakt watchlist
        """
        logger.log(u"Retrieving episodes to sync with Trakt episode's watchlist", logger.DEBUG)

        if not self.episode_watchlist:
            logger.log(u"No episode found in your watchlist, aborting episode update", logger.DEBUG)
            return

        managed_show = []

        indexer = int(sickbeard.TRAKT_DEFAULT_INDEXER)
        trakt_id = sickbeard.indexerApi(indexer).config['trakt_id']

        for watchlist_item in self.episode_watchlist[trakt_id]:
            indexer_id = int(watchlist_item)
            show = self.episode_watchlist[trakt_id][watchlist_item]

            new_show = Show.find(sickbeard.showList, indexer_id)

            try:
                if not new_show:
                    if indexer_id not in managed_show:
                        self.add_show(indexer, indexer_id, show['title'], SKIPPED)
                        managed_show.append(indexer_id)

                        for season_item in show['seasons']:
                            season = int(season_item)

                            for episode_item in show['seasons'][season_item]['episodes']:
                                self.todoWanted.append((indexer_id, season, int(episode_item)))
                else:
                    if new_show.indexer == indexer:
                        for season_item in show['seasons']:
                            season = int(season_item)

                            for episode_item in show['seasons'][season_item]['episodes']:
                                setEpisodeToWanted(new_show, season, int(episode_item))
            except TypeError:
                logger.log(u"Could not parse the output from trakt for '{}' ".format(show["title"]), logger.DEBUG)


    @staticmethod
    def add_show(indexer, indexer_id, show_name, status):
        """
        Adds a new show with the default settings
        """
        if not Show.find(sickbeard.showList, int(indexer_id)):
            root_dirs = sickbeard.ROOT_DIRS.split('|')

            location = root_dirs[int(root_dirs[0]) + 1] if root_dirs else None

            if location:
                show_path = ek(os.path.join, location, show_name)
                logger.log(u"Adding show '{}' with ID: '{}' in location: '{}'".format(show_name, indexer_id, show_path))
                dir_exists = helpers.makeDir(show_path)

                if not dir_exists:
                    logger.log(u"Unable to create the folder {}. Unable to add the show {}".format(show_path, show_name), logger.WARNING)
                    return
                else:
                    logger.log(u"Creating the folder '{}'".format(show_path), logger.DEBUG)
                    helpers.chmodAsParent(show_path)

                sickbeard.showQueueScheduler.action.addShow(indexer, indexer_id, show_path,
                                                            default_status=status,
                                                            quality=int(sickbeard.QUALITY_DEFAULT),
                                                            flatten_folders=int(sickbeard.FLATTEN_FOLDERS_DEFAULT),
                                                            paused=sickbeard.TRAKT_START_PAUSED,
                                                            default_status_after=status)
            else:
                logger.log(u"There was an error creating the show, no root directory setting found", logger.WARNING)
                return

    def manage_new_show(self, show):
        logger.log(u"Checking if trakt watchlist wants to search for episodes from new show " + show.name, logger.DEBUG)
        episodes = [i for i in self.todoWanted if i[0] == show.indexerid]

        for episode in episodes:
            self.todoWanted.remove(episode)
            setEpisodeToWanted(show, episode[1], episode[2])

    def _check_list(self, trakt_id, showid, season, episode, List=None): # pylint: disable=too-many-arguments
        """
         Check in the Watchlist or collection list for Show
         Is the Show, Season and Episode in the trakt_id list (tvdb / tvrage)
        """

        if "Collection" == List:
            try:
                if self.collection_list[trakt_id][showid]['seasons'][season]['episodes'][episode] == episode:
                    return True
            except Exception:
                return False
        elif "Show" == List:
            try:
                if self.show_watchlist[trakt_id][showid]['id'] == showid:
                    return True
            except Exception:
                return False
        else:
            try:
                if self.episode_watchlist[trakt_id][showid]['seasons'][season]['episodes'][episode] == episode:
                    return True
            except Exception:
                return False

    def _get_show_watchlist(self):
        """
        Get Watchlist and parse once into addressable structure
        """
        try:
            self.show_watchlist = {'tvdb_id': {}, 'tvrage_id': {}}
            trakt_show_watchlist = self.trakt_api.traktRequest("sync/watchlist/shows")
            tvdb_id = 'tvdb'
            tvrage_id = 'tvrage'

            for watchlist_item in trakt_show_watchlist:
                tvdb = True if watchlist_item['show']['ids']["tvdb"] else False
                tvrage = True if watchlist_item['show']['ids']["tvrage"] else False
                title = watchlist_item['show']['title']
                year = watchlist_item['show']['year']
                slug = watchlist_item['show']['ids']['slug']

                if tvdb:
                    showid = watchlist_item['show']['ids'][tvdb_id]
                    self.show_watchlist[tvdb_id + '_id'][showid] = {'id': showid, 'title': title, 'year': year, 'slug': slug}

                if tvrage:
                    showid = watchlist_item['show']['ids'][tvrage_id]
                    self.show_watchlist[tvrage_id + '_id'][showid] = {'id': showid, 'title': title, 'year': year, 'slug': slug}
        except TraktException as e:
            logger.log(u"Could not connect to Trakt. Unable to retrieve show's watchlist: {}".format(repr(e)), logger.WARNING)
            return False
        return True

    def _get_episode_watchlist(self):
        """
         Get Watchlist and parse once into addressable structure
        """
        try:
            self.episode_watchlist = {'tvdb_id': {}, 'tvrage_id': {}}
            trakt_episode_watchlist = self.trakt_api.traktRequest("sync/watchlist/episodes")
            tvdb_id = 'tvdb'
            tvrage_id = 'tvrage'

            for watchlist_item in trakt_episode_watchlist:
                tvdb = True if watchlist_item['show']['ids']["tvdb"] else False
                tvrage = True if watchlist_item['show']['ids']["tvrage"] else False
                title = watchlist_item['show']['title']
                year = watchlist_item['show']['year']
                season = watchlist_item['episode']['season']
                episode = watchlist_item['episode']['number']

                if tvdb:
                    showid = watchlist_item['show']['ids'][tvdb_id]

                    if showid not in self.episode_watchlist[tvdb_id + '_id'].keys():
                        self.episode_watchlist[tvdb_id + '_id'][showid] = {'id': showid, 'title': title, 'year': year, 'seasons': {}}

                    if season not in self.episode_watchlist[tvdb_id + '_id'][showid]['seasons'].keys():
                        self.episode_watchlist[tvdb_id + '_id'][showid]['seasons'][season] = {'s': season, 'episodes': {}}

                    if episode not in self.episode_watchlist[tvdb_id + '_id'][showid]['seasons'][season]['episodes'].keys():
                        self.episode_watchlist[tvdb_id + '_id'][showid]['seasons'][season]['episodes'][episode] = episode

                if tvrage:
                    showid = watchlist_item['show']['ids'][tvrage_id]

                    if showid not in self.episode_watchlist[tvrage_id + '_id'].keys():
                        self.episode_watchlist[tvrage_id + '_id'][showid] = {'id': showid, 'title': title, 'year': year, 'seasons': {}}

                    if season not in self.episode_watchlist[tvrage_id + '_id'][showid]['seasons'].keys():
                        self.episode_watchlist[tvrage_id + '_id'][showid]['seasons'][season] = {'s': season, 'episodes': {}}

                    if episode not in self.episode_watchlist[tvrage_id + '_id'][showid]['seasons'][season]['episodes'].keys():
                        self.episode_watchlist[tvrage_id + '_id'][showid]['seasons'][season]['episodes'][episode] = episode
        except TraktException as e:
            logger.log(u"Could not connect to Trakt. Unable to retrieve episode's watchlist: {}".format(repr(e)), logger.WARNING)
            return False
        return True

    def _get_show_collection(self): # pylint: disable=too-many-branches
        """
        Get Collection and parse once into addressable structure
        """
        try:
            self.collection_list = {'tvdb_id': {}, 'tvrage_id': {}}
            logger.log(u"Getting Show Collection", logger.DEBUG)
            trakt_collection = self.trakt_api.traktRequest("sync/collection/shows")
            tvdb_id = 'tvdb'
            tvrage_id = 'tvrage'

            for watchlist_item in trakt_collection:
                tvdb = True if watchlist_item['show']['ids']["tvdb"] else False
                tvrage = True if watchlist_item['show']['ids']["tvrage"] else False
                title = watchlist_item['show']['title']
                year = watchlist_item['show']['year']

                if 'seasons' in watchlist_item:
                    for season_item in watchlist_item['seasons']:
                        for episode_item in season_item['episodes']:
                            season = season_item['number']
                            episode = episode_item['number']

                            if tvdb:
                                showid = watchlist_item['show']['ids'][tvdb_id]

                                if showid not in self.collection_list[tvdb_id + '_id'].keys():
                                    self.collection_list[tvdb_id + '_id'][showid] = {'id': showid, 'title': title, 'year': year, 'seasons': {}}

                                if season not in self.collection_list[tvdb_id + '_id'][showid]['seasons'].keys():
                                    self.collection_list[tvdb_id + '_id'][showid]['seasons'][season] = {'s': season, 'episodes': {}}

                                if episode not in self.collection_list[tvdb_id + '_id'][showid]['seasons'][season]['episodes'].keys():
                                    self.collection_list[tvdb_id + '_id'][showid]['seasons'][season]['episodes'][episode] = episode

                            if tvrage:
                                showid = watchlist_item['show']['ids'][tvrage_id]

                                if showid not in self.collection_list[tvrage_id + '_id'].keys():
                                    self.collection_list[tvrage_id + '_id'][showid] = {'id': showid, 'title': title, 'year': year, 'seasons': {}}

                                if season not in self.collection_list[tvrage_id + '_id'][showid]['seasons'].keys():
                                    self.collection_list[tvrage_id + '_id'][showid]['seasons'][season] = {'s': season, 'episodes': {}}

                                if episode not in self.collection_list[tvrage_id + '_id'][showid]['seasons'][season]['episodes'].keys():
                                    self.collection_list[tvrage_id + '_id'][showid]['seasons'][season]['episodes'][episode] = episode
        except TraktException as e:
            logger.log(u"Could not connect to Trakt. Unable to retrieve show's collection: {}".format(repr(e)), logger.WARNING)
            return False
        return True

    @staticmethod
    def trakt_bulk_data_generate(data): # pylint: disable=too-many-locals
        """
        Build the JSON structure to send back to Trakt
        """
        uniqueShows = {}
        uniqueSeasons = {}

        for showid, indexerid, show_name, startyear, season, episode in data:
            if showid not in uniqueShows:
                uniqueShows[showid] = {'title': show_name, 'year': startyear, 'ids': {}, 'seasons': []}
                trakt_id = sickbeard.indexerApi(indexerid).config['trakt_id']

                if trakt_id == 'tvdb_id':
                    uniqueShows[showid]['ids']["tvdb"] = showid
                else:
                    uniqueShows[showid]['ids']["tvrage"] = showid
                uniqueSeasons[showid] = []

        # Get the unique seasons per Show
        for showid, indexerid, show_name, startyear, season, episode in data:
            if season not in uniqueSeasons[showid]:
                uniqueSeasons[showid].append(season)

        # build the query
        showList = []
        seasonsList = {}

        for searchedShow in uniqueShows:
            seasonsList[searchedShow] = []

            for searchedSeason in uniqueSeasons[searchedShow]:
                episodesList = []

                for showid, indexerid, show_name, startyear, season, episode in data:
                    if season == searchedSeason and showid == searchedShow:
                        episodesList.append({'number': episode})
                show = uniqueShows[searchedShow]
                show['seasons'].append({'number': searchedSeason, 'episodes': episodesList})
            showList.append(show)
        post_data = {'shows': showList}
        return post_data
