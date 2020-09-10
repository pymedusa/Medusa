# coding=utf-8
"""Request handler for alias (scene exceptions)."""
from __future__ import unicode_literals

from os.path import basename

from medusa import db
from medusa.common import DOWNLOADED, FAILED, SNATCHED, SUBTITLED, statusStrings
from medusa.providers.generic_provider import GenericProvider
from medusa.server.api.v2.base import BaseRequestHandler
from medusa.tv.series import SeriesIdentifier


class HistoryHandler(BaseRequestHandler):
    """History request handler."""

    #: resource name
    name = 'history'
    #: identifier
    identifier = ('series_slug', r'\w+')
    #: path param
    path_param = ('path_param', r'\w+')
    #: allowed HTTP methods
    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')

    def get(self, series_slug, path_param):
        """
        Get history records.

        History records can be specified using a show slug.
        """
        sql_base = """
            SELECT rowid, date, action, quality,
                   provider, version, resource, size, proper_tags,
                   indexer_id, showid, season, episode, manually_searched, info_hash
            FROM history
        """
        params = []

        arg_page = self._get_page()
        arg_limit = self._get_limit(default=50)

        if series_slug is not None:
            series_identifier = SeriesIdentifier.from_slug(series_slug)
            if not series_identifier:
                return self._bad_request('Invalid series')

            sql_base += ' WHERE indexer_id = ? AND showid = ?'
            params += [series_identifier.indexer.id, series_identifier.id]

        sql_base += ' ORDER BY date DESC'
        results = db.DBConnection().select(sql_base, params)

        def data_generator():
            """Read and paginate history records."""
            start = arg_limit * (arg_page - 1)

            for item in results[start:start + arg_limit]:
                provider = {}
                release_group = None
                release_name = None
                file_name = None
                subtitle_language = None

                if item['action'] in (SNATCHED, FAILED):
                    provider.update({
                        'id': GenericProvider.make_id(item['provider']),
                        'name': item['provider']
                    })
                    release_name = item['resource']

                if item['action'] == DOWNLOADED:
                    release_group = item['provider']
                    file_name = item['resource']

                if item['action'] == SUBTITLED:
                    subtitle_language = item['resource']

                if item['action'] == SUBTITLED:
                    subtitle_language = item['resource']

                yield {
                    'id': item['rowid'],
                    'series': SeriesIdentifier.from_id(item['indexer_id'], item['showid']).slug,
                    'status': item['action'],
                    'statusName': statusStrings.get(item['action']),
                    'actionDate': item['date'],
                    'quality': item['quality'],
                    'resource': basename(item['resource']),
                    'size': item['size'],
                    'properTags': item['proper_tags'],
                    'season': item['season'],
                    'episode': item['episode'],
                    'manuallySearched': bool(item['manually_searched']),
                    'infoHash': item['info_hash'],
                    'provider': provider,
                    'release_name': release_name,
                    'releaseGroup': release_group,
                    'fileName': file_name,
                    'subtitleLanguage': subtitle_language
                }

        if not results:
            return self._not_found('History data not found')

        return self._paginate(data_generator=data_generator)

    def delete(self, identifier, **kwargs):
        """Delete a history record."""
        identifier = self._parse(identifier)
        if not identifier:
            return self._bad_request('Invalid history id')

        main_db_con = db.DBConnection()
        last_changes = main_db_con.connection.total_changes
        main_db_con.action('DELETE FROM history WHERE row_id = ?', [identifier])
        if main_db_con.connection.total_changes - last_changes <= 0:
            return self._not_found('History row not found')

        return self._no_content()
