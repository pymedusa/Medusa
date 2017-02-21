# coding=utf-8
# Author: Nic Wolfe <nic@wolfeden.ca>
#
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

from __future__ import unicode_literals

import logging
import threading
import time
import warnings
from collections import defaultdict

import adba
from medusa.indexers.indexer_api import indexerApi
from six import iteritems
from . import app, db, helpers
from .indexers.indexer_config import INDEXER_TVDBV2

logger = logging.getLogger(__name__)

exceptions_cache = defaultdict(lambda: defaultdict(set))
exceptionLock = threading.Lock()

xem_session = helpers.make_session()

# TODO: Fix multiple indexer support


def refresh_exceptions_cache():
    """Query the db for show exceptions and update the exceptions_cache."""
    logger.info('Updating exception_cache and exception_season_cache')

    # Empty the module level variables
    exceptions_cache.clear()

    cache_db_con = db.DBConnection('cache.db')
    exceptions = cache_db_con.select(
        b'SELECT indexer, indexer_id, show_name, season '
        b'FROM scene_exceptions'
    ) or []

    # Start building up a new exceptions_cache.
    for exception in exceptions:
        # indexer = int(exception[b'indexer'])
        indexer_id = int(exception[b'indexer_id'])
        season = int(exception[b'season'])
        show = exception[b'show_name']

        # exceptions_cache[indexerid][season] = ['showname 1', 'showname 2']
        if show not in exceptions_cache[indexer_id][season]:
            exceptions_cache[indexer_id][season].add(show)

    logger.info('Finished processing {x} scene exceptions.', x=len(exceptions))


def get_last_refresh(ex_list):
    """Get the last update timestamp for the specific scene exception list."""
    cache_db_con = db.DBConnection('cache.db')
    return cache_db_con.select(b'SELECT last_refreshed FROM scene_exceptions_refresh WHERE list = ?', [ex_list])


def should_refresh(ex_list):
    """
    Check if we should refresh cache for items in ex_list.

    :param ex_list: exception list to check if exception needs a refresh
    :return: True if refresh is needed
    """
    max_refresh_age_secs = 86400  # 1 day
    rows = get_last_refresh(ex_list)

    if rows:
        last_refresh = int(rows[0][b'last_refreshed'])
        return int(time.time()) > last_refresh + max_refresh_age_secs
    else:
        return True


def set_last_refresh(source):
    """
    Update last cache update time for shows in list.

    :param source: scene exception source refreshed (e.g. xem)
    """
    cache_db_con = db.DBConnection('cache.db')
    cache_db_con.upsert(
        b'scene_exceptions_refresh',
        {b'last_refreshed': int(time.time())},
        {b'list': source}
    )


def get_scene_exceptions(indexer_id, indexer, season=-1):
    """Get scene exceptions from exceptions_cache for an indexer id."""
    exceptions_list = exceptions_cache[indexer_id][season]

    if season != -1 and not exceptions_list:
        exceptions_list = get_scene_exceptions(indexer_id, indexer)

    # Return a set to avoid duplicates and it makes a copy of the list so the
    # original doesn't get modified
    return set(exceptions_list)


def get_all_scene_exceptions(indexer_id):
    """
    Get all scene exceptions for a show ID.

    :param indexer_id: ID to check
    :return: dict of exceptions (e.g. exceptions_cache[season][exception_name])
    """
    return exceptions_cache.get(int(indexer_id), defaultdict(set))


def get_scene_seasons(indexer_id):
    """
    Get season numbers with scene exceptions.

    :param indexer_id: ID to check
    :return: list of seasons.
    """
    warnings.warn('Use dict.keys() directly instead.', DeprecationWarning)
    return exceptions_cache[int(indexer_id)].keys()


def get_scene_exception_by_name(show_name):
    """Get the first indexer_id and season of the scene exception."""
    warnings.warn(
        'Use the first element of get_scene_exceptions_by_name instead.',
        DeprecationWarning,
    )
    return get_scene_exceptions_by_name(show_name)[0]


