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


import threading
import time
import traceback

from .. import app, common, failed_history, generic_queue, history, logger, providers, ui
from ..search.core import (
    search_for_needed_episodes,
    search_providers,
    snatch_episode,
)

search_queue_lock = threading.Lock()

BACKLOG_SEARCH = 10
DAILY_SEARCH = 20
FAILED_SEARCH = 30
FORCED_SEARCH = 40
MANUAL_SEARCH = 50

FORCED_SEARCH_HISTORY = []
FORCED_SEARCH_HISTORY_SIZE = 100


class SearchQueue(generic_queue.GenericQueue):
    def __init__(self):
        generic_queue.GenericQueue.__init__(self)
        self.queue_name = "SEARCHQUEUE"
        self.force = False

    def is_in_queue(self, show, segment):
        for cur_item in self.queue:
            if isinstance(cur_item, (BacklogQueueItem, FailedQueueItem,
                                     ForcedSearchQueueItem, ManualSnatchQueueItem)) \
                    and cur_item.show == show and cur_item.segment == segment:
                return True
        return False

    def pause_backlog(self):
        self.min_priority = generic_queue.QueuePriorities.HIGH

    def unpause_backlog(self):
        self.min_priority = 0

    def is_backlog_paused(self):
        # backlog priorities are NORMAL, this should be done properly somewhere
        return self.min_priority >= generic_queue.QueuePriorities.NORMAL

    def is_backlog_in_progress(self):
        for cur_item in self.queue + [self.currentItem]:
            if isinstance(cur_item, BacklogQueueItem):
                return True
        return False

    def is_dailysearch_in_progress(self):
        for cur_item in self.queue + [self.currentItem]:
            if isinstance(cur_item, DailySearchQueueItem):
                return True
        return False

    def queue_length(self):
        length = {'backlog': 0, 'daily': 0}
        for cur_item in self.queue:
            if isinstance(cur_item, DailySearchQueueItem):
                length['daily'] += 1
            elif isinstance(cur_item, BacklogQueueItem):
                length['backlog'] += 1
        return length

    def add_item(self, item):
        if isinstance(item, DailySearchQueueItem):
            # daily searches
            generic_queue.GenericQueue.add_item(self, item)
        elif isinstance(item, (BacklogQueueItem, FailedQueueItem,
                               ManualSnatchQueueItem, ForcedSearchQueueItem)) \
                and not self.is_in_queue(item.show, item.segment):
            generic_queue.GenericQueue.add_item(self, item)
        else:
            logger.log(u"Not adding item, it's already in the queue", logger.DEBUG)

    def force_daily(self):
        if not self.is_dailysearch_in_progress and not self.currentItem.amActive:
            self.force = True
            return True
        return False


class ForcedSearchQueue(generic_queue.GenericQueue):
    """Search Queueu used for Forced Search, Failed Search and """
    def __init__(self):
        """Initialize ForcedSearch Queue"""
        generic_queue.GenericQueue.__init__(self)
        self.queue_name = "SEARCHQUEUE"

    def is_in_queue(self, show, segment):
        """
        Verify if the show and segment (episode or number of episodes) are scheduled.
        """
        for cur_item in self.queue:
            if cur_item.show == show and cur_item.segment == segment:
                return True
        return False

    def is_ep_in_queue(self, segment):
        """
        Verify if the show and segment (episode or number of episodes) are scheduled in a
        ForcedSearchQueueItem or FailedQueueItem.
        """
        for cur_item in self.queue:
            if isinstance(cur_item, (ForcedSearchQueueItem, FailedQueueItem)) and cur_item.segment == segment:
                return True
        return False

    def is_show_in_queue(self, show):
        """Verify if the show is queued in this queue as a ForcedSearchQueueItem or FailedQueueItem."""
        for cur_item in self.queue:
            if isinstance(cur_item, (ForcedSearchQueueItem, FailedQueueItem)) and cur_item.show.indexerid == show:
                return True
        return False

    def get_all_ep_from_queue(self, show):
        """
        Get QueueItems from the queue if the queue item is scheduled to search for the passed Show.
        @param show: Show indexer_id

        @return: A list of ForcedSearchQueueItem or FailedQueueItem items
        @todo: In future a show object should be passed instead of the indexer_id, as we might migrate
        to a system with multiple indexer_id's for one added show.
        """
        ep_obj_list = []
        for cur_item in self.queue:
            if isinstance(cur_item, (ForcedSearchQueueItem, FailedQueueItem)) and str(cur_item.show.indexerid) == show:
                ep_obj_list.append(cur_item)
        return ep_obj_list

    def is_backlog_paused(self):
        """
        Verify if the ForcedSearchQueue's min_priority has been changed. This indicates that the
        queue has been paused.
        # backlog priorities are NORMAL, this should be done properly somewhere
        """
        return self.min_priority >= generic_queue.QueuePriorities.NORMAL

    def is_forced_search_in_progress(self):
        """Tests of a forced search is currently running, it doesn't check what's in queue"""
        if isinstance(self.currentItem, (ForcedSearchQueueItem, FailedQueueItem)):
            return True
        return False

    def queue_length(self):
        length = {'forced_search': 0, 'manual_search': 0, 'failed': 0}
        for cur_item in self.queue:
            if isinstance(cur_item, FailedQueueItem):
                length['failed'] += 1
            elif isinstance(cur_item, ForcedSearchQueueItem) and not cur_item.manual_search:
                length['forced_search'] += 1
            elif isinstance(cur_item, ForcedSearchQueueItem) and cur_item.manual_search:
                length['manual_search'] += 1
        return length

    def add_item(self, item):
        """Add a new ForcedSearchQueueItem or FailedQueueItem to the ForcedSearchQueue"""
        if isinstance(item, (ForcedSearchQueueItem, FailedQueueItem)) and not self.is_ep_in_queue(item.segment):
            # manual, snatch and failed searches
            generic_queue.GenericQueue.add_item(self, item)
        else:
            logger.log(u"Not adding item, it's already in the queue", logger.DEBUG)


