# coding=utf-8
# Author: Nic Wolfe <nic@wolfeden.ca>
#
# Git: https://github.com/PyMedusa/SickRage.git
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

import datetime
import threading
import time

import adba

from indexers.indexer_config import INDEXER_TVDB

import sickbeard

from sickbeard import db, helpers, logger

from six import iteritems


exception_dict = {}
anidb_exception_dict = {}
xem_exception_dict = {}

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
    rows = cache_db_con.select('SELECT last_refreshed FROM scene_exceptions_refresh WHERE list = ?', [ex_list])
    if rows:
        last_refresh = int(rows[0]['last_refreshed'])
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
        'scene_exceptions_refresh',
        {'last_refreshed': int(time.mktime(datetime.datetime.today().timetuple()))},
        {'list': ex_list}
    )


def get_scene_exceptions(indexer_id, season=-1):
    """Given a indexer_id, return a list of all the scene exceptions."""
    exceptions_list = []

    if indexer_id not in exceptionsCache or season not in exceptionsCache[indexer_id]:
        cache_db_con = db.DBConnection('cache.db')
        exceptions = cache_db_con.select('SELECT show_name FROM scene_exceptions WHERE indexer_id = ? AND season = ?',
                                         [indexer_id, season])
        if exceptions:
            exceptions_list = list({cur_exception['show_name'] for cur_exception in exceptions})

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
    exceptions = cache_db_con.select('SELECT show_name, season FROM scene_exceptions WHERE indexer_id = ?',
                                     [indexer_id])
    if exceptions:
        for cur_exception in exceptions:
            if not cur_exception['season'] in exceptions_dict:
                exceptions_dict[cur_exception['season']] = []
            exceptions_dict[cur_exception['season']].append(cur_exception['show_name'])

    return exceptions_dict


def get_scene_seasons(indexer_id):
    """Return a list of season numbers that have scene exceptions."""
    exceptions_season_list = []

    if indexer_id not in exceptionsSeasonCache:
        cache_db_con = db.DBConnection('cache.db')
        sql_results = cache_db_con.select(
            'SELECT DISTINCT(season) AS season FROM scene_exceptions WHERE indexer_id = ?', [indexer_id])
        if sql_results:
            exceptions_season_list = list({int(x['season']) for x in sql_results})

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
        'SELECT indexer_id, season FROM scene_exceptions WHERE LOWER(show_name) = ? ORDER BY season ASC',
        [show_name.lower()])
    if exception_result:
        return [(int(x['indexer_id']), int(x['season'])) for x in exception_result]

    out = []
    all_exception_results = cache_db_con.select('SELECT show_name, indexer_id, season FROM scene_exceptions')

    for cur_exception in all_exception_results:

        cur_exception_name = cur_exception['show_name']
        cur_indexer_id = int(cur_exception['indexer_id'])

        if show_name.lower() in (cur_exception_name.lower(),
                                 helpers.sanitizeSceneName(cur_exception_name).lower().replace('.', ' ')):

            logger.log(u'Scene exception lookup got indexer id {0}, using that'.format
                       (cur_indexer_id), logger.DEBUG)

            out.append((cur_indexer_id, int(cur_exception['season'])))

    if out:
        return out

    return [(None, None)]


