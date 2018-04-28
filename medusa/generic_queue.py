# coding=utf-8

from __future__ import unicode_literals

import datetime
import logging
import threading
from builtins import object
from functools import cmp_to_key

log = logging.getLogger()


class QueuePriorities(object):
    LOW = 10
    NORMAL = 20
    HIGH = 30


class GenericQueue(object):
    def __init__(self):
        self.currentItem = None
        self.queue = []
        self.queue_name = "QUEUE"
        self.min_priority = 0
        self.lock = threading.Lock()
        self.amActive = False

    def pause(self):
        """Pauses this queue."""
        log.info(u"Pausing queue")
        self.min_priority = 999999999999

    def unpause(self):
        """Unpauses this queue."""
        log.info(u"Unpausing queue")
        self.min_priority = 0

    def add_item(self, item):
        """
        Adds an item to this queue

        :param item: Queue object to add
        :return: item
        """
        with self.lock:
            item.added = datetime.datetime.now()
            self.queue.append(item)

            return item

    def run(self, force=False):
        """
        Process items in this queue

        :param force: Force queue processing (currently not implemented)
        """
        with self.lock:
            # only start a new task if one isn't already going
            if self.currentItem is None or not self.currentItem.isAlive():

                # if the thread is dead then the current item should be
                # finished
                if self.currentItem:
                    self.currentItem.finish()
                    self.currentItem = None

                # if there's something in the queue then run it in a thread
                # and take it out of the queue
                if self.queue:

                    # sort by priority
                    def sorter(x, y):
                        """
                        Sorts by priority descending then time ascending
                        """
                        if x.priority == y.priority:
                            if y.added == x.added:
                                return 0
                            elif y.added < x.added:
                                return 1
                            elif y.added > x.added:
                                return -1
                        else:
                            return y.priority - x.priority

                    self.queue.sort(key=cmp_to_key(sorter))
                    if self.queue[0].priority < self.min_priority:
                        return

                    # launch the queue item in a thread
                    self.currentItem = self.queue.pop(0)
                    self.currentItem.name = u'{queue}-{item}'.format(
                        queue=self.queue_name,
                        item=self.currentItem.name,
                    )
                    self.currentItem.start()

        self.amActive = False


class QueueItem(threading.Thread):
    def __init__(self, name, action_id=0):
        super(QueueItem, self).__init__()
        self.name = name.replace(" ", "-").upper()
        self.inProgress = False
        self.priority = QueuePriorities.NORMAL
        self.action_id = action_id
        self.stop = threading.Event()
        self.added = None

    def run(self):
        """Implementing classes should call this."""
        self.inProgress = True

    def finish(self):
        """Implementing Classes should call this."""
        self.inProgress = False
        threading.currentThread().name = self.name
