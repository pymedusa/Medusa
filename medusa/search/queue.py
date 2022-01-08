# coding=utf-8

"""Module with different types of Queue Items for searching and snatching."""

from __future__ import unicode_literals

import datetime
import logging
import operator
import re
import threading
import time
import traceback
from builtins import map
from builtins import str

from medusa import app, common, db, failed_history, helpers, history, ui, ws
from medusa.common import DOWNLOADED, SNATCHED, SNATCHED_BEST, SNATCHED_PROPER, SUBTITLED
from medusa.helper.common import enabled_providers
from medusa.helper.exceptions import AuthException, ex
from medusa.helpers import pretty_file_size
from medusa.logger.adapters.style import BraceAdapter
from medusa.name_parser.parser import InvalidNameException, InvalidShowException, NameParser
from medusa.queues import generic_queue
from medusa.search import BACKLOG_SEARCH, DAILY_SEARCH, FAILED_SEARCH, MANUAL_SEARCH, PROPER_SEARCH, SNATCH_RESULT, SearchType
from medusa.search.core import (
    filter_results,
    pick_result,
    search_for_needed_episodes,
    search_providers,
    snatch_result,
)
from medusa.show.history import History

from six import itervalues, text_type


log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())

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
        for cur_item in self.queue + [self.current_item]:
            if isinstance(cur_item, BacklogQueueItem):
                return True
        return False

    def is_dailysearch_in_progress(self):
        """Check if daily search is in progress."""
        for cur_item in self.queue + [self.current_item]:
            if isinstance(cur_item, DailySearchQueueItem):
                return True
        return False

    def is_proper_search_in_progress(self):
        """Check if proper search is in progress."""
        for cur_item in self.queue + [self.current_item]:
            if isinstance(cur_item, ProperSearchQueueItem):
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
        if isinstance(item, (DailySearchQueueItem, ProperSearchQueueItem)):
            # daily searches and proper searches
            generic_queue.GenericQueue.add_item(self, item)
        elif isinstance(item, (BacklogQueueItem, FailedQueueItem,
                               SnatchQueueItem, ManualSearchQueueItem)) \
                and not self.is_in_queue(item.show, item.segment):
            generic_queue.GenericQueue.add_item(self, item)
        else:
            log.debug('Item already in the queue, skipping')

    def force_daily(self):
        """Force daily searched."""
        if not self.is_dailysearch_in_progress and not self.current_item.amActive:
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
        if isinstance(self.current_item, (BacklogQueueItem, ManualSearchQueueItem, FailedQueueItem)):
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
                self.success = snatch_result(result)
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

                log.info('Marking episode as failed: {ep}', {'ep': ep_obj.pretty_name()})

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
            search_result = search_providers(self.show, self.segment, forced_search=True)

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


