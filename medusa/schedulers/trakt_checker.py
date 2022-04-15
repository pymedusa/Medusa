# coding=utf-8

"""Trakt checker module."""
from __future__ import unicode_literals

import datetime
import logging
import time
from builtins import object
from builtins import str
from json.decoder import JSONDecodeError

from medusa import app, db, ui
from medusa.common import ARCHIVED, DOWNLOADED, Quality, SKIPPED, SNATCHED, SNATCHED_BEST, SNATCHED_PROPER, WANTED
from medusa.helper.common import episode_num
from medusa.helpers.externals import show_in_library
from medusa.helpers.trakt import create_episode_structure, create_show_structure, get_trakt_user
from medusa.indexers.config import EXTERNAL_IMDB, EXTERNAL_TRAKT, indexerConfig
from medusa.indexers.imdb.api import ImdbIdentifier
from medusa.indexers.utils import get_trakt_indexer
from medusa.logger.adapters.style import BraceAdapter
from medusa.search.queue import BacklogQueueItem
from medusa.show.show import Show

from requests.exceptions import RequestException

from trakt import sync, tv
from trakt.errors import TraktException


log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


def set_episode_to_wanted(show, season, episode):
    """Set an episode to wanted, only if it is currently skipped."""
    # Episode must be loaded from DB to get current status and not default blank episode status
    ep_obj = show.get_episode(season, episode)
    if ep_obj:

        with ep_obj.lock:
            if ep_obj.status != SKIPPED or ep_obj.airdate == datetime.date.fromordinal(1):
                log.info("Not setting episode '{show}' {ep} to WANTED because current status is not SKIPPED "
                         "or it doesn't have a valid airdate", {'show': show.name, 'ep': episode_num(season, episode)})
                return

            log.info("Setting episode '{show}' {ep} to wanted", {
                'show': show.name,
                'ep': episode_num(season, episode)
            })
            # figure out what segment the episode is in and remember it so we can backlog it

            ep_obj.status = WANTED
            # As we created the episode and updated the status, need to save to DB
            ep_obj.save_to_db()

        cur_backlog_queue_item = BacklogQueueItem(show, [ep_obj])
        app.search_queue_scheduler.action.add_item(cur_backlog_queue_item)

        log.info("Starting backlog search for '{show}' {ep} because some episodes were set to wanted", {
            'show': show.name,
            'ep': episode_num(season, episode)
        })


