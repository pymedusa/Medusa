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

import os
import traceback

from imdb import _exceptions as imdb_exceptions
from six import binary_type, text_type
from traktor import TraktException
from . import app, generic_queue, logger, name_cache, notifiers, scene_numbering, ui
from .black_and_white_list import BlackAndWhiteList
from .common import WANTED
from .helper.common import episode_num, sanitize_filename
from .helper.exceptions import (
    CantRefreshShowException, CantRemoveShowException, CantUpdateShowException,
    EpisodeDeletedException, MultipleShowObjectsException, ShowDirectoryNotFoundException, ex
)
from .helper.externals import check_existing_shows
from .helpers import chmod_as_parent, delete_empty_folders, get_showname_from_indexer, make_dir
from .indexers.indexer_api import indexerApi
from .indexers.indexer_exceptions import (IndexerAttributeNotFound, IndexerError, IndexerException,
                                          IndexerShowAllreadyInLibrary, IndexerShowIncomplete,
                                          IndexerShowNotFoundInLanguage)
from .tv import Series


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
        self.queue_name = "SHOWQUEUE"

    def _isInQueue(self, show, actions):
        if not show:
            return False

        return show.indexerid in [x.show.indexerid if x.show else 0 for x in self.queue if x.action_id in actions]

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
        for action, message in self.mappings.items():
            if self._isBeingSomethinged(show, (action, )):
                return action, message

        for action, message in self.queue_mappings.items():
            if self._isInQueue(show, (action, )):
                return action, message

        return None, None

    loadingShowList = property(_getLoadingShowList)

    def updateShow(self, show, season=None):

        if self.isBeingAdded(show):
            raise CantUpdateShowException(
                u"{show_name} is still being added, wait until it is finished before you update."
                .format(show_name=show.name))

        if self.isBeingUpdated(show):
            raise CantUpdateShowException(
                u"{show_name} is already being updated by Post-processor or manually started, "
                u"can't update again until it's done."
                .format(show_name=show.name))

        if self.isInUpdateQueue(show):
            raise CantUpdateShowException(
                u"{show_name} is in process of being updated by Post-processor or manually started, "
                u"can't update again until it's done."
                .format(show_name=show.name))

        queue_item_update_show = QueueItemUpdate(show) if season is None else QueueItemSeasonUpdate(show, season)

        self.add_item(queue_item_update_show)

        return queue_item_update_show

    def refreshShow(self, show, force=False):

        if self.isBeingRefreshed(show) and not force:
            raise CantRefreshShowException("This show is already being refreshed, not refreshing again.")

        if (self.isBeingUpdated(show) or self.isInUpdateQueue(show)) and not force:
            logger.log(
                u"A refresh was attempted but there is already an update queued or in progress. "
                u"Since updates do a refresh at the end anyway I'm skipping this request.", logger.DEBUG)
            return

        queueItemObj = QueueItemRefresh(show, force=force)

        logger.log(u"{id}: Queueing show refresh for {show}".format
                   (id=show.indexerid, show=show.name), logger.DEBUG)

        self.add_item(queueItemObj)

        return queueItemObj

    def renameShowEpisodes(self, show):

        queueItemObj = QueueItemRename(show)

        self.add_item(queueItemObj)

        return queueItemObj

    def download_subtitles(self, show):

        queueItemObj = QueueItemSubtitle(show)

        self.add_item(queueItemObj)

        return queueItemObj

    def addShow(self, indexer, indexer_id, showDir, default_status=None, quality=None, flatten_folders=None,
                lang=None, subtitles=None, anime=None, scene=None, paused=None, blacklist=None, whitelist=None,
                default_status_after=None, root_dir=None):

        if lang is None:
            lang = app.INDEXER_DEFAULT_LANGUAGE

        queueItemObj = QueueItemAdd(indexer, indexer_id, showDir, default_status, quality, flatten_folders, lang,
                                    subtitles, anime, scene, paused, blacklist, whitelist, default_status_after,
                                    root_dir)

        self.add_item(queueItemObj)

        return queueItemObj

    def removeShow(self, show, full=False):
        if show is None:
            raise CantRemoveShowException(u'Failed removing show: Show does not exist')

        if not hasattr(show, u'indexerid'):
            raise CantRemoveShowException(u'Failed removing show: Show does not have an indexer id')

        if self.isBeingRemoved(show):
            raise CantRemoveShowException(u'[{!s}]: Show is already being removed'.format(show.indexerid))

        if self.isInRemoveQueue(show):
            raise CantRemoveShowException(u'[{!s}]: Show is already queued to be removed'.format(show.indexerid))

        # remove other queued actions for this show.
        for item in self.queue:
            if item and item.show and item != self.currentItem and show.indexerid == item.show.indexerid:
                self.queue.remove(item)

        queue_item_obj = QueueItemRemove(show=show, full=full)
        self.add_item(queue_item_obj)

        # Show removal has been queued, let's updaste the app.RECENTLY_DELETED global, to keep track of it
        app.RECENTLY_DELETED.update([show.indexerid])

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

    def isInQueue(self):
        return self in app.show_queue_scheduler.action.queue + [
            app.show_queue_scheduler.action.currentItem]  # @UndefinedVariable

    def _getName(self):
        return str(self.show.indexerid)

    def _isLoading(self):
        return False

    show_name = property(_getName)

    isLoading = property(_isLoading)


