# coding=utf-8
import threading
import traceback

from sickrage.helper.exceptions import ex
from six.moves.queue import Empty, Queue
from . import logger


class Event(object):
    def __init__(self, event_type):
        self._type = event_type

    @property
    def event_type(self):
        """
        Returns the type of the event
        """

        return self._type


class Events(threading.Thread):
    def __init__(self, callback):
        super(Events, self).__init__()
        self.queue = Queue()
        self.daemon = True
        self.callback = callback
        self.name = "EVENT-QUEUE"
        self.stop = threading.Event()

    def put(self, event_type):
        self.queue.put(event_type)

    def run(self):
        """
        Actually runs the thread to process events
        """
        try:
            while not self.stop.is_set():
                try:
                    # get event type
                    event_type = self.queue.get(True, 1)

                    # perform callback if we got a event type
                    self.callback(event_type)

                    # event completed
                    self.queue.task_done()
                except Empty:
                    event_type = None

            # exiting thread
            self.stop.clear()
        except Exception as e:
            logger.log(u"Exception generated in thread " + self.name + ": " + ex(e), logger.ERROR)
            logger.log(repr(traceback.format_exc()), logger.DEBUG)

    # System Events
    class SystemEvent(Event):
        RESTART = "RESTART"
        SHUTDOWN = "SHUTDOWN"
