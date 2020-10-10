# coding=utf-8

"""Module with different types of Queue Items for searching and snatching."""

from __future__ import unicode_literals

import logging
import threading
import time
import traceback

from medusa import app, common, failed_history, history, ui, ws
from medusa.helpers import pretty_file_size
from medusa.logger.adapters.style import BraceAdapter
from medusa.queues import generic_queue
from medusa.search import BACKLOG_SEARCH, DAILY_SEARCH, FAILED_SEARCH, MANUAL_SEARCH, SNATCH_RESULT, SearchType
from medusa.search.core import (
    search_for_needed_episodes,
    search_providers,
    snatch_episode,
)


log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())

search_queue_lock = threading.Lock()

SEARCH_HISTORY = []
SEARCH_HISTORY_SIZE = 100


class SearchQueue(generic_queue.GenericQueue):
    """Search queue class."""

    def __init__(self):
        """Initialize the class."""
        generic_queue.GenericQueue.__init__(self)
        self.queue_name = 'SEARCHQUEUE'
        self.force = False

    def is_in_queue(self, show, segment):
        """Check if item is in queue."""
        for cur_item in self.queue:
            if isinstance(cur_item, (BacklogQueueItem, FailedQueueItem,
                                     SnatchQueueItem, ManualSearchQueueItem)) \
                    and cur_item.show == show and cur_item.segment == segment:
                return True
        return False

    def pause_backlog(self):
        """Pause the backlog."""
        self.min_priority = generic_queue.QueuePriorities.HIGH

    def unpause_backlog(self):
        """Unpause the backlog."""
        self.min_priority = 0

    def is_backlog_paused(self):
        """Check if backlog is paused."""
        # backlog priorities are NORMAL, this should be done properly somewhere
        return self.min_priority >= generic_queue.QueuePriorities.NORMAL

    def is_backlog_in_progress(self):
        """Check is backlog is in progress."""
        for cur_item in self.queue + [self.currentItem]:
            if isinstance(cur_item, BacklogQueueItem):
                return True
        return False

    def is_dailysearch_in_progress(self):
        """Check if daily search is in progress."""
        for cur_item in self.queue + [self.currentItem]:
            if isinstance(cur_item, DailySearchQueueItem):
                return True
        return False

    def queue_length(self):
        """Get queue lenght."""
        length = {'backlog': 0, 'daily': 0}
        for cur_item in self.queue:
            if isinstance(cur_item, DailySearchQueueItem):
                length['daily'] += 1
            elif isinstance(cur_item, BacklogQueueItem):
                length['backlog'] += 1
        return length

    def add_item(self, item):
        """Add item to queue."""
        if isinstance(item, DailySearchQueueItem):
            # daily searches
            generic_queue.GenericQueue.add_item(self, item)
        elif isinstance(item, (BacklogQueueItem, FailedQueueItem,
                               SnatchQueueItem, ManualSearchQueueItem)) \
                and not self.is_in_queue(item.show, item.segment):
            generic_queue.GenericQueue.add_item(self, item)
        else:
            log.debug('Item already in the queue, skipping')

    def force_daily(self):
        """Force daily searched."""
        if not self.is_dailysearch_in_progress and not self.currentItem.amActive:
            self.force = True
            return True
        return False


