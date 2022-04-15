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
from __future__ import unicode_literals

import logging
import traceback
from builtins import object
from json.decoder import JSONDecodeError

from imdbpie.exceptions import ImdbAPIError

from medusa import (
    app,
    scene_numbering,
    ui,
    ws,
)
from medusa.common import statusStrings
from medusa.helper.common import episode_num
from medusa.helper.exceptions import (
    CantRefreshShowException,
    CantRemoveShowException,
    CantUpdateShowException,
    EpisodeDeletedException,
    ShowDirectoryNotFoundException
)
from medusa.image_cache import replace_images
from medusa.indexers.api import indexerApi
from medusa.indexers.exceptions import (
    IndexerAttributeNotFound,
    IndexerError,
    IndexerException,
    IndexerShowNotFoundInLanguage,
)
from medusa.indexers.utils import indexer_id_to_slug
from medusa.logger.adapters.style import BraceAdapter
from medusa.name_cache import build_name_cache
from medusa.queues import generic_queue
from medusa.tv.series import ChangeIndexerException, SaveSeriesException, Series, SeriesIdentifier

from requests.exceptions import RequestException

from six import ensure_text, text_type, viewitems

from trakt.errors import TraktException


log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class ShowQueueActions(object):

    def __init__(self):
        pass

    REFRESH = 1
    ADD = 2
    UPDATE = 3
    RENAME = 5
    SUBTITLE = 6
    REMOVE = 7
    SEASON_UPDATE = 8
    CHANGE = 9

    names = {
        REFRESH: 'Refresh',
        ADD: 'Add',
        UPDATE: 'Update',
        RENAME: 'Rename',
        SUBTITLE: 'Subtitle',
        REMOVE: 'Remove Show',
        SEASON_UPDATE: 'Season Update',
        CHANGE: 'Change Indexer'
    }


