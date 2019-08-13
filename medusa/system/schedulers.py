# coding=utf-8
"""Helper functions to get info about running schedulers."""
from __future__ import unicode_literals

from medusa import app
from medusa.generic_queue import QueuePriorities
from medusa.helpers.utils import timedelta_in_milliseconds
from medusa.show_queue import ShowQueueActions


all_schedulers = [
    ('dailySearch', 'Daily Search', 'daily_search_scheduler'),
    ('backlog', 'Backlog', 'backlog_search_scheduler'),
    ('showUpdate', 'Show Update', 'show_update_scheduler'),
    ('versionCheck', 'Version Check', 'version_check_scheduler'),
    ('showQueue', 'Show Queue', 'show_queue_scheduler'),
    ('searchQueue', 'Search Queue', 'search_queue_scheduler'),
    ('properFinder', 'Proper Finder', 'proper_finder_scheduler'),
    ('postProcess', 'Post Process', 'post_processor_scheduler'),
    ('subtitlesFinder', 'Subtitles Finder', 'subtitles_finder_scheduler'),
    ('traktChecker', 'Trakt Checker', 'trakt_checker_scheduler'),
    ('torrentChecker', 'Torrent Checker', 'torrent_checker_scheduler'),
]


def _is_enabled(key, scheduler):
    if key == 'backlog' and app.search_queue_scheduler.action.is_backlog_paused():
        return 'Paused'

    return bool(scheduler.enable)


def _is_active(key, scheduler):
    if key == 'backlog' and app.search_queue_scheduler.action.is_backlog_in_progress():
        return True

    try:
        return bool(scheduler.action.amActive)
    except AttributeError:
        return None


def _scheduler_to_json(key, name, scheduler):
    scheduler = getattr(app, scheduler)
    if not scheduler:
        # Not initialized
        return {
            'key': key,
            'name': name,
        }

    return {
        'key': key,
        'name': name,
        'isAlive': scheduler.is_alive(),
        'isEnabled': _is_enabled(key, scheduler),
        'isActive': _is_active(key, scheduler),
        'startTime': scheduler.start_time.isoformat() if scheduler.start_time else None,
        'cycleTime': timedelta_in_milliseconds(scheduler.cycleTime) or None,
        'nextRun': timedelta_in_milliseconds(scheduler.timeLeft()) if scheduler.enable else None,
        'lastRun': scheduler.lastRun.isoformat(),
        'isSilent': bool(scheduler.silent)
    }


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
            show_dir = item.showDir

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
        'added': item.added.isoformat(),
        'queueType': ShowQueueActions.names[item.action_id],
    }


def generate_schedulers():
    """
    Generate a JSON-pickable list of scheduler dictionaries.

    :returns: list of scheduler dictionaries
    """
    return [_scheduler_to_json(*scheduler) for scheduler in all_schedulers]


def scheduler_by_key(key):
    """
    Get a JSON-pickable scheduler dictionary by its key.

    :param key: the key of the scheduler to get
    :returns: a scheduler dictionary
    :raises KeyError: if the scheduler could not be found
    """
    try:
        scheduler_tuple = next(item for item in all_schedulers if item[0] == key)
    except StopIteration:
        raise KeyError('Scheduler not found')

    return _scheduler_to_json(*scheduler_tuple)


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