class ForcedSearchQueue(generic_queue.GenericQueue):
    """Search Queue used for Manual, (forced) Backlog and Failed Search."""

    def __init__(self):
        """Initialize ForcedSearch Queue."""
        generic_queue.GenericQueue.__init__(self)
        self.queue_name = 'FORCEDSEARCHQUEUE'

    def is_in_queue(self, show, segment):
        """Verify if the show and segment (episode or number of episodes) are scheduled."""
        for cur_item in self.queue:
            if cur_item.show == show and cur_item.segment == segment:
                return True
        return False

    def is_ep_in_queue(self, segment):
        """Verify if the show and segment (episode or number of episodes) are scheduled."""
        for cur_item in self.queue:
            if isinstance(cur_item, (BacklogQueueItem, FailedQueueItem, ManualSearchQueueItem)) and cur_item.segment == segment:
                return True
        return False

    def is_show_in_queue(self, show):
        """Verify if the show is queued in this queue as a BacklogQueueItem, ManualSearchQueueItem or FailedQueueItem."""
        for cur_item in self.queue:
            if isinstance(cur_item, (BacklogQueueItem, FailedQueueItem, ManualSearchQueueItem)) and cur_item.show.indexerid == show:
                return True
        return False

    def get_all_ep_from_queue(self, series_obj):
        """
        Get QueueItems from the queue if the queue item is scheduled to search for the passed Show.

        @param series_obj: Series object.

        @return: A list of BacklogQueueItem, FailedQueueItem or FailedQueueItem items
        """
        ep_obj_list = []
        for cur_item in self.queue:
            if isinstance(cur_item, (BacklogQueueItem, FailedQueueItem, ManualSearchQueueItem)):
                if series_obj and cur_item.show.identifier != series_obj.identifier:
                    continue
                ep_obj_list.append(cur_item)
        return ep_obj_list

    def is_backlog_paused(self):
        """
        Verify if the ForcedSearchQueue's min_priority has been changed.

        This indicates that the queue has been paused.
        # backlog priorities are NORMAL, this should be done properly somewhere
        """
        return self.min_priority >= generic_queue.QueuePriorities.NORMAL

    def is_forced_search_in_progress(self):
        """Test of a forced search is currently running (can be backlog, manual or failed search).

        It doesn't check what's in queue.
        """
        if isinstance(self.currentItem, (BacklogQueueItem, ManualSearchQueueItem, FailedQueueItem)):
            return True
        return False

    def queue_length(self):
        """Get queue length."""
        length = {'backlog_search': 0, 'manual_search': 0, 'failed': 0}
        for cur_item in self.queue:
            if isinstance(cur_item, FailedQueueItem):
                length['failed'] += 1
            elif isinstance(cur_item, ManualSearchQueueItem):
                length['manual_search'] += 1
            elif isinstance(cur_item, BacklogQueueItem):
                length['backlog_search'] += 1
        return length

    def add_item(self, item):
        """Add a new ManualSearchQueueItem or FailedQueueItem to the ForcedSearchQueue."""
        if isinstance(item, (ManualSearchQueueItem, FailedQueueItem, BacklogQueueItem)) and not self.is_ep_in_queue(item.segment):
            # manual, snatch and failed searches
            generic_queue.GenericQueue.add_item(self, item)
        else:
            log.debug('Item already in the queue, skipping')


class SnatchQueue(generic_queue.GenericQueue):
    """Queue for queuing SnatchQueueItem objects (snatch jobs)."""

    def __init__(self):
        """Initialize the SnatchQueue object."""
        generic_queue.GenericQueue.__init__(self)
        self.queue_name = 'SNATCHQUEUE'

    def is_in_queue(self, show, segment):
        """
        Check if the passed show and segment (episode of list of episodes) is in the queue.

        @param show: show object
        @param segment: list of episode objects

        @return: True or False
        """
        for cur_item in self.queue:
            if cur_item.show == show and cur_item.segment == segment:
                return True
        return False

    def is_ep_in_queue(self, segment):
        """
        Check if the passed segment (episode of list of episodes) is in the queue.

        @param segment: list of episode objects

        @return: True or False
        """
        for cur_item in self.queue:
            if cur_item.segment == segment:
                return True
        return False

    def queue_length(self):
        """
        Get the length of the current queue.

        @return: length of queue
        """
        return {'manual_snatch': len(self.queue)}

    def add_item(self, item):
        """
        Add a SnatchQueueItem queue item.

        @param item: SnatchQueueItem gueue object
        """
        if not self.is_in_queue(item.show, item.segment):
            # backlog searches
            generic_queue.GenericQueue.add_item(self, item)
        else:
            log.debug("Not adding item, it's already in the queue")


