# coding=utf-8

from __future__ import unicode_literals

import logging
import threading
from builtins import object
from datetime import datetime
from functools import cmp_to_key
from uuid import uuid4


log = logging.getLogger()


class QueuePriorities(object):
    LOW = 10
    NORMAL = 20
    HIGH = 30


class GenericQueue(object):
    def __init__(self, max_history=100):
        self.currentItem = None
        self.queue = []
        self.history = []
        self.max_history = max_history
        self.queue_name = 'QUEUE'
        self.min_priority = 0
        self.lock = threading.Lock()
        self.amActive = False

    def pause(self):
        """Pauses this queue."""
        log.info(u'Pausing queue')
        self.min_priority = 999999999999

    def unpause(self):
        """Unpauses this queue."""
        log.info(u'Unpausing queue')
        self.min_priority = 0

    def add_item(self, item):
        """
        Adds an item to this queue

        :param item: Queue object to add
        :return: item
        """
        with self.lock:
            item.added = datetime.utcnow()
            self.queue.append(item)

            return item

    def run(self, force=False):
        """
        Process items in this queue

        :param force: Force queue processing (currently not implemented)
        """
        with self.lock:
            # only start a new task if one isn't already going
            if self.currentItem is None or not self.currentItem.is_alive():

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
                    fifo(self.history, self.currentItem, self.max_history)

        self.amActive = False


class QueueItem(threading.Thread):
    def __init__(self, name, action_id=0):
        super(QueueItem, self).__init__()
        self.name = name.replace(' ', '-').upper()
        self.inProgress = False
        self.priority = QueuePriorities.NORMAL
        self.action_id = action_id
        self.stop = threading.Event()
        self.added = None
        self.queue_time = datetime.utcnow()
        self.start_time = None
        self.success = None
        self._to_json = {
            'identifier': str(uuid4()),
            'name': self.name,
            'priority': self.priority,
            'actionId': self.action_id,
            'queueTime': str(self.queue_time),
            'success': self.success
        }

    def run(self):
        """Implementing classes should call this."""
        self.inProgress = True
        self.start_time = datetime.utcnow()

    def finish(self):
        """Implementing Classes should call this."""
        self.inProgress = False
        threading.currentThread().name = self.name

    @property
    def to_json(self):
        """Update queue item JSON representation."""
        self._to_json.update({
            'inProgress': self.inProgress,
            'startTime': str(self.start_time) if self.start_time else None,
            'updateTime': str(datetime.utcnow()),
            'success': self.success
        })
        return self._to_json


def fifo(my_list, item, max_size=100):
    """Append item to queue and limit it to 100 items."""
    if len(my_list) >= max_size:
        my_list.pop(0)
    my_list.append(item)
