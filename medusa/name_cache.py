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
from .scene_exceptions import get_scene_exceptions, get_scene_seasons, retrieve_exceptions

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
    cache_db_con = db.DBConnection('cache.db')
    cache_db_con.action("DELETE FROM scene_names WHERE indexer_id = ? OR indexer_id = ?", (indexerid, 0))

    toRemove = [key for key, value in iteritems(name_cache) if value == 0 or value == indexerid]
    for key in toRemove:
        del name_cache[key]


def saveNameCacheToDb():
    """Commit cache to database file."""
    cache_db_con = db.DBConnection('cache.db')

    for name, indexer_id in iteritems(name_cache):
        cache_db_con.action("INSERT OR REPLACE INTO scene_names (indexer_id, name) VALUES (?, ?)", [indexer_id, name])


def build_name_cache(show=None):
    """Build internal name cache

    :param show: Specify show to build name cache for, if None, just do all shows
    """
    def _cache_name(show):
        """Builds the name cache for a single show."""
        clear_cache(show.indexerid)
        for season in [-1] + get_scene_seasons(show.indexerid):
            for name in set(get_scene_exceptions(show.indexerid, season=season) + [show.name]):
                name = full_sanitize_scene_name(name)
                if name in name_cache:
                    continue
                name_cache[name] = int(show.indexerid)
        logger.log(u'Internal name cache for {show.name} set to: [{names}]'.format(
            show=show,
            names=u', '.join([key for key, value
                              in iteritems(name_cache)
                              if value == show.indexerid])
        ), logger.DEBUG)

    with nameCacheLock:
        retrieve_exceptions()

    if not show:
        # logger.log(u"Building internal name cache for all shows", logger.INFO)
        for show in app.showList:
            _cache_name(show)
    else:
        # logger.log(u"Building internal name cache for " + show.name, logger.DEBUG)
        _cache_name(show)