class DailySearchQueueItem(generic_queue.QueueItem):
    """Daily search queue item class."""

    def __init__(self, scheduler_start_time, force):
        """Initialize the class."""
        generic_queue.QueueItem.__init__(self, u'Daily Search', DAILY_SEARCH)

        self.success = None
        self.started = None
        self.scheduler_start_time = scheduler_start_time
        self.force = force

        self.to_json.update({
            'success': self.success,
            'force': self.force
        })

    def run(self):
        """Run daily search thread."""
        generic_queue.QueueItem.run(self)
        self.started = True

        try:
            log.info('Beginning daily search for new episodes')

            # Push an update to any open Web UIs through the WebSocket
            ws.Message('QueueItemUpdate', self.to_json).push()

            found_results = search_for_needed_episodes(self.scheduler_start_time, force=self.force)

            if not found_results:
                log.info('No needed episodes found')
            else:
                for result in found_results:
                    # just use the first result for now
                    if result.seeders not in (-1, None) and result.leechers not in (-1, None):
                        log.info(
                            'Downloading {name} with {seeders} seeders and {leechers} leechers'
                            ' and size {size} from {provider}', {
                                'name': result.name,
                                'seeders': result.seeders,
                                'leechers': result.leechers,
                                'size': pretty_file_size(result.size),
                                'provider': result.provider.name,
                            }
                        )
                    else:
                        log.info(
                            'Downloading {name} with size: {size} from {provider}', {
                                'name': result.name,
                                'size': pretty_file_size(result.size),
                                'provider': result.provider.name,
                            }
                        )

                    # Set the search_type for the result.
                    result.search_type = SearchType.DAILY_SEARCH

                    # Create the queue item
                    snatch_queue_item = SnatchQueueItem(result.series, result.episodes, result)

                    # Add the queue item to the queue
                    app.manual_snatch_scheduler.action.add_item(snatch_queue_item)

                    self.success = False
                    while snatch_queue_item.success is False:
                        if snatch_queue_item.started and snatch_queue_item.success:
                            self.success = True
                        time.sleep(1)

                    # give the CPU a break
                    time.sleep(common.cpu_presets[app.CPU_PRESET])

        except Exception as error:
            self.success = False
            log.exception('DailySearchQueueItem Exception, error: {error!r}', {'error': error})

        if self.success is None:
            self.success = False

        # Push an update to any open Web UIs through the WebSocket
        ws.Message('QueueItemUpdate', self.to_json).push()

        self.finish()


class ManualSearchQueueItem(generic_queue.QueueItem):
    """Manual search queue item class."""

    def __init__(self, show, segment, manual_search_type='episode'):
        """
        Initialize class of a QueueItem used to queue forced and manual searches.

        :param show: A show object
        :param segment: A list of episode objects.
        :param manual_search_type: Used to switch between episode and season search. Options are 'episode' or 'season'.
        :return: The run() method searches and snatches the episode(s) if possible or it only searches and saves results to cache tables.
        """
        generic_queue.QueueItem.__init__(self, u'Manual Search', MANUAL_SEARCH)
        self.priority = generic_queue.QueuePriorities.HIGH
        self.name = '{search_type}-{indexerid}'.format(
            search_type='MANUAL',
            indexerid=show.indexerid
        )

        self.success = None
        self.started = None
        self.results = None

        self.show = show
        self.segment = segment
        self.manual_search_type = manual_search_type

        self.to_json.update({
            'show': self.show.to_json(),
            'segment': [ep.to_json() for ep in self.segment],
            'success': self.success,
            'manualSearchType': self.manual_search_type
        })

    def run(self):
        """Run manual search thread."""
        generic_queue.QueueItem.run(self)
        self.started = True

        try:
            log.info(
                'Beginning {search_type} {season_pack}search for: {ep}', {
                    'search_type': 'manual',
                    'season_pack': ('', 'season pack ')[bool(self.manual_search_type == 'season')],
                    'ep': self.segment[0].pretty_name()
                }
            )

            # Push an update to any open Web UIs through the WebSocket
            ws.Message('QueueItemUpdate', self.to_json).push()

            search_result = search_providers(self.show, self.segment, forced_search=True, down_cur_quality=True,
                                             manual_search=True, manual_search_type=self.manual_search_type)

            if search_result:
                self.results = search_result
                self.success = True

                if self.manual_search_type == 'season':
                    ui.notifications.message('We have found season packs for {show_name}'
                                             .format(show_name=self.show.name),
                                             'These should become visible in the manual select page.')
                else:
                    ui.notifications.message('We have found results for {ep}'
                                             .format(ep=self.segment[0].pretty_name()),
                                             'These should become visible in the manual select page.')

            else:
                ui.notifications.message('No results were found')
                log.info(
                    'Unable to find {search_type} {season_pack}results for: {ep}', {
                        'search_type': 'manual',
                        'season_pack': ('', 'season pack ')[bool(self.manual_search_type == 'season')],
                        'ep': self.segment[0].pretty_name()
                    }
                )

        # TODO: Remove catch all exception.
        except Exception:
            self.success = False
            log.debug(traceback.format_exc())

        # Keep a list with the 100 last executed searches
        fifo(SEARCH_HISTORY, self, SEARCH_HISTORY_SIZE)

        if self.success is None:
            self.success = False

        # Push an update to any open Web UIs through the WebSocket
        msg = ws.Message('QueueItemUpdate', self.to_json)
        msg.push()

        self.finish()


