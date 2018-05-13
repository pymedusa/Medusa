# coding=utf-8
"""Request handler for statistics."""
from __future__ import unicode_literals

from datetime import date

from medusa import db
from medusa.common import (
    FAILED,
    Quality,
    SKIPPED,
    UNAIRED,
    WANTED
)
from medusa.server.api.v2.base import BaseRequestHandler


class StatsHandler(BaseRequestHandler):
    """Statistics request handler."""

    #: resource name
    name = 'stats'
    #: identifier
    identifier = ('identifier', r'\w+')
    #: path param
    path_param = ('path_param', r'\w+')
    #: allowed HTTP methods
    allowed_methods = ('GET', )

    def get(self, identifier, path_param=None):
        """Query statistics.

        :param identifier:
        :param path_param:
        :type path_param: str
        """
        main_db_con = db.DBConnection()

        snatched = Quality.SNATCHED + Quality.SNATCHED_PROPER + Quality.SNATCHED_BEST
        downloaded = Quality.DOWNLOADED + Quality.ARCHIVED

        # FIXME: This inner join is not multi indexer friendly.
        sql_result = main_db_con.select(
            b"""
            SELECT indexer AS indexerId, showid AS seriesId,
              (SELECT COUNT(*) FROM tv_episodes
               WHERE showid=tv_eps.showid AND
                     indexer=tv_eps.indexer AND
                     season > 0 AND
                     episode > 0 AND
                     airdate > 1 AND
                     status IN {status_quality}
              ) AS epSnatched,
              (SELECT COUNT(*) FROM tv_episodes
               WHERE showid=tv_eps.showid AND
                     indexer=tv_eps.indexer AND
                     season > 0 AND
                     episode > 0 AND
                     airdate > 1 AND
                     status IN {status_download}
              ) AS epDownloaded,
              (SELECT COUNT(*) FROM tv_episodes
               WHERE showid=tv_eps.showid AND
                     indexer=tv_eps.indexer AND
                     season > 0 AND
                     episode > 0 AND
                     airdate > 1 AND
                     ((airdate <= {today} AND (status = {skipped} OR
                                               status = {wanted} OR
                                               status = {failed})) OR
                      (status IN {status_quality}) OR
                      (status IN {status_download}))
              ) AS epTotal,
              (SELECT airdate FROM tv_episodes
               WHERE showid=tv_eps.showid AND
                     indexer=tv_eps.indexer AND
                     airdate >= {today} AND
                     (status = {unaired} OR status = {wanted})
               ORDER BY airdate ASC
               LIMIT 1
              ) AS epAirsNext,
              (SELECT airdate FROM tv_episodes
               WHERE showid=tv_eps.showid AND
                     indexer=tv_eps.indexer AND
                     airdate > 1 AND
                     status <> {unaired}
               ORDER BY airdate DESC
               LIMIT 1
              ) AS epAirsPrev,
              (SELECT SUM(file_size) FROM tv_episodes
               WHERE showid=tv_eps.showid AND
                     indexer=tv_eps.indexer
              ) AS seriesSize
            FROM tv_episodes tv_eps
            GROUP BY showid, indexer
            """.format(status_quality='({statuses})'.format(statuses=','.join([str(x) for x in snatched])),
                       status_download='({statuses})'.format(statuses=','.join([str(x) for x in downloaded])),
                       skipped=SKIPPED, wanted=WANTED, unaired=UNAIRED, failed=FAILED,
                       today=date.today().toordinal())
        )

        stats_data = {}
        stats_data['seriesStat'] = list()
        stats_data['maxDownloadCount'] = 1000
        for cur_result in sql_result:
            stats_data['seriesStat'].append(dict(cur_result))
            if cur_result[b'epTotal'] > stats_data['maxDownloadCount']:
                stats_data['maxDownloadCount'] = cur_result[b'epTotal']

        stats_data['maxDownloadCount'] *= 100

        if identifier is not None:
            if identifier not in stats_data:
                return self._bad_request('{key} is a invalid path'.format(key=identifier))

            stats_data = stats_data[identifier]

        return self._ok(data=stats_data)