class TraktChecker(object):
    """Trakt checker class."""

    def __init__(self):
        """Initialize the class."""
        self.todo_wanted = []
        self.show_watchlist = []
        self.episode_watchlist = []
        self.collection_list = []
        self.amActive = False

    def run(self, force=False):
        """Run Trakt Checker."""
        self.amActive = True

        # add shows from Trakt watchlist
        if app.TRAKT_SYNC_WATCHLIST:
            self.todo_wanted = []  # its about to all get re-added
            if len(app.ROOT_DIRS) < 2:
                log.warning('No default root directory')
                ui.notifications.error('Unable to add show',
                                       'You do not have any default root directory. '
                                       'Please configure in general settings!')
                return

            try:
                self.sync_watchlist()
                self.sync_library()
            except (TraktException, RequestException, JSONDecodeError) as error:
                log.exception('Trakt exception while running trakt_checker.\nError: {error}', {'error': error})

        self.amActive = False

    def find_show(self, indexerid, indexer):
        """Find show in Trakt library."""
        trakt_library = []
        try:
            trakt_library = sync.get_collection('shows')
        except (TraktException, RequestException, JSONDecodeError) as error:
            log.info('Unable to retrieve shows from Trakt collection. Error: {error!r}', {'error': error})

        if not trakt_library:
            log.info('No shows found in your Trakt library. Nothing to sync')
            return
        trakt_show = [show for show in trakt_library if
                      get_trakt_indexer(indexer)
                      and show.ids['ids'].get(get_trakt_indexer(indexer))
                      and indexerid in [show.ids['ids'].get(get_trakt_indexer(indexer))]]

        return trakt_show if trakt_show else None

    def remove_show_trakt_library(self, show_obj):
        """Remove show from trakt library."""
        if self.find_show(show_obj.indexerid, show_obj.indexer):

            # Check if TRAKT supports that indexer
            if not get_trakt_indexer(show_obj.indexer):
                return

            log.info("Removing '{show}' from Trakt library", {'show': show_obj.name})

            # Remove all episodes from the Trakt collection for this show
            try:
                self.remove_episode_trakt_collection(filter_show=show_obj)
            except (TraktException, RequestException, JSONDecodeError) as error:
                log.info("Unable to remove all episodes from show '{show}' from Trakt library. Error: {error!r}", {
                    'show': show_obj.name,
                    'error': error
                })

            try:
                sync.remove_from_collection(create_show_structure(show_obj))
            except (TraktException, RequestException, JSONDecodeError) as error:
                log.info("Unable to remove show '{show}' from Trakt library. Error: {error!r}", {
                    'show': show_obj.name,
                    'error': error
                })

    def add_show_trakt_library(self, show_obj):
        """Add show to trakt library."""
        if self.find_show(show_obj.indexerid, show_obj.indexer):
            return

        # Check if TRAKT supports that indexer
        if not get_trakt_indexer(show_obj.indexer):
            return

        log.info("Adding show '{show}' to Trakt library", {'show': show_obj.name})

        try:
            result = sync.add_to_collection(create_show_structure(show_obj))
        except (TraktException, RequestException, JSONDecodeError) as error:
            log.info("Unable to add show '{show}' to Trakt library. Error: {error!r}", {
                'show': show_obj.name,
                'error': error
            })
            return

        if result and (result.get('added') or result.get('existing')):
            return True

        return False

    def sync_library(self):
        """Sync Trakt library."""
        if app.TRAKT_SYNC and app.USE_TRAKT:
            log.debug('Syncing Trakt collection')

            if self._get_show_collection():
                self.add_episode_trakt_collection()
                if app.TRAKT_SYNC_REMOVE:
                    self.remove_episode_trakt_collection()
                log.debug('Synced Trakt collection')

    def remove_episode_trakt_collection(self, filter_show=None):
        """Remove episode from trakt collection.

        For episodes that no longer have a media file (location)
        :param filter_show: optional. Only remove episodes from trakt collection for given shows
        """
        if not (app.TRAKT_SYNC_REMOVE and app.TRAKT_SYNC and app.USE_TRAKT):
            return

        params = []
        main_db_con = db.DBConnection()
        statuses = [DOWNLOADED, ARCHIVED]
        sql_selection = 'SELECT s.indexer, s.startyear, s.indexer_id, s.show_name,' \
                        'e.season, e.episode, e.status ' \
                        'FROM tv_episodes AS e, tv_shows AS s WHERE e.indexer = s.indexer AND ' \
                        's.indexer_id = e.showid and e.location = "" ' \
                        'AND e.status in ({0})'.format(','.join(['?'] * len(statuses)))
        if filter_show:
            sql_selection += ' AND s.indexer_id = ? AND e.indexer = ?'
            params = [filter_show.series_id, filter_show.indexer]

        sql_result = main_db_con.select(sql_selection, statuses + params)

        if not sql_result:
            return

        episodes = []
        shows = {}
        for cur_episode in sql_result:
            # Check if TRAKT supports that indexer
            if not get_trakt_indexer(cur_episode['indexer']):
                continue

            show_id = cur_episode['indexer'], cur_episode['indexer_id']
            episode = cur_episode['season'], cur_episode['episode']

            if show_id not in shows:
                shows[show_id] = []

            shows[show_id].append(episode)

        media_object_shows = []
        for show_id in shows:
            episodes = []
            show_obj = Show.find_by_id(app.showList, show_id[0], show_id[1])
            for season, episode in shows[show_id]:
                if not self._check_list(
                    indexer=show_obj.indexer, indexer_id=show_obj.series_id,
                    season=season, episode=episode,
                    list_type='Collection'
                ):
                    continue

                log.info("Removing episode '{show}' {ep} from Trakt collection", {
                    'show': show_obj.name,
                    'ep': episode_num(season, episode)
                })
                episodes.append(show_obj.get_episode(season, episode))
            media_object_shows.append(create_episode_structure(show_obj, episodes))

        try:
            sync.remove_from_collection({'shows': media_object_shows})
            self._get_show_collection()
        except (TraktException, RequestException, JSONDecodeError) as error:
            log.info('Unable to remove episodes from Trakt collection. Error: {error!r}', {
                'error': error
            })

    def add_episode_trakt_collection(self):
        """Add all existing episodes to Trakt collections.

        For episodes that have a media file (location)
        """
        if not(app.TRAKT_SYNC and app.USE_TRAKT):
            return

        main_db_con = db.DBConnection()
        statuses = [DOWNLOADED, ARCHIVED]
        sql_selection = 'SELECT s.indexer, s.startyear, s.indexer_id, s.show_name, e.season, e.episode ' \
                        'FROM tv_episodes AS e, tv_shows AS s ' \
                        'WHERE e.indexer = s.indexer AND s.indexer_id = e.showid ' \
                        "AND e.status in ({0}) AND e.location <> ''".format(','.join(['?'] * len(statuses)))

        sql_result = main_db_con.select(sql_selection, statuses)
        if not sql_result:
            return

        episodes = []
        shows = {}
        for cur_episode in sql_result:
            # Check if TRAKT supports that indexer
            if not get_trakt_indexer(cur_episode['indexer']):
                continue

            show_id = cur_episode['indexer'], cur_episode['indexer_id']
            episode = cur_episode['season'], cur_episode['episode']

            if show_id not in shows:
                shows[show_id] = []

            shows[show_id].append(episode)

        media_object_shows = []
        for show_id in shows:
            episodes = []
            show_obj = Show.find_by_id(app.showList, show_id[0], show_id[1])
            for season, episode in shows[show_id]:
                if not self._check_list(
                    indexer=show_obj.indexer, indexer_id=show_obj.series_id,
                    season=season, episode=episode,
                    list_type='Collection'
                ):
                    continue

                log.info("Adding episode '{show}' {ep} to Trakt collection", {
                    'show': show_obj.name,
                    'ep': episode_num(season, episode)
                })
                episodes.append(show_obj.get_episode(season, episode))
            media_object_shows.append(create_episode_structure(show_obj, episodes))

        try:
            sync.add_to_collection({'shows': media_object_shows})
            self._get_show_collection()
        except (TraktException, RequestException, JSONDecodeError) as error:
            log.info('Unable to add episodes to Trakt collection. Error: {error!r}', {'error': error})

    def sync_watchlist(self):
        """Sync Trakt watchlist."""
        if app.USE_TRAKT and app.TRAKT_SYNC_WATCHLIST:
            log.debug('Syncing Trakt Watchlist')

            self.remove_from_library()

            if self._get_show_watchlist():
                log.debug('Syncing shows from Trakt watchlist to library')
                self.sync_trakt_shows()

            if app.TRAKT_SYNC_TO_WATCHLIST:
                log.debug('Syncing shows from library to Trakt watchlist')
                self.add_show_watchlist()

            if self._get_episode_watchlist():
                log.debug('Syncing episodes from Trakt watchlist to library')
                self.remove_episode_watchlist()
                self.sync_trakt_episodes()

            log.debug('Syncing episodes from library to trakt watchlist')
            self.add_episode_watchlist()

            log.debug('Synced Trakt watchlist')

    def remove_episode_watchlist(self):
        """Remove episode from Trakt watchlist."""
        if not (app.TRAKT_SYNC_WATCHLIST and app.USE_TRAKT):
            return

        main_db_con = db.DBConnection()
        statuses = [DOWNLOADED, ARCHIVED]
        sql_selection = 'SELECT s.indexer, s.startyear, s.indexer_id, s.show_name, e.season, e.episode ' \
                        'FROM tv_episodes AS e, tv_shows AS s ' \
                        'WHERE e.indexer = s.indexer ' \
                        'AND s.indexer_id = e.showid AND e.status in ({0})'.format(','.join(['?'] * len(statuses)))

        sql_result = main_db_con.select(sql_selection, statuses)

        if not sql_result:
            return

        episodes = []
        shows = {}
        for cur_episode in sql_result:
            # Check if TRAKT supports that indexer
            if not get_trakt_indexer(cur_episode['indexer']):
                continue

            show_id = cur_episode['indexer'], cur_episode['indexer_id']
            episode = cur_episode['season'], cur_episode['episode']

            if show_id not in shows:
                shows[show_id] = []

            shows[show_id].append(episode)

        media_object_shows = []
        for show_id in shows:
            episodes = []
            show_obj = Show.find_by_id(app.showList, show_id[0], show_id[1])
            for season, episode in shows[show_id]:
                if not self._check_list(
                    indexer=show_obj.indexer, indexer_id=show_obj.series_id,
                    season=season, episode=episode,
                    list_type='Collection'
                ):
                    continue

                log.info("Removing episode '{show}' {ep} from Trakt watchlist", {
                    'show': show_obj.name,
                    'ep': episode_num(season, episode)
                })
                episodes.append(show_obj.get_episode(season, episode))
            media_object_shows.append(create_episode_structure(show_obj, episodes))

        try:
            sync.remove_from_collection({'shows': media_object_shows})
            self._get_episode_watchlist()
        except (TraktException, RequestException, JSONDecodeError) as error:
            log.info('Unable to remove episodes from Trakt watchlist. Error: {error!r}', {
                'error': error
            })

    def add_episode_watchlist(self):
        """Add episode to Tratk watchlist."""
        if not(app.TRAKT_SYNC_WATCHLIST and app.USE_TRAKT):
            return

        main_db_con = db.DBConnection()
        statuses = [SNATCHED, SNATCHED_BEST, SNATCHED_PROPER, WANTED]
        sql_selection = 'SELECT s.indexer, s.startyear, s.indexer_id, s.show_name, e.season, e.episode ' \
                        'FROM tv_episodes AS e, tv_shows AS s ' \
                        'WHERE e.indexer = s.indexer AND s.indexer_id = e.showid AND s.paused = 0 ' \
                        'AND e.status in ({0})'.format(','.join(['?'] * len(statuses)))

        sql_result = main_db_con.select(sql_selection, statuses)

        if not sql_result:
            return

        episodes = []
        shows = {}
        for cur_episode in sql_result:
            # Check if TRAKT supports that indexer
            if not get_trakt_indexer(cur_episode['indexer']):
                continue

            show_id = cur_episode['indexer'], cur_episode['indexer_id']
            episode = cur_episode['season'], cur_episode['episode']

            if show_id not in shows:
                shows[show_id] = []

            shows[show_id].append(episode)

        media_object_shows = []
        for show_id in shows:
            episodes = []
            show_obj = Show.find_by_id(app.showList, show_id[0], show_id[1])
            for season, episode in shows[show_id]:
                if not self._check_list(
                    indexer=show_obj.indexer, indexer_id=show_obj.series_id,
                    season=season, episode=episode,
                    list_type='Collection'
                ):
                    continue

                log.info("Adding episode '{show}' {ep} to Trakt watchlist", {
                    'show': show_obj.name,
                    'ep': episode_num(season, episode)
                })
                episodes.append(show_obj.get_episode(season, episode))
            media_object_shows.append(create_episode_structure(show_obj, episodes))

        try:
            sync.add_to_watchlist({'shows': media_object_shows})
            self._get_episode_watchlist()
        except (TraktException, RequestException, JSONDecodeError) as error:
            log.info('Unable to add episode to Trakt watchlist. Error: {error!r}', {
                'error': error
            })

    def add_show_watchlist(self):
        """Add show to Trakt watchlist.

        It will add all shows from Medusa library
        """
        if not (app.TRAKT_SYNC_WATCHLIST and app.USE_TRAKT):
            return

        if not app.showList:
            return

        trakt_show_objects = []
        for show_obj in app.showList:
            if not self._check_list(show_obj=show_obj, list_type='Show'):
                log.info("Adding show '{show}' to Trakt watchlist", {'show': show_obj.name})
                trakt_show_objects.append(create_show_structure(show_obj))

        if trakt_show_objects:
            try:
                sync.add_to_watchlist({'shows': trakt_show_objects})
            except (TraktException, RequestException, JSONDecodeError) as error:
                log.info('Unable to add shows to Trakt watchlist. Error: {error!r}', {'error': error})
            self._get_show_watchlist()

    def remove_from_library(self):
        """Remove show from Medusa library if it is ended/completed."""
        if not (app.TRAKT_SYNC_WATCHLIST and app.USE_TRAKT and app.TRAKT_REMOVE_SHOW_FROM_APPLICATION):
            return

        log.debug('Retrieving ended/completed shows to remove from Medusa')

        if not app.showList:
            return

        for show in app.showList:
            if show.status == 'Ended':
                trakt_id = show.externals.get('trakt_id', None)
                if not (trakt_id or show.imdb_id):
                    log.info("Unable to check Trakt progress for show '{show}' "
                             'because Trakt|IMDB ID is missing. Skipping', {'show': show.name})
                    continue

                try:
                    trakt_show = tv.TVShow(str(trakt_id or ImdbIdentifier(show.imdb_id).imdb_id))
                    progress = trakt_show.progress
                except (TraktException, RequestException, JSONDecodeError) as error:
                    log.info("Unable to check if show '{show}' is ended/completed. Error: {error!r}", {
                        'show': show.name,
                        'error': error
                    })
                    continue
                else:
                    if progress and progress.get('aired', True) == progress.get('completed', False):
                        app.show_queue_scheduler.action.removeShow(show, full=True)
                        log.info("Show '{show}' has being queued to be removed from Medusa library", {
                            'show': show.name
                        })

    def sync_trakt_shows(self):
        """Sync Trakt shows watchlist."""
        if not self.show_watchlist:
            log.info('No shows found in your Trakt watchlist. Nothing to sync')
            return

        trakt_default_indexer = int(app.TRAKT_DEFAULT_INDEXER)

        for trakt_show in self.show_watchlist:
            if trakt_show.year and trakt_show.ids['ids']['slug'].endswith(str(trakt_show.year)):
                show_name = f'{trakt_show.title} ({trakt_show.year})'
            else:
                show_name = trakt_show.title

            show = None
            indexer = None

            for i in indexerConfig:
                trakt_indexer = get_trakt_indexer(i)
                indexer_id = trakt_show.ids['ids'].get(trakt_indexer)
                if not indexer_id:
                    continue
                indexer = indexerConfig[i]['id']
                show = show_in_library(i, indexer_id)
                # show = Show.find_by_id(app.showList, indexer, indexer_id)
                if show:
                    break
            if not show:
                # If can't find with available indexers try IMDB
                trakt_indexer = get_trakt_indexer(EXTERNAL_IMDB)
                indexer_id = trakt_show.ids['ids'].get(trakt_indexer)
                show = Show.find_by_id(app.showList, EXTERNAL_IMDB, indexer_id)
            if not show:
                # If can't find with available indexers try TRAKT
                trakt_indexer = get_trakt_indexer(EXTERNAL_TRAKT)
                indexer_id = trakt_show.ids['ids'].get(trakt_indexer)
                show = Show.find_by_id(app.showList, EXTERNAL_TRAKT, indexer_id)

            if show:
                continue

            # If we don't have an indexer id for the trakt default indexer, skip it.
            indexer_id = trakt_show.ids['ids'].get(get_trakt_indexer(trakt_default_indexer))
            if not indexer_id:
                log.info(
                    'Can not add show {show_name}, as trakt does not have an {indexer} id for this show.',
                    {'show_name': show_name, 'indexer': get_trakt_indexer(trakt_default_indexer)}
                )
                continue

            if int(app.TRAKT_METHOD_ADD) != 2:
                self.add_show(trakt_default_indexer, indexer_id, show_name, SKIPPED)
            else:
                self.add_show(trakt_default_indexer, indexer_id, show_name, WANTED)

            if int(app.TRAKT_METHOD_ADD) == 1 and indexer:
                new_show = Show.find_by_id(app.showList, indexer, indexer_id)

                if new_show:
                    set_episode_to_wanted(new_show, 1, 1)
                else:
                    log.warning('Unable to find the new added show.'
                                'Pilot will be set to wanted in the next Trakt run')
                    self.todo_wanted.append((indexer, indexer_id, 1, 1))
        log.debug('Synced shows with Trakt watchlist')

    def sync_trakt_episodes(self):
        """Sync Trakt episodes watchlist."""
        if not self.episode_watchlist:
            log.info('No episodes found in your Trakt watchlist. Nothing to sync')
            return

        added_shows = []
        trakt_default_indexer = int(app.TRAKT_DEFAULT_INDEXER)

        for watchlist_item in self.episode_watchlist:
            trakt_show = watchlist_item.show
            trakt_episode = watchlist_item.episode
            trakt_season = watchlist_item.season

            show = None

            for i in indexerConfig:
                trakt_indexer = get_trakt_indexer(i)
                if not trakt_indexer:
                    continue

                indexer_id = trakt_show['ids'].get(trakt_indexer)
                indexer = indexerConfig[i]['id']
                show = Show.find_by_id(app.showList, indexer, indexer_id)
                if show:
                    break

            if not show:
                # If can't find with available indexers try IMDB
                trakt_indexer = get_trakt_indexer(EXTERNAL_IMDB)
                indexer_id = trakt_show['ids'].get(trakt_indexer)
                show = Show.find_by_id(app.showList, EXTERNAL_IMDB, indexer_id)
            if not show:
                # If can't find with available indexers try TRAKT
                trakt_indexer = get_trakt_indexer(EXTERNAL_TRAKT)
                indexer_id = trakt_show['ids'].get(trakt_indexer)
                show = Show.find_by_id(app.showList, EXTERNAL_TRAKT, indexer_id)

            # If can't find show add with default trakt indexer
            if not show:
                trakt_indexer = get_trakt_indexer(trakt_default_indexer)
                indexer_id = trakt_show['ids'].get(trakt_indexer)
                # Only add show if we didn't added it before
                if indexer_id not in added_shows:
                    self.add_show(trakt_default_indexer, indexer_id, trakt_show['title'], SKIPPED)
                    added_shows.append(indexer_id)

            elif not trakt_season == 0 and not show.paused:
                set_episode_to_wanted(show, trakt_season, trakt_episode)

        log.debug('Synced episodes with Trakt watchlist')

    @staticmethod
    def add_show(indexer, indexer_id, show_name, status):
        """Add a new show with default settings."""
        if Show.find_by_id(app.showList, EXTERNAL_IMDB, indexer_id):
            return

        root_dirs = app.ROOT_DIRS

        location = root_dirs[int(root_dirs[0]) + 1] if root_dirs else None

        if location:
            log.info("Adding show '{show}' using indexer: '{indexer_name}' and ID: {id}", {
                'show': show_name,
                'indexer_name': indexerConfig[indexer]['identifier'],
                'id': indexer_id
            })

            allowed, preferred = Quality.split_quality(int(app.QUALITY_DEFAULT))
            quality = {'allowed': allowed, 'preferred': preferred}

            app.show_queue_scheduler.action.addShow(indexer, indexer_id, None,
                                                    default_status=status,
                                                    quality=quality,
                                                    season_folders=int(app.SEASON_FOLDERS_DEFAULT),
                                                    paused=app.TRAKT_START_PAUSED,
                                                    default_status_after=status,
                                                    root_dir=location)
            tries = 0
            while tries < 3:
                if Show.find_by_id(app.showList, indexer, indexer_id):
                    return
                # Wait before show get's added and refreshed
                time.sleep(60)
                tries += 1
            log.warning("Error creating show '{show}. Please check logs' ", {
                'show': show_name
            })
            return
        else:
            log.warning("Error creating show '{show}' folder. No default root directory", {
                'show': show_name
            })
            return

    def manage_new_show(self, show):
        """Set episodes to wanted for the recently added show."""
        log.debug("Checking for wanted episodes for show '{show}' in Trakt watchlist", {'show': show.name})
        episodes = [i for i in self.todo_wanted if i[0] == show.indexer and i[1] == show.indexerid]

        for episode in episodes:
            self.todo_wanted.remove(episode)
            set_episode_to_wanted(show, episode[2], episode[3])

    def _check_list(self, show_obj=None, indexer=None, indexer_id=None, season=None, episode=None, list_type=None):
        """Check if we can find the show in the Trakt watchlist|collection list."""

        def match_trakt_by_id(trakt_show, medusa_show):
            """Try to match the trakt show object to a Medusa show."""
            trakt_supported_indexer = get_trakt_indexer(show_obj.indexer)
            if trakt_supported_indexer and getattr(trakt_show, trakt_supported_indexer) == medusa_show.indexerid:
                return True
            # Try to match by imdb_id
            if getattr(trakt_show, 'imdb') == ImdbIdentifier(medusa_show.imdb_id).imdb_id:
                return True
            return False

        if 'Collection' == list_type:
            trakt_indexer = get_trakt_indexer(indexer)
            for collected_show in self.collection_list:
                if not getattr(collected_show, trakt_indexer) == indexer_id:
                    continue
                if hasattr(collected_show, 'seasons'):
                    for season_item in collected_show.seasons:
                        for episode_item in season_item.episodes:
                            trakt_season = season_item.number
                            trakt_episode = episode_item.number
                            if trakt_season == season and trakt_episode == episode:
                                return True
                else:
                    return False
        elif 'Show' == list_type:
            for watchlisted_show in self.show_watchlist:
                if match_trakt_by_id(watchlisted_show, show_obj):
                    return True
            return False
        else:
            trakt_indexer = get_trakt_indexer(indexer)
            for watchlisted_episode in self.episode_watchlist:
                if watchlisted_episode.season == season and \
                        watchlisted_episode.episode == episode and \
                        watchlisted_episode['ids'].get(trakt_indexer) == indexer_id:
                    return True
            return False

    def _get_show_watchlist(self):
        """Get shows watchlist."""
        user = get_trakt_user()
        self.show_watchlist = user.watchlist_shows
        return self.show_watchlist

    def _get_episode_watchlist(self):
        """Get episodes watchlist."""
        try:
            self.episode_watchlist = sync.get_watchlist('episodes')
        except (TraktException, RequestException, JSONDecodeError) as error:
            log.info(u'Unable to retrieve episodes from Trakt watchlist. Error: {error!r}', {'error': error})
            return False
        return True

    def _get_show_collection(self):
        """Get show collection."""
        try:
            self.collection_list = sync.get_collection('shows')
        except (TraktException, RequestException, JSONDecodeError) as error:
            log.info('Unable to retrieve shows from Trakt collection. Error: {error!r}', {'error': error})
            return False
        return True

    @staticmethod
    def trakt_bulk_data_generate(trakt_data):
        """Build the JSON structure to send back to Trakt."""
        unique_shows = {}
        unique_seasons = {}

        for indexer_id, indexer, show_name, start_year, season, episode in trakt_data:
            if indexer_id not in unique_shows:
                unique_shows[indexer_id] = {'title': show_name, 'year': start_year, 'ids': {}, 'seasons': []}
                unique_shows[indexer_id]['ids'][get_trakt_indexer(indexer)] = indexer_id
                unique_seasons[indexer_id] = []

        # Get the unique seasons per Show
        for indexer_id, indexer, show_name, start_year, season, episode in trakt_data:
            if season not in unique_seasons[indexer_id]:
                unique_seasons[indexer_id].append(season)

        # build the query
        show_list = []
        seasons_list = {}

        for searched_show in unique_shows:
            show = []
            seasons_list[searched_show] = []

            for searched_season in unique_seasons[searched_show]:
                episodes_list = []

                for indexer_id, indexer, show_name, start_year, season, episode in trakt_data:
                    if season == searched_season and indexer_id == searched_show:
                        episodes_list.append({'number': episode})
                show = unique_shows[searched_show]
                show['seasons'].append({'number': searched_season, 'episodes': episodes_list})
            if show:
                show_list.append(show)
        post_data = {'shows': show_list}
        return post_data
