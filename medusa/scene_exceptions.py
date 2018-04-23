# coding=utf-8

"""Scene exceptions module."""

from __future__ import unicode_literals

import logging
import threading
import time
from collections import defaultdict

import adba

from medusa import app, db, helpers
from medusa.indexers.indexer_api import indexerApi
from medusa.indexers.indexer_config import INDEXER_TVDBV2
from medusa.session.core import MedusaSafeSession

from six import iteritems

logger = logging.getLogger(__name__)

exceptions_cache = defaultdict(lambda: defaultdict(set))
exceptionLock = threading.Lock()

VALID_XEM_ORIGINS = {'anidb', 'tvdb', }
safe_session = MedusaSafeSession()


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
        indexer_id = int(exception[b'indexer'])
        series_id = int(exception[b'indexer_id'])
        season = int(exception[b'season'])
        show = exception[b'show_name']

        # To support multiple indexers with same series_id, we have to combine the min a tuple.
        series = (indexer_id, series_id)

        # exceptions_cache[(1, 12345)][season] = ['showname 1', 'showname 2']
        if show not in exceptions_cache[series][season]:
            exceptions_cache[series][season].add(show)

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


def get_scene_exceptions(series_obj, season=-1):
    """Get scene exceptions from exceptions_cache for a series."""
    exceptions_list = exceptions_cache[(series_obj.indexer, series_obj.series_id)][season]

    if season != -1 and not exceptions_list:
        exceptions_list = get_scene_exceptions(series_obj)

    # Return a set to avoid duplicates and it makes a copy of the list so the
    # original doesn't get modified
    return set(exceptions_list)


def get_season_scene_exceptions(series_obj, season=-1):
    """
    Get season scene exceptions from exceptions_cache for a series.

    Use this method if you expect to get back a season exception, or a series exception.
    But without any fallback between the two. As opposed to the function get_scene_exceptions.
    :param series_obj: A Series object.
    :param season: The season to return exceptions for. Or -1 for the series exceptions.

    :return: A set of exception names.
    """
    exceptions_list = exceptions_cache[(series_obj.indexer, series_obj.series_id)][season]

    # Return a set to avoid duplicates and it makes a copy of the list so the
    # original doesn't get modified
    return set(exceptions_list)


def get_all_scene_exceptions(series_obj):
    """
    Get all scene exceptions for a show ID.

    :param indexer_id: Indexer.
    :param series_id: Series id.
    :return: dict of exceptions (e.g. exceptions_cache[season][exception_name])
    """
    return exceptions_cache.get((series_obj.indexer, series_obj.series_id), defaultdict(set))


def get_scene_exceptions_by_name(show_name):
    """Look for a series_id, season and indexer for a given series scene exception."""
    # TODO: Rewrite to use exceptions_cache since there is no need to hit db.
    # TODO: Make the query more linient. For example. `Jojo's Bizarre Adventure Stardust Crusaders` will not match
    # while `Jojo's Bizarre Adventure - Stardust Crusaders` is available.
    # Try the obvious case first
    cache_db_con = db.DBConnection('cache.db')
    scene_exceptions = cache_db_con.select(
        b'SELECT indexer, indexer_id, season '
        b'FROM scene_exceptions '
        b'WHERE show_name = ? ORDER BY season ASC',
        [show_name])
    if scene_exceptions:
        # FIXME: Need to add additional layer indexer.
        return [(int(exception[b'indexer_id']), int(exception[b'season']), int(exception[b'indexer']))
                for exception in scene_exceptions]

    result = []
    scene_exceptions = cache_db_con.select(
        b'SELECT show_name, indexer, indexer_id, season '
        b'FROM scene_exceptions'
    )

    for exception in scene_exceptions:
        indexer = int(exception[b'indexer'])
        indexer_id = int(exception[b'indexer_id'])
        season = int(exception[b'season'])
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
            result.append((indexer_id, season, indexer))

    return result or [(None, None, None)]


