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

import datetime
import threading
import time

import adba
from medusa.indexers.indexer_api import indexerApi
from six import iteritems, text_type
from . import app, db, helpers, logger
from .indexers.indexer_config import INDEXER_TVDBV2

exceptionsCache = {}
exceptionsSeasonCache = {}

exceptionLock = threading.Lock()

xem_session = helpers.make_session()


def should_refresh(ex_list):
    """
    Check if we should refresh cache for items in ex_list.

    :param ex_list: exception list to check if exception needs a refresh
    :return: True if refresh is needed
    """
    max_refresh_age_secs = 86400  # 1 day

    cache_db_con = db.DBConnection('cache.db')
    rows = cache_db_con.select(b'SELECT last_refreshed FROM scene_exceptions_refresh WHERE list = ?', [ex_list])
    if rows:
        last_refresh = int(rows[0][b'last_refreshed'])
        return int(time.mktime(datetime.datetime.today().timetuple())) > last_refresh + max_refresh_age_secs
    else:
        return True


def set_last_refresh(ex_list):
    """
    Update last cache update time for shows in list.

    :param ex_list: exception list to set refresh time
    """
    cache_db_con = db.DBConnection('cache.db')
    cache_db_con.upsert(
        b'scene_exceptions_refresh',
        {b'last_refreshed': int(time.mktime(datetime.datetime.today().timetuple()))},
        {b'list': ex_list}
    )


def get_scene_exceptions(indexer_id, season=-1):
    """Given a indexer_id, return a list of all the scene exceptions."""
    exceptions_list = []

    if indexer_id not in exceptionsCache or season not in exceptionsCache[indexer_id]:
        cache_db_con = db.DBConnection('cache.db')
        exceptions = cache_db_con.select(b'SELECT show_name FROM scene_exceptions WHERE indexer_id = ? AND season = ?',
                                         [indexer_id, season])
        if exceptions:
            exceptions_list = list({cur_exception[b'show_name'] for cur_exception in exceptions})

            if indexer_id not in exceptionsCache:
                exceptionsCache[indexer_id] = {}
            exceptionsCache[indexer_id][season] = exceptions_list
    else:
        exceptions_list = exceptionsCache[indexer_id][season]

    # Add generic exceptions regardless of the season if there is no exception for season
    if season != -1 and not exceptions_list:
        exceptions_list += get_scene_exceptions(indexer_id, season=-1)

    return list({exception for exception in exceptions_list})


def get_all_scene_exceptions(indexer_id):
    """
    Get all scene exceptions for a show ID.

    :param indexer_id: ID to check
    :return: dict of exceptions
    """
    exceptions_dict = {}

    cache_db_con = db.DBConnection('cache.db')
    exceptions = cache_db_con.select(b'SELECT show_name, season FROM scene_exceptions WHERE indexer_id = ?',
                                     [indexer_id])
    if exceptions:
        for cur_exception in exceptions:
            if not cur_exception[b'season'] in exceptions_dict:
                exceptions_dict[cur_exception[b'season']] = []
            exceptions_dict[cur_exception[b'season']].append(cur_exception[b'show_name'])

    return exceptions_dict


def get_scene_seasons(indexer_id):
    """Return a list of season numbers that have scene exceptions."""
    exceptions_season_list = []

    if indexer_id not in exceptionsSeasonCache:
        cache_db_con = db.DBConnection('cache.db')
        sql_results = cache_db_con.select(
            b'SELECT DISTINCT(season) AS season FROM scene_exceptions WHERE indexer_id = ?', [indexer_id])
        if sql_results:
            exceptions_season_list = list({int(x[b'season']) for x in sql_results})

            if indexer_id not in exceptionsSeasonCache:
                exceptionsSeasonCache[indexer_id] = {}

            exceptionsSeasonCache[indexer_id] = exceptions_season_list
    else:
        exceptions_season_list = exceptionsSeasonCache[indexer_id]

    return exceptions_season_list


def get_scene_exception_by_name(show_name):
    """Given a show name, return the first indexerid and season of the exceptions list."""
    return get_scene_exception_by_name_multiple(show_name)[0]