class ShowQueue(generic_queue.GenericQueue):

    mappings = {
        ShowQueueActions.ADD: 'This show is in the process of being downloaded - the info below is incomplete.',
        ShowQueueActions.UPDATE: 'The information on this page is in the process of being updated.',
        ShowQueueActions.SEASON_UPDATE: 'The information on this page is in the process of being updated.',
        ShowQueueActions.REFRESH: 'The episodes below are currently being refreshed from disk',
        ShowQueueActions.SUBTITLE: 'Currently downloading subtitles for this show',
        ShowQueueActions.CHANGE: "This show is in the process of changing it's indexer",
    }

    queue_mappings = {
        ShowQueueActions.REFRESH: 'This show is queued to be refreshed.',
        ShowQueueActions.UPDATE: 'This show is queued and awaiting an update.',
        ShowQueueActions.SEASON_UPDATE: 'This show is queued and awaiting a season update.',
        ShowQueueActions.SUBTITLE: 'This show is queued and awaiting subtitles download.',
    }

    def __init__(self):
        generic_queue.GenericQueue.__init__(self)
        self.queue_name = 'SHOWQUEUE'

    def _isInQueue(self, show, actions):
        if not show:
            return False

        return show.series_id in [x.show.series_id if x.show else 0 for x in self.queue if x.action_id in actions]

    def _isBeingSomethinged(self, show, actions):
        return self.current_item is not None and show == self.current_item.show and self.current_item.action_id in actions

    def isInUpdateQueue(self, show):
        return self._isInQueue(show, (ShowQueueActions.UPDATE,))

    def isInRefreshQueue(self, show):
        return self._isInQueue(show, (ShowQueueActions.REFRESH,))

    def isInRenameQueue(self, show):
        return self._isInQueue(show, (ShowQueueActions.RENAME,))

    def isInSubtitleQueue(self, show):
        return self._isInQueue(show, (ShowQueueActions.SUBTITLE,))

    def isInRemoveQueue(self, show):
        return self._isInQueue(show, (ShowQueueActions.REMOVE,))

    def isBeingAdded(self, show):
        return self._isBeingSomethinged(show, (ShowQueueActions.ADD,))

    def isBeingUpdated(self, show):
        return self._isBeingSomethinged(show, (ShowQueueActions.UPDATE,))

    def isBeingRefreshed(self, show):
        return self._isBeingSomethinged(show, (ShowQueueActions.REFRESH,))

    def isBeingRenamed(self, show):
        return self._isBeingSomethinged(show, (ShowQueueActions.RENAME,))

    def isBeingSubtitled(self, show):
        return self._isBeingSomethinged(show, (ShowQueueActions.SUBTITLE,))

    def isBeingRemoved(self, show):
        return self._isBeingSomethinged(show, (ShowQueueActions.REMOVE,))

    def _getLoadingShowList(self):
        return [x for x in self.queue + [self.current_item] if x is not None and x.isLoading]

    def getQueueActionMessage(self, show):
        return self.get_queue_action(show)[1]

    def get_queue_action(self, show):
        for action, message in viewitems(self.mappings):
            if self._isBeingSomethinged(show, (action, )):
                return action, message

        for action, message in viewitems(self.queue_mappings):
            if self._isInQueue(show, (action, )):
                return action, message

        return None, None

    loadingShowList = property(_getLoadingShowList)

    def updateShow(self, show, season=None):

        if self.isBeingAdded(show):
            raise CantUpdateShowException(
                '{show_name} is still being added,'
                ' wait until it is finished before you update.'.format(show_name=show.name)
            )

        if self.isBeingUpdated(show):
            raise CantUpdateShowException(
                '{show_name} is already being updated by Post-processor or manually started,'
                " can't update again until it's done.".format(show_name=show.name)
            )

        if self.isInUpdateQueue(show):
            raise CantUpdateShowException(
                '{show_name} is in process of being updated by Post-processor or manually started,'
                " can't update again until it's done.".format(show_name=show.name)
            )

        queue_item_update_show = QueueItemUpdate(show) if season is None else QueueItemSeasonUpdate(show, season)

        self.add_item(queue_item_update_show)

        return queue_item_update_show

    def refreshShow(self, show, force=False):

        if self.isBeingRefreshed(show) and not force:
            raise CantRefreshShowException('This show is already being refreshed, not refreshing again.')

        if (self.isBeingUpdated(show) or self.isInUpdateQueue(show)) and not force:
            log.debug('A refresh was attempted but there is already an update queued or in progress.'
                      " Since updates do a refresh at the end anyway I'm skipping this request.")
            return

        queue_item_obj = QueueItemRefresh(show, force=force)

        log.debug('{id}: Queueing show refresh for {show}', {'id': show.series_id, 'show': show.name})

        self.add_item(queue_item_obj)

        return queue_item_obj

    def renameShowEpisodes(self, show):

        queue_item_obj = QueueItemRename(show)

        self.add_item(queue_item_obj)

        return queue_item_obj

    def download_subtitles(self, show):

        queue_item_obj = QueueItemSubtitle(show)

        self.add_item(queue_item_obj)

        return queue_item_obj

    def addShow(self, indexer, indexer_id, show_dir, **options):
        if options.get('lang') is None:
            options['lang'] = app.INDEXER_DEFAULT_LANGUAGE

        queue_item_obj = QueueItemAdd(indexer, indexer_id, show_dir, **options)
        self.add_item(queue_item_obj)

        return queue_item_obj

    def changeIndexer(self, old_slug, new_slug):
        queue_item_obj = QueueItemChangeIndexer(old_slug, new_slug)
        self.add_item(queue_item_obj)

        return queue_item_obj

    def removeShow(self, show, full=False):
        if show is None:
            raise CantRemoveShowException('Failed removing show: Show does not exist')

        if not hasattr(show, 'indexerid'):
            raise CantRemoveShowException('Failed removing show: Show does not have an indexer id')

        if self.isBeingRemoved(show):
            raise CantRemoveShowException('[{!s}]: Show is already being removed'.format(show.series_id))

        if self.isInRemoveQueue(show):
            raise CantRemoveShowException('[{!s}]: Show is already queued to be removed'.format(show.series_id))

        # remove other queued actions for this show.
        for item in self.queue:
            if item and item.show and item != self.current_item and show.identifier == item.show.identifier:
                self.queue.remove(item)

        queue_item_obj = QueueItemRemove(show=show, full=full)
        self.add_item(queue_item_obj)

        # Show removal has been queued, let's update the app.RECENTLY_DELETED global, to keep track of it
        app.RECENTLY_DELETED.update([show.indexer_slug])

        return queue_item_obj


class ShowQueueItem(generic_queue.QueueItem):
    """
    Represents an item in the queue waiting to be executed.

    Can be either:
    - show being added (may or may not be associated with a show object)
    - show being refreshed
    - show being updated
    - show being force updated
    - show being subtitled
    """

    def __init__(self, action_id, show):
        generic_queue.QueueItem.__init__(self, ShowQueueActions.names[action_id], action_id)
        self.show = show

        # Update the generic_queue.py to_json.
        self.to_json.update({
            'show': self.show.to_json() if self.show else {}
        })

    def isInQueue(self):
        return self in app.show_queue_scheduler.action.queue + [
            app.show_queue_scheduler.action.current_item]  # @UndefinedVariable

    def _getName(self):
        return text_type(self.show.series_id)

    def _isLoading(self):
        return False

    show_name = property(_getName)

    isLoading = property(_isLoading)


