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
#
# Created on Sep 20, 2012
# @author: Dermot Buckley <dermot@buckley.ie>
# @copyright: Dermot Buckley
#

from __future__ import unicode_literals

import datetime
import time
import traceback
from builtins import str

from medusa import db, logger
from medusa.helper.exceptions import ex
from medusa.indexers.indexer_api import indexerApi
from medusa.scene_exceptions import safe_session


def get_scene_numbering(series_obj, season, episode, fallback_to_xem=True):
    """
    Returns a tuple, (season, episode), with the scene numbering (if there is one),
    otherwise returns the xem numbering (if fallback_to_xem is set), otherwise
    returns the TVDB numbering.
    (so the return values will always be set)

    :param series_obj: Series object.
    :param season: int
    :param episode: int
    :param fallback_to_xem: bool If set (the default), check xem for matches if there is no local scene numbering
    :return: (int, int) a tuple with (season, episode)
    """
    if series_obj is None or season is None or episode is None:
        return season, episode

    if series_obj and not series_obj.is_scene:
        return season, episode

    result = find_scene_numbering(series_obj, season, episode)
    if result:
        return result
    else:
        if fallback_to_xem:
            xem_result = find_xem_numbering(series_obj, season, episode)
            if xem_result:
                return xem_result
        return season, episode


def find_scene_numbering(series_obj, season, episode):
    """
    Same as get_scene_numbering(), but returns None if scene numbering is not set
    """
    if series_obj is None or season is None or episode is None:
        return season, episode

    main_db_con = db.DBConnection()
    rows = main_db_con.select(
        "SELECT scene_season, scene_episode FROM scene_numbering WHERE indexer = ? and indexer_id = ? and season = ? and episode = ? and (scene_season or scene_episode) != 0",
        [series_obj.indexer, series_obj.series_id, season, episode])

    if rows:
        return int(rows[0][b"scene_season"]), int(rows[0][b"scene_episode"])


def get_scene_absolute_numbering(series_obj, absolute_number, fallback_to_xem=True):
    """
    Returns a tuple, (season, episode), with the scene numbering (if there is one),
    otherwise returns the xem numbering (if fallback_to_xem is set), otherwise
    returns the TVDB numbering.
    (so the return values will always be set)

    :param series_obj: Series object.
    ;param absolute_number: int
    :param fallback_to_xem: bool If set (the default), check xem for matches if there is no local scene numbering
    :return: (int, int) a tuple with (season, episode)
    """
    if series_obj is None or absolute_number is None:
        return absolute_number

    if series_obj and not series_obj.is_scene:
        return absolute_number

    result = find_scene_absolute_numbering(series_obj, absolute_number)
    if result:
        return result
    else:
        if fallback_to_xem:
            xem_result = find_xem_absolute_numbering(series_obj, absolute_number)
            if xem_result:
                return xem_result
        return absolute_number


def find_scene_absolute_numbering(series_obj, absolute_number):
    """
    Same as get_scene_numbering(), but returns None if scene numbering is not set
    """
    if series_obj is None or absolute_number is None:
        return absolute_number

    main_db_con = db.DBConnection()
    rows = main_db_con.select(
        "SELECT scene_absolute_number FROM scene_numbering WHERE indexer = ? and indexer_id = ? and absolute_number = ? and scene_absolute_number != 0",
        [series_obj.indexer, series_obj.series_id, absolute_number])

    if rows:
        return int(rows[0][b"scene_absolute_number"])


