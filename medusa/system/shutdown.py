# coding=utf-8

from __future__ import unicode_literals

from builtins import object
from builtins import str

from medusa import app
from medusa.queues.event_queue import Events


class Shutdown(object):
    def __init__(self):
        pass

    @staticmethod
    def stop(pid):
        if str(pid) != str(app.PID):
            return False

        app.events.put(Events.SystemEvent.SHUTDOWN)

        return True
