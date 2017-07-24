# coding=utf-8
# Author: Nic Wolfe <nic@wolfeden.ca>

#
# This file is part of Medusa.
#
# Medusa is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Medusa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Medusa. If not, see <http://www.gnu.org/licenses/>.

import threading

from six import iteritems
from . import app, db, logger
from .helpers import full_sanitize_scene_name
from .scene_exceptions import (
    exceptions_cache,
    refresh_exceptions_cache,
    retrieve_exceptions,
)

name_cache = {}
nameCacheLock = threading.Lock()


def addNameToCache(name, indexer_id=0):
    """
    Adds the show & tvdb id to the scene_names table in cache.db.

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
    Looks up the given name in the scene_names table in cache.db.

    :param name: The show name to look up.
    :return: the TVDB id that resulted from the cache lookup or None if the show wasn't found in the cache
    """
    name = full_sanitize_scene_name(name)
    if name in name_cache:
        return int(name_cache[name])


def clear_cache(indexerid=0):
    """
    Deletes all "unknown" entries from the cache (names with indexer_id of 0).
    """
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
    """Build internal name cache

    :param show: Specify show to build name cache for, if None, just do all shows
    :param force: Force the build name cache. Do not depend on the scene_exception_refresh table.
    """
    def _cache_name(show):
        """Builds the name cache for a single show."""
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

        logger.log(u'Internal name cache for {show} set to: {names}'.format(
            show=show.name,
            names=', '.join(names.keys())
        ), logger.DEBUG)

    with nameCacheLock:
        retrieve_exceptions()

    # Create cache from db for the scene_exceptions.
    refresh_exceptions_cache()

    if not show:
        logger.log(u'Building internal name cache for all shows', logger.INFO)
        for show in app.showList:
            _cache_name(show)
    else:
        logger.log(u'Building internal name cache for {show}'.format(show=show.name), logger.DEBUG)
        _cache_name(show)