class SnatchQueue(generic_queue.GenericQueue):
    """Queue for queuing ManualSnatchQueueItem objects (snatch jobs)"""
    def __init__(self):
        """Initialize the SnatchQueue object"""
        generic_queue.GenericQueue.__init__(self)
        self.queue_name = "SNATCHQUEUE"

    def is_in_queue(self, show, segment):
        """Check if the passed show and segment (episode of list of episodes) is in the queue
        @param show: show object
        @param segment: list of episode objects

        @return: True or False
        """
        for cur_item in self.queue:
            if cur_item.show == show and cur_item.segment == segment:
                return True
        return False

    def is_ep_in_queue(self, segment):
        """Check if the passed segment (episode of list of episodes) is in the queue
        @param segment: list of episode objects

        @return: True or False
        """
        for cur_item in self.queue:
            if cur_item.segment == segment:
                return True
        return False

    def queue_length(self):
        """Get the length of the current queue
        @return: length of queue
        """
        return {'manual_snatch': len(self.queue)}

    def add_item(self, item):
        """Add a ManualSnatchQueueItem queue item
        @param item: ManualSnatchQueueItem gueue object
        """
        if not self.is_in_queue(item.show, item.segment):
            # backlog searches
            generic_queue.GenericQueue.add_item(self, item)
        else:
            logger.log(u"Not adding item, it's already in the queue", logger.DEBUG)


class DailySearchQueueItem(generic_queue.QueueItem):
    def __init__(self):
        generic_queue.QueueItem.__init__(self, u'Daily Search', DAILY_SEARCH)

        self.success = None
        self.started = None

    def run(self):
        """
        Run daily search thread
        """
        generic_queue.QueueItem.run(self)
        self.started = True

        try:
            logger.log(u"Beginning daily search for new episodes")
            found_results = search_for_needed_episodes()

            if not found_results:
                logger.log(u"No needed episodes found")
            else:
                for result in found_results:
                    # just use the first result for now
                    if result.seeders not in (-1, None) and result.leechers not in (-1, None):
                        logger.log(u"Downloading {0} with {1} seeders and {2} leechers from {3}".format(result.name,
                                   result.seeders, result.leechers, result.provider.name))
                    else:
                        logger.log(u"Downloading {0} from {1}".format(result.name, result.provider.name))
                    self.success = snatch_episode(result)

                    # give the CPU a break
                    time.sleep(common.cpu_presets[app.CPU_PRESET])

        except Exception:
            self.success = False
            logger.log(traceback.format_exc(), logger.DEBUG)

        if self.success is None:
            self.success = False

        self.finish()