def get_indexer_numbering(series_obj, sceneSeason, sceneEpisode, fallback_to_xem=True):
    """
    Returns a tuple, (season, episode) with the TVDB numbering for (sceneSeason, sceneEpisode)
    (this works like the reverse of get_scene_numbering)
    """
    if series_obj is None or sceneSeason is None or sceneEpisode is None:
        return sceneSeason, sceneEpisode

    main_db_con = db.DBConnection()
    rows = main_db_con.select(
        "SELECT season, episode FROM scene_numbering "
        "WHERE indexer = ? and indexer_id = ? and scene_season = ? and scene_episode = ?",
        [series_obj.indexer, series_obj.series_id, sceneSeason, sceneEpisode]
    )

    if rows:
        return int(rows[0][b"season"]), int(rows[0][b"episode"])
    else:
        if fallback_to_xem:
            return get_indexer_numbering_for_xem(series_obj, sceneSeason, sceneEpisode)
        return sceneSeason, sceneEpisode


def get_indexer_absolute_numbering(series_obj, sceneAbsoluteNumber, fallback_to_xem=True, scene_season=None):
    """
    Returns a tuple, (season, episode, absolute_number) with the TVDB absolute numbering for (sceneAbsoluteNumber)
    (this works like the reverse of get_absolute_numbering)
    """
    if series_obj is None or sceneAbsoluteNumber is None:
        return sceneAbsoluteNumber

    main_db_con = db.DBConnection()
    if scene_season is None:
        rows = main_db_con.select(
            "SELECT absolute_number FROM scene_numbering WHERE indexer = ? and indexer_id = ? and scene_absolute_number = ?",
            [series_obj.indexer, series_obj.series_id, sceneAbsoluteNumber])
    else:
        rows = main_db_con.select(
            "SELECT absolute_number FROM scene_numbering WHERE indexer = ? and indexer_id = ? and scene_absolute_number = ? and scene_season = ?",
            [series_obj.indexer, series_obj.series_id, sceneAbsoluteNumber, scene_season])

    if rows:
        return int(rows[0][b"absolute_number"])
    else:
        if fallback_to_xem:
            return get_indexer_absolute_numbering_for_xem(series_obj, sceneAbsoluteNumber, scene_season)
        return sceneAbsoluteNumber


def set_scene_numbering(series_obj, season=None, episode=None,  # pylint:disable=too-many-arguments
                        absolute_number=None, sceneSeason=None,
                        sceneEpisode=None, sceneAbsolute=None):
    """
    Set scene numbering for a season/episode.
    To clear the scene numbering, leave both sceneSeason and sceneEpisode as None.
    """
    if series_obj is None:
        return

    main_db_con = db.DBConnection()
    # Season/episode can be 0 so can't check "if season"
    if season is not None and episode is not None and absolute_number is None:
        main_db_con.action(
            "INSERT OR IGNORE INTO scene_numbering (indexer, indexer_id, season, episode) VALUES (?,?,?,?)",
            [series_obj.indexer, series_obj.series_id, season, episode])

        main_db_con.action(
            "UPDATE scene_numbering SET scene_season = ?, scene_episode = ? WHERE indexer = ? and indexer_id = ? and season = ? and episode = ?",
            [sceneSeason, sceneEpisode, series_obj.indexer, series_obj.series_id, season, episode])
    # absolute_number can be 0 so can't check "if absolute_number"
    else:
        main_db_con.action(
            "INSERT OR IGNORE INTO scene_numbering (indexer, indexer_id, absolute_number) VALUES (?,?,?)",
            [series_obj.indexer, series_obj.series_id, absolute_number])

        main_db_con.action(
            "UPDATE scene_numbering SET scene_absolute_number = ? WHERE indexer = ? and indexer_id = ? and absolute_number = ?",
            [sceneAbsolute, series_obj.indexer, series_obj.series_id, absolute_number])

    series_obj.flush_episodes()
    series_obj.erase_cached_parse()


