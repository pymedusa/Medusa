# coding=utf-8

from medusa import app
from medusa.event_queue import Events


class Restart(object):
    def __init__(self):
        pass

    @staticmethod
    def restart(pid):
        if str(pid) != str(app.PID):
            return False

        app.events.put(Events.SystemEvent.RESTART)

        return True