class QueueItemChangeIndexer(ShowQueueItem):
    """Queue Item for changing a shows indexer to another."""

    def __init__(self, old_slug, new_slug):
        """
        Initialize QueueItemChangeIndexer with an old slug and new slug.

        Old slug will be used as the currently added show. Which is used to get all show options.
        New slug is the to be created show.
        """
        self.old_slug = old_slug
        self.new_slug = new_slug
        self.show_dir = None
        self.root_dir = None

        self.options = {}
        self.old_show = None
        self.new_show = None

        # this will initialize self.show to None
        ShowQueueItem.__init__(self, ShowQueueActions.CHANGE, self.old_show)

        # Process add show in priority
        self.priority = generic_queue.QueuePriorities.HIGH

    def _store_options(self):
        self.options = {
            'default_status': None,
            'quality': {'preferred': self.old_show.qualities_preferred, 'allowed': self.old_show.qualities_allowed},
            'season_folders': self.old_show.season_folders,
            'lang': self.old_show.lang,
            'subtitles': self.old_show.subtitles,
            'anime': self.old_show.anime,
            'scene': self.old_show.scene,
            'paused': self.old_show.paused,
            'blacklist': self.old_show.release_groups.blacklist if self.old_show.release_groups else None,
            'whitelist': self.old_show.release_groups.whitelist if self.old_show.release_groups else None,
            'default_status_after': self.old_show.default_ep_status,
            'root_dir': None,
            'show_lists': self.old_show.show_lists
        }

        self.show_dir = self.old_show._location

    def run(self):
        """Run QueueItemChangeIndexer queue item."""
        step = []

        # Small helper, to reduce code for messaging
        def message_step(new_step):
            step.append(new_step)

            ws.Message('QueueItemShow', dict(
                step=step,
                oldShow=self.old_show.to_json() if self.old_show else {},
                newShow=self.new_show.to_json() if self.new_show else {},
                **self.to_json
            )).push()

        ShowQueueItem.run(self)

        def get_show_from_slug(slug):
            identifier = SeriesIdentifier.from_slug(slug)
            if not identifier:
                raise ChangeIndexerException(f'Could not create identifier with slug {slug}')

            show = Series.find_by_identifier(identifier)
            return show

        try:
            # Create reference to old show, before starting the remove it.
            self.old_show = get_show_from_slug(self.old_slug)

            # Store needed options.
            self._store_options()

            # Start of removing the old show
            log.info(
                '{id}: Removing {show}',
                {'id': self.old_show.series_id, 'show': self.old_show.name}
            )
            message_step(f'Removing old show {self.old_show.name}')

            # Need to first remove the episodes from the Trakt collection, because we need the list of
            # Episodes from the db to know which eps to remove.
            if app.USE_TRAKT:
                message_step('Removing episodes from trakt collection')
                try:
                    app.trakt_checker_scheduler.action.remove_show_trakt_library(self.old_show)
                except TraktException as error:
                    log.warning(
                        '{id}: Unable to delete show {show} from Trakt.'
                        ' Please remove manually otherwise it will be added again.'
                        ' Error: {error_msg}',
                        {'id': self.old_show.series_id, 'show': self.old_show.name, 'error_msg': error}
                    )
                except Exception as error:
                    log.exception('Exception occurred while trying to delete show {show}, error: {error',
                                  {'show': self.old_show.name, 'error': error})

            self.old_show.delete_show(full=False)

            # Send showRemoved to frontend, so we can remove it from localStorage.
            ws.Message('showRemoved', self.old_show.to_json(detailed=False)).push()  # Send ws update to client

            # Double check to see if the show really has been removed, else bail.
            if get_show_from_slug(self.old_slug):
                raise ChangeIndexerException(f'Could not create identifier with slug {self.old_slug}')

            # Start adding the new show
            log.info(
                'Starting to add show by {0}',
                ('show_dir: {0}'.format(self.show_dir)
                 if self.show_dir else
                 'New slug: {0}'.format(self.new_slug))
            )

            self.new_show = Series.from_identifier(SeriesIdentifier.from_slug(self.new_slug))

            try:
                # Push an update to any open Web UIs through the WebSocket
                message_step('load show from {indexer}'.format(indexer=indexerApi(self.new_show.indexer).name))

                api = self.new_show.identifier.get_indexer_api(self.options)

                if getattr(api[self.new_show.series_id], 'seriesname', None) is None:
                    log.error(
                        'Show in {path} has no name on {indexer}, probably searched with the wrong language.',
                        {'path': self.show_dir, 'indexer': indexerApi(self.new_show.indexer).name}
                    )

                    ui.notifications.error(
                        'Unable to add show',
                        'Show in {path} has no name on {indexer}, probably the wrong language.'
                        ' Delete .nfo and manually add the correct language.'.format(
                            path=self.show_dir, indexer=indexerApi(self.new_show.indexer).name)
                    )
                    self._finish_early()
                    raise SaveSeriesException('Indexer is missing a showname in this language: {0!r}')

                self.new_show.load_from_indexer(tvapi=api)

                message_step('load info from imdb')
                self.new_show.load_imdb_info()
            except IndexerException as error:
                log.warning('Unable to load series from indexer: {0!r}'.format(error))
                raise SaveSeriesException('Unable to load series from indexer: {0!r}'.format(error))

            try:
                message_step('configure show options')
                self.new_show.configure(self)
            except KeyError as error:
                log.error(
                    'Unable to add show {series_name} due to an error with one of the provided options: {error}',
                    {'series_name': self.new_show.name, 'error': error}
                )
                ui.notifications.error(
                    'Unable to add show {series_name} due to an error with one of the provided options: {error}'.format(
                        series_name=self.new_show.name, error=error
                    )
                )
                raise SaveSeriesException(
                    'Unable to add show {series_name} due to an error with one of the provided options: {error}'.format(
                        series_name=self.new_show.name, error=error
                    ))

            except Exception as error:
                log.error('Error trying to configure show: {0}', error)
                log.debug(traceback.format_exc())
                raise

            app.showList.append(self.new_show)
            self.new_show.save_to_db()

            try:
                message_step('load episodes from {indexer}'.format(indexer=indexerApi(self.new_show.indexer).name))
                self.new_show.load_episodes_from_indexer(tvapi=api)
                # If we provide a default_status_after through the apiv2 series route options object.
                # set it after we've added the episodes.
                self.new_show.default_ep_status = self.options['default_status_after'] or app.STATUS_DEFAULT_AFTER

            except IndexerException as error:
                log.warning('Unable to load series episodes from indexer: {0!r}'.format(error))
                raise SaveSeriesException(
                    'Unable to load series episodes from indexer: {0!r}'.format(error)
                )

            message_step('create metadata in show folder')
            self.new_show.write_metadata()
            self.new_show.update_metadata()
            self.new_show.populate_cache()
            build_name_cache(self.new_show)  # update internal name cache
            self.new_show.flush_episodes()
            self.new_show.sync_trakt()

            message_step('add scene numbering')
            self.new_show.add_scene_numbering()

            if self.show_dir:
                # If a show dir was passed, this was added as an existing show.
                # For new shows we shouldn't have any files on disk.
                message_step('refresh episodes from disk')
                try:
                    app.show_queue_scheduler.action.refreshShow(self.new_show)
                except CantRefreshShowException as error:
                    log.warning('Unable to rescan episodes from disk: {0!r}'.format(error))

        except (ChangeIndexerException, SaveSeriesException) as error:
            log.warning('Unable to add series: {0!r}'.format(error))
            self.success = False
            self._finish_early()
            log.debug(traceback.format_exc())

        default_status = self.options['default_status'] or app.STATUS_DEFAULT
        if statusStrings[default_status] == 'Wanted':
            message_step('trigger backlog search')
            app.backlog_search_scheduler.action.search_backlog([self.new_show])

        self.success = True

        ws.Message('showAdded', self.new_show.to_json(detailed=False)).push()  # Send ws update to client
        message_step('finished')
        self.finish()

    def _finish_early(self):
        if self.new_show is not None:
            app.show_queue_scheduler.action.removeShow(self.new_show)
        self.finish()


