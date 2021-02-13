# coding=utf-8

"""Proper finder module."""

from __future__ import unicode_literals

import logging
from builtins import object

from medusa import app
from medusa.logger.adapters.style import BraceAdapter
from medusa.search.queue import ProperSearchQueueItem


log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class ProperFinder(object):  # pylint: disable=too-few-public-methods
    """Proper finder class used by the proper_finder_scheduler."""

    def __init__(self):
        """Initialize the class."""
        self.amActive = False
        self.processed_propers = []
        self.ignore_processed_propers = False

    def run(self, force=False):  # pylint: disable=unused-argument
        """
        Start looking for new propers.

        :param force: Start even if already running (currently not used, defaults to False)
        """
        log.info('Beginning the search for new propers')

        if self.amActive:
            log.debug('Find propers is still running, not starting it again')
            return

        if app.forced_search_queue_scheduler.action.is_forced_search_in_progress():
            log.warning("Manual search is running. Can't start Find propers")
            return

        # queue a forced search
        app.search_queue_scheduler.action.add_item(
            ProperSearchQueueItem(
                force=force,
                processed_propers=self.processed_propers,
                ignore_processed_propers=self.ignore_processed_propers
            )
        )