class SnatchQueueItem(generic_queue.QueueItem):
    """
    A queue item that can be used to queue the snatch of a search result.

    @param show: A show object
    @param segment: A list of episode objects
    @param provider: The provider id. For example nyaatorrent and not NyaaTorrent. Or usernet_crawler and not Usenet-Crawler
    @param cached_result: An sql result of the searched result retrieved from the provider cache table.

    @return: The run() methods snatches the episode(s) if possible.
    """

    def __init__(self, show, segment, search_result):
        """Initialize the class."""
        generic_queue.QueueItem.__init__(self, u'Snatch Result', SNATCH_RESULT)
        self.priority = generic_queue.QueuePriorities.HIGH
        self.name = 'SNATCH-{indexer_id}'.format(indexer_id=search_result.series.indexerid)
        self.success = None
        self.started = None
        self.segment = segment
        self.show = show
        self.results = None
        self.search_result = search_result

        self.to_json.update({
            'show': self.show.to_json(),
            'segment': [ep.to_json() for ep in self.segment],
            'success': self.success,
            'searchResult': self.search_result.to_json()
        })

    def run(self):
        """Run manual snatch job."""
        generic_queue.QueueItem.run(self)
        self.started = True

        result = self.search_result

        try:
            log.info('Beginning to snatch release: {name}',
                     {'name': result.name})

            # Push an update to any open Web UIs through the WebSocket
            msg = ws.Message('QueueItemUpdate', self.to_json)
            msg.push()

            if result:
                if result.seeders not in (-1, None) and result.leechers not in (-1, None):
                    log.info(
                        'Downloading {name} with {seeders} seeders and {leechers} leechers'
                        ' and size {size} from {provider}, through a {search_type} search', {
                            'name': result.name,
                            'seeders': result.seeders,
                            'leechers': result.leechers,
                            'size': pretty_file_size(result.size),
                            'provider': result.provider.name,
                            'search_type': result.search_type
                        }
                    )
                else:
                    log.info(
                        'Downloading {name} with size: {size} from {provider}, through a {search_type} search', {
                            'name': result.name,
                            'size': pretty_file_size(result.size),
                            'provider': result.provider.name,
                            'search_type': result.search_type
                        }
                    )
                self.success = snatch_episode(result)
            else:
                log.info('Unable to snatch release: {name}',
                         {'name': result.name})

            # give the CPU a break
            time.sleep(common.cpu_presets[app.CPU_PRESET])

        except Exception:
            self.success = False
            log.exception('Snatch failed! For result: {name}', {'name': result.name})
            ui.notifications.message('Error while snatching selected result',
                                     'Unable to snatch the result for <i>{name}</i>'.format(name=result.name))

        if self.success is None:
            self.success = False

        # Push an update to any open Web UIs through the WebSocket
        msg = ws.Message('QueueItemUpdate', self.to_json)
        msg.push()

        self.finish()


class BacklogQueueItem(generic_queue.QueueItem):
    """Backlog queue item class."""

    def __init__(self, show, segment):
        """Initialize the class."""
        generic_queue.QueueItem.__init__(self, u'Backlog', BACKLOG_SEARCH)
        self.priority = generic_queue.QueuePriorities.LOW
        self.name = 'BACKLOG-{indexer_id}'.format(indexer_id=show.indexerid)

        self.started = None

        self.show = show
        self.segment = segment

        self.to_json.update({
            'show': self.show.to_json(),
            'segment': [ep.to_json() for ep in self.segment],
        })

    def run(self):
        """Run backlog search thread."""
        generic_queue.QueueItem.run(self)
        self.started = True

        if not self.show.paused:
            try:
                log.info('Beginning backlog search for: {name}',
                         {'name': self.show.name})

                # Push an update to any open Web UIs through the WebSocket
                ws.Message('QueueItemUpdate', self.to_json).push()

                search_result = search_providers(self.show, self.segment)

                if search_result:
                    for result in search_result:
                        # just use the first result for now
                        if result.seeders not in (-1, None) and result.leechers not in (-1, None):
                            log.info(
                                'Downloading {name} with {seeders} seeders and {leechers} leechers '
                                'and size {size} from {provider}', {
                                    'name': result.name,
                                    'seeders': result.seeders,
                                    'leechers': result.leechers,
                                    'size': pretty_file_size(result.size),
                                    'provider': result.provider.name,
                                }
                            )
                        else:
                            log.info(
                                'Downloading {name} with size: {size} from {provider}', {
                                    'name': result.name,
                                    'size': pretty_file_size(result.size),
                                    'provider': result.provider.name,
                                }
                            )

                        # Set the search_type for the result.
                        result.search_type = SearchType.BACKLOG_SEARCH

                        # Create the queue item
                        snatch_queue_item = SnatchQueueItem(result.series, result.episodes, result)

                        # Add the queue item to the queue
                        app.manual_snatch_scheduler.action.add_item(snatch_queue_item)

                        self.success = False
                        while snatch_queue_item.success is False:
                            if snatch_queue_item.started and snatch_queue_item.success:
                                self.success = True
                            time.sleep(1)

                        # give the CPU a break
                        time.sleep(common.cpu_presets[app.CPU_PRESET])
                else:
                    log.info('No needed episodes found during backlog search for: {name}',
                             {'name': self.show.name})

            # TODO: Remove the catch all exception.
            except Exception:
                self.success = False
                log.debug(traceback.format_exc())

        # Keep a list with the 100 last executed searches
        fifo(SEARCH_HISTORY, self, SEARCH_HISTORY_SIZE)

        if self.success is None:
            self.success = False

        # Push an update to any open Web UIs through the WebSocket
        ws.Message('QueueItemUpdate', self.to_json).push()

        self.finish()


