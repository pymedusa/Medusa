import logging
import os
import traceback

from imdbpie.exceptions import ImdbAPIError

from medusa import (
    app,
    generic_queue,
    name_cache,
    notifiers,
    scene_numbering,
    ui,
)
from medusa.black_and_white_list import BlackAndWhiteList
from medusa.common import WANTED, statusStrings
from medusa.helper.common import episode_num, sanitize_filename
from medusa.helper.exceptions import (
    CantRefreshShowException,
    CantRemoveShowException,
    CantUpdateShowException,
    EpisodeDeletedException,
    MultipleShowObjectsException,
    ShowDirectoryNotFoundException
)
from medusa.helpers import (
    chmod_as_parent,
    delete_empty_folders,
    get_showname_from_indexer,
    make_dir,
)
from medusa.helpers.externals import check_existing_shows
from medusa.image_cache import replace_images
from medusa.indexers.api import indexerApi
from medusa.indexers.exceptions import (
    IndexerAttributeNotFound,
    IndexerError,
    IndexerException,
    IndexerShowAllreadyInLibrary,
    IndexerShowIncomplete,
    IndexerShowNotFoundInLanguage,
)
from medusa.tv import Series

from six import binary_type, text_type

from traktor import TraktException

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


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

    def _is_in_queue(self, show, actions):
        if not show:
            return False

        return show.series_id in [x.show.series_id if x.show else 0 for x in self.queue if x.action_id in actions]

    def _is_being_processed(self, show, actions):
        return self.currentItem is not None and show == self.currentItem.show and self.currentItem.action_id in actions

    def is_in_update_queue(self, show):
        return self._is_in_queue(show, (ShowQueueActions.UPDATE,))

    def is_in_refresh_queue(self, show):
        return self._is_in_queue(show, (ShowQueueActions.REFRESH,))

    def is_in_rename_queue(self, show):
        return self._is_in_queue(show, (ShowQueueActions.RENAME,))

    def is_in_subtitle_queue(self, show):
        return self._is_in_queue(show, (ShowQueueActions.SUBTITLE,))

    def is_in_remove_queue(self, show):
        return self._is_in_queue(show, (ShowQueueActions.REMOVE,))

    def is_being_added(self, show):
        return self._is_being_processed(show, (ShowQueueActions.ADD,))

    def is_being_updated(self, show):
        return self._is_being_processed(show, (ShowQueueActions.UPDATE,))

    def is_being_refreshed(self, show):
        return self._is_being_processed(show, (ShowQueueActions.REFRESH,))

    def is_being_renamed(self, show):
        return self._is_being_processed(show, (ShowQueueActions.RENAME,))

    def is_being_subtitled(self, show):
        return self._is_being_processed(show, (ShowQueueActions.SUBTITLE,))

    def is_being_removed(self, show):
        return self._is_being_processed(show, (ShowQueueActions.REMOVE,))

    def _get_loading_show_list(self):
        return [x for x in self.queue + [self.currentItem] if x is not None and x.isLoading]

    def get_queue_action_message(self, show):
        return self.get_queue_action(show)[1]

    def get_queue_action(self, show):
        for action, message in self.mappings.items():
            if self._is_being_processed(show, (action,)):
                return action, message

        for action, message in self.queue_mappings.items():
            if self._is_in_queue(show, (action,)):
                return action, message

        return None, None

    loading_show_list = property(_get_loading_show_list)

    def update_show(self, show, season=None):

        if self.is_being_added(show):
            raise CantUpdateShowException(
                u"{show_name} is still being added, wait until it is finished before you update."
                .format(show_name=show.name))

        if self.is_being_updated(show):
            raise CantUpdateShowException(
                u"{show_name} is already being updated by Post-processor or manually started, "
                u"can't update again until it's done."
                .format(show_name=show.name))

        if self.is_in_update_queue(show):
            raise CantUpdateShowException(
                u"{show_name} is in process of being updated by Post-processor or manually started, "
                u"can't update again until it's done."
                .format(show_name=show.name))

        queue_item_update_show = QueueItemUpdate(show) if season is None else QueueItemSeasonUpdate(show, season)

        self.add_item(queue_item_update_show)

        return queue_item_update_show

    def refresh_show(self, show, force=False):

        if self.is_being_refreshed(show) and not force:
            raise CantRefreshShowException("This show is already being refreshed, not refreshing again.")

        if (self.is_being_updated(show) or self.is_in_update_queue(show)) and not force:
            log.debug(
                u"A refresh was attempted but there is already an update"
                u" queued or in progress. Since updates do a refresh at the"
                u" end anyway I'm skipping this request."
            )
            return

        queueItemObj = QueueItemRefresh(show, force=force)

        log.debug(
            u"{id}: Queueing show refresh for {show}".format(
                id=show.series_id, show=show.name
            )
        )

        self.add_item(queueItemObj)

        return queueItemObj

    def rename_show_episodes(self, show):

        queueItemObj = QueueItemRename(show)

        self.add_item(queueItemObj)

        return queueItemObj

    def download_subtitles(self, show):

        queueItemObj = QueueItemSubtitle(show)

        self.add_item(queueItemObj)

        return queueItemObj

    def add_show(self, indexer, indexer_id, showDir, default_status=None, quality=None, flatten_folders=None,
                 lang=None, subtitles=None, anime=None, scene=None, paused=None, blacklist=None, whitelist=None,
                 default_status_after=None, root_dir=None):

        if lang is None:
            lang = app.INDEXER_DEFAULT_LANGUAGE

        queueItemObj = QueueItemAdd(indexer, indexer_id, showDir, default_status, quality, flatten_folders, lang,
                                    subtitles, anime, scene, paused, blacklist, whitelist, default_status_after,
                                    root_dir)

        self.add_item(queueItemObj)

        return queueItemObj

    def remove_show(self, show, full=False):
        if show is None:
            raise CantRemoveShowException(u'Failed removing show: Show does not exist')

        if not hasattr(show, u'indexerid'):
            raise CantRemoveShowException(u'Failed removing show: Show does not have an indexer id')

        if self.is_being_removed(show):
            raise CantRemoveShowException(u'[{!s}]: Show is already being removed'.format(show.series_id))

        if self.is_in_remove_queue(show):
            raise CantRemoveShowException(u'[{!s}]: Show is already queued to be removed'.format(show.series_id))

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

    def is_in_queue(self):
        return self in app.show_queue_scheduler.action.queue + [
            app.show_queue_scheduler.action.currentItem]  # @UndefinedVariable

    def _get_name(self):
        return str(self.show.series_id)

    def _is_loading(self):
        return False

    show_name = property(_get_name)

    is_loading = property(_is_loading)


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

    def _get_name(self):
        """
        Returns the show name if there is a show object created, if not returns
        the dir that the show is being added to.
        """
        if self.show is None:
            return self.showDir
        return self.show.name

    show_name = property(_get_name)

    def _is_loading(self):
        """
        Returns True if we've gotten far enough to have a show object, or False
        if we still only know the folder name.
        """
        if self.show is None:
            return True
        return False

    is_loading = property(_is_loading)

    def run(self):

        ShowQueueItem.run(self)

        if self.showDir:
            log.info(u'Starting to add series by directory: {0}'.format(self.showDir))
        else:
            log.info(u'Starting to add series by indexer id {0}'.format(self.indexer_id))

        # make sure the Indexer IDs are valid
        try:
            l_indexer_api_params = indexerApi(self.indexer).api_params.copy()
            if self.lang:
                l_indexer_api_params['language'] = self.lang

            log.info(u"" + str(indexerApi(self.indexer).name) + ": " + repr(l_indexer_api_params))

            indexer_api = indexerApi(self.indexer).indexer(**l_indexer_api_params)
            s = indexer_api[self.indexer_id]

            # Let's try to create the show Dir if it's not provided. This way we force the show dir
            # to build build using the Indexers provided series name
            if not self.showDir and self.root_dir:
                show_name = get_showname_from_indexer(self.indexer, self.indexer_id, self.lang)
                if show_name:
                    self.showDir = os.path.join(self.root_dir, sanitize_filename(show_name))
                    dir_exists = make_dir(self.showDir)
                    if not dir_exists:
                        log.info(u"Unable to create the folder {0}, can't add the show".format(self.showDir))
                        return

                    chmod_as_parent(self.showDir)
                else:
                    log.info(u"Unable to get a show {0}, can't add the show".format(self.showDir))
                    return

            # this usually only happens if they have an NFO in their show dir which gave us a Indexer ID that
            # has no proper english version of the show
            if getattr(s, 'seriesname', None) is None:
                log.error(
                    u"Show in {0} has no name on {1}, probably searched with"
                    u" the wrong language.".format(
                        self.showDir, indexerApi(self.indexer).name
                    )
                )
                ui.notifications.error('Unable to add show',
                                       'Show in {0} has no name on {1}, probably the wrong language. \
                                       Delete .nfo and manually add the correct language.'
                                       .format(self.showDir, indexerApi(self.indexer).name))
                self._finish_early()
                return
            # if the show has no episodes/seasons
            if not s:
                log.info(
                    u"Show " + str(s['seriesname']) + u" is on " +
                    str(indexerApi(self.indexer).name) +
                    u" but contains no season/episode data."
                )
                ui.notifications.error("Unable to add show",
                                       "Show {0} is on {1} but contains no season/episode data.".
                                       format(s['seriesname'], indexerApi(self.indexer).name))
                self._finish_early()

                return

            # Check if we can already find this show in our current showList.
            try:
                check_existing_shows(s, self.indexer)
            except IndexerShowAllreadyInLibrary as e:
                log.warning(
                    u"Could not add the show %s, as it already is in your"
                    u" library. Error: %s" % (s['seriesname'], e.message)
                )
                ui.notifications.error(
                    'Unable to add show',
                    'reason: {0}' .format(e.message)
                )
                self._finish_early()

                # Clean up leftover if the newly created directory is empty.
                delete_empty_folders(self.showDir)
                return

        # TODO: Add more specific indexer exceptions, that should provide the user with some accurate feedback.
        except IndexerShowIncomplete as e:
            log.warning(
                u"%s Error while loading information from indexer %s."
                u" Error: %s" % (
                    self.indexer_id,
                    indexerApi(self.indexer).name,
                    e.message
                )
            )
            ui.notifications.error(
                "Unable to add show",
                "Unable to look up the show in {0} on {1} using ID {2} "
                "Reason: {3}"
                .format(self.showDir, indexerApi(self.indexer).name, self.indexer_id, e.message)
            )
            self._finish_early()
            return
        except IndexerShowNotFoundInLanguage as e:
            log.warning(
                u'{id}: Data retrieved from {indexer} was incomplete.'
                u' The indexer does not provide show information in the'
                u' searched language {language}.'
                u' Aborting: {error_msg}'.format(
                    id=self.indexer_id, indexer=indexerApi(self.indexer).name,
                    language=e.language, error_msg=e.message
                )
            )
            ui.notifications.error('Error adding show!',
                                   'Unable to add show {indexer_id} on {indexer} with this language: {language}'.
                                   format(indexer_id=self.indexer_id,
                                          indexer=indexerApi(self.indexer).name,
                                          language=e.language))
            self._finish_early()
            return
        except Exception as e:
            log.error(
                u"%s Error while loading information from indexer %s."
                u" Error: %r" % (
                    self.indexer_id,
                    indexerApi(self.indexer).name,
                    e.message
                )
            )
            ui.notifications.error(
                "Unable to add show",
                "Unable to look up the show in {0} on {1} using ID {2}, not using the NFO. "
                "Delete .nfo and try adding manually again.".
                format(self.showDir, indexerApi(self.indexer).name, self.indexer_id)
            )
            self._finish_early()
            return

        try:
            newShow = Series(self.indexer, self.indexer_id, self.lang)
            newShow.load_from_indexer(indexer_api)

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
            log.info(
                u"Setting all previously aired episodes to the specified"
                u" status: {status}".format(
                    status=statusStrings[self.default_status]
                )
            )
            self.show.default_ep_status = self.default_status

            if self.show.anime:
                self.show.release_groups = BlackAndWhiteList(self.show)
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
            log.error(u"Unable to add show due to an error with " + indexerApi(self.indexer).name + ": " + e.message)
            if self.show:
                ui.notifications.error(
                    "Unable to add " + str(self.show.name) + " due to an error with " + indexerApi(
                        self.indexer).name + "")
            else:
                ui.notifications.error(
                    "Unable to add show due to an error with " + indexerApi(self.indexer).name + "")
            self._finish_early()
            return

        except MultipleShowObjectsException:
            log.warning(u"The show in " + self.showDir + " is already in your show list, skipping")
            ui.notifications.error('Show skipped', "The show in " + self.showDir + " is already in your show list")
            self._finish_early()
            return

        except Exception as e:
            log.error(u"Error trying to add show: " + e.message)
            log.debug(traceback.format_exc())
            self._finish_early()
            raise

        log.debug(u"Retrieving show info from IMDb")
        try:
            self.show.load_imdb_info()
        except ImdbAPIError as e:
            log.info(u"Something wrong on IMDb api: " + e.message)
        except Exception as e:
            log.error(u"Error loading IMDb info: " + e.message)

        try:
            self.show.save_to_db()
        except Exception as e:
            log.error(u"Error saving the show to the database: " + e.message)
            log.debug(traceback.format_exc())
            self._finish_early()
            raise

        # add it to the show list
        app.showList.append(self.show)

        try:
            self.show.load_episodes_from_indexer(tvapi=indexer_api)
        except Exception as e:
            log.error(u"Error with " + indexerApi(self.show.indexer).name + ", not creating episode list: " + e.message)
            log.debug(traceback.format_exc())

        # update internal name cache
        name_cache.build_name_cache(self.show)

        try:
            self.show.load_episodes_from_dir()
        except Exception as e:
            log.error(u"Error searching dir for episodes: " + e.message)
            log.debug(traceback.format_exc())

        # if they set default ep status to WANTED then run the backlog to search for episodes
        # FIXME: This needs to be a backlog queue item!!!
        if self.show.default_ep_status == WANTED:
            log.info(u"Launching backlog for this show since its episodes are WANTED")
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
                log.info(u"update watchlist")
                notifiers.trakt_notifier.update_watchlist(show_obj=self.show)

        # Load XEM data to DB for show
        scene_numbering.xem_refresh(self.show, force=True)

        # check if show has XEM mapping so we can determine if searches
        # should go by scene numbering or indexer numbering.
        if not self.scene and scene_numbering.get_xem_numbering_for_show(self.show):
            self.show.scene = 1

        # After initial add, set to default_status_after.
        self.show.default_ep_status = self.default_status_after

        self.finish()

    def _finish_early(self):
        if self.show is not None:
            app.show_queue_scheduler.action.remove_show(self.show)

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

        log.info(u"{id}: Performing refresh on {show}".format(id=self.show.series_id, show=self.show.name))

        try:
            self.show.refresh_dir()
            if self.force:
                self.show.update_metadata()
            self.show.write_metadata()
            self.show.populate_cache()

            # Load XEM data to DB for show
            scene_numbering.xem_refresh(self.show)
        except Exception as e:
            log.error(
                u"{id}: Error while refreshing show {show}."
                u" Error: {error_msg}".format(
                    id=self.show.series_id, show=self.show.name,
                    error_msg=e.message
                )
            )

        self.finish()