class QueueItemAdd(ShowQueueItem):
    def __init__(self, indexer, indexer_id, show_dir, **options):
        self.indexer = indexer
        self.indexer_id = indexer_id
        self.show_dir = ensure_text(show_dir) if show_dir else None
        self.default_status = options.get('default_status')
        self.quality = options.get('quality')
        self.season_folders = options.get('season_folders')
        self.lang = options.get('lang')
        self.subtitles = options.get('subtitles')
        self.anime = options.get('anime')
        self.scene = options.get('scene')
        self.paused = options.get('paused')
        self.blacklist = options.get('blacklist')
        self.whitelist = options.get('whitelist')
        self.default_status_after = options.get('default_status_after')
        self.root_dir = options.get('root_dir')
        self.show_lists = options.get('show_lists')
        self.options = options

        self.show = None

        # this will initialize self.show to None
        ShowQueueItem.__init__(self, ShowQueueActions.ADD, self.show)

        # Process add show in priority
        self.priority = generic_queue.QueuePriorities.HIGH

    def _getName(self):
        """
        Returns the show name if there is a show object created, if not returns
        the dir that the show is being added to.
        """
        if self.show is None:
            return self.show_dir
        return self.show.name

    show_name = property(_getName)

    def _isLoading(self):
        """
        Returns True if we've gotten far enough to have a show object, or False
        if we still only know the folder name.
        """
        if self.show is None:
            return True
        return False

    isLoading = property(_isLoading)

    def run(self):

        ShowQueueItem.run(self)

        log.info(
            'Starting to add show by {0}',
            ('show_dir: {0}'.format(self.show_dir)
             if self.show_dir else
             'Indexer Id: {0}'.format(self.indexer_id))
        )

        show_slug = indexer_id_to_slug(self.indexer, self.indexer_id)
        self.show = Series.from_identifier(SeriesIdentifier.from_slug(show_slug))

        step = []

        # Small helper, to reduce code for messaging
        def message_step(new_step):
            step.append(new_step)
            ws.Message('QueueItemShow', dict(
                step=step, **self.to_json
            )).push()

        try:
            try:
                # Push an update to any open Web UIs through the WebSocket
                message_step('load show from {indexer}'.format(indexer=indexerApi(self.indexer).name))

                api = self.show.identifier.get_indexer_api(self.options)

                if getattr(api[self.indexer_id], 'seriesname', None) is None:
                    log.error(
                        'Show in {path} has no name on {indexer}, probably searched with the wrong language.',
                        {'path': self.show_dir, 'indexer': indexerApi(self.indexer).name}
                    )

                    ui.notifications.error(
                        'Unable to add show',
                        'Show in {path} has no name on {indexer}, probably the wrong language.'
                        ' Delete .nfo and manually add the correct language.'.format(
                            path=self.show_dir, indexer=indexerApi(self.indexer).name)
                    )
                    self._finish_early()
                    raise SaveSeriesException('Indexer is missing a showname in this language: {0!r}')

                self.show.load_from_indexer(tvapi=api)

                message_step('load info from imdb')
                self.show.load_imdb_info()
            except IndexerException as error:
                log.warning('Unable to load series from indexer: {0!r}'.format(error))
                raise SaveSeriesException('Unable to load series from indexer: {0!r}'.format(error))

            try:
                message_step('configure show options')
                self.show.configure(self)
            except KeyError as error:
                log.error(
                    'Unable to add show {series_name} due to an error with one of the provided options: {error}',
                    {'series_name': self.show.name, 'error': error}
                )
                ui.notifications.error(
                    'Unable to add show {series_name} due to an error with one of the provided options: {error}'.format(
                        series_name=self.show.name, error=error
                    )
                )
                raise SaveSeriesException(
                    'Unable to add show {series_name} due to an error with one of the provided options: {error}'.format(
                        series_name=self.show.name, error=error
                    ))

            except Exception as error:
                log.error('Error trying to configure show: {0}', error)
                log.debug(traceback.format_exc())
                raise

            app.showList.append(self.show)
            self.show.save_to_db()

            try:
                message_step('load episodes from {indexer}'.format(indexer=indexerApi(self.indexer).name))
                self.show.load_episodes_from_indexer(tvapi=api)
                # If we provide a default_status_after through the apiv2 series route options object.
                # set it after we've added the episodes.
                self.show.default_ep_status = self.options['default_status_after'] or app.STATUS_DEFAULT_AFTER

            except IndexerException as error:
                log.warning('Unable to load series episodes from indexer: {0!r}'.format(error))
                raise SaveSeriesException(
                    'Unable to load series episodes from indexer: {0!r}'.format(error)
                )

            message_step('create metadata in show folder')
            self.show.write_metadata()
            self.show.update_metadata()
            self.show.populate_cache()
            build_name_cache(self.show)  # update internal name cache
            self.show.flush_episodes()
            self.show.sync_trakt()

            message_step('add scene numbering')
            self.show.add_scene_numbering()

            # Load search templates
            message_step('generate search templates')
            self.show.init_search_templates()

            if self.show_dir:
                # If a show dir was passed, this was added as an existing show.
                # For new shows we should have any files on disk.
                message_step('refresh episodes from disk')
                try:
                    app.show_queue_scheduler.action.refreshShow(self.show)
                except CantRefreshShowException as error:
                    log.warning('Unable to rescan episodes from disk: {0!r}'.format(error))

        except SaveSeriesException as error:
            log.warning('Unable to add series: {0!r}'.format(error))
            self.success = False
            self._finish_early()
            log.debug(traceback.format_exc())

        default_status = self.options['default_status'] or app.STATUS_DEFAULT
        if statusStrings[default_status] == 'Wanted':
            message_step('trigger backlog search')
            app.backlog_search_scheduler.action.search_backlog([self.show])

        self.success = True

        ws.Message('showAdded', self.show.to_json(detailed=False)).push()  # Send ws update to client
        message_step('finished')
        self.finish()

    def _finish_early(self):
        if self.show is not None:
            app.show_queue_scheduler.action.removeShow(self.show)

        self.finish()


