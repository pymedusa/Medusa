# coding=utf-8
# Author: Tyler Fenby <tylerfenby@gmail.com>

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
"""failed history code."""
import re

from datetime import datetime, timedelta

from . import db, logger
from .common import FAILED, Quality, WANTED, statusStrings
from .helper.common import episode_num
from .helper.exceptions import EpisodeNotFoundException
from .show.history import History


def prepare_failed_name(release):
    """Standardize release name for failed DB."""
    if release.endswith('.nzb'):
        release = release.rpartition('.')[0]

    fixed = re.sub(r'\W', '_', release)

    return fixed


def log_failed(release):
    """Log release as failed in failed.db."""
    log_str = u''
    size = -1
    provider = ''

    release = prepare_failed_name(release)

    failed_db_con = db.DBConnection('failed.db')
    sql_results = failed_db_con.select(
        'SELECT * '
        'FROM history '
        'WHERE release=?',
        [release]
    )

    if not sql_results:
        logger.log(u'Release not found in snatch history: {0}'.format(release), logger.WARNING)
    elif len(sql_results) == 1:
        size = sql_results[0]['size']
        provider = sql_results[0]['provider']
    else:
        logger.log(u'Multiple logged snatches found for release',
                   logger.WARNING)
        sizes = len(set(x['size'] for x in sql_results))
        providers = len(set(x['provider'] for x in sql_results))
        if sizes == 1:
            logger.log(u'However, they are all the same size. '
                       u'Continuing with found size.', logger.WARNING)
            size = sql_results[0]['size']
        else:
            logger.log(u'They also vary in size. '
                       u'Deleting the logged snatches and recording this '
                       u'release with no size/provider', logger.WARNING)
            for result in sql_results:
                delete_logged_snatch(
                    result['release'],
                    result['size'],
                    result['provider']
                )

        if providers == 1:
            logger.log(u'They are also from the same provider. '
                       u'Using it as well.')
            provider = sql_results[0]['provider']

    if not has_failed(release, size, provider):
        failed_db_con = db.DBConnection('failed.db')
        failed_db_con.action(
            'INSERT INTO failed (release, size, provider) '
            'VALUES (?, ?, ?)',
            [release, size, provider]
        )

    delete_logged_snatch(release, size, provider)

    return log_str


def log_success(release):
    """Log release as success on failed.db."""
    release = prepare_failed_name(release)

    failed_db_con = db.DBConnection('failed.db')
    failed_db_con.action(
        'DELETE '
        'FROM history '
        'WHERE release=?',
        [release]
    )


def has_failed(release, size, provider='%'):
    """
    Return True if a release has previously failed.

    If provider is given, return True only if the release is found
    with that specific provider. Otherwise, return True if the release
    is found with any provider.

    :param release: Release name to record failure
    :param size: Size of release
    :param provider: Specific provider to search (defaults to all providers)
    :return: True if a release has previously failed.
    """
    release = prepare_failed_name(release)

    failed_db_con = db.DBConnection('failed.db')
    sql_results = failed_db_con.select(
        'SELECT release '
        'FROM failed '
        'WHERE release=?'
        ' AND size=?'
        ' AND provider LIKE ? '
        'LIMIT 1',
        [release, size, provider]
    )

    return len(sql_results) > 0


def revert_episode(ep_obj):
    """Restore the episodes of a failed download to their original state."""
    failed_db_con = db.DBConnection('failed.db')
    sql_results = failed_db_con.select(
        'SELECT episode, old_status '
        'FROM history '
        'WHERE showid=?'
        ' AND season=?',
        [ep_obj.show.indexerid, ep_obj.season]
    )

    history_eps = {res['episode']: res for res in sql_results}

    try:
        logger.log(u'Reverting episode status for {show} {ep}. Checking if we have previous status'.format
                   (show=ep_obj.name, ep=episode_num(ep_obj.season, ep_obj.episode)))
        with ep_obj.lock:
            if ep_obj.episode in history_eps:
                ep_obj.status = history_eps[ep_obj.episode]['old_status']
                logger.log(u'Episode have a previous status to revert. Setting it back to {0}'.format
                           (statusStrings[ep_obj.status]), logger.DEBUG)
            else:
                logger.log(u'Episode does not have a previous snatched status '
                           u'to revert. Setting it back to WANTED',
                           logger.DEBUG)
                ep_obj.status = WANTED
            ep_obj.save_to_db()

    except EpisodeNotFoundException as error:
        logger.log(u'Unable to create episode, please set its status '
                   u'manually: {error}'.format(error=error),
                   logger.WARNING)


