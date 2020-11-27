# coding=utf-8
"""Helper functions to get info about queues."""
from __future__ import unicode_literals

from medusa import app
from medusa.helpers import get_disk_space_usage
from medusa.queues.generic_queue import QueuePriorities
from medusa.queues.show_queue import ShowQueueActions
from medusa.sbdatetime import sbdatetime


def _queued_show_to_json(item):
    try:
        show_slug = item.show.slug
    except AttributeError:
        show_slug = None

    show_title = None
    show_dir = None
    try:
        show_title = item.show.name
    except AttributeError:
        if item.action_id == ShowQueueActions.ADD:
            show_dir = item.show_dir

    if item.priority == QueuePriorities.LOW:
        priority = 'low'
    elif item.priority == QueuePriorities.NORMAL:
        priority = 'normal'
    elif item.priority == QueuePriorities.HIGH:
        priority = 'high'
    else:
        priority = item.priority

    return {
        'showSlug': show_slug,
        'showTitle': show_title,
        'showDir': show_dir,
        'inProgress': bool(item.inProgress),
        'priority': priority,
        'added': sbdatetime.convert_to_setting(item.added.replace(microsecond=0)).isoformat(),
        'queueType': ShowQueueActions.names[item.action_id],
    }


def generate_show_queue():
    """
    Generate a JSON-pickable list of items in the show queue.

    :returns: list of show queue items
    """
    if not app.show_queue_scheduler:
        return []

    # Make a shallow copy of the current queue.
    queue = []
    queue.extend(app.show_queue_scheduler.action.queue)
    if app.show_queue_scheduler.action.currentItem is not None:
        queue.insert(0, app.show_queue_scheduler.action.currentItem)

    return [_queued_show_to_json(item) for item in queue]


def generate_location_disk_space():
    """
    Generate a JSON-pickable object with disk space information.

    Collect information on the TV_DOWNLOAD_DIR and the ROOT_DIRS.
    :returns: Object with disk space information.
    """
    locations = {}
    locations['tvDownloadDir'] = {
        'type': 'TV Download Directory',
        'location': app.TV_DOWNLOAD_DIR,
        'freeSpace': get_disk_space_usage(app.TV_DOWNLOAD_DIR)
    }

    locations['rootDir'] = []
    if app.ROOT_DIRS:
        backend_pieces = app.ROOT_DIRS
        backend_dirs = backend_pieces[1:]
    else:
        backend_dirs = []

    if backend_dirs:
        for location in backend_dirs:
            locations['rootDir'].append({
                'type': 'Media Root Directory',
                'location': location,
                'freeSpace': get_disk_space_usage(location)
            })

    return locations