class QueueItemRefresh(ShowQueueItem):
    """QueueItemRefresh class."""

    def __init__(self, show=None, force=False):
        """Queue item refresh constructor."""
        ShowQueueItem.__init__(self, ShowQueueActions.REFRESH, show)

        # do refreshes first because they're quick
        self.priority = generic_queue.QueuePriorities.HIGH

        # force refresh certain items
        self.force = force

    def run(self):
        """Run QueueItemRefresh queue item."""
        ShowQueueItem.run(self)

        log.info(
            '{id}: Performing refresh on {show}',
            {'id': self.show.series_id, 'show': self.show.name}
        )
        ws.Message('QueueItemShow', self.to_json).push()

        try:
            self.show.refresh_dir()
            if self.force:
                self.show.update_metadata()
            self.show.write_metadata()
            self.show.populate_cache()

            # Load XEM data to DB for show
            scene_numbering.xem_refresh(self.show, force=True)
            self.success = True
        except IndexerException as error:
            log.warning(
                '{id}: Unable to contact {indexer}. Aborting: {error_msg}',
                {'id': self.show.series_id, 'indexer': indexerApi(self.show.indexer).name,
                 'error_msg': error}
            )
        except Exception as error:
            log.error(
                '{id}: Error while refreshing show {show}. Error: {error_msg}',
                {'id': self.show.series_id, 'show': self.show.name, 'error_msg': error}
            )

        self.finish()
        ws.Message('QueueItemShow', self.to_json).push()


