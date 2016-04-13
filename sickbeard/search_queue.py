# coding=utf-8
# Author: Nic Wolfe <nic@wolfeden.ca>
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


import time
import traceback
import threading
import sickbeard
from sickbeard import common
from sickbeard import logger
from sickbeard import generic_queue
from sickbeard import search, failed_history, history
from sickbeard import ui
from sickbeard import providers

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

    def is_in_queue(self, show, segment):
        for cur_item in self.queue:
            if isinstance(cur_item, BacklogQueueItem) and cur_item.show == show and cur_item.segment == segment:
                return True
        return False

    def is_ep_in_queue(self, segment):
        for cur_item in self.queue:
            if isinstance(cur_item, (ForcedSearchQueueItem, FailedQueueItem, ManualSearchQueueItem)) and cur_item.segment == segment:
                return True
        return False

    def is_show_in_queue(self, show):
        for cur_item in self.queue:
            if isinstance(cur_item, (ForcedSearchQueueItem, FailedQueueItem)) and cur_item.show.indexerid == show:
                return True
        return False

    def get_all_ep_from_queue(self, show):
        ep_obj_list = []
        for cur_item in self.queue:
            if isinstance(cur_item, (ForcedSearchQueueItem, FailedQueueItem)) and str(cur_item.show.indexerid) == show:
                ep_obj_list.append(cur_item)
        return ep_obj_list

    def pause_backlog(self):
        self.min_priority = generic_queue.QueuePriorities.HIGH

    def unpause_backlog(self):
        self.min_priority = 0

    def is_backlog_paused(self):
        # backlog priorities are NORMAL, this should be done properly somewhere
        return self.min_priority >= generic_queue.QueuePriorities.NORMAL

    def stop_backlog(self):
        """Function to stop all running and queued backlog queue items"""
        if isinstance(self.currentItem, BacklogQueueItem):
            self.currentItem.force_stop[0] = True
        for queued_item in self.queue:
            if isinstance(queued_item, BacklogQueueItem):
                queued_item.force_stop[0] = True

    def is_manualsearch_in_progress(self):
        # Only referenced in webserve.py, only current running manualsearch or failedsearch is needed!!
        if isinstance(self.currentItem, (ForcedSearchQueueItem, FailedQueueItem)):
            return True
        return False

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
        length = {'backlog': 0, 'daily': 0, 'forced_search': 0, 'manual_search': 0, 'failed': 0}
        for cur_item in self.queue:
            if isinstance(cur_item, DailySearchQueueItem):
                length['daily'] += 1
            elif isinstance(cur_item, BacklogQueueItem):
                length['backlog'] += 1
            elif isinstance(cur_item, ForcedSearchQueueItem):
                length['forced_search'] += 1
            elif isinstance(cur_item, FailedQueueItem):
                length['failed'] += 1
            elif isinstance(cur_item, ManualSearchQueueItem):
                length['manual_search'] += 1
        return length

    def add_item(self, item):
        if isinstance(item, DailySearchQueueItem):
            # daily searches
            generic_queue.GenericQueue.add_item(self, item)
        elif isinstance(item, BacklogQueueItem) and not self.is_in_queue(item.show, item.segment):
            # backlog searches
            generic_queue.GenericQueue.add_item(self, item)
        elif isinstance(item, (ForcedSearchQueueItem, ManualSearchQueueItem, FailedQueueItem)) and not self.is_ep_in_queue(item.segment):
            # manual, snatch and failed searches
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
            found_results = search.searchForNeededEpisodes()

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
                    self.success = search.snatchEpisode(result)

                    # give the CPU a break
                    time.sleep(common.cpu_presets[sickbeard.CPU_PRESET])
            # What is this for ?!
            generic_queue.QueueItem.finish(self)

        except Exception:
            self.success = False
            logger.log(traceback.format_exc(), logger.DEBUG)

        if self.success is None:
            self.success = False

        self.finish()


class ForcedSearchQueueItem(generic_queue.QueueItem):
    def __init__(self, show, segment, downCurQuality=False, manual_search=False):
        generic_queue.QueueItem.__init__(self, u'Forced Search', FORCED_SEARCH)
        self.priority = generic_queue.QueuePriorities.HIGH
        self.name = 'FORCEDSEARCH-' + str(show.indexerid) if not manual_search else 'MANUALSEARCH-' + str(show.indexerid)

        self.success = None
        self.started = None
        self.results = None

        self.show = show
        self.segment = segment
        self.downCurQuality = downCurQuality
        self.manual_search = manual_search
        self.search_prov = search.Search(manual_search=manual_search, force_stop=self.force_stop)

    def run(self):
        """
        Run forced search thread
        """
        generic_queue.QueueItem.run(self)
        self.started = True

        try:
            logger.log(u"Beginning {0} search for: [{1}]".format(('forced','manual')[bool(self.manual_search)], self.segment.prettyName()))

            search_result = self.search_prov.searchProviders(self.show, [self.segment], True, self.downCurQuality)

            if not self.manual_search and search_result:
                # just use the first result for now
                if search_result[0].seeders not in (-1, None) and search_result[0].leechers not in (-1, None):
                    logger.log(u"Downloading {0} with {1} seeders and {2} leechers from {3}".
                               format(search_result[0].name,
                                      search_result[0].seeders, search_result[0].leechers, search_result[0].provider.name))
                else:
                    logger.log(u"Downloading {0} from {1}".format(search_result[0].name, search_result[0].provider.name))
                self.success = search.snatchEpisode(search_result[0])

                # give the CPU a break
                time.sleep(common.cpu_presets[sickbeard.CPU_PRESET])
            elif self.manual_search and search_result:
                self.results = search_result
                self.success = True
                ui.notifications.message("We have found downloads for {0}".format(self.segment.prettyName()),
                                         "These should become visible in the manual select page.")
            else:
                ui.notifications.message('No downloads were found', "Couldn't find a download for <i>{0}</i>".format(self.segment.prettyName()))
                logger.log(u"Unable to find a download for: [{0}]".format(self.segment.prettyName()))

        except Exception:
            self.success = False
            logger.log(traceback.format_exc(), logger.DEBUG)

        # ## Keep a list with the 100 last executed searches
        fifo(FORCED_SEARCH_HISTORY, self, FORCED_SEARCH_HISTORY_SIZE)

        if self.success is None:
            self.success = False

        self.finish()