def get_scene_exception_by_name_multiple(show_name):
    """Given a show name, return the indexerid of the exception, None if no exception is present."""
    # Try the obvious case first
    cache_db_con = db.DBConnection('cache.db')
    exception_result = cache_db_con.select(
        b'SELECT indexer_id, season FROM scene_exceptions WHERE LOWER(show_name) = ? ORDER BY season ASC',
        [show_name.lower()])
    if exception_result:
        return [(int(x[b'indexer_id']), int(x[b'season'])) for x in exception_result]

    out = []
    all_exception_results = cache_db_con.select(b'SELECT show_name, indexer_id, season FROM scene_exceptions')

    for cur_exception in all_exception_results:

        cur_exception_name = cur_exception[b'show_name']
        cur_indexer_id = int(cur_exception[b'indexer_id'])

        if show_name.lower() in (cur_exception_name.lower(),
                                 helpers.sanitize_scene_name(cur_exception_name).lower().replace('.', ' ')):
            logger.log('Scene exception lookup got indexer ID {0}, using that'.format
                       (cur_indexer_id), logger.DEBUG)

            out.append((cur_indexer_id, int(cur_exception[b'season'])))

    if out:
        return out

    return [(None, None)]


def update_scene_exceptions(indexer_id, scene_exceptions, season=-1):
    """Given a indexer_id, and a list of all show scene exceptions, update the db."""
    cache_db_con = db.DBConnection('cache.db')
    cache_db_con.action(b'DELETE FROM scene_exceptions WHERE indexer_id=? and season=?', [indexer_id, season])

    logger.log('Updating scene exceptions...', logger.INFO)

    # A change has been made to the scene exception list. Let's clear the cache, to make this visible
    if indexer_id in exceptionsCache:
        exceptionsCache[indexer_id] = {}
        exceptionsCache[indexer_id][season] = [se.decode('utf-8') for se in scene_exceptions]

    for cur_exception in [se.decode('utf-8') for se in scene_exceptions]:
        cache_db_con.action(b'INSERT INTO scene_exceptions (indexer_id, show_name, season) VALUES (?,?,?)',
                            [indexer_id, cur_exception, season])


def retrieve_exceptions():
    """
    Look up the exceptions from all sources.

    Parses the exceptions into a dict, and inserts them into the
    scene_exceptions table in cache.db. Also clears the scene name cache.
    """
    # Custom scene exceptions
    custom_exceptions = _get_custom_exceptions()

    # XEM scene exceptions
    xem_exceptions = _get_xem_exceptions()

    # AniDB scene exceptions
    anidb_exceptions = _get_anidb_exceptions()

    # Combined scene exceptions from all sources
    combined_exceptions = combine_exceptions(custom_exceptions, xem_exceptions, anidb_exceptions)

    queries = []
    cache_db_con = db.DBConnection('cache.db')
    for indexer in combined_exceptions:
        for indexer_id in combined_exceptions[indexer]:
            sql_ex = cache_db_con.select(b'SELECT show_name, indexer FROM scene_exceptions WHERE indexer = ? AND '
                                         b'indexer_id = ?', [indexer, indexer_id])
            existing_exceptions = [x[b'show_name'] for x in sql_ex]

            for exception_dict in combined_exceptions[indexer][indexer_id]:
                for scene_exception, season in iteritems(exception_dict):
                    if scene_exception not in existing_exceptions:
                        queries.append(
                            [
                                b'INSERT OR IGNORE INTO scene_exceptions (indexer, indexer_id, show_name, season) '
                                b'VALUES (?,?,?,?)',
                                [indexer, indexer_id, scene_exception, season]])
    if queries:
        cache_db_con.mass_action(queries)
        logger.log('Updated scene exceptions.', logger.INFO)


def combine_exceptions(*scene_exceptions):
    """Combine the exceptions from all sources."""
    # ex_dicts = iter(scene_exceptions)
    combined_ex = {}

    for scene_exception in scene_exceptions:
        if scene_exception:
            for indexer in scene_exception:
                if indexer not in combined_ex:
                    combined_ex[indexer] = {}
                combined_ex[indexer].update(scene_exception[indexer])

    return combined_ex


