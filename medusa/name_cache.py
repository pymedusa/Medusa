# coding=utf-8

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

from six import iteritems

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())

name_cache = {}
nameCacheLock = threading.Lock()


def addNameToCache(name, indexer_id=0):
    """
    Add the show & tvdb id to the scene_names table in cache.db.

    :param name: The show name to cache
    :param indexer_id: the TVDB id that this show should be cached with (can be None/0 for unknown)
    """
    cache_db_con = db.DBConnection('cache.db')

    # standardize the name we're using to account for small differences in providers
    name = full_sanitize_scene_name(name)
    if name not in name_cache:
        name_cache[name] = int(indexer_id)
        cache_db_con.action("INSERT OR REPLACE INTO scene_names (indexer_id, name) VALUES (?, ?)", [indexer_id, name])


def retrieveNameFromCache(name):
    """
    Look up the given name in the scene_names table in cache.db.

    :param name: The show name to look up.
    :return: the TVDB id that resulted from the cache lookup or None if the show wasn't found in the cache
    """
    name = full_sanitize_scene_name(name)
    if name in name_cache:
        return int(name_cache[name])


def clear_cache(indexerid=0):
    """Delete all "unknown" entries from the cache (names with indexer_id of 0)."""
    indexer_ids = (0, indexerid)
    cache_db_con = db.DBConnection('cache.db')
    cache_db_con.action(
        "DELETE FROM scene_names "
        "WHERE indexer_id = 0 OR"
        "    indexer_id = ?",
        [indexerid]
    )
    to_remove = {
        key
        for key, value in iteritems(name_cache)
        if value in indexer_ids
    }
    for key in to_remove:
        del name_cache[key]


def saveNameCacheToDb():
    """Commit cache to database file."""
    cache_db_con = db.DBConnection('cache.db')

    for name, indexer_id in iteritems(name_cache):
        cache_db_con.action("INSERT OR REPLACE INTO scene_names (indexer_id, name) VALUES (?, ?)", [indexer_id, name])


def build_name_cache(show=None):
    """Build internal name cache.

    :param show: Specify show to build name cache for, if None, just do all shows
    :param force: Force the build name cache. Do not depend on the scene_exception_refresh table.
    """
    def _cache_name(show):
        """Build the name cache for a single show."""
        indexer_id = show.indexerid
        clear_cache(indexer_id)

        scene_exceptions = exceptions_cache[indexer_id].copy()
        names = {
            full_sanitize_scene_name(name): int(indexer_id)
            for season_exceptions in scene_exceptions.values()
            for name in season_exceptions
        }
        # Add original name to name cache
        show_name = full_sanitize_scene_name(show.name)
        names[show_name] = indexer_id

        # Add scene exceptions to name cache
        name_cache.update(names)

        log.debug(u'Internal name cache for {show} set to: {names}',
                  {'show': show.name,
                   'names': names.keys()
                   })

    with nameCacheLock:
        retrieve_exceptions()

    # Create cache from db for the scene_exceptions.
    refresh_exceptions_cache()

    if not show:
        log.info(u'Building internal name cache for all shows')
        for show in app.showList:
            _cache_name(show)
    else:
        log.info(u'Building internal name cache for {show}', {'show': show.name})
        _cache_name(show)