def get_scene_exceptions_by_name(show_name):
    """Get the indexer_id and season of the scene exception."""
    # TODO: Rewrite to use exceptions_cache since there is no need to hit db.
    # Try the obvious case first
    cache_db_con = db.DBConnection('cache.db')
    scene_exceptions = cache_db_con.select(
        b'SELECT indexer_id, season '
        b'FROM scene_exceptions '
        b'WHERE show_name = ? ORDER BY season ASC',
        [show_name])
    if scene_exceptions:
        return [(int(exception[b'indexer_id']), int(exception[b'season']))
                for exception in scene_exceptions]

    result = []
    scene_exceptions = cache_db_con.select(
        b'SELECT show_name, indexer_id, season '
        b'FROM scene_exceptions'
    )

    for exception in scene_exceptions:
        indexer_id = int(exception[b'indexer_id'])
        exception_name = exception[b'show_name']

        sanitized_name = helpers.sanitize_scene_name(exception_name)
        show_names = (
            exception_name.lower(),
            sanitized_name.lower().replace('.', ' '),
        )

        if show_name.lower() in show_names:
            logger.debug(
                'Scene exception lookup got indexer ID {cur_indexer},'
                ' using that', cur_indexer=indexer_id
            )
            result.append((indexer_id, int(exception[b'season'])))

    return result or [(None, None)]


def update_scene_exceptions(indexer_id, indexer, scene_exceptions, season=-1):
    """Update database with all show scene exceptions by indexer_id."""
    logger.info('Updating scene exceptions...')

    cache_db_con = db.DBConnection('cache.db')
    cache_db_con.action(
        b'DELETE FROM scene_exceptions '
        b'WHERE indexer_id=? and '
        b'    season=? and '
        b'    indexer=?',
        [indexer_id, season, indexer]
    )

    # A change has been made to the scene exception list.
    # Let's clear the cache, to make this visible
    # TODO: make sure we add indexer when the exceptions_cache changes
    exceptions_cache[indexer_id].clear()

    decoded_scene_exceptions = (
        exception.decode('utf-8')
        for exception in scene_exceptions
    )
    for exception in decoded_scene_exceptions:
        if exception not in exceptions_cache[indexer_id][season]:
            # Add to cache
            exceptions_cache[indexer_id][season].add(exception)

            # Add to db
            cache_db_con.action(
                b'INSERT INTO scene_exceptions '
                b'    (indexer_id, show_name, season, indexer)'
                b'VALUES (?,?,?,?)',
                [indexer_id, exception, season, indexer]
            )


def retrieve_exceptions(force=False):
    """
    Look up the exceptions from all sources.

    Parses the exceptions into a dict, and inserts them into the
    scene_exceptions table in cache.db. Also clears the scene name cache.
    :param force: If enabled this will force the refresh of scene exceptions using the medusa exceptions,
    xem exceptions and anidb exceptions.
    """
    # Combined scene exceptions from all sources
    combined_exceptions = combine_exceptions(
        # Custom scene exceptions
        _get_custom_exceptions(force),
        # XEM scene exceptions
        _get_xem_exceptions(force),
        # AniDB scene exceptions
        _get_anidb_exceptions(force),
    )

    queries = []
    cache_db_con = db.DBConnection('cache.db')

    # TODO: See if this can be optimized
    for indexer in combined_exceptions:
        for indexer_id in combined_exceptions[indexer]:
            sql_ex = cache_db_con.select(
                b'SELECT show_name, indexer '
                b'FROM scene_exceptions '
                b'WHERE indexer = ? AND '
                b'    indexer_id = ?',
                [indexer, indexer_id]
            )
            existing_exceptions = [x[b'show_name'] for x in sql_ex]

            for exception_dict in combined_exceptions[indexer][indexer_id]:
                for scene_exception, season in iteritems(exception_dict):
                    if scene_exception not in existing_exceptions:
                        queries.append([
                            b'INSERT OR IGNORE INTO scene_exceptions'
                            b'(indexer, indexer_id, show_name, season)'
                            b'VALUES (?,?,?,?)',
                            [indexer, indexer_id, scene_exception, season]
                        ])
    if queries:
        cache_db_con.mass_action(queries)
        logger.info('Updated scene exceptions.')


def combine_exceptions(*scene_exceptions):
    """Combine the exceptions from all sources."""
    # ex_dicts = iter(scene_exceptions)
    combined_ex = defaultdict(dict)

    for scene_exception in scene_exceptions:
        for indexer in scene_exception or []:
            combined_ex[indexer].update(scene_exception[indexer])

    return combined_ex