def find_xem_numbering(series_obj, season, episode):
    """
    Returns the scene numbering, as retrieved from xem.
    Refreshes/Loads as needed.

    :param indexer_id: int
    :param season: int
    :param episode: int
    :return: (int, int) a tuple of scene_season, scene_episode, or None if there is no special mapping.
    """
    if series_obj is None or season is None or episode is None:
        return season, episode

    xem_refresh(series_obj)

    main_db_con = db.DBConnection()
    rows = main_db_con.select(
        "SELECT scene_season, scene_episode "
        "FROM tv_episodes "
        "WHERE indexer = ? and showid = ? and season = ? "
        "and episode = ? and (scene_season or scene_episode) != 0",
        [series_obj.indexer, series_obj.series_id, season, episode]
    )

    if rows:
        return int(rows[0][b"scene_season"]), int(rows[0][b"scene_episode"])


def find_xem_absolute_numbering(series_obj, absolute_number):
    """
    Returns the scene numbering, as retrieved from xem.
    Refreshes/Loads as needed.

    :param indexer_id: int
    :param absolute_number: int
    :return: int
    """
    if series_obj is None or absolute_number is None:
        return absolute_number

    xem_refresh(series_obj)

    main_db_con = db.DBConnection()
    rows = main_db_con.select(
        "SELECT scene_absolute_number "
        "FROM tv_episodes "
        "WHERE indexer = ? and showid = ? "
        "and absolute_number = ? and scene_absolute_number != 0",
        [series_obj.indexer, series_obj.series_id, absolute_number])

    if rows:
        return int(rows[0][b"scene_absolute_number"])


def get_indexer_numbering_for_xem(series_obj, sceneSeason, sceneEpisode):
    """
    Reverse of find_xem_numbering: lookup a tvdb season and episode using scene numbering

    :param indexer_id: int
    :param sceneSeason: int
    :param sceneEpisode: int
    :return: (int, int) a tuple of (season, episode)
    """
    if series_obj is None or sceneSeason is None or sceneEpisode is None:
        return sceneSeason, sceneEpisode

    xem_refresh(series_obj)

    main_db_con = db.DBConnection()
    rows = main_db_con.select(
        "SELECT season, episode "
        "FROM tv_episodes "
        "WHERE indexer = ? and showid = ? "
        "and scene_season = ? and scene_episode = ?",
        [series_obj.indexer, series_obj.series_id, sceneSeason, sceneEpisode])

    if rows:
        return int(rows[0][b"season"]), int(rows[0][b"episode"])

    return sceneSeason, sceneEpisode


def get_indexer_absolute_numbering_for_xem(series_obj, sceneAbsoluteNumber, scene_season=None):
    """
    Reverse of find_xem_numbering: lookup a tvdb season and episode using scene numbering

    :param indexer_id: int
    :param sceneAbsoluteNumber: int
    :return: int
    """
    if series_obj is None or sceneAbsoluteNumber is None:
        return sceneAbsoluteNumber

    xem_refresh(series_obj)

    main_db_con = db.DBConnection()
    if scene_season is None:
        rows = main_db_con.select(
            "SELECT absolute_number "
            "FROM tv_episodes "
            "WHERE indexer = ? AND showid = ? "
            "AND scene_absolute_number = ?",
            [series_obj.indexer, series_obj.series_id, sceneAbsoluteNumber])
    else:
        rows = main_db_con.select(
            "SELECT absolute_number "
            "FROM tv_episodes "
            "WHERE indexer = ? "
            "AND showid = ? AND scene_absolute_number = ? and scene_season = ?",
            [series_obj.indexer, series_obj.series_id, sceneAbsoluteNumber, scene_season])

    if rows:
        return int(rows[0][b"absolute_number"])

    return sceneAbsoluteNumber


def get_scene_numbering_for_show(series_obj):
    """
    Returns a dict of (season, episode) : (sceneSeason, sceneEpisode) mappings
    for an entire show.  Both the keys and values of the dict are tuples.
    Will be empty if there are no scene numbers set
    """
    if series_obj is None:
        return {}

    main_db_con = db.DBConnection()
    rows = main_db_con.select(
        'SELECT season, episode, scene_season, scene_episode FROM scene_numbering WHERE indexer = ? and indexer_id = ? and (scene_season or scene_episode) != 0 ORDER BY season, episode',
        [series_obj.indexer, series_obj.series_id])

    result = {}
    for row in rows:
        season = int(row[b'season'])
        episode = int(row[b'episode'])
        scene_season = int(row[b'scene_season'])
        scene_episode = int(row[b'scene_episode'])

        result[(season, episode)] = (scene_season, scene_episode)

    return result


