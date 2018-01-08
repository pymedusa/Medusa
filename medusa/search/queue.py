# coding=utf-8

"""Module with different types of Queue Items for searching and snatching."""

from __future__ import unicode_literals

import logging
import threading
import time
import traceback

from medusa import app, common, failed_history, generic_queue, history, providers, ui
from medusa.helpers import pretty_file_size
from medusa.logger.adapters.style import BraceAdapter
from medusa.search import BACKLOG_SEARCH, DAILY_SEARCH, FAILED_SEARCH, FORCED_SEARCH, MANUAL_SEARCH
from medusa.search.core import (
    search_for_needed_episodes,
    search_providers,
    snatch_episode,
)


log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())

search_queue_lock = threading.Lock()

FORCED_SEARCH_HISTORY = []
FORCED_SEARCH_HISTORY_SIZE = 100


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
                                     ForcedSearchQueueItem, ManualSnatchQueueItem)) \
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
                length[b'daily'] += 1
            elif isinstance(cur_item, BacklogQueueItem):
                length[b'backlog'] += 1
        return length

    def add_item(self, item):
        """Add item to queue."""
        if isinstance(item, DailySearchQueueItem):
            # daily searches
            generic_queue.GenericQueue.add_item(self, item)
        elif isinstance(item, (BacklogQueueItem, FailedQueueItem,
                               ManualSnatchQueueItem, ForcedSearchQueueItem)) \
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
    """Search Queueu used for Forced Search, Failed Search."""

    def __init__(self):
        """Initialize ForcedSearch Queue."""
        generic_queue.GenericQueue.__init__(self)
        self.queue_name = 'SEARCHQUEUE'

    def is_in_queue(self, show, segment):
        """Verify if the show and segment (episode or number of episodes) are scheduled."""
        for cur_item in self.queue:
            if cur_item.show == show and cur_item.segment == segment:
                return True
        return False

    def is_ep_in_queue(self, segment):
        """Verify if the show and segment (episode or number of episodes) are scheduled."""
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

    def get_all_ep_from_queue(self, series_obj):
        """
        Get QueueItems from the queue if the queue item is scheduled to search for the passed Show.

        @param series_obj: Series object.

        @return: A list of ForcedSearchQueueItem or FailedQueueItem items
        """
        ep_obj_list = []
        for cur_item in self.queue:
            if isinstance(cur_item, (ForcedSearchQueueItem, FailedQueueItem)):
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
        """Test of a forced search is currently running, it doesn't check what's in queue."""
        if isinstance(self.currentItem, (ForcedSearchQueueItem, FailedQueueItem)):
            return True
        return False

    def queue_length(self):
        """Get queue length."""
        length = {'forced_search': 0, 'manual_search': 0, 'failed': 0}
        for cur_item in self.queue:
            if isinstance(cur_item, FailedQueueItem):
                length[b'failed'] += 1
            elif isinstance(cur_item, ForcedSearchQueueItem) and not cur_item.manual_search:
                length[b'forced_search'] += 1
            elif isinstance(cur_item, ForcedSearchQueueItem) and cur_item.manual_search:
                length[b'manual_search'] += 1
        return length

    def add_item(self, item):
        """Add a new ForcedSearchQueueItem or FailedQueueItem to the ForcedSearchQueue."""
        if isinstance(item, (ForcedSearchQueueItem, FailedQueueItem)) and not self.is_ep_in_queue(item.segment):
            # manual, snatch and failed searches
            generic_queue.GenericQueue.add_item(self, item)
        else:
            log.debug('Item already in the queue, skipping')