class QueueItemRename(ShowQueueItem):
    def __init__(self, show=None):
        ShowQueueItem.__init__(self, ShowQueueActions.RENAME, show)

    def run(self):

        ShowQueueItem.run(self)

        log.info(u"Performing rename on " + self.show.name)

        try:
            self.show.location
        except ShowDirectoryNotFoundException:
            log.warning(u"Can't perform rename on " + self.show.name + " when the show dir is missing.")
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
            u'{id}: Downloading subtitles for {show}'.format(
                id=self.show.series_id, show=self.show.name
            )
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
            u'{id}: Beginning update of {show}'.format(
                id=self.show.series_id, show=self.show.name
            )
        )
        log.debug(
            u'{id}: Retrieving show info from {indexer}'.format(
                id=self.show.series_id,
                indexer=indexerApi(self.show.indexer).name
            )
        )
        try:
            # Let's make sure we refresh the indexer_api object attached to the show object.
            self.show.create_indexer()
            self.show.load_from_indexer()
        except IndexerError as e:
            log.warning(
                u'{id}: Unable to contact {indexer}.'
                u' Aborting: {error_msg}'.format(
                    id=self.show.series_id,
                    indexer=indexerApi(self.show.indexer).name,
                    error_msg=e.message
                )
            )
            return
        except IndexerAttributeNotFound as e:
            log.warning(
                u'{id}: Data retrieved from {indexer} was incomplete.'
                u' Aborting: {error_msg}'.format(
                    id=self.show.series_id,
                    indexer=indexerApi(self.show.indexer).name,
                    error_msg=e.message
                )
            )
            return
        except IndexerShowNotFoundInLanguage as e:
            log.warning(
                u'{id}: Data retrieved from {indexer} was incomplete.'
                u' The indexer does not provide show information in the'
                u' searched language {language}. Aborting: {error_msg}'.format(
                    id=self.show.series_id,
                    indexer=indexerApi(self.show.indexer).name,
                    language=e.language, error_msg=e.message
                )
            )
            ui.notifications.error('Error changing language show!',
                                   'Unable to change language for show {show_name} on {indexer} to language: {language}'.
                                   format(show_name=self.show.name,
                                          indexer=indexerApi(self.show.indexer).name,
                                          language=e.language))
            return

        log.debug(u'{id}: Retrieving show info from IMDb'.format(id=self.show.series_id))
        try:
            self.show.load_imdb_info()
        except ImdbAPIError as e:
            log.info(
                u'{id}: Something wrong on IMDb api: {error_msg}'.format(
                    id=self.show.series_id, error_msg=e.message
                )
            )
        except Exception as e:
            log.warning(
                u'{id}: Error loading IMDb info: {error_msg}'.format(
                    id=self.show.series_id, error_msg=e.message
                )
            )

        # have to save show before reading episodes from db
        try:
            log.debug(
                u'{id}: Saving new IMDb show info to database'.format(
                    id=self.show.series_id
                )
            )
            self.show.save_to_db()
        except Exception as e:
            log.warning(
                u"{id}: Error saving new IMDb show info to database:"
                u" {error_msg}".format(
                    id=self.show.series_id,
                    error_msg=e.message
                )
            )
            log.error(traceback.format_exc())

        # get episode list from DB
        try:
            episodes_from_db = self.show.load_episodes_from_db()
        except IndexerException as e:
            log.warning(
                u'{id}: Unable to contact {indexer}. Aborting:'
                u' {error_msg}'.format(
                    id=self.show.series_id,
                    indexer=indexerApi(self.show.indexer).name,
                    error_msg=e.message
                )
            )
            return

        # get episode list from the indexer
        try:
            episodes_from_indexer = self.show.load_episodes_from_indexer()
        except IndexerException as e:
            log.warning(
                u'{id}: Unable to get info from {indexer}. The show info will'
                u' not be refreshed. Error: {error_msg}'.format(
                    id=self.show.series_id,
                    indexer=indexerApi(self.show.indexer).name,
                    error_msg=e.message
                )
            )
            episodes_from_indexer = None

        if episodes_from_indexer is None:
            log.warning(
                u'{id}: No data returned from {indexer} during full show'
                u' update. Unable to update this show'.format(
                    id=self.show.series_id,
                    indexer=indexerApi(self.show.indexer).name
                )
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
                        u'{id}: Permanently deleting episode {show} {ep} from'
                        u' the database'.format(
                            id=self.show.series_id, show=self.show.name,
                            ep=episode_num(cur_season, cur_episode)
                        )
                    )
                    # Create the ep object only because Im going to delete it
                    ep_obj = self.show.get_episode(cur_season, cur_episode)
                    try:
                        ep_obj.delete_episode()
                    except EpisodeDeletedException:
                        log.debug(
                            u'{id}: Episode {show} {ep} successfully deleted'
                            u' from the database'.format(
                                id=self.show.series_id,
                                show=self.show.name,
                                ep=episode_num(cur_season, cur_episode)
                            )
                        )

        # Save only after all changes were applied
        try:
            log.debug(
                u'{id}: Saving all updated show info to'
                u' database'.format(id=self.show.series_id)
            )
            self.show.save_to_db()
        except Exception as e:
            log.warning(
                u'{id}: Error saving all updated show info to database:'
                u' {error_msg}'.format(
                    id=self.show.series_id, error_msg=e.message
                )
            )
            log.error(traceback.format_exc())

        # Replace the images in cache
        log.info(
            u'{id}: Replacing images for show {show}'.format(
                id=self.show.series_id, show=self.show.name
            )
        )
        replace_images(self.show)

        log.debug(
            u'{id}: Finished update of {show}'.format(
                id=self.show.series_id, show=self.show.name
            )
        )

        # Refresh show needs to be forced since current execution locks the queue
        app.show_queue_scheduler.action.refresh_show(self.show, True)
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
            u'{id}: Beginning update of {show}{season}'.format(
                id=self.show.series_id,
                show=self.show.name,
                season=u' with season(s) [{0}]'.format(
                    u','.join(str(s) for s in self.seasons)
                    if self.seasons else u''
                )
            )
        )

        log.debug(
            u'{id}: Retrieving show info from {indexer}'.format(
                id=self.show.series_id,
                indexer=indexerApi(self.show.indexer).name
            )
        )
        try:
            # Let's make sure we refresh the indexer_api object attached to the show object.
            self.show.create_indexer()
            self.show.load_from_indexer()
        except IndexerError as e:
            log.warning(
                u'{id}: Unable to contact {indexer}. Aborting:'
                u' {error_msg}'.format(
                    id=self.show.series_id,
                    indexer=indexerApi(self.show.indexer).name,
                    error_msg=e.message
                )
            )
            return
        except IndexerAttributeNotFound as e:
            log.warning(
                u'{id}: Data retrieved from {indexer} was incomplete.'
                u' Aborting: {error_msg}'.format(
                    id=self.show.series_id,
                    indexer=indexerApi(self.show.indexer).name,
                    error_msg=e.message
                )
            )
            return

        log.debug(u'{id}: Retrieving show info from IMDb'.format(id=self.show.series_id))
        try:
            self.show.load_imdb_info()
        except ImdbAPIError as e:
            log.info(u'{id}: Something wrong on IMDb api: {error_msg}'.format(id=self.show.series_id, error_msg=e.message))
        except Exception as e:
            log.warning(u'{id}: Error loading IMDb info: {error_msg}'.format(id=self.show.series_id, error_msg=e.message))

        # have to save show before reading episodes from db
        try:
            log.debug(u'{id}: Saving new IMDb show info to database'.format(id=self.show.series_id))
            self.show.save_to_db()
        except Exception as e:
            log.warning(
                u"{id}: Error saving new IMDb show info to database:"
                u" {error_msg}".format(
                    id=self.show.series_id, error_msg=e.message
                )
            )
            log.error(traceback.format_exc())

        # get episode list from DB
        try:
            episodes_from_db = self.show.load_episodes_from_db(self.seasons)
        except IndexerException as e:
            log.warning(
                u'{id}: Unable to contact {indexer}. Aborting:'
                u' {error_msg}'.format(
                    id=self.show.series_id,
                    indexer=indexerApi(self.show.indexer).name,
                    error_msg=e.message
                )
            )
            return

        # get episode list from the indexer
        try:
            episodes_from_indexer = self.show.load_episodes_from_indexer(self.seasons)
        except IndexerException as e:
            log.warning(
                u'{id}: Unable to get info from {indexer}. The show info will'
                u' not be refreshed. Error: {error_msg}'.format(
                    id=self.show.series_id,
                    indexer=indexerApi(self.show.indexer).name,
                    error_msg=e.message
                )
            )
            episodes_from_indexer = None

        if episodes_from_indexer is None:
            log.warning(
                u'{id}: No data returned from {indexer} during season show'
                u' update. Unable to update this show'.format(
                    id=self.show.series_id,
                    indexer=indexerApi(self.show.indexer).name
                )
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
                        u'{id}: Permanently deleting episode {show} {ep}'
                        u' from the database'.format(
                            id=self.show.series_id, show=self.show.name,
                            ep=episode_num(cur_season, cur_episode)
                        )
                    )
                    # Create the ep object only because Im going to delete it
                    ep_obj = self.show.get_episode(cur_season, cur_episode)
                    try:
                        ep_obj.delete_episode()
                    except EpisodeDeletedException:
                        log.debug(
                            u'{id}: Episode {show} {ep} successfully deleted'
                            u' from the database'.format(
                                id=self.show.series_id, show=self.show.name,
                                ep=episode_num(cur_season, cur_episode)
                            )
                        )

        # Save only after all changes were applied
        try:
            log.debug(u'{id}: Saving all updated show info to database'.format(id=self.show.series_id))
            self.show.save_to_db()
        except Exception as e:
            log.warning(
                u'{id}: Error saving all updated show info to database:'
                u' {error_msg}'.format(
                    id=self.show.series_id, error_msg=e.message
                )
            )
            log.error(traceback.format_exc())

        log.info(
            u'{id}: Finished update of {show}'.format(
                id=self.show.series_id, show=self.show.name
            )
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

        log.info(u'{id}: Removing {show}'.format(id=self.show.series_id, show=self.show.name))

        # Need to first remove the episodes from the Trakt collection, because we need the list of
        # Episodes from the db to know which eps to remove.
        if app.USE_TRAKT:
            try:
                app.trakt_checker_scheduler.action.remove_show_trakt_library(self.show)
            except TraktException as e:
                log.warning(
                    u'{id}: Unable to delete show {show} from Trakt. Please'
                    u' remove manually otherwise it will be added again.'
                    u' Error: {error_msg}'.format(
                        id=self.show.series_id,
                        show=self.show.name,
                        error_msg=e.message
                    )
                )

        self.show.delete_show(full=self.full)

        self.finish()
