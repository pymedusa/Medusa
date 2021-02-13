# coding=utf-8

from __future__ import division
from __future__ import unicode_literals

import datetime
import logging
import threading
import time

from medusa import exception_handler
from medusa.logger.adapters.style import BraceAdapter

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class Scheduler(threading.Thread):
    def __init__(self, action, cycleTime=datetime.timedelta(minutes=10), start_time=None,
                 threadName='ScheduledThread', silent=True):
        super(Scheduler, self).__init__()

        self.action = action
        self.cycleTime = cycleTime if start_time is None else datetime.timedelta(days=1)
        self.start_time = start_time

        self.lastRun = datetime.datetime.now()
        self.name = threadName
        self.silent = silent
        self.stop = threading.Event()
        self.force = False
        self.enable = False

    def timeLeft(self):
        """
        Check how long we have until we run again.

        :return: timedelta
        """
        if self.is_alive():
            if self.start_time is None:
                return self.cycleTime - (datetime.datetime.now() - self.lastRun)
            else:
                last_run = self.lastRun
                start_time_next = datetime.datetime.combine(last_run.date(), self.start_time)
                if last_run > start_time_next:
                    start_time_next += self.cycleTime

                return start_time_next - datetime.datetime.now()
        else:
            return datetime.timedelta(seconds=0)

    def forceRun(self):
        if not self.action.amActive:
            self.force = True
            return True
        return False

    def run(self):
        """Run the thread."""
        try:
            while not self.stop.is_set():
                if self.enable:
                    should_run = False
                    time_left = self.timeLeft()

                    # Is self.force enable
                    if self.force:
                        should_run = True

                    # check if interval has passed
                    elif time_left.total_seconds() <= 0:
                        should_run = True

                    if should_run:
                        if not self.silent:
                            log.debug('Starting new thread: {name}', {'name': self.name})
                        self.action.run(self.force)
                        self.lastRun = datetime.datetime.now()

                    if self.force:
                        self.force = False

                time.sleep(1)
            # exiting thread
            self.stop.clear()
        except Exception as e:
            exception_handler.handle(e)
