# coding=utf-8

"""Scene exceptions module."""

from __future__ import unicode_literals

import logging
import time
from collections import defaultdict, namedtuple
from os.path import join

import adba

from medusa import app, db
from medusa.helpers import sanitize_scene_name
from medusa.indexers.api import indexerApi
from medusa.indexers.config import INDEXER_TVDBV2
from medusa.logger.adapters.style import BraceAdapter
from medusa.session.core import MedusaSafeSession

from six import iteritems

logger = BraceAdapter(logging.getLogger(__name__))
logger.logger.addHandler(logging.NullHandler())

exceptions_cache = defaultdict(lambda: defaultdict(set))
VALID_XEM_ORIGINS = {'anidb', 'tvdb', }
safe_session = MedusaSafeSession()

TitleException = namedtuple('TitleException', 'title, season, indexer, series_id, custom')


def refresh_exceptions_cache(series_obj=None):
    """
    Query the db for show exceptions and update the exceptions_cache.

    :param series_obj: Series Object. If passed only exceptions for this show are refreshed.
    """
    logger.info('Updating exception_cache and exception_season_cache')

    # Empty the module level variables
    exceptions_cache.clear()

    main_db_con = db.DBConnection()
    query = """
        SELECT indexer, series_id, title, season, custom
        FROM scene_exceptions
    """
    where = []

    if series_obj:
        query += ' WHERE indexer = ? AND series_id = ?'
        where += [series_obj.indexer, series_obj.series_id]

    exceptions = main_db_con.select(query, where) or []

    # Start building up a new exceptions_cache.
    for exception in exceptions:
        indexer = int(exception['indexer'])
        series_id = int(exception['series_id'])
        season = int(exception['season'])
        title = exception['title']
        custom = bool(exception['custom'])

        # To support multiple indexers with same series_id, we have to combine the min a tuple.
        series = (indexer, series_id)
        series_exception = TitleException(
            title=title,
            season=season,
            indexer=indexer,
            series_id=series_id,
            custom=custom
        )

        # exceptions_cache[(1, 12345)][season] =
        # TitleExeption('title', 'season', indexer, series_id)
        if series_exception not in exceptions_cache[series][season]:
            exceptions_cache[series][season].add(series_exception)

    logger.info('Finished processing {x} scene exceptions.', x=len(exceptions))


def get_last_refresh(ex_list):
    """Get the last update timestamp for the specific scene exception list."""
    cache_db_con = db.DBConnection('cache.db')
    return cache_db_con.select('SELECT last_refreshed FROM scene_exceptions_refresh WHERE list = ?', [ex_list])


def should_refresh(ex_list):
    """
    Check if we should refresh cache for items in ex_list.

    :param ex_list: exception list to check if exception needs a refresh
    :return: True if refresh is needed
    """
    max_refresh_age_secs = 86400  # 1 day
    rows = get_last_refresh(ex_list)

    if rows:
        last_refresh = int(rows[0]['last_refreshed'])
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
        'scene_exceptions_refresh',
        {'last_refreshed': int(time.time())},
        {'list': source}
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


def get_season_from_name(series_obj, exception_name):
    """
    Get season number from exceptions_cache for a series scene exception name.

    Use this method if you expect to get back a season number from a scene exception.
    :param series_obj: A Series object.
    :param series_name: The scene exception name.

    :return: The season number or None.
    """
    exceptions_list = exceptions_cache[(series_obj.indexer, series_obj.series_id)]
    for season, exceptions in exceptions_list.items():
        # Skip whole series exceptions
        if season == -1:
            continue
        for exception in exceptions:
            if exception.title.lower() == exception_name.lower():
                return exception.season


def get_all_scene_exceptions(series_obj):
    """
    Get all scene exceptions for a show ID.

    :param series_obj: series object.
    :return: dict of exceptions (e.g. exceptions_cache[season][exception_name])
    """
    return exceptions_cache.get((series_obj.indexer, series_obj.series_id), defaultdict(set))


def get_scene_exception_by_name(series_name):
    """Get the season of a scene exception."""
    # Flatten the exceptions_cache.
    scene_exceptions = []
    for exception_set in list(exceptions_cache.values()):
        for title_exception in list(exception_set.values()):
            scene_exceptions += title_exception

    # First attempt exact match.
    for title_exception in scene_exceptions:
        if series_name == title_exception.title:
            return title_exception

    # Let's try out some sanitized names.
    for title_exception in scene_exceptions:
        sanitized_name = sanitize_scene_name(title_exception.title)
        titles = (
            title_exception.title.lower(),
            sanitized_name.lower().replace('.', ' '),
        )

        if series_name.lower() in titles:
            logger.debug(
                'Scene exception lookup got series id {title_exception.series_id} '
                'from indexer {title_exception.indexer},'
                ' using that', title_exception=title_exception
            )
            return title_exception


