# coding=utf-8
"""Request handler for cache tables."""
from tornado.escape import json_decode
from .base import BaseRequestHandler
from .... import db


class SceneExceptionHandler(BaseRequestHandler):
    """Shows request handler."""

    def set_default_headers(self):
        """Set default CORS headers."""
        super(SceneExceptionHandler, self).set_default_headers()
        self.set_header('Access-Control-Allow-Methods', 'GET, OPTIONS, PUT, POST')

    def get(self, *args, **kwargs):
        """Query scene_exception information.

        :param show_indexer_id: The indexer id. Like 1 for tmdb and 3 for tvmaze.
        :param show_id:
        :type show_indexer_id: str
        :param season:
        """
        try:
            exception_id = int(kwargs.pop('row_id', 'throwme'))
        except (ValueError, TypeError):
            return self.api_finish(status=400, error="Require a valid exception row id.")

        indexer = self.get_query_argument('indexer', None)
        indexer_id = self.get_query_argument('indexer_id', None)
        season = self.get_query_argument('season', None)

        cache_db_con = db.DBConnection('cache.db')
        if indexer and indexer_id and season:
            sql_base = b'SELECT * FROM scene_exceptions WHERE indexer = ? AND indexer_id = ?'
            params = [indexer, indexer_id]
            if season:
                sql_base += b' AND season = ?'
                params.append(season)
        else:
            sql_base = b'SELECT * FROM scene_exceptions'
            params = []
            if exception_id:
                sql_base += ' WHERE exception_id = ?'
                params.append(exception_id)

        if sql_base:
            exceptions = cache_db_con.select(sql_base, params)
        else:
            self.api_finish(data={},error="Error, need to provide")

        data = [{'exception_id': row[0],
                 'indexer': row[1],
                 'indexer_id': row[2],
                 'show_name': row[3],
                 'season': row[4],
                 'custom': row[5]}
                for row in exceptions]

        self.api_finish(data=data)

    def put(self, *args, **kwargs):
        """Update show information.

        :param show_id:
        :type show_id: str
        """
        try:
            exception_id = int(kwargs.pop('row_id', 'throwme'))
        except (ValueError, TypeError):
            return self.api_finish(status=400, error="Require a valid exception row id.")

        data = json_decode(self.request.body)

        if not all([data.get('indexer_id'),
                    data.get('season'),
                    data.get('show_name'),
                    data.get('indexer')]):
            return self.api_finish(status=400, error="Invalid post body, can't update")

        cache_db_con = db.DBConnection('cache.db')
        last_changes = cache_db_con.connection.total_changes
        cache_db_con.action(b'UPDATE scene_exceptions'
                            b' set indexer = ?'
                            b', indexer_id = ?'
                            b', show_name = ?'
                            b', season = ?'
                            b', custom = 1'
                            b' WHERE exception_id = ?',
                            [data.get('indexer'),
                             data.get('indexer_id'),
                             data.get('show_name'),
                             data.get('season'),
                             exception_id])
        if cache_db_con.connection.total_changes - last_changes == 1:
            return self.api_finish(status=204)
        return self.api_finish(status=400, error="Could not update.")

    def post(self, *args, **kwargs):
        """Add a show."""
        data = json_decode(self.request.body)

        if not all([data.get('indexer_id'),
                    data.get('season'),
                    data.get('show_name'),
                    data.get('indexer')]):
            return self.api_finish(status=400, error="Invalid post body, can't update")

        cache_db_con = db.DBConnection('cache.db')
        last_changes = cache_db_con.connection.total_changes
        cache_db_con.action(b'INSERT INTO scene_exceptions'
                            b' (indexer, indexer_id, show_name, season, custom) '
                            b' values (?,?,?,?,1)',
                            [data.get('indexer'),
                             data.get('indexer_id'),
                             data.get('show_name'),
                             data.get('season')])
        if cache_db_con.connection.total_changes - last_changes > 0:
            return self.api_finish(status=204)
        return self.api_finish(status=400, error="Could not update.")

        return self.api_finish()

    def delete(self, *args, **kwargs):
        """Delete a show.

        :param exception_id:
        :type exception_id: str
        """
        try:
            exception_id = int(kwargs.pop('row_id', 'throwme'))
        except (ValueError, TypeError):
            return self.api_finish(status=400, error="Require a valid exception row id.")

        cache_db_con = db.DBConnection('cache.db')
        last_changes = cache_db_con.connection.total_changes
        cache_db_con.action(b'DELETE FROM scene_exceptions WHERE exception_id = ?', [exception_id])
        if cache_db_con.connection.total_changes - last_changes > 0:
            return self.api_finish(status=204, data={'result': 'Deleted {0} row.'
                                   .format(cache_db_con.connection.total_changes - last_changes)})
        return self.api_finish(status=400, error="Failed to delete.")

        return self.api_finish()
