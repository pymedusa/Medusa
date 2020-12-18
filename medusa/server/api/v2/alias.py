# coding=utf-8
"""Request handler for alias (scene exceptions)."""
from __future__ import unicode_literals

from medusa import db
from medusa.server.api.v2.base import BaseRequestHandler
from medusa.tv.series import SeriesIdentifier

from tornado.escape import json_decode


class AliasHandler(BaseRequestHandler):
    """Alias request handler."""

    #: resource name
    name = 'alias'
    #: identifier
    identifier = ('identifier', r'\d+')
    #: path param
    path_param = ('path_param', r'\w+')
    #: allowed HTTP methods
    allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')

    def get(self, identifier, path_param):
        """Query scene_exception information."""
        main_db_con = db.DBConnection()
        sql_base = ('SELECT '
                    '  exception_id, '
                    '  indexer, '
                    '  series_id, '
                    '  title, '
                    '  season, '
                    '  custom '
                    'FROM scene_exceptions ')
        sql_where = []
        params = []

        if identifier is not None:
            sql_where.append('exception_id')
            params += [identifier]
        else:
            series_slug = self.get_query_argument('series', None)
            series_identifier = SeriesIdentifier.from_slug(series_slug)

            if series_slug and not series_identifier:
                return self._bad_request('Invalid series')

            season = self._parse(self.get_query_argument('season', None))
            exception_type = self.get_query_argument('type', None)
            if exception_type and exception_type not in ('local', ):
                return self._bad_request('Invalid type')

            if series_identifier:
                sql_where.append('indexer')
                sql_where.append('series_id')
                params += [series_identifier.indexer.id, series_identifier.id]

            if season is not None:
                sql_where.append('season')
                params += [season]

            if exception_type == 'local':
                sql_where.append('custom')
                params += [1]

        if sql_where:
            sql_base += ' WHERE ' + ' AND '.join([where + ' = ? ' for where in sql_where])

        sql_results = main_db_con.select(sql_base, params)

        data = []
        for item in sql_results:
            d = {}
            d['id'] = item['exception_id']
            d['series'] = SeriesIdentifier.from_id(item['indexer'], item['series_id']).slug
            d['name'] = item['title']
            d['season'] = item['season'] if item['season'] >= 0 else None
            d['type'] = 'local' if item['custom'] else None
            data.append(d)

        if not identifier:
            return self._paginate(data, sort='id')

        if not data:
            return self._not_found('Alias not found')

        data = data[0]
        if path_param:
            if path_param not in data:
                return self._bad_request('Invalid path parameter')
            data = data[path_param]

        return self._ok(data=data)

    def put(self, identifier, **kwargs):
        """Update alias information."""
        identifier = self._parse(identifier)
        if not identifier:
            return self._not_found('Invalid alias id')

        data = json_decode(self.request.body)

        if not data or not all([data.get('id'), data.get('series'), data.get('name'),
                                data.get('type')]) or data['id'] != identifier:
            return self._bad_request('Invalid request body')

        series_identifier = SeriesIdentifier.from_slug(data.get('series'))
        if not series_identifier:
            return self._bad_request('Invalid series')

        main_db_con = db.DBConnection()
        last_changes = main_db_con.connection.total_changes
        main_db_con.action('UPDATE scene_exceptions'
                           ' set indexer = ?'
                           ', series_id = ?'
                           ', title = ?'
                           ', season = ?'
                           ', custom = 1'
                           ' WHERE exception_id = ?',
                           [series_identifier.indexer.id,
                            series_identifier.id,
                            data['name'],
                            data.get('season'),
                            identifier])

        if main_db_con.connection.total_changes - last_changes != 1:
            return self._not_found('Alias not found')

        return self._no_content()

    def post(self, identifier, **kwargs):
        """Add an alias."""
        if identifier is not None:
            return self._bad_request('Alias id should not be specified')

        data = json_decode(self.request.body)

        if not data or not all([data.get('series'), data.get('name'),
                                data.get('type')]) or 'id' in data or data['type'] != 'local':
            return self._bad_request('Invalid request body')

        series_identifier = SeriesIdentifier.from_slug(data.get('series'))
        if not series_identifier:
            return self._bad_request('Invalid series')

        main_db_con = db.DBConnection()
        last_changes = main_db_con.connection.total_changes
        cursor = main_db_con.action('INSERT INTO scene_exceptions'
                                    ' (indexer, series_id, title, season, custom) '
                                    ' values (?,?,?,?,1)',
                                    [series_identifier.indexer.id,
                                     series_identifier.id,
                                     data['name'],
                                     data.get('season', -1)])

        if main_db_con.connection.total_changes - last_changes <= 0:
            return self._conflict('Unable to create alias')

        data['id'] = cursor.lastrowid
        return self._created(data=data, identifier=data['id'])

    def delete(self, identifier, **kwargs):
        """Delete an alias."""
        identifier = self._parse(identifier)
        if not identifier:
            return self._bad_request('Invalid alias id')

        main_db_con = db.DBConnection()
        last_changes = main_db_con.connection.total_changes
        main_db_con.action('DELETE FROM scene_exceptions WHERE exception_id = ?', [identifier])
        if main_db_con.connection.total_changes - last_changes <= 0:
            return self._not_found('Alias not found')

        return self._no_content()