class QueueItemRename(ShowQueueItem):
    def __init__(self, show=None):
        ShowQueueItem.__init__(self, ShowQueueActions.RENAME, show)

    def run(self):

        ShowQueueItem.run(self)
        ws.Message('QueueItemShow', self.to_json).push()

        log.info(
            'Performing rename on {series_name}',
            {'series_name': self.show.name}
        )

        try:
            self.show.validate_location
        except ShowDirectoryNotFoundException:
            log.warning(
                "Can't perform rename on {series_name} when the show dir is missing.",
                {'series_name': self.show.name}
            )
            return

        ep_obj_rename_list = []

        ep_obj_list = self.show.get_all_episodes(has_location=True)
        for cur_ep_obj in ep_obj_list:
            # Only want to rename if we have a location
            if cur_ep_obj.location:
                if cur_ep_obj.related_episodes:
                    # do we have one of multi-episodes in the rename list already
                    have_already = False
                    for cur_related_ep in cur_ep_obj.related_episodes + [cur_ep_obj]:
                        if cur_related_ep in ep_obj_rename_list:
                            have_already = True
                            break
                    if not have_already:
                        ep_obj_rename_list.append(cur_ep_obj)

                else:
                    ep_obj_rename_list.append(cur_ep_obj)

        for cur_ep_obj in ep_obj_rename_list:
            cur_ep_obj.rename()

        self.finish()
        ws.Message('QueueItemShow', self.to_json).push()


class QueueItemSubtitle(ShowQueueItem):
    def __init__(self, show=None):
        ShowQueueItem.__init__(self, ShowQueueActions.SUBTITLE, show)

    def run(self):

        ShowQueueItem.run(self)
        ws.Message('QueueItemShow', self.to_json).push()

        log.info(
            '{id}: Downloading subtitles for {show}',
            {'id': self.show.series_id, 'show': self.show.name}
        )

        self.show.download_subtitles()
        self.finish()
        ws.Message('QueueItemShow', self.to_json).push()