def get_xem_numbering_for_show(series_obj, refresh_data=True):
    """
    Returns a dict of (season, episode) : (sceneSeason, sceneEpisode) mappings
    for an entire show.  Both the keys and values of the dict are tuples.
    Will be empty if there are no scene numbers set in xem
    """
    if series_obj is None:
        return {}

    if refresh_data:
        xem_refresh(series_obj)

    main_db_con = db.DBConnection()
    rows = main_db_con.select(
        'SELECT season, episode, scene_season, scene_episode '
        'FROM tv_episodes '
        'WHERE indexer = ? AND showid = ? '
        'AND (scene_season or scene_episode) != 0 '
        'ORDER BY season, episode',
        [series_obj.indexer, series_obj.series_id]
    )

    result = {}
    for row in rows:
        season = int(row[b'season'])
        episode = int(row[b'episode'])
        scene_season = int(row[b'scene_season'])
        scene_episode = int(row[b'scene_episode'])

        result[(season, episode)] = (scene_season, scene_episode)

    return result


def get_scene_absolute_numbering_for_show(series_obj):
    """
    Returns a dict of (season, episode) : (sceneSeason, sceneEpisode) mappings
    for an entire show.  Both the keys and values of the dict are tuples.
    Will be empty if there are no scene numbers set
    """
    if series_obj is None:
        return {}

    main_db_con = db.DBConnection()
    rows = main_db_con.select(
        'SELECT absolute_number, scene_absolute_number FROM scene_numbering WHERE indexer = ? and indexer_id = ? and scene_absolute_number != 0 ORDER BY absolute_number',
        [series_obj.indexer, series_obj.series_id])

    result = {}
    for row in rows:
        absolute_number = int(row[b'absolute_number'])
        scene_absolute_number = int(row[b'scene_absolute_number'])

        result[absolute_number] = scene_absolute_number

    return result


def get_xem_absolute_numbering_for_show(series_obj):
    """
    Returns a dict of (season, episode) : (sceneSeason, sceneEpisode) mappings
    for an entire show.  Both the keys and values of the dict are tuples.
    Will be empty if there are no scene numbers set in xem
    """
    if series_obj is None:
        return {}

    xem_refresh(series_obj)

    result = {}
    main_db_con = db.DBConnection()
    rows = main_db_con.select(
        'SELECT absolute_number, scene_absolute_number '
        'FROM tv_episodes '
        'WHERE indexer = ? and showid = ? and scene_absolute_number != 0 '
        'ORDER BY absolute_number',
        [series_obj.indexer, series_obj.series_id])

    for row in rows:
        absolute_number = int(row[b'absolute_number'])
        scene_absolute_number = int(row[b'scene_absolute_number'])

        result[absolute_number] = scene_absolute_number

    return result