class FailedQueueItem(generic_queue.QueueItem):
    """Failed queue item class."""

    def __init__(self, show, segment, down_cur_quality=False):
        """Initialize the class."""
        generic_queue.QueueItem.__init__(self, u'Retry', FAILED_SEARCH)
        self.priority = generic_queue.QueuePriorities.HIGH
        self.name = 'RETRY-{indexer_id}'.format(indexer_id=show.indexerid)

        self.success = None
        self.started = None

        self.show = show
        self.segment = segment
        self.down_cur_quality = down_cur_quality

        self.to_json.update({
            'show': self.show.to_json(),
            'segment': [ep.to_json() for ep in self.segment],
            'success': self.success,
            'downloadCurrentQuality': self.down_cur_quality
        })

    def run(self):
        """Run failed thread."""
        generic_queue.QueueItem.run(self)
        self.started = True

        # Push an update to any open Web UIs through the WebSocket
        ws.Message('QueueItemUpdate', self.to_json).push()

        try:
            for ep_obj in self.segment:

                log.info('Marking episode as bad: {ep}',
                         {'ep': ep_obj.pretty_name()})

                failed_history.mark_failed(ep_obj)

                (release, provider) = failed_history.find_release(ep_obj)
                if release:
                    failed_history.log_failed(release)
                    history.log_failed(ep_obj, release, provider)

                failed_history.revert_episode(ep_obj)
                log.info('Beginning failed download search for: {ep}',
                         {'ep': ep_obj.pretty_name()})

            # If it is wanted, self.down_cur_quality doesnt matter
            # if it isn't wanted, we need to make sure to not overwrite the existing ep that we reverted to!
            search_result = search_providers(self.show, self.segment, True)

            if search_result:
                for result in search_result:
                    # just use the first result for now
                    if result.seeders not in (-1, None) and result.leechers not in (-1, None):
                        log.info(
                            'Downloading {name} with {seeders} seeders and {leechers} leechers '
                            'and size {size} from {provider}', {
                                'name': result.name,
                                'seeders': result.seeders,
                                'leechers': result.leechers,
                                'size': pretty_file_size(result.size),
                                'provider': result.provider.name,
                            }
                        )
                    else:
                        log.info(
                            'Downloading {name} with size: {size} from {provider}', {
                                'name': result.name,
                                'size': pretty_file_size(result.size),
                                'provider': result.provider.name,
                            }
                        )

                    # Set the search_type for the result.
                    result.search_type = SearchType.FAILED_SEARCH

                    # Create the queue item
                    snatch_queue_item = SnatchQueueItem(result.series, result.episodes, result)

                    # Add the queue item to the queue
                    app.manual_snatch_scheduler.action.add_item(snatch_queue_item)

                    self.success = False
                    while snatch_queue_item.success is False:
                        if snatch_queue_item.started and snatch_queue_item.success:
                            self.success = True
                        time.sleep(1)

                    # give the CPU a break
                    time.sleep(common.cpu_presets[app.CPU_PRESET])
            else:
                log.info('No needed episodes found during failed search for: {name}',
                         {'name': self.show.name})

        # TODO: Replace the catch all exception with a more specific one.
        except Exception:
            self.success = False
            log.info(traceback.format_exc())

        # Keep a list with the 100 last executed searches
        fifo(SEARCH_HISTORY, self, SEARCH_HISTORY_SIZE)

        if self.success is None:
            self.success = False

        # Push an update to any open Web UIs through the WebSocket
        ws.Message('QueueItemUpdate', self.to_json).push()

        self.finish()


def fifo(my_list, item, max_size=100):
    """Append item to queue and limit it to 100 items."""
    if len(my_list) >= max_size:
        my_list.pop(0)
    my_list.append(item)