class QueueItemUpdate(ShowQueueItem):
    def __init__(self, show):
        """Use QueueItem to perform full show updates.

        :param show: Show object to update.
        """
        ShowQueueItem.__init__(self, ShowQueueActions.UPDATE, show)
        self.priority = generic_queue.QueuePriorities.HIGH

    def run(self):

        ShowQueueItem.run(self)
        ws.Message('QueueItemShow', self.to_json).push()

        log.debug(
            '{id}: Beginning update of {show}',
            {'id': self.show.series_id, 'show': self.show.name}
        )

        log.debug(
            '{id}: Retrieving show info from {indexer}',
            {'id': self.show.series_id, 'indexer': indexerApi(self.show.indexer).name}
        )
        try:
            # Let's make sure we refresh the indexer_api object attached to the show object.
            self.show.create_indexer()
            self.show.load_from_indexer()
        except IndexerError as error:
            log.warning(
                '{id}: Unable to contact {indexer}. Aborting: {error_msg}',
                {'id': self.show.series_id, 'indexer': indexerApi(self.show.indexer).name, 'error_msg': error}
            )
            return
        except IndexerAttributeNotFound as error:
            log.warning(
                '{id}: Data retrieved from {indexer} was incomplete. Aborting: {error_msg}',
                {'id': self.show.series_id, 'indexer': indexerApi(self.show.indexer).name, 'error_msg': error}
            )
            return
        except IndexerShowNotFoundInLanguage as error:
            log.warning(
                '{id}: Data retrieved from {indexer} was incomplete. The indexer does not provide'
                ' show information in the searched language {language}. Aborting: {error_msg}',
                {'id': self.show.series_id, 'indexer': indexerApi(self.show.indexer).name,
                 'language': error.language, 'error_msg': error}
            )
            ui.notifications.error(
                'Error changing language show!',
                'Unable to change language for show {show_name}'
                ' on {indexer} to language: {language}'.format(
                    show_name=self.show.name, indexer=indexerApi(self.show.indexer).name,
                    language=error.language)
            )
            return

        log.debug(
            '{id}: Retrieving show info from IMDb',
            {'id': self.show.series_id}
        )
        try:
            self.show.load_imdb_info()
        except ImdbAPIError as error:
            log.info(
                '{id}: Something wrong on IMDb api: {error_msg}',
                {'id': self.show.series_id, 'error_msg': error}
            )
        except RequestException as error:
            log.warning(
                '{id}: Error loading IMDb info: {error_msg}',
                {'id': self.show.series_id, 'error_msg': error}
            )

        # have to save show before reading episodes from db
        try:
            log.debug(
                '{id}: Saving new IMDb show info to database',
                {'id': self.show.series_id}
            )
            self.show.save_to_db()
        except Exception as error:
            log.warning(
                '{id}: Error saving new IMDb show info to database: {error_msg}',
                {'id': self.show.series_id, 'error_msg': error}
            )
            log.error(traceback.format_exc())

        # get episode list from DB
        try:
            episodes_from_db = self.show.load_episodes_from_db()
        except IndexerException as error:
            log.warning(
                '{id}: Unable to contact {indexer}. Aborting: {error_msg}',
                {'id': self.show.series_id, 'indexer': indexerApi(self.show.indexer).name,
                 'error_msg': error}
            )
            return

        # get episode list from the indexer
        try:
            episodes_from_indexer = self.show.load_episodes_from_indexer()
        except IndexerException as error:
            log.warning(
                '{id}: Unable to get info from {indexer}. The show info will not be refreshed.'
                ' Error: {error_msg}',
                {'id': self.show.series_id, 'indexer': indexerApi(self.show.indexer).name,
                 'error_msg': error}
            )
            episodes_from_indexer = None

        if episodes_from_indexer is None:
            log.warning(
                '{id}: No data returned from {indexer} during full show update.'
                ' Unable to update this show',
                {'id': self.show.series_id, 'indexer': indexerApi(self.show.indexer).name}
            )
        else:
            # for each ep we found on the Indexer delete it from the DB list
            for cur_season in episodes_from_indexer:
                for cur_episode in episodes_from_indexer[cur_season]:
                    if cur_season in episodes_from_db and cur_episode in episodes_from_db[cur_season]:
                        del episodes_from_db[cur_season][cur_episode]

            # remaining episodes in the DB list are not on the indexer, just delete them from the DB
            for cur_season in episodes_from_db:
                for cur_episode in episodes_from_db[cur_season]:
                    log.debug(
                        '{id}: Permanently deleting episode {show} {ep} from the database',
                        {'id': self.show.series_id, 'show': self.show.name,
                         'ep': episode_num(cur_season, cur_episode)}
                    )
                    # Create the ep object only because Im going to delete it
                    ep_obj = self.show.get_episode(cur_season, cur_episode)
                    try:
                        ep_obj.delete_episode()
                    except EpisodeDeletedException:
                        log.debug(
                            '{id}: Episode {show} {ep} successfully deleted from the database',
                            {'id': self.show.series_id, 'show': self.show.name,
                             'ep': episode_num(cur_season, cur_episode)}
                        )

        # Save only after all changes were applied
        try:
            log.debug(
                '{id}: Saving all updated show info to database',
                {'id': self.show.series_id}
            )
            self.show.save_to_db()
        except Exception as error:
            log.warning(
                '{id}: Error saving all updated show info to database: {error_msg}',
                {'id': self.show.series_id, 'error_msg': error}
            )
            log.error(traceback.format_exc())

        # Replace the images in cache
        log.info(
            '{id}: Replacing images for show {show}',
            {'id': self.show.series_id, 'show': self.show.name}
        )
        replace_images(self.show)

        log.debug(
            '{id}: Finished update of {show}',
            {'id': self.show.series_id, 'show': self.show.name}
        )

        # Refresh show needs to be forced since current execution locks the queue
        app.show_queue_scheduler.action.refreshShow(self.show, True)
        self.finish()
        ws.Message('QueueItemShow', self.to_json).push()


