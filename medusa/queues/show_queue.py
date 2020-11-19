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

from imdbpie.exceptions import ImdbAPIError

from medusa import (
    app,
    scene_numbering,
    ui,
    ws,
)
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
from medusa.tv.series import SaveSeriesException, Series, SeriesIdentifier

from requests import RequestException

from six import ensure_text, text_type, viewitems

from traktor import TraktException

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

    names = {
        REFRESH: 'Refresh',
        ADD: 'Add',
        UPDATE: 'Update',
        RENAME: 'Rename',
        SUBTITLE: 'Subtitle',
        REMOVE: 'Remove Show',
        SEASON_UPDATE: 'Season Update',
    }


class ShowQueue(generic_queue.GenericQueue):

    mappings = {
        ShowQueueActions.ADD: 'This show is in the process of being downloaded - the info below is incomplete.',
        ShowQueueActions.UPDATE: 'The information on this page is in the process of being updated.',
        ShowQueueActions.SEASON_UPDATE: 'The information on this page is in the process of being updated.',
        ShowQueueActions.REFRESH: 'The episodes below are currently being refreshed from disk',
        ShowQueueActions.SUBTITLE: 'Currently downloading subtitles for this show',
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
        return self.currentItem is not None and show == self.currentItem.show and self.currentItem.action_id in actions

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
        return [x for x in self.queue + [self.currentItem] if x is not None and x.isLoading]

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
            if item and item.show and item != self.currentItem and show.identifier == item.show.identifier:
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
            'show': self.show
        })

    def isInQueue(self):
        return self in app.show_queue_scheduler.action.queue + [
            app.show_queue_scheduler.action.currentItem]  # @UndefinedVariable

    def _getName(self):
        return text_type(self.show.series_id)

    def _isLoading(self):
        return False

    show_name = property(_getName)

    isLoading = property(_isLoading)


class QueueItemAdd(ShowQueueItem):
    def __init__(self, indexer, indexer_id, show_dir, **options):

        # show_dir, default_status, quality, season_folders, lang, subtitles, anime,
        #          scene, paused, blacklist, whitelist, default_status_after, root_dir, show_lists):

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
        series = Series.from_identifier(SeriesIdentifier.from_slug(show_slug))

        step = []

        # Small helper, to reduce code for messaging
        def message_step(new_step):
            step.append(new_step)
            ws.Message('QueueItemShowAdd', dict(
                step=step, **self.to_json
            )).push()

        try:
            try:
                # Push an update to any open Web UIs through the WebSocket
                message_step('load show from {indexer}'.format(indexer=indexerApi(self.indexer).name))

                api = series.identifier.get_indexer_api(self.options)

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

                series.load_from_indexer(tvapi=api)

                message_step('load info from imdb')
                series.load_imdb_info()
            except IndexerException as error:
                log.warning('Unable to load series from indexer: {0!r}'.format(error))
                raise SaveSeriesException('Unable to load series from indexer: {0!r}'.format(error))

            message_step('check if show is already added')

            try:
                message_step('configure show options')
                series.configure(self)
            except KeyError as error:
                log.error(
                    'Unable to add show {series_name} due to an error with one of the provided options: {error}',
                    {'series_name': series.name, 'error': error}
                )
                ui.notifications.error(
                    'Unable to add show {series_name} due to an error with one of the provided options: {error}'.format(
                        series_name=series.name, error=error
                    )
                )
                raise SaveSeriesException(
                    'Unable to add show {series_name} due to an error with one of the provided options: {error}'.format(
                        series_name=series.name, error=error
                    ))

            except Exception as error:
                log.error('Error trying to configure show: {0}', error)
                log.debug(traceback.format_exc())
                raise

            app.showList.append(series)
            series.save_to_db()

            try:
                message_step('load episodes from {indexer}'.format(indexer=indexerApi(self.indexer).name))
                series.load_episodes_from_indexer(tvapi=api)
                # If we provide a default_status_after through the apiv2 series route options object.
                # set it after we've added the episodes.
                self.default_ep_status = self.options['default_status_after'] \
                    if self.options.get('default_status_after') is not None else app.STATUS_DEFAULT_AFTER

            except IndexerException as error:
                log.warning('Unable to load series episodes from indexer: {0!r}'.format(error))
                raise SaveSeriesException(
                    'Unable to load series episodes from indexer: {0!r}'.format(error)
                )

            message_step('create metadata in show folder')
            series.write_metadata()
            series.update_metadata()
            series.populate_cache()
            build_name_cache(series)  # update internal name cache
            series.flush_episodes()
            series.sync_trakt()

            message_step('add scene numbering')
            series.add_scene_numbering()

        except SaveSeriesException as error:
            log.warning('Unable to add series: {0!r}'.format(error))
            self.success = False
            self._finish_early()
            log.debug(traceback.format_exc())

        self.success = True

        ws.Message('showAdded', series.to_json(detailed=False)).push()  # Send ws update to client
        message_step('finished')
        self.finish()

    def _finish_early(self):
        if self.show is not None:
            app.show_queue_scheduler.action.removeShow(self.show)

        self.finish()