class ManualSearchQueueItem(generic_queue.QueueItem):
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
        self.name = 'MANUALSEARCH-' + str(show.indexerid)
        self.success = None
        self.started = None
        self.results = None
        self.provider = provider
        self.segment = segment
        self.show = show
        self.cached_result = cached_result

    def run(self):
        """
        Run manual search thread
        """
        generic_queue.QueueItem.run(self)
        self.started = True

        search_result = providers.getProviderClass(self.provider).get_result(self.segment)
        search_result.show = self.show
        search_result.url = self.cached_result['url']
        search_result.quality = int(self.cached_result['quality'])
        search_result.name = self.cached_result['name']
        search_result.size = int(self.cached_result['size'])
        search_result.seeders = int(self.cached_result['seeders'])
        search_result.leechers = int(self.cached_result['leechers'])
        search_result.release_group = self.cached_result['release_group']
        search_result.version = int(self.cached_result['version'])

        try:
            logger.log(u"Beginning to manual snatch release: {0}".format(search_result.name))

            if search_result:
                if search_result.seeders not in (-1, None) and search_result.leechers not in (-1, None):
                    logger.log(u"Downloading {0} with {1} seeders and {2} leechers from {3}".
                               format(search_result.name,
                                      search_result.seeders, search_result.leechers, search_result.provider.name))
                else:
                    logger.log(u"Downloading {0} from {1}".format(search_result.name, search_result.provider.name))
                self.success = search.snatchEpisode(search_result)
            else:
                logger.log(u"Unable to snatch release: {0}".format(search_result.name))

            # give the CPU a break
            time.sleep(common.cpu_presets[sickbeard.CPU_PRESET])

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
        self.search_prov = search.Search(manual_search=False, force_stop=self.force_stop)

    def run(self):
        """
        Run backlog search thread
        """
        generic_queue.QueueItem.run(self)
        self.started = True

        if not self.show.paused:
            try:
                logger.log(u"Beginning backlog search for: [" + self.show.name + "]")
                search_result = self.search_prov.searchProviders(self.show, self.segment, False, False)

                if search_result:
                    for result in search_result:
                        # just use the first result for now
                        if result.seeders not in (-1, None) and result.leechers not in (-1, None):
                            logger.log(u"Downloading {0} with {1} seeders and {2} leechers from {3}".
                                       format(result.name,
                                              result.seeders, result.leechers, result.provider.name))
                        else:
                            logger.log(u"Downloading {0} from {1}".format(result.name, result.provider.name))
                        self.success = search.snatchEpisode(result)

                        # give the CPU a break
                        time.sleep(common.cpu_presets[sickbeard.CPU_PRESET])
                else:
                    logger.log(u"No needed episodes found during backlog search for: [" + self.show.name + "]")

            except Exception:
                self.success = False
                logger.log(traceback.format_exc(), logger.DEBUG)

        if self.success is None:
            self.success = False

        self.finish()


class FailedQueueItem(generic_queue.QueueItem):
    def __init__(self, show, segment, downCurQuality=False):
        generic_queue.QueueItem.__init__(self, u'Retry', FAILED_SEARCH)
        self.priority = generic_queue.QueuePriorities.HIGH
        self.name = 'RETRY-' + str(show.indexerid)

        self.success = None
        self.started = None

        self.show = show
        self.segment = segment
        self.downCurQuality = downCurQuality
        self.search_prov = search.Search(manual_search=False, force_stop=self.force_stop)

    def run(self):
        """
        Run failed thread
        """
        generic_queue.QueueItem.run(self)
        self.started = True

        try:
            for epObj in self.segment:

                logger.log(u"Marking episode as bad: [" + epObj.prettyName() + "]")

                failed_history.markFailed(epObj)

                (release, provider) = failed_history.findRelease(epObj)
                if release:
                    failed_history.logFailed(release)
                    history.logFailed(epObj, release, provider)

                failed_history.revertEpisode(epObj)
                logger.log(u"Beginning failed download search for: [" + epObj.prettyName() + "]")

            # If it is wanted, self.downCurQuality doesnt matter
            # if it isnt wanted, we need to make sure to not overwrite the existing ep that we reverted to!
            search_result = self.search_prov.searchProviders(self.show, self.segment, True, False)

            if search_result:
                for result in search_result:
                    # just use the first result for now
                    if result.seeders not in (-1, None) and result.leechers not in (-1, None):
                        logger.log(u"Downloading {0} with {1} seeders and {2} leechers from {3}".format(result.name,
                                   result.seeders, result.leechers, result.provider.name))
                    else:
                        logger.log(u"Downloading {0} from {1}".format(result.name, result.provider.name))
                    self.success = search.snatchEpisode(result)

                    # give the CPU a break
                    time.sleep(common.cpu_presets[sickbeard.CPU_PRESET])
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