def retrieve_exceptions():
    """
    Look up the exceptions on github.

    Parses the exceptions into a dict, and inserts them into the
    scene_exceptions table in cache.db. Also clears the scene name cache.
    """
    do_refresh = False
    for indexer in sickbeard.indexerApi().indexers:
        if should_refresh(sickbeard.indexerApi(indexer).name):
            do_refresh = True

    if do_refresh:
        loc = sickbeard.indexerApi(INDEXER_TVDB).config['scene_loc']
        logger.log(u'Checking for scene exception updates from {0}'.format(loc))

        response = helpers.getURL(loc, session=sickbeard.indexerApi(INDEXER_TVDB).session, returns='response')
        try:
            jdata = response.json()
        except ValueError:
            logger.log(u'Check scene exceptions update failed. Unable to update from {0}'.format(loc), logger.WARNING)
            jdata = None

        if jdata:
            for indexer in sickbeard.indexerApi().indexers:
                try:
                    set_last_refresh(sickbeard.indexerApi(indexer).name)
                    for indexer_id in jdata[sickbeard.indexerApi(indexer).config['xem_origin']]:
                        alias_list = [
                            {scene_exception: int(scene_season)}
                            for scene_season in jdata[sickbeard.indexerApi(indexer).config['xem_origin']][indexer_id]
                            for scene_exception in jdata[sickbeard.indexerApi(indexer).config
                                                         ['xem_origin']][indexer_id][scene_season]
                        ]
                        exception_dict[indexer_id] = alias_list
                except Exception:
                    continue

    # XEM scene exceptions
    _xem_exceptions_fetcher()
    for xem_ex in xem_exception_dict:
        if xem_ex in exception_dict:
            exception_dict[xem_ex] += exception_dict[xem_ex]
        else:
            exception_dict[xem_ex] = xem_exception_dict[xem_ex]

    # AniDB scene exceptions
    _anidb_exceptions_fetcher()
    for anidb_ex in anidb_exception_dict:
        if anidb_ex in exception_dict:
            exception_dict[anidb_ex] += anidb_exception_dict[anidb_ex]
        else:
            exception_dict[anidb_ex] = anidb_exception_dict[anidb_ex]

    queries = []
    cache_db_con = db.DBConnection('cache.db')
    for cur_indexer_id in exception_dict:
        sql_ex = cache_db_con.select('SELECT show_name FROM scene_exceptions WHERE indexer_id = ?;', [cur_indexer_id])
        existing_exceptions = [x['show_name'] for x in sql_ex]
        if cur_indexer_id not in exception_dict:
            continue

        for cur_exception_dict in exception_dict[cur_indexer_id]:
            for ex in iteritems(cur_exception_dict):
                cur_exception, curSeason = ex
                if cur_exception not in existing_exceptions:
                    queries.append(
                        ['INSERT OR IGNORE INTO scene_exceptions (indexer_id, show_name, season) VALUES (?,?,?);',
                         [cur_indexer_id, cur_exception, curSeason]])
    if queries:
        cache_db_con.mass_action(queries)
        logger.log(u'Updated scene exceptions', logger.DEBUG)

    # Cleanup
    exception_dict.clear()
    anidb_exception_dict.clear()
    xem_exception_dict.clear()


def update_scene_exceptions(indexer_id, scene_exceptions, season=-1):
    """Given a indexer_id, and a list of all show scene exceptions, update the db."""
    cache_db_con = db.DBConnection('cache.db')
    cache_db_con.action('DELETE FROM scene_exceptions WHERE indexer_id=? and season=?', [indexer_id, season])

    logger.log(u'Updating scene exceptions', logger.INFO)

    # A change has been made to the scene exception list. Let's clear the cache, to make this visible
    if indexer_id in exceptionsCache:
        exceptionsCache[indexer_id] = {}
        exceptionsCache[indexer_id][season] = [se.decode('utf-8') for se in scene_exceptions]

    for cur_exception in [se.decode('utf-8') for se in scene_exceptions]:
        cache_db_con.action('INSERT INTO scene_exceptions (indexer_id, show_name, season) VALUES (?,?,?)',
                            [indexer_id, cur_exception, season])


def _anidb_exceptions_fetcher():
    if should_refresh('anidb'):
        logger.log(u'Checking for scene exception updates for AniDB')
        for show in sickbeard.showList:
            if show.is_anime and show.indexer == 1:
                try:
                    anime = adba.Anime(None, name=show.name, tvdbid=show.indexerid, autoCorrectName=True)
                except Exception:
                    logger.log(u'Check AniDB scene exceptions update failed for {0}.'.format
                               (show.name), logger.DEBUG)
                    continue

                if anime and anime.name != show.name:
                    anidb_exception_dict[show.indexerid] = [{anime.name: -1}]

        set_last_refresh('anidb')

    return anidb_exception_dict


def _xem_exceptions_fetcher():
    if should_refresh('xem'):
        for indexer in sickbeard.indexerApi().indexers:
            logger.log(u'Checking for XEM scene exception updates for {0}'.format
                       (sickbeard.indexerApi(indexer).name))

            url = 'http://thexem.de/map/allNames?origin={0}&seasonNumbers=1'.format(
                  sickbeard.indexerApi(indexer).config['xem_origin'])

            response = helpers.getURL(url, session=xem_session, timeout=90, returns='response')
            try:
                jdata = response.json()
            except ValueError:
                logger.log(u'Check scene exceptions update failed for {0}, Unable to get URL: {1}'.format
                           (sickbeard.indexerApi(indexer).name, url), logger.DEBUG)
                continue

            if jdata['result'] == 'failure' or not jdata['data']:
                logger.log(u'No data returned from XEM when checking scene exceptions. Update failed for {0}'.format
                           (sickbeard.indexerApi(indexer).name), logger.DEBUG)
                continue

            for indexerid, names in iteritems(jdata['data']):
                try:
                    xem_exception_dict[int(indexerid)] = names
                except Exception as error:
                    logger.log(u'XEM: Rejected entry: indexerid:{0}; names:{1}'.format
                               (indexerid, names), logger.WARNING)
                    logger.log(u'XEM: Rejected entry error message:{0}'.format(error), logger.ERROR)

        set_last_refresh('xem')

    return xem_exception_dict