class ProperSearchQueueItem(generic_queue.QueueItem):
    """Proper search queue item class."""

    def __init__(self, force, processed_propers, ignore_processed_propers):
        """Initialize the class."""
        generic_queue.QueueItem.__init__(self, u'Proper Search', PROPER_SEARCH)

        self.success = None
        self.started = None
        self.force = force
        self.processed_propers = processed_propers
        self.ignore_processed_propers = ignore_processed_propers

        self.to_json.update({
            'success': self.success,
            'force': self.force
        })

    def run(self):
        """Run proper search thread."""
        generic_queue.QueueItem.run(self)
        self.started = True

        try:
            log.info('Beginning proper search for new episodes')

            # Push an update to any open Web UIs through the WebSocket
            ws.Message('QueueItemUpdate', self.to_json).push()

            # If force we should ignore existing processed propers
            self.ignore_processed_propers = False
            if self.force:
                self.ignore_processed_propers = True
                log.debug("Ignoring already processed propers as it's a forced search")

            log.info('Using proper search days: {search_days}', {'search_days': app.PROPERS_SEARCH_DAYS})

            propers = self._get_proper_results()

            if propers:
                self._download_propers(propers)

            self._set_last_proper_search(datetime.datetime.today().toordinal())

            run_at = ''
            if app.proper_finder_scheduler.start_time is None:
                run_in = app.proper_finder_scheduler.lastRun + \
                    app.proper_finder_scheduler.cycleTime - datetime.datetime.now()
                hours, remainder = divmod(run_in.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                run_at = ', next check in approx. {0}'.format(
                    '{0}h, {1}m'.format(hours, minutes) if 0 < hours else '{0}m, {1}s'.format(minutes, seconds))

            log.info('Completed the search for new propers{run_at}', {'run_at': run_at})

            # Push an update to any open Web UIs through the WebSocket
            ws.Message('QueueItemUpdate', self.to_json).push()

        # TODO: Remove the catch all exception.
        except Exception:
            self.success = False
            log.debug(traceback.format_exc())

    def _get_proper_results(self):  # pylint: disable=too-many-locals, too-many-branches, too-many-statements
        """Retrieve a list of recently aired episodes, and search for these episodes in the different providers."""
        propers = {}

        # For each provider get the list of propers
        original_thread_name = threading.currentThread().name
        providers = enabled_providers('backlog')

        search_date = datetime.datetime.today() - datetime.timedelta(days=app.PROPERS_SEARCH_DAYS)
        main_db_con = db.DBConnection()
        if not app.POSTPONE_IF_NO_SUBS:
            # Get the recently aired (last 2 days) shows from DB
            recently_aired = main_db_con.select(
                'SELECT indexer, showid, season, episode, status, airdate'
                ' FROM tv_episodes'
                ' WHERE airdate >= ?'
                ' AND status = ?',
                [search_date.toordinal(), DOWNLOADED]
            )
        else:
            # Get recently subtitled episodes (last 2 days) from DB
            # Episode status becomes downloaded only after found subtitles
            last_subtitled = search_date.strftime(History.date_format)
            recently_aired = main_db_con.select('SELECT indexer_id AS indexer, showid, season, episode FROM history '
                                                'WHERE date >= ? AND action = ?', [last_subtitled, SUBTITLED])

        if not recently_aired:
            log.info('No recently aired new episodes, nothing to search for')
            return []

        # Loop through the providers, and search for releases
        for cur_provider in providers:
            threading.currentThread().name = '{thread} :: [{provider}]'.format(thread=original_thread_name,
                                                                               provider=cur_provider.name)

            log.info('Searching for any new PROPER releases from {provider}', {'provider': cur_provider.name})

            try:
                cur_propers = cur_provider.find_propers(recently_aired)
            except AuthException as e:
                log.debug('Authentication error: {error}', {'error': ex(e)})
                continue

            # if they haven't been added by a different provider than add the proper to the list
            for proper in cur_propers:
                name = self._sanitize_name(proper.name)
                if name not in propers:
                    log.debug('Found new possible proper result: {name}', {'name': proper.name})
                    propers[name] = proper

        threading.currentThread().name = original_thread_name

        # Take the list of unique propers and get it sorted by
        sorted_propers = sorted(list(itervalues(propers)), key=operator.attrgetter('date'), reverse=True)
        final_propers = []

        # Keep only items from last PROPER_SEARCH_DAYS setting in processed propers:
        latest_proper = datetime.datetime.now() - datetime.timedelta(days=app.PROPERS_SEARCH_DAYS)
        self.processed_propers = [p for p in self.processed_propers if p.get('date') >= latest_proper]

        # Get proper names from processed propers
        processed_propers_names = [proper.get('name') for proper in self.processed_propers if proper.get('name')]

        for cur_proper in sorted_propers:

            if not self.ignore_processed_propers and cur_proper.name in processed_propers_names:
                log.debug(u'Proper already processed. Skipping: {proper_name}', {'proper_name': cur_proper.name})
                continue

            try:
                cur_proper.parse_result = NameParser().parse(cur_proper.name)
            except (InvalidNameException, InvalidShowException) as error:
                log.debug('{error}', {'error': error})
                continue

            if not cur_proper.parse_result.proper_tags:
                log.info('Skipping non-proper: {name}', {'name': cur_proper.name})
                continue

            if not cur_proper.series.episodes.get(cur_proper.parse_result.season_number) or \
                    any([ep for ep in cur_proper.parse_result.episode_numbers
                         if not cur_proper.series.episodes[cur_proper.parse_result.season_number].get(ep)]):
                log.info('Skipping proper for wrong season/episode: {name}', {'name': cur_proper.name})
                continue

            log.debug('Proper tags for {proper}: {tags}', {
                'proper': cur_proper.name,
                'tags': cur_proper.parse_result.proper_tags
            })

            if not cur_proper.parse_result.series_name:
                log.debug('Ignoring invalid show: {name}', {'name': cur_proper.name})
                if cur_proper.name not in processed_propers_names:
                    self.processed_propers.append({'name': cur_proper.name, 'date': cur_proper.date})
                continue

            if not cur_proper.parse_result.episode_numbers:
                log.debug('Ignoring full season instead of episode: {name}', {'name': cur_proper.name})
                if cur_proper.name not in processed_propers_names:
                    self.processed_propers.append({'name': cur_proper.name, 'date': cur_proper.date})
                continue

            log.debug('Successful match! Matched {original_name} to show {new_name}',
                      {'original_name': cur_proper.parse_result.original_name,
                       'new_name': cur_proper.parse_result.series.name
                       })

            # Map the indexerid in the db to the show's indexerid
            cur_proper.indexerid = cur_proper.parse_result.series.indexerid

            # Map the indexer in the db to the show's indexer
            cur_proper.indexer = cur_proper.parse_result.series.indexer

            # Map our Proper instance
            cur_proper.series = cur_proper.parse_result.series
            cur_proper.actual_season = cur_proper.parse_result.season_number
            cur_proper.actual_episodes = cur_proper.parse_result.episode_numbers
            cur_proper.release_group = cur_proper.parse_result.release_group
            cur_proper.version = cur_proper.parse_result.version
            cur_proper.quality = cur_proper.parse_result.quality
            cur_proper.proper_tags = cur_proper.parse_result.proper_tags

            cur_proper.update_search_result()

            # filter release, in this case, it's just a quality gate. As we only send one result.
            wanted_results = filter_results(cur_proper)
            best_result = pick_result(wanted_results)

            if not best_result:
                log.info('Rejected proper: {name}', {'name': cur_proper.name})
                if cur_proper.name not in processed_propers_names:
                    self.processed_propers.append({'name': cur_proper.name, 'date': cur_proper.date})
                continue

            # only get anime proper if it has release group and version
            if best_result.series.is_anime:
                if not best_result.release_group and best_result.version == -1:
                    log.info('Ignoring proper without release group and version: {name}', {'name': best_result.name})
                    if cur_proper.name not in processed_propers_names:
                        self.processed_propers.append({'name': cur_proper.name, 'date': cur_proper.date})
                    continue

            # check if we have the episode as DOWNLOADED
            main_db_con = db.DBConnection()
            sql_results = main_db_con.select('SELECT quality, release_name '
                                             'FROM tv_episodes WHERE indexer = ? '
                                             'AND showid = ? AND season = ? '
                                             'AND episode = ? AND status = ?',
                                             [best_result.indexer,
                                              best_result.series.indexerid,
                                              best_result.actual_season,
                                              best_result.actual_episodes[0],
                                              DOWNLOADED])
            if not sql_results:
                log.info("Ignoring proper because this episode doesn't have 'DOWNLOADED' status: {name}", {
                    'name': best_result.name
                })
                continue

            # only keep the proper if we have already downloaded an episode with the same quality
            old_quality = int(sql_results[0]['quality'])
            if old_quality != best_result.quality:
                log.info('Ignoring proper because quality is different: {name}', {'name': best_result.name})
                if cur_proper.name not in processed_propers_names:
                    self.processed_propers.append({'name': cur_proper.name, 'date': cur_proper.date})
                continue

            # only keep the proper if we have already downloaded an episode with the same codec
            release_name = sql_results[0]['release_name']
            if release_name:
                release_name_guess = NameParser()._parse_string(release_name)
                current_codec = release_name_guess.video_codec

                # Ignore proper if codec differs from downloaded release codec
                if all([current_codec, best_result.parse_result.video_codec,
                        best_result.parse_result.video_codec != current_codec]):
                    log.info('Ignoring proper because codec is different: {name}', {'name': best_result.name})
                    if best_result.name not in processed_propers_names:
                        self.processed_propers.append({'name': best_result.name, 'date': best_result.date})
                    continue

                streaming_service = release_name_guess.guess.get(u'streaming_service')
                # Ignore proper if streaming service differs from downloaded release streaming service
                if best_result.parse_result.guess.get(u'streaming_service') != streaming_service:
                    log.info('Ignoring proper because streaming service is different: {name}',
                             {'name': best_result.name})
                    if best_result.name not in processed_propers_names:
                        self.processed_propers.append({'name': best_result.name, 'date': best_result.date})
                    continue
            else:
                log.debug("Coudn't find a release name in database. Skipping codec comparison for: {name}", {
                    'name': best_result.name
                })

            # check if we actually want this proper (if it's the right release group and a higher version)
            if best_result.series.is_anime:
                main_db_con = db.DBConnection()
                sql_results = main_db_con.select(
                    'SELECT release_group, version '
                    'FROM tv_episodes WHERE indexer = ? AND showid = ? '
                    'AND season = ? AND episode = ?',
                    [best_result.indexer, best_result.series.indexerid, best_result.actual_season,
                     best_result.actual_episodes[0]])

                old_version = int(sql_results[0]['version'])
                old_release_group = (sql_results[0]['release_group'])

                if -1 < old_version < best_result.version:
                    log.info('Found new anime version {new} to replace existing version {old}: {name}',
                             {'old': old_version,
                              'new': best_result.version,
                              'name': best_result.name
                              })
                else:
                    log.info('Ignoring proper with the same or lower version: {name}', {'name': best_result.name})
                    if cur_proper.name not in processed_propers_names:
                        self.processed_propers.append({'name': best_result.name, 'date': best_result.date})
                    continue

                if old_release_group != best_result.release_group:
                    log.info('Ignoring proper from release group {new} instead of current group {old}',
                             {'new': best_result.release_group,
                              'old': old_release_group})
                    if best_result.name not in processed_propers_names:
                        self.processed_propers.append({'name': best_result.name, 'date': best_result.date})
                    continue

            # if the show is in our list and there hasn't been a proper already added for that particular episode
            # then add it to our list of propers
            if best_result.indexerid != -1 and (
                best_result.indexerid, best_result.actual_season, best_result.actual_episodes
            ) not in list(map(operator.attrgetter('indexerid', 'actual_season', 'actual_episodes'), final_propers)):
                log.info('Found a desired proper: {name}', {'name': best_result.name})
                final_propers.append(best_result)

            if best_result.name not in processed_propers_names:
                self.processed_propers.append({'name': best_result.name, 'date': best_result.date})

        return final_propers

    def _download_propers(self, proper_list):
        """
        Download proper (snatch it).

        :param proper_list:
        """
        for candidate in proper_list:

            history_limit = datetime.datetime.today() - datetime.timedelta(days=30)

            main_db_con = db.DBConnection()
            history_results = main_db_con.select(
                'SELECT resource, proper_tags FROM history '
                'WHERE showid = ? '
                'AND season = ? '
                'AND episode IN ({episodes}) '
                'AND quality = ? '
                'AND date >= ? '
                'AND action IN (?, ?, ?, ?)'.format(
                    episodes=','.join(
                        text_type(ep) for ep in candidate.actual_episodes
                    ),
                ),
                [candidate.indexerid, candidate.actual_season, candidate.quality,
                 history_limit.strftime(History.date_format),
                 DOWNLOADED, SNATCHED, SNATCHED_PROPER, SNATCHED_BEST])

            proper_tags_len = len(candidate.proper_tags)
            proper_name = self._canonical_name(candidate.name, clear_extension=True)
            proper_name_ext = self._canonical_name(candidate.name)

            for result in history_results:

                proper_tags = result['proper_tags']
                if proper_tags and len(proper_tags.split('|')) >= proper_tags_len:
                    log.debug(
                        'Current release has the same or more proper tags,'
                        ' skipping new proper {result!r}',
                        {'result': candidate.name},
                    )
                    break

                # make sure that none of the existing history downloads are the same proper we're
                # trying to downloadif the result exists in history already we need to skip it
                if proper_name == self._canonical_name(
                    result['resource'], clear_extension=True
                ) or proper_name_ext == self._canonical_name(result['resource']):
                    log.debug(
                        'This proper {result!r} is already in history, skipping it',
                        {'result': candidate.name},
                    )
                    break

            else:
                # snatch it
                snatch_result(candidate)

    @staticmethod
    def _canonical_name(name, clear_extension=False):
        ignore_list = {'website', 'mimetype', 'parsing_time'} | {'container'} if clear_extension else {}
        return helpers.canonical_name(name, ignore_list=ignore_list).lower()

    @staticmethod
    def _sanitize_name(name):
        return re.sub(r'[._\-]', ' ', name).lower()

    @staticmethod
    def _set_last_proper_search(when):
        """Record last propersearch in DB.

        :param when: When was the last proper search
        """
        log.debug('Setting the last Proper search in the DB to {when}', {'when': when})

        main_db_con = db.DBConnection()
        sql_results = main_db_con.select('SELECT last_proper_search FROM info')

        if not sql_results:
            main_db_con.action('INSERT INTO info (last_backlog, last_indexer, last_proper_search) VALUES (?,?,?)',
                               [0, 0, str(when)])
        else:
            main_db_con.action('UPDATE info SET last_proper_search={0}'.format(when))

    @staticmethod
    def _get_last_proper_search():
        """Find last propersearch from DB."""
        main_db_con = db.DBConnection()
        sql_results = main_db_con.select('SELECT last_proper_search FROM info')

        try:
            last_proper_search = datetime.date.fromordinal(int(sql_results[0]['last_proper_search']))
        except Exception:
            return datetime.date.fromordinal(1)

        return last_proper_search


class PostProcessQueue(generic_queue.GenericQueue):
    """Queue for queuing PostProcess queue objects."""

    def __init__(self):
        """Initialize the PostProcess queue object."""
        generic_queue.GenericQueue.__init__(self)
        self.queue_name = 'POSTPROCESSQUEUE'

    def is_in_queue(self, item):
        """
        Check if the postprocess job is in queue based on it's path and resource_name.

        :param item: New post-process queue item
        :type item: :class:`PostProcessQueueItem` object.

        :return: True or False
        """
        for queue_item in self.queue:
            if queue_item.path == item.path and queue_item.resource_name == item.resource_name:
                return True
        return False

    def is_running(self, item):
        """Check if the postprocess job is currently running based on its path and resource_name.

        :param item: New post-process queue item
        :type item: :class:`PostProcessQueueItem` object.

        :return: True or False
        """
        if not self.current_item:
            return False

        return item.path == self.current_item.path and item.resource_name == self.current_item.resource_name

    def queue_length(self):
        """
        Get the length of the current queue.

        :return: length of queue
        """
        return {'postprocess': len(self.queue)}

    def add_item(self, item):
        """
        Add a PostProcess queue item.

        :param item: PostProcess gueue object
        """
        if not self.is_in_queue(item) and not self.is_running(item):
            # Add PostProcessQueueItem item.
            generic_queue.GenericQueue.add_item(self, item)
        else:
            log.debug("Not adding item, it's already in the queue")


def fifo(my_list, item, max_size=100):
    """Append item to queue and limit it to 100 items."""
    if len(my_list) >= max_size:
        my_list.pop(0)
    my_list.append(item)
