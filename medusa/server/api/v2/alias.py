# coding=utf-8
"""Request handler for alias (scene exceptions)."""

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
        series_slug = self.get_query_argument('series-identifier', None)
        series_identifier = SeriesIdentifier.from_slug(series_slug)

        if series_slug and not series_identifier:
            return self._bad_request('Invalid series-identifier')

        season = self._parse(self.get_query_argument('season', None))
        exception_type = self.get_query_argument('type', None) == 'local'

        cache_db_con = db.DBConnection('cache.db')
        sql_base = (b'SELECT '
                    b'  exception_id, '
                    b'  indexer, '
                    b'  indexer_id, '
                    b'  show_name, '
                    b'  season, '
                    b'  custom '
                    b'FROM scene_exceptions')
        sql_where = []
        params = []

        if identifier is not None:
            sql_where.append(b'exception_id')
            params += [identifier]

        if series_identifier:
            sql_where.append(b'indexer')
            sql_where.append(b'indexer_id')
            params += [series_identifier.indexer.id, series_identifier.id]

        if season is not None:
            sql_where.append(b'season')
            params += [season]

        if exception_type:
            sql_where.append(b'custom')
            params += [exception_type]

        if sql_where:
            sql_base += b' WHERE ' + b' AND '.join([where + b' = ? ' for where in sql_where])

        data = cache_db_con.select(sql_base, params)

        data = [{'id': row[0],
                 'series': SeriesIdentifier.from_id(row[1], row[2]).slug,
                 'name': row[3],
                 'season': row[4] if row[4] >= 0 else None,
                 'type': 'local' if row[5] else None}
                for row in data]

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
            return self._bad_request('Invalid alias id')

        data = json_decode(self.request.body)

        if not data or not all([data.get('id'), data.get('series'), data.get('name'),
                                data.get('season', None), data.get('type')]) or data['id'] != identifier:
            return self._bad_request('Invalid request body')

        series_identifier = SeriesIdentifier.from_slug(data.get('series'))
        if not series_identifier:
            return self._bad_request('Invalid series')

        cache_db_con = db.DBConnection('cache.db')
        last_changes = cache_db_con.connection.total_changes
        cache_db_con.action(b'UPDATE scene_exceptions'
                            b' set indexer = ?'
                            b', indexer_id = ?'
                            b', show_name = ?'
                            b', season = ?'
                            b', custom = 1'
                            b' WHERE exception_id = ?',
                            [series_identifier.indexer.id,
                             series_identifier.id,
                             data['name'],
                             data.get('season'),
                             identifier])

        if cache_db_con.connection.total_changes - last_changes != 1:
            return self._not_found('Alias not found')

        return self._no_content()

    def post(self, identifier, **kwargs):
        """Add an alias."""
        if identifier is not None:
            return self._bad_request('Alias id should not be specified')

        data = json_decode(self.request.body)

        if not data or not all([data.get('series'), data.get('name'), data.get('season', None),
                                data.get('type')]) or 'id' in data or data['type'] != 'local':
            return self._bad_request('Invalid request body')

        series_identifier = SeriesIdentifier.from_slug(data.get('series'))
        if not series_identifier:
            return self._bad_request('Invalid series')

        cache_db_con = db.DBConnection('cache.db')
        last_changes = cache_db_con.connection.total_changes
        cursor = cache_db_con.action(b'INSERT INTO scene_exceptions'
                                     b' (indexer, indexer_id, show_name, season, custom) '
                                     b' values (?,?,?,?,1)',
                                     [series_identifier.indexer.id,
                                      series_identifier.id,
                                      data['name'],
                                      data.get('season')])

        if cache_db_con.connection.total_changes - last_changes <= 0:
            return self._bad_request('Unable to create alias')

        data['id'] = cursor.lastrowid
        return self._ok(data)

    def delete(self, identifier, **kwargs):
        """Delete an alias."""
        identifier = self._parse(identifier)
        if not identifier:
            return self._bad_request('Invalid alias id')

        cache_db_con = db.DBConnection('cache.db')
        last_changes = cache_db_con.connection.total_changes
        cache_db_con.action(b'DELETE FROM scene_exceptions WHERE exception_id = ?', [identifier])
        if cache_db_con.connection.total_changes - last_changes <= 0:
            return self._not_found('Alias not found')

        return self._no_content()
