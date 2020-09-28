# coding=utf-8
"""Helper functions to get info about running schedulers."""
from __future__ import unicode_literals

from medusa import app
from medusa.helpers.utils import timedelta_in_milliseconds


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
