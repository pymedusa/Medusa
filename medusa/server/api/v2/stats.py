# coding=utf-8
"""Request handler for statistics."""
from __future__ import unicode_literals

from datetime import date
from textwrap import dedent

from medusa import db
from medusa.common import (
    ARCHIVED,
    DOWNLOADED,
    FAILED,
    SKIPPED,
    SNATCHED,
    SNATCHED_BEST,
    SNATCHED_PROPER,
    UNAIRED,
    WANTED
)
from medusa.network_timezones import parse_date_time
from medusa.server.api.v2.base import BaseRequestHandler
from medusa.show.show import Show

from six.moves import map


class StatsHandler(BaseRequestHandler):
    """Statistics request handler."""

    #: resource name
    name = 'stats'
    #: identifier
    identifier = ('identifier', r'\w+')
    #: path param
    path_param = None
    #: allowed HTTP methods
    allowed_methods = ('GET', )

    def get(self, identifier):
        """Query statistics.

        :param identifier: The type of statistics to query
        :type identifier: str
        """
        if not identifier or identifier == 'overall':
            data = overall_stats()
        elif identifier == 'show':
            data = per_show_stats()
        else:
            return self._not_found('Statistics not found')

        return self._ok(data=data)


def overall_stats():
    """Generate overall library statistics."""
    return Show.overall_stats()


def per_show_stats():
    """Generate per-show library statistics."""
    pre_today = [SKIPPED, WANTED, FAILED]
    snatched = [SNATCHED, SNATCHED_PROPER, SNATCHED_BEST]
    downloaded = [DOWNLOADED, ARCHIVED]

    def query_in(items):
        return '({0})'.format(','.join(map(str, items)))

    query = dedent("""\
        SELECT tv_eps.indexer AS indexerId, tv_eps.showid AS seriesId,
            SUM(
                season > 0 AND
                episode > 0 AND
                airdate > 1 AND
                tv_eps.status IN {status_quality}
            ) AS epSnatched,
            SUM(
                season > 0 AND
                episode > 0 AND
                airdate > 1 AND
                tv_eps.status IN {status_download}
            ) AS epDownloaded,
            SUM(
                season > 0 AND
                episode > 0 AND
                airdate > 1 AND (
                    (airdate <= {today} AND tv_eps.status IN {status_pre_today}) OR
                    tv_eps.status IN {status_both}
                )
            ) AS epTotal,
            (SELECT airdate FROM tv_episodes
            WHERE tv_episodes.showid=tv_eps.showid AND
                    tv_episodes.indexer=tv_eps.indexer AND
                    airdate >= {today} AND
                    (tv_eps.status = {unaired} OR tv_eps.status = {wanted})
            ORDER BY airdate ASC
            LIMIT 1
            ) AS epAirsNext,
            (SELECT airdate FROM tv_episodes
            WHERE tv_episodes.showid=tv_eps.showid AND
                    tv_episodes.indexer=tv_eps.indexer AND
                    airdate > {today} AND
                    tv_eps.status <> {unaired}
            ORDER BY airdate DESC
            LIMIT 1
            ) AS epAirsPrev,
            SUM(file_size) AS seriesSize,
            tv_shows.airs as airs,
            tv_shows.network as network
        FROM tv_episodes tv_eps, tv_shows
        WHERE tv_eps.showid = tv_shows.indexer_id AND tv_eps.indexer = tv_shows.indexer
        GROUP BY tv_eps.showid, tv_eps.indexer;
    """).format(
        status_quality=query_in(snatched),
        status_download=query_in(downloaded),
        status_both=query_in(snatched + downloaded),
        today=date.today().toordinal(),
        status_pre_today=query_in(pre_today),
        skipped=SKIPPED,
        wanted=WANTED,
        unaired=UNAIRED,
    )

    main_db_con = db.DBConnection()
    sql_result = main_db_con.select(query)

    stats_data = {}
    stats_data['stats'] = []
    stats_data['maxDownloadCount'] = 1000
    for cur_result in sql_result:
        stats_data['stats'].append(cur_result)
        if cur_result['epTotal'] > stats_data['maxDownloadCount']:
            stats_data['maxDownloadCount'] = cur_result['epTotal']
        if cur_result['epAirsNext']:
            cur_result['epAirsNext'] = parse_date_time(cur_result['epAirsNext'], cur_result['airs'], cur_result['network'])
        if cur_result['epAirsPrev']:
            cur_result['epAirsPrev'] = parse_date_time(cur_result['epAirsPrev'], cur_result['airs'], cur_result['network'])

    stats_data['maxDownloadCount'] *= 100
    return stats_data