class ForcedSearchQueueItem(generic_queue.QueueItem):
    def __init__(self, show, segment, down_cur_quality=False, manual_search=False, manual_search_type='episode'):
        """A Queueitem used to queue Forced Searches and Manual Searches
        @param show: A show object
        @param segment: A list of episode objects. Needs to be passed as list!
        @param down_cur_quality: Not sure what it's used for. Maybe legacy.
        @param manual_search: Passed as True (bool) when the search should be performed without automatially snatching a result
        @param manual_search_type: Used to switch between episode and season search. Options are 'episode' or 'season'.

        @return: The run() methods searches and snatches the episode(s) if possible.
        Or only searches and saves results to cache tables.
        """
        generic_queue.QueueItem.__init__(self, u'Forced Search', FORCED_SEARCH)
        self.priority = generic_queue.QueuePriorities.HIGH
        # SEARCHQUEUE-MANUAL-12345
        # SEARCHQUEUE-FORCED-12345
        self.name = '{0}-{1}'.format(('FORCED','MANUAL')[bool(manual_search)], show.indexerid)

        self.success = None
        self.started = None
        self.results = None

        self.show = show
        self.segment = segment
        self.down_cur_quality = down_cur_quality
        self.manual_search = manual_search
        self.manual_search_type = manual_search_type

    def run(self):
        """
        Run forced search thread
        """
        generic_queue.QueueItem.run(self)
        self.started = True

        try:
            logger.log(u"Beginning {0} {1}search for: [{2}]".
                       format(('forced', 'manual')[bool(self.manual_search)],
                              ('', 'season pack ')[bool(self.manual_search_type == 'season')], self.segment[0].pretty_name()))

            search_result = search_providers(self.show, self.segment, True, self.down_cur_quality,
                                             self.manual_search, self.manual_search_type)

            if not self.manual_search and search_result:
                # just use the first result for now
                if search_result[0].seeders not in (-1, None) and search_result[0].leechers not in (-1, None):
                    logger.log(u"Downloading {0} with {1} seeders and {2} leechers from {3}".
                               format(search_result[0].name,
                                      search_result[0].seeders, search_result[0].leechers, search_result[0].provider.name))
                else:
                    logger.log(u"Downloading {0} from {1}".format(search_result[0].name, search_result[0].provider.name))
                self.success = snatch_episode(search_result[0])

                # give the CPU a break
                time.sleep(common.cpu_presets[app.CPU_PRESET])
            elif self.manual_search and search_result:
                self.results = search_result
                self.success = True
                if self.manual_search_type == 'season':
                    ui.notifications.message("We have found season packs for {0}".format(self.show.name),
                                             "These should become visible in the manual select page.")
                else:
                    ui.notifications.message("We have found results for {0}".format(self.segment[0].pretty_name()),
                                             "These should become visible in the manual select page.")
            else:
                ui.notifications.message('No results were found')
                logger.log(u"Unable to find {0} {1}results for: [{2}]".
                           format(('forced', 'manual')[bool(self.manual_search)],
                                  ('', 'season pack ')[bool(self.manual_search_type == 'season')],
                                  self.segment[0].pretty_name()))

        except Exception:
            self.success = False
            logger.log(traceback.format_exc(), logger.DEBUG)

        # ## Keep a list with the 100 last executed searches
        fifo(FORCED_SEARCH_HISTORY, self, FORCED_SEARCH_HISTORY_SIZE)

        if self.success is None:
            self.success = False

        self.finish()


class ManualSnatchQueueItem(generic_queue.QueueItem):
    """
    A queue item that can be used to queue the snatch of a search result.
    Currently used for the snatchSelection feature.

    @param show: A show object
    @param segment: A list of episode objects
    @param provider: The provider id. For example nyaatorrent and not NyaaTorrent. Or usernet_crawler and not Usenet-Crawler
    @param cached_result: An sql result of the searched result retrieved from the provider cache table.

    @return: The run() methods snatches the episode(s) if possible.
    """
    def __init__(self, show, segment, provider, cached_result):
        generic_queue.QueueItem.__init__(self, u'Manual Search', MANUAL_SEARCH)
        self.priority = generic_queue.QueuePriorities.HIGH
        self.name = 'MANUALSNATCH-' + str(show.indexerid)
        self.success = None
        self.started = None
        self.results = None
        self.provider = provider
        self.segment = segment
        self.show = show
        self.cached_result = cached_result

    def run(self):
        """
        Run manual snatch job
        """
        generic_queue.QueueItem.run(self)
        self.started = True

        search_result = providers.get_provider_class(self.provider).get_result(self.segment)
        search_result.show = self.show
        search_result.url = self.cached_result['url']
        search_result.quality = int(self.cached_result['quality'])
        search_result.name = self.cached_result['name']
        search_result.size = int(self.cached_result['size'])
        search_result.seeders = int(self.cached_result['seeders'])
        search_result.leechers = int(self.cached_result['leechers'])
        search_result.release_group = self.cached_result['release_group']
        search_result.version = int(self.cached_result['version'])
        search_result.proper_tags = self.cached_result['proper_tags'].split('|') if self.cached_result['proper_tags'] else u''
        search_result.manually_searched = True

        try:
            logger.log(u"Beginning to manual snatch release: {0}".format(search_result.name))

            if search_result:
                if search_result.seeders not in (-1, None) and search_result.leechers not in (-1, None):
                    logger.log(u"Downloading {0} with {1} seeders and {2} leechers from {3}".
                               format(search_result.name,
                                      search_result.seeders, search_result.leechers, search_result.provider.name))
                else:
                    logger.log(u"Downloading {0} from {1}".format(search_result.name, search_result.provider.name))
                self.success = snatch_episode(search_result)
            else:
                logger.log(u"Unable to snatch release: {0}".format(search_result.name))

            # give the CPU a break
            time.sleep(common.cpu_presets[app.CPU_PRESET])

        except Exception:
            self.success = False
            logger.log(traceback.format_exc(), logger.DEBUG)
            ui.notifications.message('Error while snatching selected result',
                                     "Couldn't snatch the result for <i>{0}</i>".format(search_result.name))

        if self.success is None:
            self.success = False

        self.finish()


