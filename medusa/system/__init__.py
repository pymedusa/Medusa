# coding=utf-8

import logging

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def add_action(app, queue, pid, action):
    """Perform a system action."""
    if str(pid) != str(app.PID):
        msg = u'Incorrect PID, could not add {action} to {queue}. '
        log.debug(msg.format(action=action, queue=queue))
        result = False
    else:
        queue.put(action)
        msg = u'Adding {action} to {queue}'
        log.debug(msg.format(action=action, queue=queue))
        result = True
    return result


def restart(app, queue, pid):
    """Restart the application."""
    return add_action(app, queue, pid, 'RESTART')


def shutdown(app, queue, pid):
    """Shutdown the application."""
    return add_action(app, queue, pid, 'SHUTDOWN')
