# coding=utf-8

"""Daily searcher module."""

from __future__ import unicode_literals

import logging
import threading
from builtins import object
from time import time

from medusa import app
from medusa.logger.adapters.style import BraceAdapter
from medusa.search.queue import DailySearchQueueItem

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class DailySearcher(object):
    """Daily search class."""

    def __init__(self):
        """Initialize the class."""
        self.lock = threading.Lock()
        self.amActive = False

    def run(self, force=False):
        """
        Run the daily searcher, queuing selected episodes for search.

        :param force: Force search
        """
        if self.amActive:
            log.debug('Daily search is still running, not starting it again')
            return
        elif app.forced_search_queue_scheduler.action.is_forced_search_in_progress() and not force:
            log.warning('Manual search is running. Unable to start Daily search')
            return

        self.amActive = True
        # Let's keep track of the exact time the scheduler kicked in,
        # as we need to compare to this time for each provider.
        scheduler_start_time = int(time())

        # queue a daily search
        app.search_queue_scheduler.action.add_item(
            DailySearchQueueItem(scheduler_start_time, force=force)
        )

        self.amActive = False
