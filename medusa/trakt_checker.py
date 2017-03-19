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

from traktor import AuthException, ServerBusy, TokenExpiredException, TraktApi, TraktException

from . import app, db, logger, ui
from .common import Quality, SKIPPED, WANTED
from .helper.common import episode_num
from .helpers import get_title_without_year
from .indexers.indexer_config import EXTERNAL_IMDB, EXTERNAL_TRAKT, get_trakt_indexer, indexerConfig
from .search.queue import BacklogQueueItem
from .show.show import Show


def setEpisodeToWanted(show, s, e):
    """
    Sets an episode to wanted, only if it is currently skipped
    """
    ep_obj = show.get_episode(s, e, no_create=True)
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

    def run(self, force=False):
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

            self.sync_watchlist()
            self.sync_library()

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
            logger.log(u'You need to get a PIN and authorize Medusa app', logger.WARNING)
            app.TRAKT_ACCESS_TOKEN = ''
            app.TRAKT_REFRESH_TOKEN = ''
            app.instance.save_config()
            raise TokenExpiredException('You need to get a PIN and authorize Medusa app')

        return library_shows

    def find_show(self, indexerid, indexer):

        try:
            trakt_library = self._request('sync/collection/shows') or []
        except (TraktException, AuthException, ServerBusy, TokenExpiredException) as e:
            logger.log('Unable to get your collected shows from Trakt. Error: {0}'.format(e.message),
                       logger.INFO)

        if not trakt_library:
            logger.log('No shows found in your library, aborting library update', logger.INFO)
            return
        trakt_show = [x for x in trakt_library if
                      int(indexerid) in [int(x['show']['ids'].get(get_trakt_indexer(indexer)))]]

        return trakt_show if trakt_show else None

    def remove_show_trakt_library(self, show_obj):
        """Remove Show from trakt collections."""
        if self.find_show(show_obj.indexerid, show_obj.indexer):

            # Check if TRAKT supports that indexer
            if not get_trakt_indexer(show_obj.indexer):
                return

            # URL parameters
            title = get_title_without_year(show_obj.name, show_obj.start_year)
            data = {
                'shows': [
                    {
                        'title': title,
                        'year': show_obj.start_year,
                        'ids': {}
                    }
                ]
            }

            data['shows'][0]['ids'][get_trakt_indexer(show_obj.indexer)] = show_obj.indexerid

            logger.log('Removing {0} from Trakt library'.format(show_obj.name), logger.INFO)

            # Remove all episodes from the Trakt collection for this show
            try:
                self.remove_episode_trakt_collection(filter_show=show_obj)
            except (TraktException, AuthException, ServerBusy, TokenExpiredException) as e:
                logger.log('Unable to remove all episodes for show {0} from Trakt library. Error: {1}'.
                           format(show_obj.name, e.message), logger.INFO)

            try:
                self._request('sync/collection/remove', data, method='POST')
            except (TraktException, AuthException, ServerBusy, TokenExpiredException) as e:
                logger.log('Unable to remove show {0} from Trakt library. Error: {1}'.
                           format(show_obj.name, e.message), logger.INFO)

    def add_show_trakt_library(self, show_obj):
        """
        Send a request to trakt indicating that the given show and all its episodes is part of our library.

        show_obj: The Series object to add to trakt
        """
        data = {}

        if not self.find_show(show_obj.indexerid, show_obj.indexer):

            # Check if TRAKT supports that indexer
            if not get_trakt_indexer(show_obj.indexer):
                return

            # URL parameters
            title = get_title_without_year(show_obj.name, show_obj.start_year)
            data = {
                'shows': [
                    {
                        'title': title,
                        'year': show_obj.start_year,
                        'ids': {}
                    }
                ]
            }

            data['shows'][0]['ids'][get_trakt_indexer(show_obj.indexer)] = show_obj.indexerid

        if data:
            logger.log('Adding {0} to Trakt library'.format(show_obj.name), logger.INFO)

            try:
                self._request('sync/collection', data, method='POST')
            except (TraktException, AuthException, ServerBusy, TokenExpiredException) as e:
                logger.log('Unable to add show {0} to Trakt library. Error: {1}'.format
                           (show_obj.name, e.message), logger.INFO)
                return

    def sync_library(self):
        if app.TRAKT_SYNC and app.USE_TRAKT:
            logger.log('Syncing Trakt collection', logger.INFO)

            if self._get_show_collection():
                self.add_episode_trakt_collection()
                if app.TRAKT_SYNC_REMOVE:
                    self.remove_episode_trakt_collection()
                logger.log(u"Synced Trakt collection", logger.INFO)

    def remove_episode_trakt_collection(self, filter_show=None):
        if app.TRAKT_SYNC_REMOVE and app.TRAKT_SYNC and app.USE_TRAKT:

            params = []
            main_db_con = db.DBConnection()
            sql_selection = b'SELECT s.indexer, s.startyear, s.indexer_id, s.show_name, e.season, e.episode, e.status ' \
                            b'FROM tv_episodes AS e, tv_shows AS s WHERE s.indexer_id = e.showid and e.location = ""'
            if filter_show:
                sql_selection += b' AND s.indexer_id = ? AND e.indexer = ?'
                params = [filter_show.indexerid, filter_show.indexer]

            sql_result = main_db_con.select(sql_selection, params)
            episodes = [dict(e) for e in sql_result]

            if episodes:
                trakt_data = []

                for cur_episode in episodes:
                    # Check if TRAKT supports that indexer
                    if not get_trakt_indexer(cur_episode[b'indexer']):
                        return
                    if self._check_list(indexer=cur_episode[b'indexer'], indexer_id=cur_episode[b'indexer_id'],
                                        season=cur_episode[b'season'], episode=cur_episode[b'episode'],
                                        List='Collection'):
                        logger.log('Removing Episode {show} {ep} from collection'.format
                                   (show=cur_episode[b'show_name'],
                                    ep=episode_num(cur_episode[b'season'], cur_episode[b'episode'])), logger.INFO)
                        trakt_data.append((cur_episode[b'indexer_id'], cur_episode[b'indexer'],
                                           cur_episode[b'show_name'], cur_episode[b'startyear'],
                                           cur_episode[b'season'], cur_episode[b'episode']))

                if trakt_data:
                    try:
                        data = self.trakt_bulk_data_generate(trakt_data)
                        self._request('sync/collection/remove', data, method='POST')
                        self._get_show_collection()
                    except (TraktException, AuthException, ServerBusy, TokenExpiredException) as e:
                        logger.log('Unable to remove episode from Trakt collection. '
                                   'Error: {0}'.format(e.message), logger.INFO)

    def add_episode_trakt_collection(self):
        """Add all episodes from local library to Trakt collections. Enabled in app.TRAKT_SYNC_WATCHLIST setting."""
        if app.TRAKT_SYNC and app.USE_TRAKT:

            main_db_con = db.DBConnection()
            selection_status = ['?' for _ in Quality.DOWNLOADED + Quality.ARCHIVED]
            sql_selection = b'SELECT s.indexer, s.startyear, s.indexer_id, s.show_name, e.season, e.episode ' \
                            b'FROM tv_episodes AS e, tv_shows AS s WHERE s.indexer_id = e.showid ' \
                            b"AND e.status in ({0}) AND e.location <> ''" \
                            b"AND s.paused = 0 AND e.season <> 0".format(','.join(selection_status))

            sql_result = main_db_con.select(sql_selection, Quality.DOWNLOADED + Quality.ARCHIVED)
            episodes = [dict(e) for e in sql_result]

            if episodes:
                trakt_data = []

                for cur_episode in episodes:
                    # Check if TRAKT supports that indexer
                    if not get_trakt_indexer(cur_episode[b'indexer']):
                        return

                    if not self._check_list(indexer=cur_episode[b'indexer'], indexer_id=cur_episode[b'indexer_id'],
                                            season=cur_episode[b'season'], episode=cur_episode[b'episode'],
                                            List='Collection'):
                        logger.log('Adding Episode {show} {ep} to collection'.format
                                   (show=cur_episode[b'show_name'],
                                    ep=episode_num(cur_episode[b'season'], cur_episode[b'episode'])),
                                   logger.INFO)
                        trakt_data.append((cur_episode[b'indexer_id'], cur_episode[b'indexer'],
                                           cur_episode[b'show_name'], cur_episode[b'startyear'],
                                           cur_episode[b'season'], cur_episode[b'episode']))

                if trakt_data:
                    try:
                        data = self.trakt_bulk_data_generate(trakt_data)
                        self._request('sync/collection', data, method='POST')
                        self._get_show_collection()
                    except (TraktException, AuthException, ServerBusy, TokenExpiredException) as e:
                        logger.log('Unable to add episode to Trakt collection. '
                                   'Error: {0}'.format(e.message), logger.INFO)

    def sync_watchlist(self):
        if app.TRAKT_SYNC_WATCHLIST and app.USE_TRAKT:
            logger.log('Syncing Trakt Watchlist', logger.INFO)

            self.remove_from_library()

            if self._get_show_watchlist():
                logger.log('Syncing shows with Trakt watchlist', logger.INFO)
                self.add_show_watchlist()
                self.fetch_trakt_shows()

            if self._get_episode_watchlist():
                logger.log('Syncing episodes with Trakt watchlist', logger.INFO)
                self.remove_episode_watchlist()
                self.add_episode_watchlist()
                self.fetch_trakt_episodes()

            logger.log('Synced Trakt watchlist', logger.INFO)

    def remove_episode_watchlist(self):
        if app.TRAKT_SYNC_WATCHLIST and app.USE_TRAKT:

            main_db_con = db.DBConnection()
            status = Quality.DOWNLOADED + Quality.ARCHIVED
            selection_status = [b'?' for _ in status]
            sql_selection = b'SELECT s.indexer, s.startyear, e.showid, s.show_name, e.season, e.episode ' \
                            b'FROM tv_episodes AS e, tv_shows AS s ' \
                            b'WHERE s.indexer_id = e.showid AND e.status in ({0})'.format(b','.join(selection_status))
            sql_result = main_db_con.select(sql_selection, status)
            episodes = [dict(i) for i in sql_result]

            if episodes:
                trakt_data = []

                for cur_episode in episodes:

                    # Check if TRAKT supports that indexer
                    if not get_trakt_indexer(cur_episode[b'indexer']):
                        return

                    if self._check_list(indexer=cur_episode[b'indexer'], indexer_id=cur_episode[b'showid'],
                                        season=cur_episode[b'season'], episode=cur_episode[b'episode']):
                        logger.log('Removing Episode {show} {ep} from watchlist'.format
                                   (show=cur_episode[b'show_name'],
                                    ep=episode_num(cur_episode[b'season'], cur_episode[b'episode'])),
                                   logger.INFO)
                        trakt_data.append((cur_episode[b'showid'], cur_episode[b'indexer'],
                                           cur_episode[b'show_name'], cur_episode[b'startyear'],
                                           cur_episode[b'season'], cur_episode[b'episode']))

                if trakt_data:
                    try:
                        data = self.trakt_bulk_data_generate(trakt_data)
                        self._request('sync/watchlist/remove', data, method='POST')
                        self._get_episode_watchlist()
                    except (TraktException, AuthException, ServerBusy, TokenExpiredException) as e:
                        logger.log('Unable to remove episode from Trakt watchlist. '
                                   'Error: {0}'.format(e.message), logger.INFO)

    def add_episode_watchlist(self):
        if app.TRAKT_SYNC_WATCHLIST and app.USE_TRAKT:

            main_db_con = db.DBConnection()
            status = Quality.SNATCHED + Quality.SNATCHED_BEST + Quality.SNATCHED_PROPER + [WANTED]
            selection_status = [b'?' for _ in status]
            sql_selection = b'SELECT s.indexer, s.startyear, e.showid, s.show_name, e.season, e.episode ' \
                            b'FROM tv_episodes AS e, tv_shows AS s ' \
                            b'WHERE s.indexer_id = e.showid AND s.paused = 0 ' \
                            b'AND e.status in ({0})'.format(b','.join(selection_status))
            sql_result = main_db_con.select(sql_selection, status)
            episodes = [dict(i) for i in sql_result]

            if episodes:
                trakt_data = []

                for cur_episode in episodes:
                    # Check if TRAKT supports that indexer
                    if not get_trakt_indexer(cur_episode[b'indexer']):
                        return

                    if not self._check_list(indexer=cur_episode[b'indexer'], indexer_id=cur_episode[b'showid'],
                                            season=cur_episode[b'season'], episode=cur_episode[b'episode']):
                        logger.log('Adding Episode {show} {ep} to watchlist'.format
                                   (show=cur_episode[b'show_name'],
                                    ep=episode_num(cur_episode[b'season'], cur_episode[b'episode'])),
                                   logger.INFO)
                        trakt_data.append((cur_episode[b'showid'], cur_episode[b'indexer'], cur_episode[b'show_name'],
                                           cur_episode[b'startyear'], cur_episode[b'season'], cur_episode[b'episode']))

                if trakt_data:
                    try:
                        data = self.trakt_bulk_data_generate(trakt_data)
                        self._request('sync/watchlist', data, method='POST')
                        self._get_episode_watchlist()
                    except (TraktException, AuthException, ServerBusy, TokenExpiredException) as e:
                        logger.log('Unable to add episode to Trakt watchlist. '
                                   'Error: {0}'.format(e.message), logger.INFO)

    def add_show_watchlist(self):
        if app.TRAKT_SYNC_WATCHLIST and app.USE_TRAKT:
            if app.showList:
                trakt_data = []

                for show_obj in app.showList:
                    if not self._check_list(show_obj=show_obj, List='Show'):
                        logger.log('Adding Show {0} to Trakt watchlist'.format
                                   (show_obj.name), logger.INFO)
                        title = get_title_without_year(show_obj.name, show_obj.start_year)
                        show_el = {'title': title, 'year': show_obj.start_year, 'ids': {}}
                        trakt_data.append(show_el)

                if trakt_data:
                    try:
                        data = {'shows': trakt_data}
                        self._request('sync/watchlist', data, method='POST')
                    except (TraktException, AuthException, ServerBusy, TokenExpiredException) as e:
                        logger.log('Unable to add shos to Trakt watchlist. Error: {0}'.format(e.message), logger.INFO)
                    self._get_show_watchlist()

    def remove_from_library(self):
        if app.TRAKT_SYNC_WATCHLIST and app.USE_TRAKT and app.TRAKT_REMOVE_SHOW_FROM_APPLICATION:
            logger.log('Retrieving ended/completed shows to remove from Medusa', logger.INFO)

            if app.showList:
                for show in app.showList:
                    if show.status == 'Ended':
                        if not show.imdb_id:
                            logger.log('Unable to check Trakt progress for {0} '
                                       'because the IMDB id is missing from tvdb data, skipping'.format(show.name),
                                       logger.DEBUG)
                            continue

                        try:
                            progress = self._request('shows/{0}/progress/watched'.format(show.imdb_id)) or []
                        except (TraktException, AuthException, ServerBusy, TokenExpiredException) as e:
                            logger.log('Unable to check if show {0} is ended/completed. Error: {1}'.format
                                       (show.name, e.message), logger.INFO)
                            continue

                        if not progress:
                            continue

                        if progress.get('aired', True) == progress.get('completed', False):
                            app.show_queue_scheduler.action.removeShow(show, full=True)
                            logger.log('Show {0} has being queued to be removed from Medusa'.format
                                       (show.name), logger.INFO)

    def fetch_trakt_shows(self):

        if not self.show_watchlist:
            logger.log('No shows found in your watchlist, aborting watchlist update', logger.INFO)
        else:
            trakt_default_indexer = int(app.TRAKT_DEFAULT_INDEXER)

            for watchlisted_show in self.show_watchlist:
                trakt_show = watchlisted_show['show']

                if trakt_show['year'] and trakt_show['ids']['slug'].endswith(str(trakt_show['year'])):
                    show_name = '{0} ({1})'.format(trakt_show['title'], trakt_show['year'])
                else:
                    show_name = trakt_show['title']

                show = None
                for i in indexerConfig:
                    trakt_indexer = get_trakt_indexer(i)
                    indexer_id = trakt_show['ids'].get(trakt_indexer, -1)
                    indexer = indexerConfig[i]['id']
                    show = Show.find(app.showList, indexer_id, indexer)
                    if show:
                        break
                if not show:
                    # If can't find with available indexers try IMDB
                    trakt_indexer = get_trakt_indexer(EXTERNAL_IMDB)
                    indexer_id = trakt_show['ids'].get(trakt_indexer, -1)
                    show = Show.find(app.showList, indexer_id, EXTERNAL_IMDB)
                if not show:
                    # If can't find with available indexers try TRAKT
                    trakt_indexer = get_trakt_indexer(EXTERNAL_TRAKT)
                    indexer_id = trakt_show['ids'].get(trakt_indexer, -1)
                    show = Show.find(app.showList, indexer_id, EXTERNAL_TRAKT)

                if show:
                    continue

                indexer_id = trakt_show['ids'].get(get_trakt_indexer(trakt_default_indexer), -1)
                if int(app.TRAKT_METHOD_ADD) != 2:
                    self.add_show(trakt_default_indexer, indexer_id, show_name, SKIPPED)
                else:
                    self.add_show(trakt_default_indexer, indexer_id, show_name, WANTED)

                if int(app.TRAKT_METHOD_ADD) == 1:
                    new_show = Show.find(app.showList, indexer_id)

                    if new_show:
                        setEpisodeToWanted(new_show, 1, 1)
                    else:
                        self.todoWanted.append(indexer_id)
            logger.log(u"Synced shows with Trakt watchlist", logger.INFO)

    def fetch_trakt_episodes(self):
        """
        Sets episodes to wanted that are in trakt watchlist
        """
        if not self.episode_watchlist:
            logger.log('No episode found in your watchlist, aborting episode update', logger.INFO)
            return

        managed_show = []
        trakt_default_indexer = int(app.TRAKT_DEFAULT_INDEXER)

        for watchlist_item in self.episode_watchlist:
            trakt_show = watchlist_item['show']
            trakt_episode = watchlist_item['episode'].get('number', -1)
            trakt_season = watchlist_item['episode'].get('season', -1)

            show = None
            for i in indexerConfig:
                trakt_indexer = get_trakt_indexer(i)
                indexer_id = trakt_show['ids'].get(trakt_indexer, -1)
                indexer = indexerConfig[i]['id']
                show = Show.find(app.showList, indexer_id, indexer)
                if show:
                    break

            if not show:
                # If can't find with available indexers try IMDB
                trakt_indexer = get_trakt_indexer(EXTERNAL_IMDB)
                indexer_id = trakt_show['ids'].get(trakt_indexer, -1)
                show = Show.find(app.showList, indexer_id, EXTERNAL_IMDB)
            if not show:
                # If can't find with available indexers try TRAKT
                trakt_indexer = get_trakt_indexer(EXTERNAL_TRAKT)
                indexer_id = trakt_show['ids'].get(trakt_indexer, -1)
                show = Show.find(app.showList, indexer_id, EXTERNAL_TRAKT)

            # If can't find show add with default trakt indexer
            if not show:
                if indexer_id not in managed_show:
                    indexer_id = trakt_show['ids'].get(get_trakt_indexer(trakt_default_indexer), -1)
                    self.add_show(trakt_default_indexer, indexer_id, trakt_show['title'], SKIPPED)
                    managed_show.append(indexer_id)
            if not trakt_season == 0 or not show.paused:
                setEpisodeToWanted(show, trakt_season, trakt_episode)

        logger.log(u"Synced episodes with Trakt watchlist", logger.INFO)

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
        logger.log('Checking if trakt watchlist wants to search for episodes from new show {0}'.format(show.name),
                   logger.INFO)
        episodes = [i for i in self.todoWanted if i[0] == show.indexerid]

        for episode in episodes:
            self.todoWanted.remove(episode)
            setEpisodeToWanted(show, episode[1], episode[2])

    def _check_list(self, show_obj=None, indexer=None, indexer_id=None, season=None, episode=None, List=None):
        """Check in the Watchlist or collection list for Show."""
        if 'Collection' == List:
            trakt_indexer = get_trakt_indexer(indexer)
            for collected_show in self.collection_list:
                if not collected_show['show']['ids'].get(trakt_indexer, '') == indexer_id:
                    continue
                if 'seasons' in collected_show:
                    for season_item in collected_show['seasons']:
                        for episode_item in season_item['episodes']:
                            trakt_season = season_item['number']
                            trakt_episode = episode_item['number']
                            if trakt_season == season and trakt_episode == episode:
                                return True
                else:
                    return False
        elif 'Show' == List:
            trakt_indexer = get_trakt_indexer(show_obj.indexer)
            for watchlisted_show in self.show_watchlist:
                if watchlisted_show['show']['ids'].get(trakt_indexer) == show_obj.indexerid or \
                        watchlisted_show['show']['ids'].get(get_trakt_indexer(EXTERNAL_IMDB), '') == show_obj.imdb_id:
                    return True
            return False
        else:
            trakt_indexer = get_trakt_indexer(indexer)
            for watchlisted_episode in self.episode_watchlist:
                if watchlisted_episode['episode'].get('season', -1) == season and \
                        watchlisted_episode['episode'].get('number', -1) == episode and \
                        watchlisted_episode['show']['ids'].get(trakt_indexer, '') == indexer_id:
                    return True
            return False

    def _get_show_watchlist(self):
        """
        Get Watchlist and parse once into addressable structure
        """
        try:
            self.show_watchlist = self._request('sync/watchlist/shows')
        except (TraktException, AuthException, ServerBusy, TokenExpiredException) as e:
            logger.log(u"Unable to retrieve user's watchlist: {0}".format(e.message),
                       logger.WARNING)
            return False
        return True

    def _get_episode_watchlist(self):
        """
         Get Watchlist and parse once into addressable structure
        """
        try:
            self.episode_watchlist = self._request('sync/watchlist/episodes')
        except (TraktException, AuthException, ServerBusy, TokenExpiredException) as e:
            logger.log(u"Unable to retrieve user episode's watchlist: {0}".format(e.message),
                       logger.WARNING)
            return False
        return True

    def _get_show_collection(self):
        """
        Get Collection and parse once into addressable structure
        """
        try:
            self.collection_list = self._request('sync/collection/shows')
        except (TraktException, AuthException, ServerBusy, TokenExpiredException) as e:
            logger.log(u"Unable to retrieve user's collection: {0}".format(e.message),
                       logger.DEBUG)
            return False
        return True

    @staticmethod
    def trakt_bulk_data_generate(data):
        """
        Build the JSON structure to send back to Trakt
        """
        uniqueShows = {}
        uniqueSeasons = {}

        for indexer_id, indexer, show_name, start_year, season, episode in data:
            if indexer_id not in uniqueShows:
                uniqueShows[indexer_id] = {'title': show_name, 'year': start_year, 'ids': {}, 'seasons': []}
                uniqueShows[indexer_id]['ids'][get_trakt_indexer(indexer)] = indexer_id
                uniqueSeasons[indexer_id] = []

        # Get the unique seasons per Show
        for indexer_id, indexer, show_name, start_year, season, episode in data:
            if season not in uniqueSeasons[indexer_id]:
                uniqueSeasons[indexer_id].append(season)

        # build the query
        showList = []
        seasonsList = {}

        for searchedShow in uniqueShows:
            seasonsList[searchedShow] = []

            for searchedSeason in uniqueSeasons[searchedShow]:
                episodesList = []

                for indexer_id, indexer, show_name, start_year, season, episode in data:
                    if season == searchedSeason and indexer_id == searchedShow:
                        episodesList.append({'number': episode})
                show = uniqueShows[searchedShow]
                show['seasons'].append({'number': searchedSeason, 'episodes': episodesList})
            showList.append(show)
        post_data = {'shows': showList}
        return post_data