def update_scene_exceptions(series_obj, scene_exceptions):
    """
    Update database with all show scene exceptions by indexer_id.

    :param series_obj: series object.
    :param scene_exceptions: list of dicts, originating from the /config/ apiv2 route. Where scene exceptions are set from the UI.
    """
    logger.info('Updating scene exceptions...')

    main_db_con = db.DBConnection()

    exceptions_cache[(series_obj.indexer, series_obj.series_id)].clear()
    # Remove exceptions for this show, so removed exceptions also become visible.
    main_db_con.action(
        'DELETE FROM scene_exceptions '
        'WHERE series_id=? AND indexer=?',
        [series_obj.series_id, series_obj.indexer]
    )

    for exception in scene_exceptions:
        # A change has been made to the scene exception list.

        # Prevent adding duplicate scene exceptions.
        if exception['title'] not in exceptions_cache[(series_obj.indexer, series_obj.series_id)][exception['season']]:
            # Add to db
            main_db_con.action(
                'INSERT INTO scene_exceptions '
                '(indexer, series_id, title, season, custom) '
                'VALUES (?,?,?,?,?)',
                [series_obj.indexer, series_obj.series_id, exception['title'], exception['season'], exception['custom']]
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
    main_db_con = db.DBConnection()

    # TODO: See if this can be optimized
    for indexer in combined_exceptions:
        for series_id in combined_exceptions[indexer]:
            sql_ex = main_db_con.select(
                'SELECT title, indexer '
                'FROM scene_exceptions '
                'WHERE indexer = ? AND '
                'series_id = ?',
                [indexer, series_id]
            )
            existing_exceptions = [x['title'] for x in sql_ex]

            for exception_dict in combined_exceptions[indexer][series_id]:
                for scene_exception, season in iteritems(exception_dict):
                    if scene_exception not in existing_exceptions:
                        queries.append([
                            'INSERT OR IGNORE INTO scene_exceptions '
                            '(indexer, series_id, title, season, custom) '
                            'VALUES (?,?,?,?,?)',
                            [indexer, series_id, scene_exception, season, False]
                        ])
    if queries:
        main_db_con.mass_action(queries)
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
    """Exceptions maintained by the medusa.github.io repo."""
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
                    ' {error}', {'indexer': indexer_api.name, 'error': error}
                )
                continue
            else:
                # XEM origin for indexer is valid
                params['origin'] = origin

            logger.info(
                'Checking for XEM scene exceptions updates for'
                ' {indexer_name}', {'indexer_name': indexer_api.name}
            )

            response = safe_session.get(url, params=params, timeout=60)
            try:
                jdata = response.json()
            except (ValueError, AttributeError) as error:
                logger.debug(
                    'Check scene exceptions update failed for {indexer}.'
                    ' Unable to get URL: {url} Error: {error}', {'indexer': indexer_api.name, 'url': url, 'error': error}
                )
                continue

            if not jdata['data'] or jdata['result'] == 'failure':
                logger.debug(
                    'No data returned from XEM while checking for scene'
                    ' exceptions. Update failed for {indexer}', {'indexer': indexer_api.name}
                )
                continue

            for indexer_id, exceptions in iteritems(jdata['data']):
                try:
                    xem_exceptions[indexer][indexer_id] = exceptions
                except Exception as error:
                    logger.warning(
                        'XEM: Rejected entry: Indexer ID: {indexer_id},'
                        ' Exceptions: {exceptions}', {'indexer_id': indexer_id, 'exceptions': exceptions}
                    )
                    logger.warning('XEM: Rejected entry error message: {error}', {'error': error})

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
                        autoCorrectName=True,
                        cache_path=join(app.CACHE_DIR, 'adba')
                    )
                except ValueError as error:
                    logger.debug(
                        "Couldn't update scene exceptions for {show},"
                        " AniDB doesn't have this show. Error: {msg}", {'show': show.name, 'msg': error}
                    )
                    continue
                except Exception as error:
                    logger.error(
                        'Checking AniDB scene exceptions update failed'
                        ' for {show}. Error: {msg}', {'show': show.name, 'msg': error}
                    )
                    continue

                if anime and anime.name != show.name:
                    series_id = int(show.series_id)
                    exceptions[series_id] = [{anime.name: -1}]

        set_last_refresh('anidb')

    return anidb_exceptions
