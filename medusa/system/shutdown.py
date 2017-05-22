# coding=utf-8

from medusa import app
from medusa.event_queue import Events


class Shutdown(object):
    def __init__(self):
        pass

    @staticmethod
    def stop(pid):
        if str(pid) != str(app.PID):
            return False

        app.events.put(Events.SystemEvent.SHUTDOWN)

        return True
