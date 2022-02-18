# coding=utf-8

from __future__ import unicode_literals

from medusa import app
from medusa.queues.event_queue import Events

from six import text_type


class Restart(object):
    def __init__(self):
        pass

    @staticmethod
    def restart(pid):
        if text_type(pid) != text_type(app.PID):
            return False

        app.events.put(Events.SystemEvent.RESTART)

        return True
