# coding=utf-8

"""Name cache module."""
from __future__ import unicode_literals

import logging
import threading

from medusa import app, db
from medusa.helpers import full_sanitize_scene_name
from medusa.logger.adapters.style import BraceAdapter
from medusa.scene_exceptions import (
    exceptions_cache,
    refresh_exceptions_cache,
    retrieve_exceptions,
)

from six import iteritems, itervalues

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())

name_cache = {}
nameCacheLock = threading.Lock()


def addNameToCache(name, indexer_id=1, show_id=0):
    """
    Add the show & tvdb id to the scene_names table in cache.db.

    :param name: The show name to cache
    :param indexer_id: the indexer's id.
    :param show_id: the TVDB id that this show should be cached with (can be None/0 for unknown)
    """
    cache_db_con = db.DBConnection('cache.db')

    # standardize the name we're using to account for small differences in providers
    name = full_sanitize_scene_name(name)
    if name not in name_cache:
        name_cache[name] = (indexer_id, show_id)
        cache_db_con.action('INSERT OR REPLACE INTO scene_names (indexer_id, name, indexer) VALUES (?, ?, ?)', [show_id, name, indexer_id])


def retrieveNameFromCache(name):
    """
    Look up the given name in the scene_names table in cache.db.

    :param name: The show name to look up.
    :return: Return a tuple with two items. First: indexer_id, Second: show_id.
    """
    name = full_sanitize_scene_name(name)
    if name in name_cache:
        return name_cache[name]
    return None, None


def clear_cache(indexer_id=0, show_id=0):
    """Delete all "unknown" entries from the cache (names with indexer_id (show_id) of 0)."""
    indexer_ids = (0, indexer_id)
    show_ids = (0, show_id)
    cache_db_con = db.DBConnection('cache.db')
    cache_db_con.action(
        "DELETE FROM scene_names "
        "WHERE (indexer_id = 0 AND indexer = ?) OR"
        "      (indexer_id = ? AND indexer = ?) ",
        [show_id, indexer_id, show_id]
    )

    keys = []
    for key, value in iteritems(name_cache):
        i_id, s_id = value
        if i_id in indexer_ids and s_id in show_ids:
            keys.append(key)

    for key in keys:
        del name_cache[key]


def saveNameCacheToDb():
    """Commit cache to database file."""
    cache_db_con = db.DBConnection('cache.db')

    for name, show in iteritems(name_cache):
        indexer_id, show_id = show
        cache_db_con.action("INSERT OR REPLACE INTO scene_names (indexer_id, name, indexer) VALUES (?, ?, ?)", [show_id, name, indexer_id])


def build_name_cache(show_obj=None):
    """Build internal name cache.

    :param show_obj: Specify show to build name cache for, if None, just do all show
    :param force: Force the build name cache. Do not depend on the scene_exception_refresh table.
    """
    def _cache_name(cache_show_obj):
        """Build the name cache for a single show."""
        clear_cache(cache_show_obj.indexer, cache_show_obj.show_id)

        show_identifier = (cache_show_obj.indexer, cache_show_obj.show_id)
        scene_exceptions = exceptions_cache[show_identifier].copy()
        names = {
            full_sanitize_scene_name(name): show_identifier
            for season_exceptions in itervalues(scene_exceptions)
            for name in season_exceptions
        }
        # Add original name to name cache
        show_name = full_sanitize_scene_name(cache_show_obj.name)
        names[show_name] = show_identifier

        # Add scene exceptions to name cache
        name_cache.update(names)

        log.debug(u'Internal name cache for {show} set to: {names}', {
            'show': show_name,
            'names': u', '.join(list(names))
        })

    with nameCacheLock:
        retrieve_exceptions()

    # Create cache from db for the scene_exceptions.
    refresh_exceptions_cache()

    if not show_obj:
        log.info(u'Building internal name cache for all shows')
        for show in app.showList:
            _cache_name(show)
    else:
        log.info(u'Building internal name cache for {show}', {'show': show_obj.name})
        _cache_name(show_obj)