class SnatchQueue(generic_queue.GenericQueue):
    """Queue for queuing ManualSnatchQueueItem objects (snatch jobs)."""

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
        Add a ManualSnatchQueueItem queue item.

        @param item: ManualSnatchQueueItem gueue object
        """
        if not self.is_in_queue(item.show, item.segment):
            # backlog searches
            generic_queue.GenericQueue.add_item(self, item)
        else:
            log.debug("Not adding item, it's already in the queue")


class DailySearchQueueItem(generic_queue.QueueItem):
    """Daily searche queue item class."""

    def __init__(self, force):
        """Initialize the class."""
        generic_queue.QueueItem.__init__(self, u'Daily Search', DAILY_SEARCH)

        self.success = None
        self.started = None
        self.force = force

    def run(self):
        """Run daily search thread."""
        generic_queue.QueueItem.run(self)
        self.started = True

        try:
            log.info('Beginning daily search for new episodes')
            found_results = search_for_needed_episodes(force=self.force)

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
                    self.success = snatch_episode(result)

                    # give the CPU a break
                    time.sleep(common.cpu_presets[app.CPU_PRESET])

        except Exception as error:
            self.success = False
            log.exception('DailySearchQueueItem Exception, error: {error}', {'error': error})

        if self.success is None:
            self.success = False

        self.finish()


class ForcedSearchQueueItem(generic_queue.QueueItem):
    """Forced search queue item class."""

    def __init__(self, show, segment, down_cur_quality=False, manual_search=False, manual_search_type='episode'):
        """
        Initialize class of a QueueItem used to queue forced and manual searches.

        :param show: A show object
        :param segment: A list of episode objects.
        :param down_cur_quality: Not sure what it's used for. Maybe legacy.
        :param manual_search: Passed as True (bool) when the search should be performed without snatching a result
        :param manual_search_type: Used to switch between episode and season search. Options are 'episode' or 'season'.
        :return: The run() method searches and snatches the episode(s) if possible or it only searches and saves results to cache tables.
        """
        generic_queue.QueueItem.__init__(self, u'Forced Search', FORCED_SEARCH)
        self.priority = generic_queue.QueuePriorities.HIGH
        # SEARCHQUEUE-MANUAL-12345
        # SEARCHQUEUE-FORCED-12345
        self.name = '{search_type}-{indexerid}'.format(
            search_type=('FORCED', 'MANUAL')[bool(manual_search)],
            indexerid=show.indexerid
        )

        self.success = None
        self.started = None
        self.results = None

        self.show = show
        self.segment = segment
        self.down_cur_quality = down_cur_quality
        self.manual_search = manual_search
        self.manual_search_type = manual_search_type

    def run(self):
        """Run forced search thread."""
        generic_queue.QueueItem.run(self)
        self.started = True

        try:
            log.info(
                'Beginning {search_type} {season_pack}search for: {ep}', {
                    'search_type': ('forced', 'manual')[bool(self.manual_search)],
                    'season_pack': ('', 'season pack ')[bool(self.manual_search_type == 'season')],
                    'ep': self.segment[0].pretty_name()
                }
            )

            search_result = search_providers(self.show, self.segment, True, self.down_cur_quality,
                                             self.manual_search, self.manual_search_type)

            if not self.manual_search and search_result:
                for result in search_result:
                    # Just use the first result for now
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
                    self.success = snatch_episode(result)

                    # Give the CPU a break
                    time.sleep(common.cpu_presets[app.CPU_PRESET])

            elif self.manual_search and search_result:
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
                        'search_type': ('forced', 'manual')[bool(self.manual_search)],
                        'season_pack': ('', 'season pack ')[bool(self.manual_search_type == 'season')],
                        'ep': self.segment[0].pretty_name()
                    }
                )

        # TODO: Remove catch all exception.
        except Exception:
            self.success = False
            log.debug(traceback.format_exc())

        # Keep a list with the 100 last executed searches
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
        """Initialize the class."""
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
        """Run manual snatch job."""
        generic_queue.QueueItem.run(self)
        self.started = True

        result = providers.get_provider_class(self.provider).get_result(self.segment)
        result.series = self.show
        result.url = self.cached_result[b'url']
        result.quality = int(self.cached_result[b'quality'])
        result.name = self.cached_result[b'name']
        result.size = int(self.cached_result[b'size'])
        result.seeders = int(self.cached_result[b'seeders'])
        result.leechers = int(self.cached_result[b'leechers'])
        result.release_group = self.cached_result[b'release_group']
        result.version = int(self.cached_result[b'version'])
        result.proper_tags = self.cached_result[b'proper_tags'].split('|') \
            if self.cached_result[b'proper_tags'] else ''
        result.manually_searched = True

        try:
            log.info('Beginning to manual snatch release: {name}',
                     {'name': result.name})

            if result:
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
                self.success = snatch_episode(result)
            else:
                log.info('Unable to snatch release: {name}',
                         {'name': result.name})

            # give the CPU a break
            time.sleep(common.cpu_presets[app.CPU_PRESET])

        except Exception:
            self.success = False
            log.exception('Manual snatch failed!. For result: {name}', {'name': result.name})
            ui.notifications.message('Error while snatching selected result',
                                     'Unable to snatch the result for <i>{name}</i>'.format(name=result.name))

        if self.success is None:
            self.success = False

        self.finish()


class BacklogQueueItem(generic_queue.QueueItem):
    """Backlog queue item class."""

    def __init__(self, show, segment):
        """Initialize the class."""
        generic_queue.QueueItem.__init__(self, u'Backlog', BACKLOG_SEARCH)
        self.priority = generic_queue.QueuePriorities.LOW
        self.name = 'BACKLOG-' + str(show.indexerid)

        self.success = None
        self.started = None

        self.show = show
        self.segment = segment

    def run(self):
        """Run backlog search thread."""
        generic_queue.QueueItem.run(self)
        self.started = True

        if not self.show.paused:
            try:
                log.info('Beginning backlog search for: {name}',
                         {'name': self.show.name})
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
                        self.success = snatch_episode(result)

                        # give the CPU a break
                        time.sleep(common.cpu_presets[app.CPU_PRESET])
                else:
                    log.info('No needed episodes found during backlog search for: {name}',
                             {'name': self.show.name})

            # TODO: Remove the catch all exception.
            except Exception:
                self.success = False
                log.debug(traceback.format_exc())

        if self.success is None:
            self.success = False

        self.finish()


class FailedQueueItem(generic_queue.QueueItem):
    """Failed queue item class."""

    def __init__(self, show, segment, down_cur_quality=False):
        """Initialize the class."""
        generic_queue.QueueItem.__init__(self, u'Retry', FAILED_SEARCH)
        self.priority = generic_queue.QueuePriorities.HIGH
        self.name = 'RETRY-' + str(show.indexerid)

        self.success = None
        self.started = None

        self.show = show
        self.segment = segment
        self.down_cur_quality = down_cur_quality

    def run(self):
        """Run failed thread."""
        generic_queue.QueueItem.run(self)
        self.started = True

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
                    self.success = snatch_episode(result)

                    # give the CPU a break
                    time.sleep(common.cpu_presets[app.CPU_PRESET])
            else:
                log.info('No needed episodes found during failed search for: {name}',
                         {'name': self.show.name})

        # TODO: Replace the catch all exception with a more specific one.
        except Exception:
            self.success = False
            log.info(traceback.format_exc())

        # ## Keep a list with the 100 last executed searches
        fifo(FORCED_SEARCH_HISTORY, self, FORCED_SEARCH_HISTORY_SIZE)

        if self.success is None:
            self.success = False

        self.finish()


def fifo(my_list, item, max_size=100):
    """Append item to queue and limit it to 100 items."""
    if len(my_list) >= max_size:
        my_list.pop(0)
    my_list.append(item)