def update_scene_exceptions(series_obj, scene_exceptions, season=-1):
    """Update database with all show scene exceptions by indexer_id."""
    logger.info('Updating scene exceptions...')

    cache_db_con = db.DBConnection('cache.db')
    cache_db_con.action(
        b'DELETE FROM scene_exceptions '
        b'WHERE indexer_id=? AND '
        b'    season=? AND '
        b'    indexer=?',
        [series_obj.series_id, season, series_obj.indexer]
    )

    # A change has been made to the scene exception list.
    # Let's clear the cache, to make this visible

    exceptions_cache[(series_obj.indexer, series_obj.series_id)].clear()

    for exception in scene_exceptions:
        if exception not in exceptions_cache[(series_obj.indexer, series_obj.series_id)][season]:
            # Add to cache
            exceptions_cache[(series_obj.indexer, series_obj.series_id)][season].add(exception)

            # Add to db
            cache_db_con.action(
                b'INSERT INTO scene_exceptions '
                b'    (indexer, indexer_id, show_name, season)'
                b'VALUES (?,?,?,?)',
                [series_obj.indexer, series_obj.series_id, exception, season]
            )


def retrieve_exceptions(force=False, exception_type=None):
    """
    Look up the exceptions from all sources.

    Parses the exceptions into a dict, and inserts them into the
    scene_exceptions table in cache.db. Also clears the scene name cache.
    :param force: If enabled this will force the refresh of scene exceptions using the medusa exceptions,
    xem exceptions and anidb exceptions.
    :param exception_type: Only refresh a specific exception_type. Options are: 'medusa', 'anidb', 'xem'
    """
    custom_exceptions = _get_custom_exceptions(force) if exception_type in ['custom_exceptions', None] else defaultdict(dict)
    xem_exceptions = _get_xem_exceptions(force) if exception_type in ['xem', None] else defaultdict(dict)
    anidb_exceptions = _get_anidb_exceptions(force) if exception_type in ['anidb', None] else defaultdict(dict)

    # Combined scene exceptions from all sources
    combined_exceptions = combine_exceptions(
        # Custom scene exceptions
        custom_exceptions,
        # XEM scene exceptions
        xem_exceptions,
        # AniDB scene exceptions
        anidb_exceptions,
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

    if force or should_refresh('custom_exceptions'):
        for indexer in indexerApi().indexers:
            location = indexerApi(indexer).config['scene_loc']
            logger.info(
                'Checking for scene exception updates from {location}',
                location=location
            )
            try:
                # When any Medusa Safe session exception, session returns None and then AttributeError when json()
                jdata = safe_session.get(location, timeout=60).json()
            except (ValueError, AttributeError) as error:
                logger.debug(
                    'Check scene exceptions update failed. Unable to '
                    'update from {location}. Error: {error}'.format(
                        location=location, error=error
                    )
                )
                # If unable to get scene exceptions, assume we can't connect to CDN so we don't `continue`
                return custom_exceptions

            indexer_ids = jdata[indexerApi(indexer).config['identifier']]
            for indexer_id in indexer_ids:
                indexer_exceptions = indexer_ids[indexer_id]
                alias_list = [{exception: int(season)}
                              for season in indexer_exceptions
                              for exception in indexer_exceptions[season]]
                custom_exceptions[indexer][indexer_id] = alias_list

            set_last_refresh('custom_exceptions')

    return custom_exceptions


def _get_xem_exceptions(force):
    xem_exceptions = defaultdict(dict)
    url = 'http://thexem.de/map/allNames'
    params = {
        'origin': None,
        'seasonNumbers': 1,
    }

    if force or should_refresh('xem'):
        for indexer in indexerApi().indexers:
            indexer_api = indexerApi(indexer)

            try:
                # Get XEM origin for indexer
                origin = indexer_api.config['xem_origin']
                if origin not in VALID_XEM_ORIGINS:
                    msg = 'invalid origin for XEM: {0}'.format(origin)
                    raise ValueError(msg)
            except KeyError:
                # Indexer has no XEM origin
                continue
            except ValueError as error:
                # XEM origin for indexer is invalid
                logger.error(
                    'Error getting XEM scene exceptions for {indexer}:'
                    ' {error}'.format(indexer=indexer_api.name, error=error)
                )
                continue
            else:
                # XEM origin for indexer is valid
                params['origin'] = origin

            logger.info(
                'Checking for XEM scene exceptions updates for'
                ' {indexer_name}'.format(
                    indexer_name=indexer_api.name
                )
            )

            response = safe_session.get(url, params=params, timeout=60)
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

    if force or should_refresh('anidb'):
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
                    series_id = int(show.series_id)
                    exceptions[series_id] = [{anime.name.decode('utf-8'): -1}]

        set_last_refresh('anidb')

    return anidb_exceptions