class QueueItemAdd(ShowQueueItem):
    def __init__(self, indexer, indexer_id, showDir, default_status, quality, flatten_folders, lang, subtitles, anime,
                 scene, paused, blacklist, whitelist, default_status_after, root_dir):

        if isinstance(showDir, binary_type):
            self.showDir = text_type(showDir, 'utf-8')
        else:
            self.showDir = showDir

        self.indexer = indexer
        self.indexer_id = indexer_id
        self.default_status = default_status
        self.quality = quality
        self.flatten_folders = flatten_folders
        self.lang = lang
        self.subtitles = subtitles
        self.anime = anime
        self.scene = scene
        self.paused = paused
        self.blacklist = blacklist
        self.whitelist = whitelist
        self.default_status_after = default_status_after
        self.root_dir = root_dir

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
            return self.showDir
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

        logger.log(u"Starting to add show {0}".format("by ShowDir: {0}".format(self.showDir) if self.showDir else
                   u"by Indexer Id: {0}".format(self.indexer_id)))

        # make sure the Indexer IDs are valid
        try:
            lINDEXER_API_PARMS = indexerApi(self.indexer).api_params.copy()
            if self.lang:
                lINDEXER_API_PARMS['language'] = self.lang

            logger.log(u"" + str(indexerApi(self.indexer).name) + ": " + repr(lINDEXER_API_PARMS))

            t = indexerApi(self.indexer).indexer(**lINDEXER_API_PARMS)
            s = t[self.indexer_id]

            # Let's try to create the show Dir if it's not provided. This way we force the show dir
            # to build build using the Indexers provided series name
            if not self.showDir and self.root_dir:
                show_name = get_showname_from_indexer(self.indexer, self.indexer_id, self.lang)
                if show_name:
                    self.showDir = os.path.join(self.root_dir, sanitize_filename(show_name))
                    dir_exists = make_dir(self.showDir)
                    if not dir_exists:
                        logger.log(u"Unable to create the folder {0}, can't add the show".format(self.showDir))
                        return

                    chmod_as_parent(self.showDir)
                else:
                    logger.log(u"Unable to get a show {0}, can't add the show".format(self.showDir))
                    return

            # this usually only happens if they have an NFO in their show dir which gave us a Indexer ID that
            # has no proper english version of the show
            if getattr(s, 'seriesname', None) is None:
                logger.log(u"Show in {0} has no name on {1}, probably searched with the wrong language.".format
                           (self.showDir, indexerApi(self.indexer).name), logger.ERROR)

                ui.notifications.error('Unable to add show',
                                       'Show in {0} has no name on {1}, probably the wrong language. \
                                       Delete .nfo and manually add the correct language.'
                                       .format(self.showDir, indexerApi(self.indexer).name))
                self._finishEarly()
                return
            # if the show has no episodes/seasons
            if not s:
                logger.log(u"Show " + str(s['seriesname']) + u" is on " + str(indexerApi(self.indexer).name) +
                           u" but contains no season/episode data.")
                ui.notifications.error("Unable to add show",
                                       "Show {0} is on {1} but contains no season/episode data.".
                                       format(s['seriesname'], indexerApi(self.indexer).name))
                self._finishEarly()

                return

            # Check if we can already find this show in our current showList.
            try:
                check_existing_shows(s, self.indexer)
            except IndexerShowAllreadyInLibrary as e:
                logger.log(u"Could not add the show %s, as it already is in your library."
                           u" Error: %s" % (s['seriesname'], e.message), logger.WARNING)
                ui.notifications.error(
                    'Unable to add show',
                    'reason: {0}' .format(e.message)
                )
                self._finishEarly()

                # Clean up leftover if the newly created directory is empty.
                delete_empty_folders(self.showDir)
                return

        # TODO: Add more specific indexer exceptions, that should provide the user with some accurate feedback.
        except IndexerShowIncomplete as e:
            logger.log(u"%s Error while loading information from indexer %s. "
                       u"Error: %s" % (self.indexer_id, indexerApi(self.indexer).name, e.message), logger.WARNING)
            ui.notifications.error(
                "Unable to add show",
                "Unable to look up the show in {0} on {1} using ID {2} "
                "Reason: {3}"
                .format(self.showDir, indexerApi(self.indexer).name, self.indexer_id, e)
            )
            self._finishEarly()
            return
        except Exception as e:
            logger.log(u"%s Error while loading information from indexer %s. "
                       u"Error: %r" % (self.indexer_id, indexerApi(self.indexer).name, ex(e)), logger.ERROR)
            ui.notifications.error(
                "Unable to add show",
                "Unable to look up the show in {0} on {1} using ID {2}, not using the NFO. "
                "Delete .nfo and try adding manually again.".
                format(self.showDir, indexerApi(self.indexer).name, self.indexer_id)
            )
            self._finishEarly()
            return

        try:
            newShow = Series(self.indexer, self.indexer_id, self.lang)
            newShow.load_from_indexer(t)

            self.show = newShow

            # set up initial values
            self.show.location = self.showDir
            self.show.subtitles = self.subtitles if self.subtitles is not None else app.SUBTITLES_DEFAULT
            self.show.quality = self.quality if self.quality else app.QUALITY_DEFAULT
            self.show.flatten_folders = self.flatten_folders if self.flatten_folders is not None \
                else app.FLATTEN_FOLDERS_DEFAULT
            self.show.anime = self.anime if self.anime is not None else app.ANIME_DEFAULT
            self.show.scene = self.scene if self.scene is not None else app.SCENE_DEFAULT
            self.show.paused = self.paused if self.paused is not None else False

            # set up default new/missing episode status
            logger.log(u"Setting all episodes to the specified default status: " + str(self.show.default_ep_status))
            self.show.default_ep_status = self.default_status

            if self.show.anime:
                self.show.release_groups = BlackAndWhiteList(self.show.indexerid)
                if self.blacklist:
                    self.show.release_groups.set_black_keywords(self.blacklist)
                if self.whitelist:
                    self.show.release_groups.set_white_keywords(self.whitelist)

            # # be smartish about this
            # if self.show.genre and "talk show" in self.show.genre.lower():
            #     self.show.air_by_date = 1
            # if self.show.genre and "documentary" in self.show.genre.lower():
            #     self.show.air_by_date = 0
            # if self.show.classification and "sports" in self.show.classification.lower():
            #     self.show.sports = 1

        except IndexerException as e:
            logger.log(
                u"Unable to add show due to an error with " + indexerApi(self.indexer).name + ": " + ex(e),
                logger.ERROR)
            if self.show:
                ui.notifications.error(
                    "Unable to add " + str(self.show.name) + " due to an error with " + indexerApi(
                        self.indexer).name + "")
            else:
                ui.notifications.error(
                    "Unable to add show due to an error with " + indexerApi(self.indexer).name + "")
            self._finishEarly()
            return

        except MultipleShowObjectsException:
            logger.log(u"The show in " + self.showDir + " is already in your show list, skipping", logger.WARNING)
            ui.notifications.error('Show skipped', "The show in " + self.showDir + " is already in your show list")
            self._finishEarly()
            return

        except Exception as e:
            logger.log(u"Error trying to add show: " + ex(e), logger.ERROR)
            logger.log(traceback.format_exc(), logger.DEBUG)
            self._finishEarly()
            raise

        logger.log(u"Retrieving show info from IMDb", logger.DEBUG)
        try:
            self.show.load_imdb_info()
        except imdb_exceptions.IMDbError as e:
            logger.log(u"Something wrong on IMDb api: " + ex(e), logger.WARNING)
        except Exception as e:
            logger.log(u"Error loading IMDb info: " + ex(e), logger.ERROR)

        try:
            self.show.save_to_db()
        except Exception as e:
            logger.log(u"Error saving the show to the database: " + ex(e), logger.ERROR)
            logger.log(traceback.format_exc(), logger.DEBUG)
            self._finishEarly()
            raise

        # add it to the show list
        app.showList.append(self.show)

        try:
            self.show.load_episodes_from_indexer(tvapi=t)
        except Exception as e:
            logger.log(
                u"Error with " + indexerApi(self.show.indexer).name + ", not creating episode list: " + ex(e),
                logger.ERROR)
            logger.log(traceback.format_exc(), logger.DEBUG)

        # update internal name cache
        name_cache.build_name_cache(self.show)

        try:
            self.show.load_episodes_from_dir()
        except Exception as e:
            logger.log(u"Error searching dir for episodes: " + ex(e), logger.ERROR)
            logger.log(traceback.format_exc(), logger.DEBUG)

        # if they set default ep status to WANTED then run the backlog to search for episodes
        # FIXME: This needs to be a backlog queue item!!!
        if self.show.default_ep_status == WANTED:
            logger.log(u"Launching backlog for this show since its episodes are WANTED")
            app.backlog_search_scheduler.action.search_backlog([self.show])

        self.show.write_metadata()
        self.show.update_metadata()
        self.show.populate_cache()

        self.show.flush_episodes()

        if app.USE_TRAKT:
            # if there are specific episodes that need to be added by trakt
            app.trakt_checker_scheduler.action.manage_new_show(self.show)

            # add show to trakt.tv library
            if app.TRAKT_SYNC:
                app.trakt_checker_scheduler.action.add_show_trakt_library(self.show)

            if app.TRAKT_SYNC_WATCHLIST:
                logger.log(u"update watchlist")
                notifiers.trakt_notifier.update_watchlist(show_obj=self.show)

        # Load XEM data to DB for show
        scene_numbering.xem_refresh(self.show.indexerid, self.show.indexer, force=True)

        # check if show has XEM mapping so we can determine if searches
        # should go by scene numbering or indexer numbering.
        if not self.scene and scene_numbering.get_xem_numbering_for_show(self.show.indexerid,
                                                                         self.show.indexer):
            self.show.scene = 1

        # After initial add, set to default_status_after.
        self.show.default_ep_status = self.default_status_after

        self.finish()

    def _finishEarly(self):
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

        logger.log(u"{id}: Performing refresh on {show}".format(id=self.show.indexerid, show=self.show.name))

        try:
            self.show.refresh_dir()
            if self.force:
                self.show.update_metadata()
            self.show.write_metadata()
            self.show.populate_cache()

            # Load XEM data to DB for show
            scene_numbering.xem_refresh(self.show.indexerid, self.show.indexer)
        except Exception as e:
            logger.log(u"{id}: Error while refreshing show {show}. Error: {error_msg}".format
                       (id=self.show.indexerid, show=self.show.name, error_msg=e), logger.ERROR)

        self.finish()