def xem_refresh(series_obj, force=False):
    """
    Refresh data from xem for a tv show

    :param indexer_id: int
    """
    if not series_obj or series_obj.series_id < 1:
        return

    indexer_id = series_obj.indexer
    series_id = series_obj.series_id

    MAX_REFRESH_AGE_SECS = 86400  # 1 day

    main_db_con = db.DBConnection()
    rows = main_db_con.select("SELECT last_refreshed FROM xem_refresh WHERE indexer = ? and indexer_id = ?",
                              [indexer_id, series_id])
    if rows:
        lastRefresh = int(rows[0][b'last_refreshed'])
        refresh = int(time.mktime(datetime.datetime.today().timetuple())) > lastRefresh + MAX_REFRESH_AGE_SECS
    else:
        refresh = True

    if refresh or force:
        logger.log(
            u'Looking up XEM scene mapping for show ID {0} on {1}'.format(series_id, series_obj.indexer_name), logger.DEBUG)

        # mark refreshed
        main_db_con.upsert(
            "xem_refresh",
            {'last_refreshed': int(time.mktime(datetime.datetime.today().timetuple()))},
            {'indexer': indexer_id, 'indexer_id': series_id}
        )

        try:
            if not indexerApi(indexer_id).config.get('xem_origin'):
                logger.log(u'{0} is an unsupported indexer in XEM'.format(indexerApi(indexer_id).name), logger.DEBUG)
                return
            # XEM MAP URL
            url = "http://thexem.de/map/havemap?origin={0}".format(indexerApi(indexer_id).config['xem_origin'])
            parsed_json = safe_session.get_json(url)
            if not parsed_json or 'result' not in parsed_json or 'success' not in parsed_json['result'] or 'data' not in parsed_json or str(series_id) not in parsed_json['data']:
                logger.log(u'No XEM data for show ID {0} on {1}'.format(series_id, series_obj.indexer_name), logger.DEBUG)
                return

            # XEM API URL
            url = "http://thexem.de/map/all?id={0}&origin={1}&destination=scene".format(series_id, indexerApi(indexer_id).config['xem_origin'])
            parsed_json = safe_session.get_json(url)
            if not parsed_json or 'result' not in parsed_json or 'success' not in parsed_json['result']:
                logger.log(u'No XEM data for show ID {0} on {1}'.format(indexer_id, series_obj.indexer_name), logger.DEBUG)
                return

            cl = []
            for entry in parsed_json['data']:
                if 'scene' in entry:
                    cl.append([
                        "UPDATE tv_episodes SET scene_season = ?, scene_episode = ?, scene_absolute_number = ? "
                        "WHERE indexer = ? AND showid = ? AND season = ? AND episode = ?",
                        [entry['scene']['season'], entry['scene']['episode'],
                         entry['scene']['absolute'], indexer_id, series_id,
                         entry[indexerApi(indexer_id).config['xem_origin']]['season'],
                         entry[indexerApi(indexer_id).config['xem_origin']]['episode']]
                    ])
                    cl.append([
                        "UPDATE tv_episodes SET absolute_number = ? "
                        "WHERE indexer = ? AND showid = ? AND season = ? AND episode = ? AND absolute_number = 0",
                        [entry[indexerApi(indexer_id).config['xem_origin']]['absolute'], indexer_id, series_id,
                         entry[indexerApi(indexer_id).config['xem_origin']]['season'],
                         entry[indexerApi(indexer_id).config['xem_origin']]['episode']]
                    ])
                if 'scene_2' in entry:  # for doubles
                    cl.append([
                        "UPDATE tv_episodes SET scene_season = ?, scene_episode = ?, scene_absolute_number = ? "
                        "WHERE indexer = ? AND showid = ? AND season = ? AND episode = ?",
                        [entry['scene_2']['season'], entry['scene_2']['episode'],
                         entry['scene_2']['absolute'], indexer_id, series_id,
                         entry[indexerApi(indexer_id).config['xem_origin']]['season'],
                         entry[indexerApi(indexer_id).config['xem_origin']]['episode']]
                    ])

            if cl:
                main_db_con = db.DBConnection()
                main_db_con.mass_action(cl)

        except Exception as e:
            logger.log(u"Exception while refreshing XEM data for show ID {0} on {1}: {2}".format
                       (series_id, series_obj.indexer_name, ex(e)), logger.WARNING)
            logger.log(traceback.format_exc(), logger.DEBUG)


