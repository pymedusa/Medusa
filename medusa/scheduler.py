# coding=utf-8

from __future__ import unicode_literals

import datetime
import logging
from threading import Event, Thread

from medusa.logger.adapters.style import BraceAdapter

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class Scheduler(Thread):
    def __init__(self, action, cycleTime=None, start_time=None, threadName=None, silent=True):
        Thread.__init__(self)

        self.action = action
        self.cycleTime = cycleTime if start_time is None else datetime.timedelta(days=1)
        self.start_time = start_time
        self.name = threadName or 'ScheduledThread'
        self.silent = silent

        self.stopped = Event()
        self.lastRun = None
        self.enable = False

    def timeLeft(self):
        """
        Check how long we have until we run again.

        :return: timedelta
        """
        if self.start_time is None:
            return self.cycleTime - (datetime.datetime.now() - self.lastRun)
        else:
            time_now = datetime.datetime.now()
            start_time_today = datetime.datetime.combine(time_now.date(), self.start_time)
            if time_now >= start_time_today:
                start_time_tomorrow = start_time_today + datetime.timedelta(days=1)
                return start_time_tomorrow - time_now
            else:
                return start_time_today - time_now

    def forceRun(self):
        if not self.action.amActive:
            self.run(force=True)
            return True
        return False

    def run(self, force=False):
        if not self.lastRun:
            self.lastRun = datetime.datetime.now()
        while force or not self.stopped.wait(self.cycleTime.total_seconds()):
            self.action.run(force)
            if force:
                force = False
            else:
                self.lastRun = datetime.datetime.now()

    def stop(self):
        self.stopped.set()
        self.join()
