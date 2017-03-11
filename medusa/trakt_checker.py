# coding=utf-8
# Author: Frank Fenton
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

from __future__ import unicode_literals

import datetime
import traceback

from traktor import TokenExpiredException, TraktApi, TraktException
from . import app, db, logger, ui
from .common import Quality, SKIPPED, UNKNOWN, WANTED
from .helper.common import episode_num
from .helper.exceptions import ex
from .indexers.indexer_api import indexerApi
from .search.queue import BacklogQueueItem
from .show.show import Show


def setEpisodeToWanted(show, s, e):
    """
    Sets an episode to wanted, only if it is currently skipped
    """
    ep_obj = show.get_episode(s, e)
    if ep_obj:

        with ep_obj.lock:
            if ep_obj.status != SKIPPED or ep_obj.airdate == datetime.date.fromordinal(1):
                return

            logger.log('Setting episode {show} {ep} to wanted'.format
                       (show=show.name, ep=episode_num(s, e)))
            # figure out what segment the episode is in and remember it so we can backlog it

            ep_obj.status = WANTED
            ep_obj.save_to_db()

        cur_backlog_queue_item = BacklogQueueItem(show, [ep_obj])
        app.search_queue_scheduler.action.add_item(cur_backlog_queue_item)

        logger.log('Starting backlog search for {show} {ep} because some episodes were set to wanted'.format
                   (show=show.name, ep=episode_num(s, e)))


