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
import logging
import time
import traceback
from builtins import str

from medusa import db, logger
from medusa.helper.common import episode_num
from medusa.helper.exceptions import ex
from medusa.indexers.api import indexerApi
from medusa.logger.adapters.style import BraceAdapter
from medusa.scene_exceptions import safe_session

from six import viewitems


log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


def find_scene_numbering(series_obj, season, episode):
    """
    Same as get_scene_numbering(), but returns None if scene numbering is not set
    """
    if series_obj is None or season is None or episode is None:
        return season, episode

    main_db_con = db.DBConnection()
    rows = main_db_con.select(
        'SELECT scene_season, scene_episode FROM scene_numbering WHERE indexer = ? '
        'and indexer_id = ? and season = ? and episode = ? and (scene_season or scene_episode) != 0',
        [series_obj.indexer, series_obj.series_id, season, episode])

    if rows:
        return int(rows[0]['scene_season']), int(rows[0]['scene_episode'])


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
    Get scene absolute numbering.

    Returns None if scene numbering is not set.
    """
    if series_obj is None or absolute_number is None:
        return absolute_number

    main_db_con = db.DBConnection()
    rows = main_db_con.select(
        'SELECT scene_absolute_number FROM scene_numbering WHERE indexer = ? and indexer_id = ? and absolute_number = ? and scene_absolute_number != 0',
        [series_obj.indexer, series_obj.series_id, absolute_number])

    if rows:
        return int(rows[0]['scene_absolute_number'])


def set_scene_numbering(series_obj, season=None, episode=None,
                        absolute_number=None, scene_season=None,
                        scene_episode=None, scene_absolute=None):
    """
    Set scene numbering for a season/episode.

    To clear the scene numbering, leave both scene_season and scene_episode as None.
    """
    if series_obj is None:
        return

    main_db_con = db.DBConnection()
    # Season/episode can be 0 so can't check "if season"
    if season is not None and episode is not None and absolute_number is None:
        main_db_con.action(
            'INSERT OR IGNORE INTO scene_numbering (indexer, indexer_id, season, episode) VALUES (?,?,?,?)',
            [series_obj.indexer, series_obj.series_id, season, episode])

        main_db_con.action(
            'UPDATE scene_numbering SET scene_season = ?, scene_episode = ? WHERE indexer = ? and indexer_id = ? and season = ? and episode = ?',
            [scene_season, scene_episode, series_obj.indexer, series_obj.series_id, season, episode])
    # absolute_number can be 0 so can't check "if absolute_number"
    else:
        main_db_con.action(
            'INSERT OR IGNORE INTO scene_numbering (indexer, indexer_id, absolute_number) VALUES (?,?,?)',
            [series_obj.indexer, series_obj.series_id, absolute_number])

        main_db_con.action(
            'UPDATE scene_numbering SET scene_absolute_number = ? WHERE indexer = ? and indexer_id = ? and absolute_number = ?',
            [scene_absolute, series_obj.indexer, series_obj.series_id, absolute_number])

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
        'SELECT scene_season, scene_episode '
        'FROM tv_episodes '
        'WHERE indexer = ? and showid = ? and season = ? '
        'and episode = ? and (scene_season or scene_episode) != 0',
        [series_obj.indexer, series_obj.series_id, season, episode]
    )

    if rows:
        return int(rows[0]['scene_season']), int(rows[0]['scene_episode'])


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
        'SELECT scene_absolute_number '
        'FROM tv_episodes '
        'WHERE indexer = ? and showid = ? '
        'and absolute_number = ? and scene_absolute_number != 0',
        [series_obj.indexer, series_obj.series_id, absolute_number])

    if rows:
        return int(rows[0]['scene_absolute_number'])


def get_scene_numbering(series_obj, episode, season=None):
    xem_refresh(series_obj)
    main_db_con = db.DBConnection()

    if season is None:
        rows = main_db_con.select(
            'SELECT season, episode FROM tv_episodes '
            'WHERE indexer = ? AND showid = ? AND scene_absolute_number = ?',
            [series_obj.indexer, series_obj.series_id, episode]
        )
    else:
        rows = main_db_con.select(
            'SELECT season, episode FROM tv_episodes '
            'WHERE indexer = ? AND showid = ? '
            'AND scene_season = ? AND scene_episode = ?',
            [series_obj.indexer, series_obj.series_id, season, episode]
        )

    if not rows:
        return None, None

    (new_sea, new_ep) = int(rows[0]['season']), int(rows[0]['episode'])
    log.debug('Found numbering {new} from scene for show {show} {old}', {
        'new': episode_num(new_sea, new_ep),
        'show': series_obj.name,
        'old': episode_num(season, episode)
    })
    return new_sea, new_ep


def get_scene_abs_number(series_obj, episode, season=None):
    xem_refresh(series_obj)
    main_db_con = db.DBConnection()

    if season is None:
        rows = main_db_con.select(
            'SELECT absolute_number FROM tv_episodes '
            'WHERE indexer = ? AND showid = ? AND scene_absolute_number = ?',
            [series_obj.indexer, series_obj.series_id, episode]
        )
    else:
        rows = main_db_con.select(
            'SELECT absolute_number FROM tv_episodes '
            'WHERE indexer = ? AND showid = ? '
            'AND scene_season = ? AND scene_episode = ?',
            [series_obj.indexer, series_obj.series_id, season, episode]
        )

    if rows:
        absolute_number = int(rows[0]['absolute_number'])
        log.debug('Found absolute number {absolute} from scene for show {show} {ep}', {
            'absolute': absolute_number,
            'show': series_obj.name,
            'ep': episode_num(season, episode),
        })
        return absolute_number


def get_custom_numbering(series_obj, episode, season=None):
    main_db_con = db.DBConnection()

    if season is None:
        rows = main_db_con.select(
            'SELECT season, episode FROM scene_numbering '
            'WHERE indexer = ? AND indexer_id = ? AND scene_absolute_number = ?',
            [series_obj.indexer, series_obj.series_id, episode]
        )
    else:
        rows = main_db_con.select(
            'SELECT season, episode FROM scene_numbering '
            'WHERE indexer = ? AND indexer_id = ? '
            'AND scene_season = ? AND scene_episode = ?',
            [series_obj.indexer, series_obj.series_id, season, episode]
        )

    if not rows:
        return None, None

    (new_sea, new_ep) = int(rows[0]['season']), int(rows[0]['episode'])
    log.debug('Found numbering {new} from scene for show {show} {old}', {
        'new': episode_num(new_sea, new_ep),
        'show': series_obj.name,
        'old': episode_num(season, episode)
    })
    return new_sea, new_ep


def get_custom_abs_number(series_obj, episode, season=None):
    main_db_con = db.DBConnection()

    if season is None:
        rows = main_db_con.select(
            'SELECT absolute_number FROM scene_numbering '
            'WHERE indexer = ? AND indexer_id = ? AND scene_absolute_number = ?',
            [series_obj.indexer, series_obj.series_id, episode]
        )
    else:
        rows = main_db_con.select(
            'SELECT absolute_number FROM scene_numbering '
            'WHERE indexer = ? AND indexer_id = ? '
            'AND scene_season = ? AND scene_episode = ?',
            [series_obj.indexer, series_obj.series_id, season, episode]
        )

    if rows:
        absolute_number = int(rows[0]['absolute_number'])
        log.debug('Found absolute number {absolute} from custom for show {show} {ep}', {
            'absolute': absolute_number,
            'show': series_obj.name,
            'ep': episode_num(season, episode),
        })
        return absolute_number


def get_indexer_numbering(series_obj, episode, season=None):
    """Find the numbering for a show episode and season.

    :param series_obj: Show object
    :param episode: Episode number
    :param season: Season number (optional)
    :return: Tuple, (season, episode) or (None, None)
    """
    numbering = get_custom_numbering(series_obj, episode, season)
    if all(number is not None for number in numbering):
        return numbering

    if series_obj.is_scene:
        numbering = get_scene_numbering(series_obj, episode, season)
        if all(number is not None for number in numbering):
            return numbering

    if season is not None:
        log.debug('Found numbering {new} from parser for show {show} {old}', {
            'new': episode_num(season, episode),
            'show': series_obj.name,
            'old': episode_num(season, episode)
        })
        return season, episode

    main_db_con = db.DBConnection()
    rows = main_db_con.select(
        'SELECT season, episode FROM tv_episodes '
        'WHERE indexer = ? AND showid = ? '
        'AND absolute_number = ?',
        [series_obj.indexer, series_obj.series_id, episode]
    )

    if not rows:
        log.debug('No entries for numbering for show {show} {ep}',
                  {'show': series_obj.name, 'ep': episode_num(season, episode)})
        return None, None

    (new_sea, new_ep) = int(rows[0]['season']), int(rows[0]['episode'])
    log.debug('Found numbering {new} from indexer for show {show} {old}', {
        'new': episode_num(new_sea, new_ep),
        'show': series_obj.name,
        'old': episode_num(season, episode)
    })
    return new_sea, new_ep


def get_indexer_abs_numbering(series_obj, episode, season=None):
    """Find the absolute numbering for a show episode and season.

    :param series_obj: Show object
    :param episode: Episode number
    :param season: Season number (optional)
    :return: The absolute number or None
    """
    abs_number = get_custom_abs_number(series_obj, episode, season)
    if abs_number:
        return abs_number

    if series_obj.is_scene:
        abs_number = get_scene_abs_number(series_obj, episode, season)
        if abs_number:
            return abs_number

    if season is None:
        abs_number = episode
        log.debug('Found absolute number {absolute} from parser for show {show} {ep}', {
            'absolute': abs_number,
            'show': series_obj.name,
            'ep': episode_num(season, episode),
        })
        return abs_number

    main_db_con = db.DBConnection()
    rows = main_db_con.select(
        'SELECT absolute_number FROM tv_episodes '
        'WHERE indexer = ? AND showid = ? '
        'AND season = ? AND episode = ?',
        [series_obj.indexer, series_obj.series_id, season, episode]
    )

    if rows:
        abs_number = int(rows[0]['absolute_number'])
        log.debug('Found absolute number {absolute} from indexer for show {show} {ep}', {
            'absolute': abs_number,
            'show': series_obj.name,
            'ep': episode_num(season, episode),
        })
        return abs_number

    log.debug('No entries for absolute number for show {show} {ep}',
              {'show': series_obj.name, 'ep': episode_num(season, episode)})


def get_scene_numbering_for_show(series_obj):
    """
    Returns a dict of (season, episode) : (scene_season, scene_episode) mappings for an entire show.

    Both the keys and values of the dict are tuples.
    Will be empty if there are no scene numbers set
    """
    if series_obj is None:
        return {}

    main_db_con = db.DBConnection()
    rows = main_db_con.select(
        'SELECT season, episode, scene_season, scene_episode '
        'FROM scene_numbering WHERE indexer = ? AND indexer_id = ? '
        'AND (scene_season or scene_episode) != 0 ORDER BY season, episode',
        [series_obj.indexer, series_obj.series_id])

    result = {}
    for row in rows:
        season = int(row['season'])
        episode = int(row['episode'])
        scene_season = int(row['scene_season'])
        scene_episode = int(row['scene_episode'])

        result[(season, episode)] = (scene_season, scene_episode)

    return result


def get_xem_numbering_for_show(series_obj, refresh_data=True):
    """
    Return a dict of (season, episode) : (scene_season, scene_episode) mappings for an entire show.

    Both the keys and values of the dict are tuples.
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
        season = int(row['season'])
        episode = int(row['episode'])
        scene_season = int(row['scene_season'])
        scene_episode = int(row['scene_episode'])

        result[(season, episode)] = (scene_season, scene_episode)

    return result