class QueueItemRefresh(ShowQueueItem):
    def __init__(self, show=None, force=False):
        ShowQueueItem.__init__(self, ShowQueueActions.REFRESH, show)

        # do refreshes first because they're quick
        self.priority = generic_queue.QueuePriorities.HIGH

        # force refresh certain items
        self.force = force

    def run(self):

        ShowQueueItem.run(self)

        log.info(
            '{id}: Performing refresh on {show}',
            {'id': self.show.series_id, 'show': self.show.name}
        )

        try:
            self.show.refresh_dir()
            if self.force:
                self.show.update_metadata()
            self.show.write_metadata()
            self.show.populate_cache()

            # Load XEM data to DB for show
            scene_numbering.xem_refresh(self.show, force=True)
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


class QueueItemRename(ShowQueueItem):
    def __init__(self, show=None):
        ShowQueueItem.__init__(self, ShowQueueActions.RENAME, show)

    def run(self):

        ShowQueueItem.run(self)

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


class QueueItemSubtitle(ShowQueueItem):
    def __init__(self, show=None):
        ShowQueueItem.__init__(self, ShowQueueActions.SUBTITLE, show)

    def run(self):

        ShowQueueItem.run(self)

        log.info(
            '{id}: Downloading subtitles for {show}',
            {'id': self.show.series_id, 'show': self.show.name}
        )

        self.show.download_subtitles()
        self.finish()


class QueueItemUpdate(ShowQueueItem):
    def __init__(self, show):
        """Use QueueItem to perform full show updates.

        :param show: Show object to update.
        """
        ShowQueueItem.__init__(self, ShowQueueActions.UPDATE, show)
        self.priority = generic_queue.QueuePriorities.HIGH

    def run(self):

        ShowQueueItem.run(self)

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
            self.show.load_from_indexer()
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


class QueueItemRemove(ShowQueueItem):
    def __init__(self, show=None, full=False):
        ShowQueueItem.__init__(self, ShowQueueActions.REMOVE, show)

        # let's make sure this happens before any other high priority actions
        self.priority = generic_queue.QueuePriorities.HIGH + generic_queue.QueuePriorities.HIGH
        self.full = full

    def run(self):

        ShowQueueItem.run(self)

        log.info(
            '{id}: Removing {show}',
            {'id': self.show.series_id, 'show': self.show.name}
        )

        # Need to first remove the episodes from the Trakt collection, because we need the list of
        # Episodes from the db to know which eps to remove.
        if app.USE_TRAKT:
            try:
                app.trakt_checker_scheduler.action.remove_show_trakt_library(self.show)
            except TraktException as error:
                log.warning(
                    '{id}: Unable to delete show {show} from Trakt.'
                    ' Please remove manually otherwise it will be added again.'
                    ' Error: {error_msg}',
                    {'id': self.show.series_id, 'show': self.show.name, 'error_msg': error}
                )

        self.show.delete_show(full=self.full)

        self.finish()
