# coding=utf-8
"""Request handler for scene_exceptions."""

from medusa.scene_exceptions import get_last_refresh, retrieve_exceptions
from tornado.escape import json_decode
from .base import BaseRequestHandler
from .... import db


def get_last_updates():
    """Query the cache table for the last update for every scene exception source."""
    last_updates = {}
    for scene_exception_source in ['custom_exceptions', 'xem', 'anidb']:
        last_updates[scene_exception_source] = get_last_refresh(scene_exception_source)[0]['last_refreshed']
    return last_updates


class SceneExceptionOperationHandler(BaseRequestHandler):
    """Scene Exception request handler."""

    def set_default_headers(self):
        """Set default CORS headers."""
        super(SceneExceptionOperationHandler, self).set_default_headers()
        self.set_header('Access-Control-Allow-Methods', 'PUT')

    def put(self):
        """Start fetch retrieving scene name exceptions."""
        json_body = json_decode(self.request.body)

        if json_body.get('type', '') == 'REFRESH':
            retrieve_exceptions(force=True)
            return self.api_finish(status=201)
        return self.api_finish(status=400)


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
        exception_id = self._parse(kwargs.pop('row_id'))
        indexer = self.get_query_argument('indexer', None)
        indexer_id = self.get_query_argument('indexer_id', None)
        season = self.get_query_argument('season', None)
        detailed = self.get_query_argument('detailed', 'true').lower()

        if detailed == 'false':
            return self.api_finish(data={"last_updates": get_last_updates()})

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
            self.api_finish(status=400, error='bad request')

        exceptions = [{'exception_id': row[0],
                       'indexer': row[1],
                       'indexer_id': row[2],
                       'show_name': row[3],
                       'season': row[4],
                       'custom': row[5]}
                      for row in exceptions]

        self.api_finish(data={"exceptions": exceptions, "last_updates": get_last_updates()})

    def put(self, *args, **kwargs):
        """Update show information.

        :param show_id:
        :type show_id: str
        """
        exception_id = self._parse(kwargs.pop('row_id'))

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
            return self.api_finish(status=201)
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

    def delete(self, *args, **kwargs):
        """Delete a show.

        :param exception_id:
        :type exception_id: str
        """
        exception_id = self._parse(kwargs.pop('row_id'))

        cache_db_con = db.DBConnection('cache.db')
        last_changes = cache_db_con.connection.total_changes
        cache_db_con.action(b'DELETE FROM scene_exceptions WHERE exception_id = ?', [exception_id])
        if cache_db_con.connection.total_changes - last_changes > 0:
            return self.api_finish(status=204)
        return self.api_finish(status=400, error="Failed to delete.")

        return self.api_finish()