def get_scene_absolute_numbering_for_show(series_obj):
    """
    Return a dict of (season, episode) : (scene_season, scene_episode) mappings for an entire show.

    Both the keys and values of the dict are tuples.
    Will be empty if there are no scene numbers set
    """
    if series_obj is None:
        return {}

    main_db_con = db.DBConnection()
    rows = main_db_con.select(
        'SELECT absolute_number, scene_absolute_number '
        'FROM scene_numbering WHERE indexer = ? AND indexer_id = ? '
        'AND scene_absolute_number != 0 ORDER BY absolute_number',
        [series_obj.indexer, series_obj.series_id])

    result = {}
    for row in rows:
        absolute_number = int(row['absolute_number'])
        scene_absolute_number = int(row['scene_absolute_number'])

        result[absolute_number] = scene_absolute_number

    return result


def get_xem_absolute_numbering_for_show(series_obj):
    """
    Return a dict of (season, episode) : (scene_season, scene_episode) mappings for an entire show.

    Both the keys and values of the dict are tuples.
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
        absolute_number = int(row['absolute_number'])
        scene_absolute_number = int(row['scene_absolute_number'])

        result[absolute_number] = scene_absolute_number

    return result


def xem_refresh(series_obj, force=False):
    """
    Refresh data from xem for a tv show.

    :param indexer_id: int
    """
    if not series_obj or series_obj.series_id < 1:
        return

    indexer_id = series_obj.indexer
    series_id = series_obj.series_id

    MAX_REFRESH_AGE_SECS = 86400  # 1 day

    main_db_con = db.DBConnection()
    rows = main_db_con.select('SELECT last_refreshed FROM xem_refresh WHERE indexer = ? and indexer_id = ?',
                              [indexer_id, series_id])
    if rows:
        last_refresh = int(rows[0]['last_refreshed'])
        refresh = int(time.mktime(datetime.datetime.today().timetuple())) > last_refresh + MAX_REFRESH_AGE_SECS
    else:
        refresh = True

    if refresh or force:
        logger.log(
            u'Looking up XEM scene mapping for show ID {0} on {1}'.format(series_id, series_obj.indexer_name), logger.DEBUG)

        # mark refreshed
        main_db_con.upsert(
            'xem_refresh',
            {'last_refreshed': int(time.mktime(datetime.datetime.today().timetuple()))},
            {'indexer': indexer_id, 'indexer_id': series_id}
        )

        try:
            if not indexerApi(indexer_id).config.get('xem_origin'):
                logger.log(u'{0} is an unsupported indexer in XEM'.format(indexerApi(indexer_id).name), logger.DEBUG)
                return
            # XEM MAP URL
            url = 'http://thexem.de/map/havemap?origin={0}'.format(indexerApi(indexer_id).config['xem_origin'])
            parsed_json = safe_session.get_json(url)
            if not parsed_json or 'result' not in parsed_json or 'success' not in parsed_json['result'] or 'data' not in parsed_json or str(series_id) not in parsed_json['data']:
                logger.log(u'No XEM data for show ID {0} on {1}'.format(series_id, series_obj.indexer_name), logger.DEBUG)
                return

            # XEM API URL
            url = 'http://thexem.de/map/all?id={0}&origin={1}&destination=scene'.format(series_id, indexerApi(indexer_id).config['xem_origin'])
            parsed_json = safe_session.get_json(url)
            if not parsed_json or 'result' not in parsed_json or 'success' not in parsed_json['result']:
                logger.log(u'No XEM data for show ID {0} on {1}'.format(indexer_id, series_obj.indexer_name), logger.DEBUG)
                return

            cl = []
            for entry in parsed_json['data']:
                if 'scene' in entry:
                    cl.append([
                        'UPDATE tv_episodes SET scene_season = ?, scene_episode = ?, scene_absolute_number = ? '
                        'WHERE indexer = ? AND showid = ? AND season = ? AND episode = ?',
                        [entry['scene']['season'], entry['scene']['episode'],
                         entry['scene']['absolute'], indexer_id, series_id,
                         entry[indexerApi(indexer_id).config['xem_origin']]['season'],
                         entry[indexerApi(indexer_id).config['xem_origin']]['episode']]
                    ])
                    # Update the absolute_number from xem, but do not set it when it has already been set by tvdb.
                    # We want to prevent doubles and tvdb is leading in that case.
                    cl.append([
                        'UPDATE tv_episodes SET absolute_number = ? '
                        'WHERE indexer = ? AND showid = ? AND season = ? AND episode = ? AND absolute_number = 0 '
                        'AND {absolute_number} NOT IN '
                        '(SELECT absolute_number '
                        'FROM tv_episodes '
                        'WHERE absolute_number = ? AND indexer = ? AND showid = ?)'.format(
                            absolute_number=entry[indexerApi(indexer_id).config['xem_origin']]['absolute']
                        ),
                        [entry[indexerApi(indexer_id).config['xem_origin']]['absolute'], indexer_id, series_id,
                         entry[indexerApi(indexer_id).config['xem_origin']]['season'],
                         entry[indexerApi(indexer_id).config['xem_origin']]['episode'],
                         entry[indexerApi(indexer_id).config['xem_origin']]['absolute'],
                         indexer_id, series_id]
                    ])
                if 'scene_2' in entry:  # for doubles
                    cl.append([
                        'UPDATE tv_episodes SET scene_season = ?, scene_episode = ?, scene_absolute_number = ? '
                        'WHERE indexer = ? AND showid = ? AND season = ? AND episode = ?',
                        [entry['scene_2']['season'], entry['scene_2']['episode'],
                         entry['scene_2']['absolute'], indexer_id, series_id,
                         entry[indexerApi(indexer_id).config['xem_origin']]['season'],
                         entry[indexerApi(indexer_id).config['xem_origin']]['episode']]
                    ])

            if cl:
                main_db_con = db.DBConnection()
                main_db_con.mass_action(cl)

        except Exception as e:
            logger.log(u'Exception while refreshing XEM data for show ID {0} on {1}: {2}'.format
                       (series_id, series_obj.indexer_name, ex(e)), logger.WARNING)
            logger.log(traceback.format_exc(), logger.DEBUG)


def numbering_tuple_to_dict(values, left_desc='source', right_desc='destination', level_2_left='season', level_2_right='episode'):
    """
    Convert a dictionary with tuple to tuple (key/value) mapping to a json structure.

    For each key/value pair, create a new dictionary and move key/value to a new object,
    with left_desc and right_desc as its keys.

    This method is required because the swagger spec does not support describing the dynamic key/value mapping.
    The json schema supports additionalProperties (which is required to document this). But Swagger itself has limited support for it.
    https://support.reprezen.com/support/solutions/articles/6000162892-support-for-additionalproperties-in-swagger-2-0-schemas.

    For example the values {(a, b): (c: d)} will be transformed to:
    [{"source": {"season": a, "episode": b}, "destination": {"season": c, "episode": d}}]

    :param values: Dict with double tuple mapping. For example: (src season, src episode): (dest season, dest episode).
    :param left_desc: The key description used for the orginal "key" value.
    :param right_desc: The key description used for the original "value" value.
    :param level_2_left: When passing {tuple: tuple}, it's used to map the value of the first tuple's value.
    :param level_2_right: When passing {tuple: tuple}, it's used to map the value of the second tuple's value.
    :return: List of dictionaries with dedicated keys for source and destination.
    """
    return [{left_desc: {level_2_left: src[0], level_2_right: src[1]},
             right_desc: {level_2_left: dest[0], level_2_right: dest[1]}}
            for src, dest in viewitems(values)]