def _get_custom_exceptions(force):
    custom_exceptions = defaultdict(dict)

    if should_refresh('custom_exceptions') or force:
        for indexer in indexerApi().indexers:
            try:
                location = indexerApi(indexer).config['scene_loc']
                logger.info(
                    'Checking for scene exception updates from {location}',
                    location=location
                )

                response = helpers.get_url(
                    location,
                    session=indexerApi(indexer).session,
                    timeout=60,
                    returns='response'
                )
                try:
                    jdata = response.json()
                except (ValueError, AttributeError) as error:
                    logger.debug(
                        'Check scene exceptions update failed. Unable to '
                        'update from {location}. Error: {error}'.format(
                            location=location, error=error
                        )
                    )
                    return custom_exceptions

                indexer_ids = jdata[indexerApi(indexer).config['identifier']]
                for indexer_id in indexer_ids:
                    indexer_exceptions = indexer_ids[indexer_id]
                    alias_list = [{exception: int(season)}
                                  for season in indexer_exceptions
                                  for exception in indexer_exceptions[season]]
                    custom_exceptions[indexer][indexer_id] = alias_list
            except Exception as error:
                logger.error(
                    'Unable to update scene exceptions for {indexer}.'
                    ' Error: {error}'.format(
                        indexer=indexer, error=error
                    )
                )
                continue

            set_last_refresh('custom_exceptions')

    return custom_exceptions


def _get_xem_exceptions(force):
    xem_exceptions = defaultdict(dict)
    xem_url = 'http://thexem.de/map/allNames?origin={0}&seasonNumbers=1'

    if should_refresh('xem') or force:
        for indexer in indexerApi().indexers:
            indexer_api = indexerApi(indexer)

            # Not query XEM for unsupported indexers
            if not indexer_api.config.get('xem_origin'):
                continue

            logger.info(
                'Checking for XEM scene exceptions updates for'
                ' {indexer_name}'.format(
                    indexer_name=indexer_api.name
                )
            )

            url = xem_url.format(indexer_api.config['xem_origin'])
            response = helpers.get_url(url, session=xem_session,
                                       timeout=60, returns='response')
            try:
                jdata = response.json()
            except (ValueError, AttributeError) as error:
                logger.debug(
                    'Check scene exceptions update failed for {indexer}.'
                    ' Unable to get URL: {url} Error: {error}'.format(
                        indexer=indexer_api.name, url=url, error=error,
                    )
                )
                continue

            if not jdata['data'] or jdata['result'] == 'failure':
                logger.debug(
                    'No data returned from XEM while checking for scene'
                    ' exceptions. Update failed for {indexer}'.format(
                        indexer=indexer_api.name
                    )
                )
                continue

            for indexer_id, exceptions in iteritems(jdata['data']):
                try:
                    xem_exceptions[indexer][indexer_id] = exceptions
                except Exception as error:
                    logger.warning(
                        'XEM: Rejected entry: Indexer ID: {indexer_id},'
                        ' Exceptions: {e}'.format(
                            indexer_id=indexer_id, e=exceptions
                        )
                    )
                    logger.warning('XEM: Rejected entry error message:'
                                   ' {error}'.format(error=error))

        set_last_refresh('xem')

    return xem_exceptions


def _get_anidb_exceptions(force):
    anidb_exceptions = defaultdict(dict)
    # AniDB exceptions use TVDB as indexer
    exceptions = anidb_exceptions[INDEXER_TVDBV2]

    if should_refresh('anidb') or force:
        logger.info('Checking for scene exceptions updates from AniDB')

        for show in app.showList:
            if all([show.name, show.is_anime, show.indexer == INDEXER_TVDBV2]):
                try:
                    anime = adba.Anime(
                        None,
                        name=show.name,
                        tvdbid=show.indexerid,
                        autoCorrectName=True
                    )
                except ValueError as error:
                    logger.debug(
                        "Couldn't update scene exceptions for {show},"
                        " AniDB doesn't have this show. Error: {msg}".format(
                            show=show.name, msg=error,
                        )
                    )
                    continue
                except Exception as error:
                    logger.error(
                        'Checking AniDB scene exceptions update failed'
                        ' for {show}. Error: {msg}'.format(
                            show=show.name, msg=error,
                        )
                    )
                    continue

                if anime and anime.name != show.name:
                    indexer_id = int(show.indexerid)
                    exceptions[indexer_id] = [{anime.name.decode('utf-8'): -1}]

        set_last_refresh('anidb')

    return anidb_exceptions