def _get_custom_exceptions():
    custom_exceptions = {}

    if should_refresh('custom_exceptions'):
        for indexer in indexerApi().indexers:
            try:
                location = indexerApi(indexer).config['scene_loc']
                logger.log('Checking for scene exception updates from {0}'.format(location))

                response = helpers.get_url(location, session=indexerApi(indexer).session,
                                           timeout=60, returns='response')
                try:
                    jdata = response.json()
                except (ValueError, AttributeError) as error:
                    logger.log('Check scene exceptions update failed. Unable to update from {0}. Error: {1}'.format
                               (location, error), logger.DEBUG)
                    return custom_exceptions

                if indexer not in custom_exceptions:
                    custom_exceptions[indexer] = {}

                for indexer_id in jdata[indexerApi(indexer).config['identifier']]:
                    alias_list = [{scene_exception: int(scene_season)}
                                  for scene_season in jdata[indexerApi(indexer).config['identifier']][indexer_id]
                                  for scene_exception in jdata[indexerApi(indexer).config
                                  ['identifier']][indexer_id][scene_season]]
                    custom_exceptions[indexer][indexer_id] = alias_list
            except Exception as error:
                logger.log('Unable to update scene exceptions for {0}. Error: {1}'.format
                           (indexer, error), logger.ERROR)
                continue

            set_last_refresh('custom_exceptions')

    return custom_exceptions


def _get_xem_exceptions():
    xem_exceptions = {}

    if should_refresh('xem'):
        for indexer in indexerApi().indexers:

            # Not query XEM for unsupported indexers
            if not indexerApi(indexer).config.get('xem_origin'):
                continue

            logger.log('Checking for XEM scene exceptions updates for {0}'.format
                       (indexerApi(indexer).name))

            if indexer not in xem_exceptions:
                xem_exceptions[indexer] = {}

            xem_url = 'http://thexem.de/map/allNames?origin={0}&seasonNumbers=1'.format(
                indexerApi(indexer).config['xem_origin'])

            response = helpers.get_url(xem_url, session=xem_session, timeout=60, returns='response')
            try:
                jdata = response.json()
            except (ValueError, AttributeError) as error:
                logger.log('Check scene exceptions update failed for {0}. Unable to get URL: {1}'.format
                           (indexerApi(indexer).name, xem_url), logger.DEBUG)
                continue

            if not jdata['data'] or jdata['result'] == 'failure':
                logger.log('No data returned from XEM while checking for scene exceptions. '
                           'Update failed for {0}'.format(indexerApi(indexer).name), logger.DEBUG)
                continue

            for indexer_id, exceptions in iteritems(jdata['data']):
                try:
                    xem_exceptions[indexer][indexer_id] = exceptions
                except Exception as error:
                    logger.log('XEM: Rejected entry: Indexer ID: {0}, Exceptions: {1}'.format
                               (indexer_id, exceptions), logger.WARNING)
                    logger.log('XEM: Rejected entry error message: {0}'.format(error), logger.ERROR)

        set_last_refresh('xem')

    return xem_exceptions


def _get_anidb_exceptions():
    anidb_exceptions = {}

    if should_refresh('anidb'):
        logger.log('Checking for scene exceptions updates from AniDB')

        for show in app.showList:
            if all([show.name, show.is_anime, show.indexer == INDEXER_TVDBV2]):
                try:
                    anime = adba.Anime(None, name=show.name, tvdbid=show.indexerid, autoCorrectName=True)
                except ValueError as error:
                    logger.log("Couldn't update scene exceptions for {0}, AniDB doesn't have this show.".format
                               (show.name), logger.DEBUG)
                    continue
                except Exception as error:
                    logger.log('Checking AniDB scene exceptions update failed for {0}. Error: {1}'.format
                               (show.name, error), logger.ERROR)
                    continue

                if anime and anime.name != show.name:
                    anidb_exceptions[INDEXER_TVDBV2] = {}
                    anidb_exceptions[INDEXER_TVDBV2][text_type(show.indexerid)] = [{anime.name.decode('utf-8'): -1}]

        set_last_refresh('anidb')

    return anidb_exceptions