class QueueItemRename(ShowQueueItem):
    def __init__(self, show=None):
        ShowQueueItem.__init__(self, ShowQueueActions.RENAME, show)

    def run(self):

        ShowQueueItem.run(self)

        logger.log(u"Performing rename on " + self.show.name)

        try:
            self.show.location
        except ShowDirectoryNotFoundException:
            logger.log(u"Can't perform rename on " + self.show.name + " when the show dir is missing.", logger.WARNING)
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

        logger.log(u'{id}: Downloading subtitles for {show}'.format
                   (id=self.show.indexerid, show=self.show.name), logger.INFO)

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

        logger.log(u'{id}: Beginning update of {show}'.format(id=self.show.indexerid,
                   show=self.show.name), logger.DEBUG)

        logger.log(u'{id}: Retrieving show info from {indexer}'.format
                   (id=self.show.indexerid, indexer=indexerApi(self.show.indexer).name),
                   logger.DEBUG)
        try:
            # Let's make sure we refresh the indexer_api object attached to the show object.
            self.show.create_indexer()
            self.show.load_from_indexer()
        except IndexerError as e:
            logger.log(u'{id}: Unable to contact {indexer}. Aborting: {error_msg}'.format
                       (id=self.show.indexerid, indexer=indexerApi(self.show.indexer).name,
                        error_msg=ex(e)), logger.WARNING)
            return
        except IndexerAttributeNotFound as e:
            logger.log(u'{id}: Data retrieved from {indexer} was incomplete. Aborting: {error_msg}'.format
                       (id=self.show.indexerid, indexer=indexerApi(self.show.indexer).name,
                        error_msg=ex(e)), logger.WARNING)
            return
        except IndexerShowNotFoundInLanguage as e:
            logger.log(u'{id}: Data retrieved from {indexer} was incomplete. The indexer does not provide '
                       u'show information in the searched language {language}. Aborting: {error_msg}'.format
                       (language=e.language, id=self.show.indexerid, indexer=indexerApi(self.show.indexer).name,
                        error_msg=ex(e)), logger.WARNING)
            ui.notifications.error('Error changing language show!',
                                   'Unable to change language for show {show_name} on {indexer} to language: {language}'.
                                   format(show_name=self.show.name,
                                          indexer=indexerApi(self.show.indexer).name,
                                          language=e.language))
            return

        logger.log(u'{id}: Retrieving show info from IMDb'.format(id=self.show.indexerid), logger.DEBUG)
        try:
            self.show.load_imdb_info()
        except imdb_exceptions.IMDbError as e:
            logger.log(u'{id}: Something wrong on IMDb api: {error_msg}'.format
                       (id=self.show.indexerid, error_msg=ex(e)), logger.WARNING)
        except Exception as e:
            logger.log(u'{id}: Error loading IMDb info: {error_msg}'.format
                       (id=self.show.indexerid, error_msg=ex(e)), logger.WARNING)

        # have to save show before reading episodes from db
        try:
            logger.log(u'{id}: Saving new IMDb show info to database'.format(id=self.show.indexerid), logger.DEBUG)
            self.show.save_to_db()
        except Exception as e:
            logger.log(u"{id}: Error saving new IMDb show info to database: {error_msg}".format
                       (id=self.show.indexerid, error_msg=ex(e)), logger.WARNING)
            logger.log(traceback.format_exc(), logger.ERROR)

        # get episode list from DB
        try:
            episodes_from_db = self.show.load_episodes_from_db()
        except IndexerException as e:
            logger.log(u'{id}: Unable to contact {indexer}. Aborting: {error_msg}'.format
                       (id=self.show.indexerid, indexer=indexerApi(self.show.indexer).name,
                        error_msg=e), logger.WARNING)
            return

        # get episode list from the indexer
        try:
            episodes_from_indexer = self.show.load_episodes_from_indexer()
        except IndexerException as e:
            logger.log(u'{id}: Unable to get info from {indexer}. The show info will not be refreshed. '
                       u'Error: {error_msg}'.format
                       (id=self.show.indexerid, indexer=indexerApi(self.show.indexer).name, error_msg=ex(e)),
                       logger.WARNING)
            episodes_from_indexer = None

        if episodes_from_indexer is None:
            logger.log(u'{id}: No data returned from {indexer} during full show update. Unable to update this show'.format
                       (id=self.show.indexerid, indexer=indexerApi(self.show.indexer).name),
                       logger.WARNING)
        else:
            # for each ep we found on the Indexer delete it from the DB list
            for cur_season in episodes_from_indexer:
                for cur_episode in episodes_from_indexer[cur_season]:
                    if cur_season in episodes_from_db and cur_episode in episodes_from_db[cur_season]:
                        del episodes_from_db[cur_season][cur_episode]

            # remaining episodes in the DB list are not on the indexer, just delete them from the DB
            for cur_season in episodes_from_db:
                for cur_episode in episodes_from_db[cur_season]:
                    logger.log(u'{id}: Permanently deleting episode {show} {ep} from the database'.format
                               (id=self.show.indexerid, show=self.show.name, ep=episode_num(cur_season, cur_episode)),
                               logger.DEBUG)
                    # Create the ep object only because Im going to delete it
                    ep_obj = self.show.get_episode(cur_season, cur_episode)
                    try:
                        ep_obj.delete_episode()
                    except EpisodeDeletedException:
                        logger.log(u'{id}: Episode {show} {ep} successfully deleted from the database'.format
                                   (id=self.show.indexerid, show=self.show.name,
                                    ep=episode_num(cur_season, cur_episode)), logger.DEBUG)

        # Save only after all changes were applied
        try:
            logger.log(u'{id}: Saving all updated show info to database'.format(id=self.show.indexerid), logger.DEBUG)
            self.show.save_to_db()
        except Exception as e:
            logger.log(u'{id}: Error saving all updated show info to database: {error_msg}'.format
                       (id=self.show.indexerid, error_msg=ex(e)), logger.WARNING)
            logger.log(traceback.format_exc(), logger.ERROR)

        logger.log(u'{id}: Finished update of {show}'.format
                   (id=self.show.indexerid, show=self.show.name), logger.DEBUG)

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

        logger.log(u'{id}: Beginning update of {show}{season}'.format
                   (id=self.show.indexerid,
                    show=self.show.name,
                    season=u' with season(s) [{0}]'.
                    format(u','.join(str(s) for s in self.seasons) if self.seasons else u'')
                    ), logger.INFO)

        logger.log(u'{id}: Retrieving show info from {indexer}'.format
                   (id=self.show.indexerid, indexer=indexerApi(self.show.indexer).name),
                   logger.DEBUG)
        try:
            # Let's make sure we refresh the indexer_api object attached to the show object.
            self.show.create_indexer()
            self.show.load_from_indexer()
        except IndexerError as e:
            logger.log(u'{id}: Unable to contact {indexer}. Aborting: {error_msg}'.format
                       (id=self.show.indexerid, indexer=indexerApi(self.show.indexer).name,
                        error_msg=ex(e)), logger.WARNING)
            return
        except IndexerAttributeNotFound as e:
            logger.log(u'{id}: Data retrieved from {indexer} was incomplete. Aborting: {error_msg}'.format
                       (id=self.show.indexerid, indexer=indexerApi(self.show.indexer).name,
                        error_msg=ex(e)), logger.WARNING)
            return

        logger.log(u'{id}: Retrieving show info from IMDb'.format(id=self.show.indexerid), logger.DEBUG)
        try:
            self.show.load_imdb_info()
        except imdb_exceptions.IMDbError as e:
            logger.log(u'{id}: Something wrong on IMDb api: {error_msg}'.format
                       (id=self.show.indexerid, error_msg=ex(e)), logger.WARNING)
        except Exception as e:
            logger.log(u'{id}: Error loading IMDb info: {error_msg}'.format
                       (id=self.show.indexerid, error_msg=ex(e)), logger.WARNING)

        # have to save show before reading episodes from db
        try:
            logger.log(u'{id}: Saving new IMDb show info to database'.format(id=self.show.indexerid), logger.DEBUG)
            self.show.save_to_db()
        except Exception as e:
            logger.log(u"{id}: Error saving new IMDb show info to database: {error_msg}".format
                       (id=self.show.indexerid, error_msg=ex(e)), logger.WARNING)
            logger.log(traceback.format_exc(), logger.ERROR)

        # get episode list from DB
        try:
            episodes_from_db = self.show.load_episodes_from_db(self.seasons)
        except IndexerException as e:
            logger.log(u'{id}: Unable to contact {indexer}. Aborting: {error_msg}'.format
                       (id=self.show.indexerid, indexer=indexerApi(self.show.indexer).name,
                        error_msg=e), logger.WARNING)
            return

        # get episode list from the indexer
        try:
            episodes_from_indexer = self.show.load_episodes_from_indexer(self.seasons)
        except IndexerException as e:
            logger.log(u'{id}: Unable to get info from {indexer}. The show info will not be refreshed. '
                       u'Error: {error_msg}'.format
                       (id=self.show.indexerid, indexer=indexerApi(self.show.indexer).name, error_msg=ex(e)),
                       logger.WARNING)
            episodes_from_indexer = None

        if episodes_from_indexer is None:
            logger.log(u'{id}: No data returned from {indexer} during season show update. Unable to update this show'.format
                       (id=self.show.indexerid, indexer=indexerApi(self.show.indexer).name),
                       logger.WARNING)
        else:
            # for each ep we found on the Indexer delete it from the DB list
            for cur_season in episodes_from_indexer:
                for cur_episode in episodes_from_indexer[cur_season]:
                    if cur_season in episodes_from_db and cur_episode in episodes_from_db[cur_season]:
                        del episodes_from_db[cur_season][cur_episode]

            # remaining episodes in the DB list are not on the indexer, just delete them from the DB
            for cur_season in episodes_from_db:
                for cur_episode in episodes_from_db[cur_season]:
                    logger.log(u'{id}: Permanently deleting episode {show} {ep} from the database'.format
                               (id=self.show.indexerid, show=self.show.name, ep=episode_num(cur_season, cur_episode)),
                               logger.DEBUG)
                    # Create the ep object only because Im going to delete it
                    ep_obj = self.show.get_episode(cur_season, cur_episode)
                    try:
                        ep_obj.delete_episode()
                    except EpisodeDeletedException:
                        logger.log(u'{id}: Episode {show} {ep} successfully deleted from the database'.format
                                   (id=self.show.indexerid, show=self.show.name,
                                    ep=episode_num(cur_season, cur_episode)), logger.DEBUG)

        # Save only after all changes were applied
        try:
            logger.log(u'{id}: Saving all updated show info to database'.format(id=self.show.indexerid), logger.DEBUG)
            self.show.save_to_db()
        except Exception as e:
            logger.log(u'{id}: Error saving all updated show info to database: {error_msg}'.format
                       (id=self.show.indexerid, error_msg=ex(e)), logger.WARNING)
            logger.log(traceback.format_exc(), logger.ERROR)

        logger.log(u'{id}: Finished update of {show}'.format
                   (id=self.show.indexerid, show=self.show.name), logger.INFO)

        self.finish()


class QueueItemRemove(ShowQueueItem):
    def __init__(self, show=None, full=False):
        ShowQueueItem.__init__(self, ShowQueueActions.REMOVE, show)

        # let's make sure this happens before any other high priority actions
        self.priority = generic_queue.QueuePriorities.HIGH + generic_queue.QueuePriorities.HIGH
        self.full = full

    def run(self):

        ShowQueueItem.run(self)

        logger.log(u'{id}: Removing {show}'.format(id=self.show.indexerid, show=self.show.name))

        # Need to first remove the episodes from the Trakt collection, because we need the list of
        # Episodes from the db to know which eps to remove.
        if app.USE_TRAKT:
            try:
                app.trakt_checker_scheduler.action.remove_show_trakt_library(self.show)
            except TraktException as e:
                logger.log(u'{id}: Unable to delete show {show} from Trakt. '
                           u'Please remove manually otherwise it will be added again. Error: {error_msg}'.format
                           (id=self.show.indexerid, show=self.show.name, error_msg=ex(e)), logger.WARNING)

        self.show.delete_show(full=self.full)

        self.finish()