class TraktChecker(object):
    def __init__(self):
        trakt_settings = {'trakt_api_key': app.TRAKT_API_KEY,
                          'trakt_api_secret': app.TRAKT_API_SECRET,
                          'trakt_access_token': app.TRAKT_ACCESS_TOKEN,
                          'trakt_refresh_token': app.TRAKT_REFRESH_TOKEN}
        self.trakt_api = TraktApi(app.SSL_VERIFY, app.TRAKT_TIMEOUT, **trakt_settings)
        self.todoWanted = []
        self.show_watchlist = {}
        self.episode_watchlist = {}
        self.collection_list = {}
        self.amActive = False

    def run(self, force=False):  # pylint: disable=unused-argument
        self.amActive = True

        # add shows from Trakt watchlist
        if app.TRAKT_SYNC_WATCHLIST:
            self.todoWanted = []  # its about to all get re-added
            if len(app.ROOT_DIRS.split('|')) < 2:
                logger.log('No default root directory', logger.WARNING)
                ui.notifications.error('Unable to add show',
                                       'You do not have any default root directory configured. '
                                       'Please configure in general settings!')
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

    def _request(self, path, data=None, method='GET'):
        """Fetch shows from trakt and store the refresh token when needed."""
        try:
            library_shows = self.trakt_api.request(path, data, method=method) or []
            if self.trakt_api.access_token_refreshed:
                app.TRAKT_ACCESS_TOKEN = self.trakt_api.access_token
                app.TRAKT_REFRESH_TOKEN = self.trakt_api.refresh_token
                app.instance.save_config()
        except TokenExpiredException:
            app.TRAKT_ACCESS_TOKEN = ''
            raise

        return library_shows

    def find_show(self, indexerid):

        try:
            trakt_library = self._request('sync/collection/shows') or []
            if not trakt_library:
                logger.log('No shows found in your library, aborting library update', logger.DEBUG)
                return

            trakt_show = [x for x in trakt_library if int(indexerid) in [int(x['show']['ids']['tvdb'] or 0), int(x['show']['ids']['tvrage'] or 0)]]
        except TraktException as e:
            logger.log('Could not connect to Trakt. Aborting library check. Error: {0}'.format(repr(e)), logger.WARNING)

        return trakt_show if trakt_show else None

    def remove_show_trakt_library(self, show_obj):
        """Remove Show from trakt collections."""
        if self.find_show(show_obj.indexerid):
            trakt_id = indexerApi(show_obj.indexer).config['trakt_id']

            # URL parameters
            data = {
                'shows': [
                    {
                        'title': show_obj.name,
                        'year': show_obj.start_year,
                        'ids': {}
                    }
                ]
            }

            if trakt_id == 'tvdb_id':
                data['shows'][0]['ids']['tvdb'] = show_obj.indexerid
            else:
                data['shows'][0]['ids']['tvrage'] = show_obj.indexerid

            logger.log('Removing {0} from Trakt library'.format(show_obj.name), logger.DEBUG)

            # Remove all episodes from the Trakt collection for this show
            try:
                self.remove_episode_trakt_collection(filter_show=show_obj)
            except TraktException as e:
                logger.log('Could not connect to Trakt. Aborting removing episodes for show {0} from Trakt library. Error: {1}'.
                           format(show_obj.name, repr(e)), logger.WARNING)

            try:
                self._request('sync/collection/remove', data, method='POST')
            except TraktException as e:
                logger.log('Could not connect to Trakt. Aborting removing show {0} from Trakt library. Error: {1}'.
                           format(show_obj.name, repr(e)), logger.WARNING)

    def add_show_trakt_library(self, show_obj):
        """
        Sends a request to trakt indicating that the given show and all its episodes is part of our library.

        show_obj: The Series object to add to trakt
        """
        data = {}

        if not self.find_show(show_obj.indexerid):
            trakt_id = indexerApi(show_obj.indexer).config['trakt_id']
            # URL parameters
            data = {
                'shows': [
                    {
                        'title': show_obj.name,
                        'year': show_obj.start_year,
                        'ids': {}
                    }
                ]
            }

            if trakt_id == 'tvdb_id':
                data['shows'][0]['ids']['tvdb'] = show_obj.indexerid
            else:
                data['shows'][0]['ids']['tvrage'] = show_obj.indexerid

        if data:
            logger.log('Adding {0} to Trakt library'.format(show_obj.name), logger.DEBUG)

            try:
                self._request('sync/collection', data, method='POST')
            except TraktException as e:
                logger.log('Could not connect to Trakt. Aborting adding show {0} to Trakt library. Error: {1}'.format(show_obj.name, repr(e)), logger.WARNING)
                return

    def sync_library(self):
        if app.TRAKT_SYNC and app.USE_TRAKT:
            logger.log('Starting to sync Medusa with Trakt collection', logger.DEBUG)

            if self._get_show_collection():
                self.add_episode_trakt_collection()
                if app.TRAKT_SYNC_REMOVE:
                    self.remove_episode_trakt_collection()

    def remove_episode_trakt_collection(self, filter_show=None):
        if app.TRAKT_SYNC_REMOVE and app.TRAKT_SYNC and app.USE_TRAKT:

            params = []
            main_db_con = db.DBConnection()
            sql_selection = b'select tv_shows.indexer, tv_shows.startyear, showid, show_name, season, episode, tv_episodes.status,' \
                            b'tv_episodes.location from tv_episodes, tv_shows where tv_shows.indexer_id = tv_episodes.showid'
            if filter_show:
                sql_selection += b' AND tv_shows.indexer_id = ? AND tv_shows.indexer = ?'
                params = [filter_show.indexerid, filter_show.indexer]

            episodes = main_db_con.select(sql_selection, params)

            if episodes:
                trakt_data = []

                for cur_episode in episodes:
                    trakt_id = indexerApi(cur_episode[b'indexer']).config['trakt_id']

                    if self._check_list(trakt_id, cur_episode[b'showid'], cur_episode[b'season'], cur_episode[b'episode'],
                                        List='Collection'):

                        if cur_episode[b'location'] == '':
                            logger.log('Removing Episode {show} {ep} from collection'.format
                                       (show=cur_episode[b'show_name'],
                                        ep=episode_num(cur_episode[b'season'], cur_episode[b'episode'])),
                                       logger.DEBUG)
                            trakt_data.append((cur_episode[b'showid'], cur_episode[b'indexer'], cur_episode[b'show_name'],
                                               cur_episode[b'startyear'], cur_episode[b'season'], cur_episode[b'episode']))

                if trakt_data:
                    try:
                        data = self.trakt_bulk_data_generate(trakt_data)
                        self._request('sync/collection/remove', data, method='POST')
                        self._get_show_collection()
                    except TraktException as e:
                        logger.log('Could not connect to Trakt. Error: {0}'.format(ex(e)), logger.WARNING)

    def add_episode_trakt_collection(self):
        """Add all episodes from local library to Trakt collections. Enabled in app.TRAKT_SYNC_WATCHLIST setting."""
        if app.TRAKT_SYNC and app.USE_TRAKT:

            main_db_con = db.DBConnection()
            selection_status = ['?' for _ in Quality.DOWNLOADED + Quality.ARCHIVED]
            sql_selection = b'select tv_shows.indexer, tv_shows.startyear, showid, show_name, season, ' \
                            b'episode from tv_episodes,tv_shows where tv_shows.indexer_id = tv_episodes.showid ' \
                            b"and tv_episodes.status in ({0}) and tv_episodes.location <> ''".format(','.join(selection_status))
            episodes = main_db_con.select(sql_selection, Quality.DOWNLOADED + Quality.ARCHIVED)

            if episodes:
                trakt_data = []

                for cur_episode in episodes:
                    trakt_id = indexerApi(cur_episode[b'indexer']).config['trakt_id']

                    if not self._check_list(trakt_id, cur_episode[b'showid'], cur_episode[b'season'], cur_episode[b'episode'], List='Collection'):
                        logger.log('Adding Episode {show} {ep} to collection'.format
                                   (show=cur_episode[b'show_name'],
                                    ep=episode_num(cur_episode[b'season'], cur_episode[b'episode'])),
                                   logger.DEBUG)
                        trakt_data.append((cur_episode[b'showid'], cur_episode[b'indexer'], cur_episode[b'show_name'], cur_episode[b'startyear'], cur_episode[b'season'], cur_episode[b'episode']))

                if trakt_data:
                    try:
                        data = self.trakt_bulk_data_generate(trakt_data)
                        self._request('sync/collection', data, method='POST')
                        self._get_show_collection()
                    except TraktException as e:
                        logger.log('Could not connect to Trakt. Error: {0}'.format(ex(e)), logger.WARNING)

    def sync_watchlist(self):
        if app.TRAKT_SYNC_WATCHLIST and app.USE_TRAKT:
            logger.log('Starting to sync Medusa with Trakt Watchlist', logger.DEBUG)

            self.remove_from_library()

            if self._get_show_watchlist():
                logger.log('Syncing shows with Trakt watchlist', logger.DEBUG)
                self.add_show_watchlist()
                self.fetch_trakt_shows()

            if self._get_episode_watchlist():
                logger.log('Syncing episodes with Trakt watchlist', logger.DEBUG)
                self.remove_episode_watchlist()
                self.add_episode_watchlist()
                self.fetch_trakt_episodes()

            logger.log('Medusa is synced with Trakt watchlist', logger.DEBUG)

    def remove_episode_watchlist(self):
        if app.TRAKT_SYNC_WATCHLIST and app.USE_TRAKT:

            main_db_con = db.DBConnection()
            sql_selection = b'select tv_shows.indexer, tv_shows.startyear, showid, show_name, season, episode, ' \
                            b'tv_episodes.status from tv_episodes,tv_shows where tv_shows.indexer_id = tv_episodes.showid'
            episodes = main_db_con.select(sql_selection)

            if episodes:
                trakt_data = []

                for cur_episode in episodes:
                    trakt_id = indexerApi(cur_episode[b'indexer']).config['trakt_id']

                    if self._check_list(trakt_id, cur_episode[b'showid'], cur_episode[b'season'], cur_episode[b'episode']):
                        if cur_episode[b'status'] not in Quality.SNATCHED + Quality.SNATCHED_PROPER + [UNKNOWN] + [WANTED]:
                            logger.log('Removing Episode {show} {ep} from watchlist'.format
                                       (show=cur_episode[b'show_name'],
                                        ep=episode_num(cur_episode[b'season'], cur_episode[b'episode'])),
                                       logger.DEBUG)
                            trakt_data.append((cur_episode[b'showid'], cur_episode[b'indexer'], cur_episode[b'show_name'], cur_episode[b'startyear'], cur_episode[b'season'], cur_episode[b'episode']))

                if trakt_data:
                    try:
                        data = self.trakt_bulk_data_generate(trakt_data)
                        self._request('sync/watchlist/remove', data, method='POST')
                        self._get_episode_watchlist()
                    except TraktException as e:
                        logger.log('Could not connect to Trakt. Error: {0}'.format(ex(e)), logger.WARNING)

    def add_episode_watchlist(self):
        if app.TRAKT_SYNC_WATCHLIST and app.USE_TRAKT:

            main_db_con = db.DBConnection()
            selection_status = [b'?' for _ in Quality.SNATCHED + Quality.SNATCHED_PROPER + [WANTED]]
            sql_selection = b'select tv_shows.indexer, tv_shows.startyear, showid, show_name, season, episode from tv_episodes, ' \
                            b'tv_shows where tv_shows.indexer_id = tv_episodes.showid and tv_episodes.status in ({0})'.format(b','.join(selection_status))
            episodes = main_db_con.select(sql_selection, Quality.SNATCHED + Quality.SNATCHED_PROPER + [WANTED])

            if episodes:
                trakt_data = []

                for cur_episode in episodes:
                    trakt_id = indexerApi(cur_episode[b'indexer']).config['trakt_id']

                    if not self._check_list(trakt_id, cur_episode[b'showid'], cur_episode[b'season'], cur_episode[b'episode']):
                        logger.log('Adding Episode {show} {ep} to watchlist'.format
                                   (show=cur_episode[b'show_name'],
                                    ep=episode_num(cur_episode[b'season'], cur_episode[b'episode'])),
                                   logger.DEBUG)
                        trakt_data.append((cur_episode[b'showid'], cur_episode[b'indexer'], cur_episode[b'show_name'], cur_episode[b'startyear'], cur_episode[b'season'],
                                           cur_episode[b'episode']))

                if trakt_data:
                    try:
                        data = self.trakt_bulk_data_generate(trakt_data)
                        self._request('sync/watchlist', data, method='POST')
                        self._get_episode_watchlist()
                    except TraktException as e:
                        logger.log('Could not connect to Trakt. Error: {0}'.format(ex(e)), logger.WARNING)

    def add_show_watchlist(self):
        if app.TRAKT_SYNC_WATCHLIST and app.USE_TRAKT:
            logger.log('Syncing shows to Trakt watchlist', logger.DEBUG)

            if app.showList:
                trakt_data = []

                for show_obj in app.showList:
                    trakt_id = indexerApi(show_obj.indexer).config['trakt_id']

                    if not self._check_list(trakt_id, show_obj.indexerid, 0, 0, List='Show'):
                        logger.log('Adding Show {0} with ID: {1} to Trakt watchlist'.format(show_obj.name, show_obj.indexerid), logger.DEBUG)
                        show_el = {'title': show_obj.name, 'year': show_obj.start_year, 'ids': {}}
                        if trakt_id == 'tvdb_id':
                            show_el['ids']['tvdb'] = show_obj.indexerid
                        else:
                            show_el['ids']['tvrage'] = show_obj.indexerid
                        trakt_data.append(show_el)

                if trakt_data:
                    try:
                        data = {'shows': trakt_data}
                        self._request('sync/watchlist', data, method='POST')
                        self._get_show_watchlist()
                    except TraktException as e:
                        logger.log('Could not connect to Trakt. Error: {0}'.format(ex(e)), logger.WARNING)

    def remove_from_library(self):
        if app.TRAKT_SYNC_WATCHLIST and app.USE_TRAKT and app.TRAKT_REMOVE_SHOW_FROM_APPLICATION:
            logger.log('Retrieving ended/completed shows to remove from Medusa', logger.DEBUG)

            if app.showList:
                for show in app.showList:
                    if show.status == 'Ended':
                        if not show.imdb_id:
                            logger.log('Could not check trakt progress for {0} because the imdb id is missing from tvdb data, skipping'.format
                                       (show.name), logger.WARNING)
                            continue

                        try:
                            progress = self._request('shows/{0}/progress/watched'.format(show.imdb_id)) or []
                        except TraktException as e:
                            logger.log('Could not connect to Trakt. Aborting removing show {0} from Medusa. Error: {1}'.format(show.name, repr(e)), logger.WARNING)
                            continue

                        if not progress:
                            continue

                        if progress.get('aired', True) == progress.get('completed', False):
                            app.show_queue_scheduler.action.removeShow(show, full=True)
                            logger.log('Show {0} has been removed from Medusa'.format(show.name), logger.DEBUG)

    def fetch_trakt_shows(self):

        if not self.show_watchlist:
            logger.log('No shows found in your watchlist, aborting watchlist update', logger.DEBUG)
        else:
            indexer = int(app.TRAKT_DEFAULT_INDEXER)
            trakt_id = indexerApi(indexer).config['trakt_id']

            for watchlisted_show in self.show_watchlist[trakt_id]:
                indexer_id = int(watchlisted_show)
                show_obj = self.show_watchlist[trakt_id][watchlisted_show]
                if show_obj['year'] and show_obj['slug'].endswith(str(show_obj['year'])):
                    show_name = '{0} ({1})'.format(show_obj['title'], show_obj['year'])
                else:
                    show_name = show_obj['title']

                if int(app.TRAKT_METHOD_ADD) != 2:
                    self.add_show(indexer, indexer_id, show_name, SKIPPED)
                else:
                    self.add_show(indexer, indexer_id, show_name, WANTED)

                if int(app.TRAKT_METHOD_ADD) == 1:
                    new_show = Show.find(app.showList, indexer_id)

                    if new_show:
                        setEpisodeToWanted(new_show, 1, 1)
                    else:
                        self.todoWanted.append(indexer_id)

    def fetch_trakt_episodes(self):
        """
        Sets episodes to wanted that are in trakt watchlist
        """
        logger.log(u"Retrieving episodes to sync with Trakt episode's watchlist", logger.DEBUG)

        if not self.episode_watchlist:
            logger.log('No episode found in your watchlist, aborting episode update', logger.DEBUG)
            return

        managed_show = []

        indexer = int(app.TRAKT_DEFAULT_INDEXER)
        trakt_id = indexerApi(indexer).config['trakt_id']

        for watchlist_item in self.episode_watchlist[trakt_id]:
            indexer_id = int(watchlist_item)
            show = self.episode_watchlist[trakt_id][watchlist_item]

            new_show = Show.find(app.showList, indexer_id)

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
                logger.log('Could not parse the output from trakt for {0} '.format(show['title']), logger.DEBUG)

    @staticmethod
    def add_show(indexer, indexer_id, show_name, status):
        """
        Adds a new show with the default settings
        """
        if not Show.find(app.showList, int(indexer_id)):
            root_dirs = app.ROOT_DIRS.split('|')

            location = root_dirs[int(root_dirs[0]) + 1] if root_dirs else None

            if location:
                logger.log('Adding show {0} with ID: {1}'.format(show_name, indexer_id))

                app.show_queue_scheduler.action.addShow(indexer, indexer_id, None,
                                                        default_status=status,
                                                        quality=int(app.QUALITY_DEFAULT),
                                                        flatten_folders=int(app.FLATTEN_FOLDERS_DEFAULT),
                                                        paused=app.TRAKT_START_PAUSED,
                                                        default_status_after=status, root_dir=location)
            else:
                logger.log('There was an error creating the show, no root directory setting found', logger.WARNING)
                return

    def manage_new_show(self, show):
        logger.log('Checking if trakt watchlist wants to search for episodes from new show {0}'.format(show.name), logger.DEBUG)
        episodes = [i for i in self.todoWanted if i[0] == show.indexerid]

        for episode in episodes:
            self.todoWanted.remove(episode)
            setEpisodeToWanted(show, episode[1], episode[2])

    def _check_list(self, trakt_id, showid, season, episode, List=None): # pylint: disable=too-many-arguments
        """
         Check in the Watchlist or collection list for Show
         Is the Show, Season and Episode in the trakt_id list (tvdb / tvrage)
        """

        if 'Collection' == List:
            try:
                if self.collection_list[trakt_id][showid]['seasons'][season]['episodes'][episode] == episode:
                    return True
            except KeyError:
                return False
        elif 'Show' == List:
            try:
                if self.show_watchlist[trakt_id][showid]['id'] == showid:
                    return True
            except KeyError:
                return False
        else:
            try:
                if self.episode_watchlist[trakt_id][showid]['seasons'][season]['episodes'][episode] == episode:
                    return True
            except KeyError:
                return False

    def _get_show_watchlist(self):
        """
        Get Watchlist and parse once into addressable structure
        """
        try:
            self.show_watchlist = {'tvdb_id': {}, 'tvrage_id': {}}
            trakt_show_watchlist = self._request('sync/watchlist/shows')

            tvdb_id = 'tvdb'
            tvrage_id = 'tvrage'

            for watchlist_item in trakt_show_watchlist:
                tvdb = True if watchlist_item['show']['ids']['tvdb'] else False
                tvrage = True if watchlist_item['show']['ids']['tvrage'] else False
                title = watchlist_item['show']['title']
                year = watchlist_item['show']['year']
                slug = watchlist_item['show']['ids']['slug']

                if tvdb:
                    showid = watchlist_item['show']['ids'][tvdb_id]
                    self.show_watchlist['{0}_id'.format(tvdb_id)][showid] = {'id': showid, 'title': title, 'year': year, 'slug': slug}

                if tvrage:
                    showid = watchlist_item['show']['ids'][tvrage_id]
                    self.show_watchlist['{0}_id'.format(tvrage_id)][showid] = {'id': showid, 'title': title, 'year': year, 'slug': slug}
        except TraktException as e:
            logger.log(u"Could not connect to Trakt. Unable to retrieve show's watchlist: {0!r}".format(e), logger.WARNING)
            return False
        return True

    def _get_episode_watchlist(self):
        """
         Get Watchlist and parse once into addressable structure
        """
        try:
            self.episode_watchlist = {'tvdb_id': {}, 'tvrage_id': {}}
            trakt_episode_watchlist = self._request('sync/watchlist/episodes')

            tvdb_id = 'tvdb'
            tvrage_id = 'tvrage'

            for watchlist_item in trakt_episode_watchlist:
                tvdb = True if watchlist_item['show']['ids']['tvdb'] else False
                tvrage = True if watchlist_item['show']['ids']['tvrage'] else False
                title = watchlist_item['show']['title']
                year = watchlist_item['show']['year']
                season = watchlist_item['episode']['season']
                episode = watchlist_item['episode']['number']

                if tvdb:
                    showid = watchlist_item['show']['ids'][tvdb_id]

                    if showid not in self.episode_watchlist['{0}_id'.format(tvdb_id)].keys():
                        self.episode_watchlist['{0}_id'.format(tvdb_id)][showid] = {'id': showid, 'title': title, 'year': year, 'seasons': {}}

                    if season not in self.episode_watchlist['{0}_id'.format(tvdb_id)][showid]['seasons'].keys():
                        self.episode_watchlist['{0}_id'.format(tvdb_id)][showid]['seasons'][season] = {'s': season, 'episodes': {}}

                    if episode not in self.episode_watchlist['{0}_id'.format(tvdb_id)][showid]['seasons'][season]['episodes'].keys():
                        self.episode_watchlist['{0}_id'.format(tvdb_id)][showid]['seasons'][season]['episodes'][episode] = episode

                if tvrage:
                    showid = watchlist_item['show']['ids'][tvrage_id]

                    if showid not in self.episode_watchlist['{0}_id'.format(tvrage_id)].keys():
                        self.episode_watchlist['{0}_id'.format(tvrage_id)][showid] = {'id': showid, 'title': title, 'year': year, 'seasons': {}}

                    if season not in self.episode_watchlist['{0}_id'.format(tvrage_id)][showid]['seasons'].keys():
                        self.episode_watchlist['{0}_id'.format(tvrage_id)][showid]['seasons'][season] = {'s': season, 'episodes': {}}

                    if episode not in self.episode_watchlist['{0}_id'.format(tvrage_id)][showid]['seasons'][season]['episodes'].keys():
                        self.episode_watchlist['{0}_id'.format(tvrage_id)][showid]['seasons'][season]['episodes'][episode] = episode
        except TraktException as e:
            logger.log(u"Could not connect to Trakt. Unable to retrieve episode's watchlist: {0!r}".format(e), logger.WARNING)
            return False
        return True

    def _get_show_collection(self): # pylint: disable=too-many-branches
        """
        Get Collection and parse once into addressable structure
        """
        try:
            self.collection_list = {'tvdb_id': {}, 'tvrage_id': {}}
            logger.log('Getting Show Collection', logger.DEBUG)
            trakt_collection = self._request('sync/collection/shows')

            tvdb_id = 'tvdb'
            tvrage_id = 'tvrage'

            for watchlist_item in trakt_collection:
                tvdb = True if watchlist_item['show']['ids']['tvdb'] else False
                tvrage = True if watchlist_item['show']['ids']['tvrage'] else False
                title = watchlist_item['show']['title']
                year = watchlist_item['show']['year']

                if 'seasons' in watchlist_item:
                    for season_item in watchlist_item['seasons']:
                        for episode_item in season_item['episodes']:
                            season = season_item['number']
                            episode = episode_item['number']

                            if tvdb:
                                showid = watchlist_item['show']['ids'][tvdb_id]

                                if showid not in self.collection_list['{0}_id'.format(tvdb_id)].keys():
                                    self.collection_list['{0}_id'.format(tvdb_id)][showid] = {'id': showid, 'title': title, 'year': year, 'seasons': {}}

                                if season not in self.collection_list['{0}_id'.format(tvdb_id)][showid]['seasons'].keys():
                                    self.collection_list['{0}_id'.format(tvdb_id)][showid]['seasons'][season] = {'s': season, 'episodes': {}}

                                if episode not in self.collection_list['{0}_id'.format(tvdb_id)][showid]['seasons'][season]['episodes'].keys():
                                    self.collection_list['{0}_id'.format(tvdb_id)][showid]['seasons'][season]['episodes'][episode] = episode

                            if tvrage:
                                showid = watchlist_item['show']['ids'][tvrage_id]

                                if showid not in self.collection_list[tvrage_id + '_id'].keys():
                                    self.collection_list[tvrage_id + '_id'][showid] = {'id': showid, 'title': title, 'year': year, 'seasons': {}}

                                if season not in self.collection_list[tvrage_id + '_id'][showid]['seasons'].keys():
                                    self.collection_list[tvrage_id + '_id'][showid]['seasons'][season] = {'s': season, 'episodes': {}}

                                if episode not in self.collection_list[tvrage_id + '_id'][showid]['seasons'][season]['episodes'].keys():
                                    self.collection_list[tvrage_id + '_id'][showid]['seasons'][season]['episodes'][episode] = episode
        except TraktException as e:
            logger.log(u"Could not connect to Trakt. Unable to retrieve show's collection: {0!r}".format(e), logger.WARNING)
            return False
        return True

    @staticmethod
    def trakt_bulk_data_generate(data): # pylint: disable=too-many-locals
        """
        Build the JSON structure to send back to Trakt
        """
        uniqueShows = {}
        uniqueSeasons = {}

        for showid, indexerid, show_name, start_year, season, episode in data:
            if showid not in uniqueShows:
                uniqueShows[showid] = {'title': show_name, 'year': start_year, 'ids': {}, 'seasons': []}
                trakt_id = indexerApi(indexerid).config['trakt_id']

                if trakt_id == 'tvdb_id':
                    uniqueShows[showid]['ids']['tvdb'] = showid
                else:
                    uniqueShows[showid]['ids']['tvrage'] = showid
                uniqueSeasons[showid] = []

        # Get the unique seasons per Show
        for showid, indexerid, show_name, start_year, season, episode in data:
            if season not in uniqueSeasons[showid]:
                uniqueSeasons[showid].append(season)

        # build the query
        showList = []
        seasonsList = {}

        for searchedShow in uniqueShows:
            seasonsList[searchedShow] = []

            for searchedSeason in uniqueSeasons[searchedShow]:
                episodesList = []

                for showid, indexerid, show_name, start_year, season, episode in data:
                    if season == searchedSeason and showid == searchedShow:
                        episodesList.append({'number': episode})
                show = uniqueShows[searchedShow]
                show['seasons'].append({'number': searchedSeason, 'episodes': episodesList})
            showList.append(show)
        post_data = {'shows': showList}
        return post_data