class QueueItemSeasonUpdate(ShowQueueItem):
    def __init__(self, show, season):
        """Use QueueItem to partly show updates based on season.

        :param show: Show object to update.
        :param season: Season of the show to update, or list of seasons (int).
        """
        ShowQueueItem.__init__(self, ShowQueueActions.SEASON_UPDATE, show)
        self.priority = generic_queue.QueuePriorities.HIGH
        self.seasons = [season] if not isinstance(season, list) else season

    def run(self):

        ShowQueueItem.run(self)
        ws.Message('QueueItemShow', self.to_json).push()

        log.info(
            '{id}: Beginning update of {show}{season}',
            {'id': self.show.series_id,
             'show': self.show.name,
             'season': ' with season(s) [{0}]'.format(
                 ','.join(text_type(s) for s in self.seasons) if self.seasons else '')
             }
        )

        log.debug(
            '{id}: Retrieving show info from {indexer}',
            {'id': self.show.series_id, 'indexer': indexerApi(self.show.indexer).name}
        )
        try:
            # Let's make sure we refresh the indexer_api object attached to the show object.
            self.show.create_indexer()
            self.show.load_from_indexer(limit_seasons=self.seasons)
        except IndexerError as error:
            log.warning(
                '{id}: Unable to contact {indexer}. Aborting: {error_msg}',
                {'id': self.show.series_id, 'indexer': indexerApi(self.show.indexer).name,
                 'error_msg': error}
            )
            return
        except IndexerAttributeNotFound as error:
            log.warning(
                '{id}: Data retrieved from {indexer} was incomplete.'
                ' Aborting: {error_msg}',
                {'id': self.show.series_id, 'indexer': indexerApi(self.show.indexer).name,
                 'error_msg': error}
            )
            return

        log.debug(
            '{id}: Retrieving show info from IMDb',
            {'id': self.show.series_id}
        )
        try:
            self.show.load_imdb_info()
        except ImdbAPIError as error:
            log.info(
                '{id}: Something wrong on IMDb api: {error_msg}',
                {'id': self.show.series_id, 'error_msg': error}
            )
        except RequestException as error:
            log.warning(
                '{id}: Error loading IMDb info: {error_msg}',
                {'id': self.show.series_id, 'error_msg': error}
            )

        # have to save show before reading episodes from db
        try:
            log.debug(
                '{id}: Saving new IMDb show info to database',
                {'id': self.show.series_id}
            )
            self.show.save_to_db()
        except Exception as error:
            log.warning(
                '{id}: Error saving new IMDb show info to database: {error_msg}',
                {'id': self.show.series_id, 'error_msg': error}
            )
            log.error(traceback.format_exc())

        # get episode list from DB
        try:
            episodes_from_db = self.show.load_episodes_from_db(self.seasons)
        except IndexerException as error:
            log.warning(
                '{id}: Unable to contact {indexer}. Aborting: {error_msg}',
                {'id': self.show.series_id, 'indexer': indexerApi(self.show.indexer).name,
                 'error_msg': error}
            )
            return

        # get episode list from the indexer
        try:
            episodes_from_indexer = self.show.load_episodes_from_indexer(self.seasons)
        except IndexerException as error:
            log.warning(
                '{id}: Unable to get info from {indexer}. The show info will not be refreshed.'
                ' Error: {error_msg}',
                {'id': self.show.series_id, 'indexer': indexerApi(self.show.indexer).name,
                 'error_msg': error}
            )
            episodes_from_indexer = None

        if episodes_from_indexer is None:
            log.warning(
                '{id}: No data returned from {indexer} during season show update.'
                ' Unable to update this show',
                {'id': self.show.series_id, 'indexer': indexerApi(self.show.indexer).name}
            )
        else:
            # for each ep we found on the Indexer delete it from the DB list
            for cur_season in episodes_from_indexer:
                for cur_episode in episodes_from_indexer[cur_season]:
                    if cur_season in episodes_from_db and cur_episode in episodes_from_db[cur_season]:
                        del episodes_from_db[cur_season][cur_episode]

            # remaining episodes in the DB list are not on the indexer, just delete them from the DB
            for cur_season in episodes_from_db:
                for cur_episode in episodes_from_db[cur_season]:
                    log.debug(
                        '{id}: Permanently deleting episode {show} {ep} from the database',
                        {'id': self.show.series_id, 'show': self.show.name,
                         'ep': episode_num(cur_season, cur_episode)}
                    )
                    # Create the ep object only because Im going to delete it
                    ep_obj = self.show.get_episode(cur_season, cur_episode)
                    try:
                        ep_obj.delete_episode()
                    except EpisodeDeletedException:
                        log.debug(
                            '{id}: Episode {show} {ep} successfully deleted from the database',
                            {'id': self.show.series_id, 'show': self.show.name,
                             'ep': episode_num(cur_season, cur_episode)}
                        )

        # Save only after all changes were applied
        try:
            log.debug(
                '{id}: Saving all updated show info to database',
                {'id': self.show.series_id}
            )
            self.show.save_to_db()
        except Exception as error:
            log.warning(
                '{id}: Error saving all updated show info to database: {error_msg}',
                {'id': self.show.series_id, 'error_msg': error}
            )
            log.error(traceback.format_exc())

        log.info(
            '{id}: Finished update of {show}',
            {'id': self.show.series_id, 'show': self.show.name}
        )

        self.finish()
        ws.Message('QueueItemShow', self.to_json).push()


class QueueItemRemove(ShowQueueItem):
    def __init__(self, show=None, full=False):
        ShowQueueItem.__init__(self, ShowQueueActions.REMOVE, show)

        # let's make sure this happens before any other high priority actions
        self.priority = generic_queue.QueuePriorities.HIGH + generic_queue.QueuePriorities.HIGH
        self.full = full

    def run(self):
        ShowQueueItem.run(self)
        ws.Message('QueueItemShow', self.to_json).push()

        log.info(
            '{id}: Removing {show}',
            {'id': self.show.series_id, 'show': self.show.name}
        )

        # Need to first remove the episodes from the Trakt collection, because we need the list of
        # Episodes from the db to know which eps to remove.
        if app.USE_TRAKT:
            try:
                app.trakt_checker_scheduler.action.remove_show_trakt_library(self.show)
            except (TraktException, RequestException, JSONDecodeError) as error:
                log.warning(
                    '{id}: Unable to delete show {show} from Trakt.'
                    ' Please remove manually otherwise it will be added again.'
                    ' Error: {error_msg}',
                    {'id': self.show.series_id, 'show': self.show.name, 'error_msg': error}
                )
            except Exception as error:
                log.exception('Exception occurred while trying to delete show {show}, error: {error',
                              {'show': self.show.name, 'error': error})

        self.show.delete_show(full=self.full)

        self.finish()
        # Send showRemoved to frontend, so we can remove it from localStorage.
        ws.Message('QueueItemShow', self.show.to_json(detailed=False)).push()