def mark_failed(ep_obj):
    """
    Mark an episode as failed.

    :param ep_obj: Episode object to mark as failed
    :return: empty string
    """
    log_str = u''

    try:
        with ep_obj.lock:
            quality = Quality.split_composite_status(ep_obj.status)[1]
            ep_obj.status = Quality.composite_status(FAILED, quality)
            ep_obj.save_to_db()

    except EpisodeNotFoundException as error:
        logger.log(u'Unable to get episode, please set its status '
                   u'manually: {error}'.format(error=error),
                   logger.WARNING)

    return log_str


def log_snatch(search_result):
    """
    Log a successful snatch.

    :param search_result: Search result that was successful
    """
    log_date = datetime.today().strftime(History.date_format)
    release = prepare_failed_name(search_result.name)

    provider_class = search_result.provider
    if provider_class is not None:
        provider = provider_class.name
    else:
        provider = 'unknown'

    show_obj = search_result.episodes[0].show

    failed_db_con = db.DBConnection('failed.db')
    for episode in search_result.episodes:
        failed_db_con.action(
            'INSERT INTO history '
            '(date, size, release, provider, showid,'
            ' season, episode, old_status)'
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            [log_date, search_result.size, release, provider, show_obj.indexerid,
             episode.season, episode.episode, episode.status]
        )


def delete_logged_snatch(release, size, provider):
    """
    Remove a snatch from history.

    :param release: release to delete
    :param size: Size of release
    :param provider: Provider to delete it from
    """
    release = prepare_failed_name(release)

    failed_db_con = db.DBConnection('failed.db')
    failed_db_con.action(
        'DELETE FROM history '
        'WHERE release=?'
        ' AND size=?'
        ' AND provider=?',
        [release, size, provider]
    )


def trim_history(days=30, seconds=0, microseconds=0, milliseconds=0,
                 minutes=0, hours=0, weeks=0):
    """Trim old results from failed history."""
    today = datetime.today()
    age = timedelta(days, seconds, microseconds, milliseconds,
                    minutes, hours, weeks)

    failed_db_con = db.DBConnection('failed.db')
    failed_db_con.action(
        'DELETE FROM history '
        'WHERE date < ?',
        [(today - age).strftime(History.date_format)]
    )


def find_release(ep_obj):
    """
    Find releases in history by show ID and season.

    Return None for release if multiple found or no release found.
    """
    release = None
    provider = None

    # Clear old snatches for this release if any exist
    failed_db_con = db.DBConnection('failed.db')
    # failed_db_con.action(
    #     'DELETE FROM history '
    #     'WHERE showid = {0}'
    #     ' AND season = {1}'
    #     ' AND episode = {2}'
    #     ' AND date < ( SELECT max(date)'
    #     '              FROM history'
    #     '              WHERE showid = {0}'
    #     '               AND season = {1}'
    #     '               AND episode = {2}'
    #     '             )'.format
    #     (ep_obj.show.indexerid, ep_obj.season, ep_obj.episode)
    # )

    # Search for release in snatch history
    results = failed_db_con.select(
        'SELECT release, provider, date '
        'FROM history '
        'WHERE showid=?'
        ' AND season=?'
        ' AND episode=?',
        [ep_obj.show.indexerid, ep_obj.season, ep_obj.episode]
    )

    for result in results:
        release = str(result['release'])
        provider = str(result['provider'])
        date = result['date']

        # Clear any incomplete snatch records for this release if any exist
        failed_db_con.action(
            'DELETE FROM history '
            'WHERE release=?'
            ' AND date!=?',
            [release, date]
        )

        # Found a previously failed release
        logger.log(u'Failed release found for {show} {ep}: {release}'.format
                   (show=ep_obj.name, ep=episode_num(ep_obj.season, ep_obj.episode),
                    release=result['release']), logger.DEBUG)
        return release, provider

    # Release was not found
    logger.log(u'No releases found for {show} {ep}'.format
               (show=ep_obj.name, ep=episode_num(ep_obj.season, ep_obj.episode)), logger.DEBUG)
    return release, provider