class BacklogQueueItem(generic_queue.QueueItem):
    def __init__(self, show, segment):
        generic_queue.QueueItem.__init__(self, u'Backlog', BACKLOG_SEARCH)
        self.priority = generic_queue.QueuePriorities.LOW
        self.name = 'BACKLOG-' + str(show.indexerid)

        self.success = None
        self.started = None

        self.show = show
        self.segment = segment

    def run(self):
        """
        Run backlog search thread
        """
        generic_queue.QueueItem.run(self)
        self.started = True

        if not self.show.paused:
            try:
                logger.log(u"Beginning backlog search for: [" + self.show.name + "]")
                search_result = search_providers(self.show, self.segment)

                if search_result:
                    for result in search_result:
                        # just use the first result for now
                        if result.seeders not in (-1, None) and result.leechers not in (-1, None):
                            logger.log(u"Downloading {0} with {1} seeders and {2} leechers from {3}".
                                       format(result.name,
                                              result.seeders, result.leechers, result.provider.name))
                        else:
                            logger.log(u"Downloading {0} from {1}".format(result.name, result.provider.name))
                        self.success = snatch_episode(result)

                        # give the CPU a break
                        time.sleep(common.cpu_presets[app.CPU_PRESET])
                else:
                    logger.log(u"No needed episodes found during backlog search for: [" + self.show.name + "]")

            except Exception:
                self.success = False
                logger.log(traceback.format_exc(), logger.DEBUG)

        if self.success is None:
            self.success = False

        self.finish()


class FailedQueueItem(generic_queue.QueueItem):
    def __init__(self, show, segment, down_cur_quality=False):
        generic_queue.QueueItem.__init__(self, u'Retry', FAILED_SEARCH)
        self.priority = generic_queue.QueuePriorities.HIGH
        self.name = 'RETRY-' + str(show.indexerid)

        self.success = None
        self.started = None

        self.show = show
        self.segment = segment
        self.down_cur_quality = down_cur_quality

    def run(self):
        """
        Run failed thread
        """
        generic_queue.QueueItem.run(self)
        self.started = True

        try:
            for ep_obj in self.segment:

                logger.log(u"Marking episode as bad: [" + ep_obj.pretty_name() + "]")

                failed_history.mark_failed(ep_obj)

                (release, provider) = failed_history.find_release(ep_obj)
                if release:
                    failed_history.log_failed(release)
                    history.log_failed(ep_obj, release, provider)

                failed_history.revert_episode(ep_obj)
                logger.log(u"Beginning failed download search for: [" + ep_obj.pretty_name() + "]")

            # If it is wanted, self.down_cur_quality doesnt matter
            # if it isnt wanted, we need to make sure to not overwrite the existing ep that we reverted to!
            search_result = search_providers(self.show, self.segment, True)

            if search_result:
                for result in search_result:
                    # just use the first result for now
                    if result.seeders not in (-1, None) and result.leechers not in (-1, None):
                        logger.log(u"Downloading {0} with {1} seeders and {2} leechers from {3}".format(result.name,
                                   result.seeders, result.leechers, result.provider.name))
                    else:
                        logger.log(u"Downloading {0} from {1}".format(result.name, result.provider.name))
                    self.success = snatch_episode(result)

                    # give the CPU a break
                    time.sleep(common.cpu_presets[app.CPU_PRESET])
            else:
                logger.log(u"No needed episodes found during failed search for: [" + self.show.name + "]")

        except Exception:
            self.success = False
            logger.log(traceback.format_exc(), logger.DEBUG)

        # ## Keep a list with the 100 last executed searches
        fifo(FORCED_SEARCH_HISTORY, self, FORCED_SEARCH_HISTORY_SIZE)

        if self.success is None:
            self.success = False

        self.finish()


def fifo(myList, item, maxSize=100):
    if len(myList) >= maxSize:
        myList.pop(0)
    myList.append(item)