def fix_xem_numbering(series_obj):  # pylint:disable=too-many-locals, too-many-branches, too-many-statements
    """
    Returns a dict of (season, episode) : (sceneSeason, sceneEpisode) mappings
    for an entire show.  Both the keys and values of the dict are tuples.
    Will be empty if there are no scene numbers set in xem
    """
    if series_obj is None:
        return {}

    main_db_con = db.DBConnection()
    rows = main_db_con.select(
        'SELECT season, episode, absolute_number, scene_season, scene_episode, scene_absolute_number '
        'FROM tv_episodes '
        'WHERE indexer = ? AND showid = ?',
        [series_obj.indexer, series_obj.series_id])

    last_absolute_number = None
    last_scene_season = None
    last_scene_episode = None
    last_scene_absolute_number = None

    update_absolute_number = False
    update_scene_season = False
    update_scene_episode = False
    update_scene_absolute_number = False

    logger.log(
        u'Fixing any XEM scene mapping issues for show ID {0} on {1}'.format(series_obj.series_id, series_obj.indexer_name),
        logger.DEBUG)

    cl = []
    for row in rows:
        season = int(row[b'season'])
        episode = int(row[b'episode'])

        if not int(row[b'scene_season']) and last_scene_season:
            scene_season = last_scene_season + 1
            update_scene_season = True
        else:
            scene_season = int(row[b'scene_season'])
            if last_scene_season and scene_season < last_scene_season:
                scene_season = last_scene_season + 1
                update_scene_season = True

        if not int(row[b'scene_episode']) and last_scene_episode:
            scene_episode = last_scene_episode + 1
            update_scene_episode = True
        else:
            scene_episode = int(row[b'scene_episode'])
            if last_scene_episode and scene_episode < last_scene_episode:
                scene_episode = last_scene_episode + 1
                update_scene_episode = True

        # check for unset values and correct them
        if not int(row[b'absolute_number']) and last_absolute_number:
            absolute_number = last_absolute_number + 1
            update_absolute_number = True
        else:
            absolute_number = int(row[b'absolute_number'])
            if last_absolute_number and absolute_number < last_absolute_number:
                absolute_number = last_absolute_number + 1
                update_absolute_number = True

        if not int(row[b'scene_absolute_number']) and last_scene_absolute_number:
            scene_absolute_number = last_scene_absolute_number + 1
            update_scene_absolute_number = True
        else:
            scene_absolute_number = int(row[b'scene_absolute_number'])
            if last_scene_absolute_number and scene_absolute_number < last_scene_absolute_number:
                scene_absolute_number = last_scene_absolute_number + 1
                update_scene_absolute_number = True

        # store values for lookup on next iteration
        last_absolute_number = absolute_number
        last_scene_season = scene_season
        last_scene_episode = scene_episode
        last_scene_absolute_number = scene_absolute_number

        if update_absolute_number:
            cl.append([
                "UPDATE tv_episodes SET absolute_number = ? WHERE indexer = ? AND showid = ? AND season = ? AND episode = ?",
                [absolute_number, series_obj.indexer, series_obj.series_id, season, episode]
            ])
            update_absolute_number = False

        if update_scene_season:
            cl.append([
                "UPDATE tv_episodes SET scene_season = ? WHERE indexer = ? AND showid = ? AND season = ? AND episode = ?",
                [scene_season, series_obj.indexer, series_obj.series_id, season, episode]
            ])
            update_scene_season = False

        if update_scene_episode:
            cl.append([
                "UPDATE tv_episodes SET scene_episode = ? WHERE indexer = ? AND showid = ? AND season = ? AND episode = ?",
                [scene_episode, series_obj.indexer, series_obj.series_id, season, episode]
            ])
            update_scene_episode = False

        if update_scene_absolute_number:
            cl.append([
                "UPDATE tv_episodes SET scene_absolute_number = ? WHERE indexer = ? AND showid = ? AND season = ? AND episode = ?",
                [scene_absolute_number, series_obj.indexer, series_obj.series_id, season, episode]
            ])
            update_scene_absolute_number = False

    if cl:
        main_db_con = db.DBConnection()
        main_db_con.mass_action(cl)
