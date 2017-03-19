# coding=utf-8
"""Request handler for scene_exceptions."""

from medusa.indexers.indexer_config import indexer_id_to_slug, slug_to_indexer_id
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


class SceneExceptionTypeHandler(BaseRequestHandler):
    """Scene Exception type request handler."""

    def set_default_headers(self):
        """Set default CORS headers."""
        super(SceneExceptionTypeHandler, self).set_default_headers()
        self.set_header('Access-Control-Allow-Methods', 'GET')

    def get(self, exception_type):
        """Return a list or instance of exception types."""
        exception_types = []
        if exception_type is not None and exception_type not in ['medusa', 'xem', 'anidb']:
            return self.api_finish(status=400)

        if exception_type:
            mapped_exception_type = {'medusa': 'custom_exceptions'}.get(exception_type, exception_type)
            for k, v in get_last_updates().items():
                if k == mapped_exception_type:
                    exception_types = {"id": {'custom_exceptions': 'medusa'}.get(k, k), "lastUpdate": v}
        else:
            exception_types = [{"id": {'custom_exceptions': 'medusa'}.get(k, k), "lastUpdate": v}
                               for k, v in get_last_updates().items()]

        self.api_finish(data=exception_types)


class SceneExceptionAllTypeOperationHandler(BaseRequestHandler):
    """Scene Exception operation request handler, to update all scene exception types."""

    def set_default_headers(self):
        """Set default CORS headers."""
        super(SceneExceptionAllTypeOperationHandler, self).set_default_headers()
        self.set_header('Access-Control-Allow-Methods', 'POST')

    def post(self):
        """Start scene exceptions type operation. To refresh all scene exception types."""
        json_body = json_decode(self.request.body)

        if json_body.get('type', '') == 'REFRESH':
            retrieve_exceptions(force=True, exception_type=None)
            return self.api_finish(status=201)
        return self.api_finish(status=400)


class SceneExceptionTypeOperationHandler(BaseRequestHandler):
    """Scene Exception operation request handler."""

    def set_default_headers(self):
        """Set default CORS headers."""
        super(SceneExceptionTypeOperationHandler, self).set_default_headers()
        self.set_header('Access-Control-Allow-Methods', 'POST')

    def post(self, exception_type):
        """Start scene exceptions type operation."""
        if not exception_type or exception_type not in ['medusa', 'xem', 'anidb']:
            return self.api_finish(status=400)

        exception_type = {'medusa': 'custom_exceptions'}.get(exception_type, exception_type)

        json_body = json_decode(self.request.body)

        if json_body.get('type', '') == 'REFRESH':
            retrieve_exceptions(force=True, exception_type=exception_type)
            return self.api_finish(status=201)
        return self.api_finish(status=400)


class SceneExceptionHandler(BaseRequestHandler):
    """Scene Exception request handler."""

    def set_default_headers(self):
        """Set default CORS headers."""
        super(SceneExceptionHandler, self).set_default_headers()
        self.set_header('Access-Control-Allow-Methods', 'GET, OPTIONS, PUT, POST')

    def get(self, exception_id, **kwargs):
        """Query scene_exception information.

        :param show_indexer_id: The indexer id. Like 1 for tmdb and 3 for tvmaze.
        :param show_id:
        :type show_indexer_id: str
        :param season:
        """
        slug = self.get_query_argument('indexer', None)
        indexer, indexer_id = slug_to_indexer_id(slug)
        season = self.get_query_argument('season', None)
        exception_type = bool(self.get_query_argument('type', None) == 'custom')

        cache_db_con = db.DBConnection('cache.db')
        sql_base = b'SELECT * FROM scene_exceptions'
        sql_where = []
        params = []

        if exception_id:
            sql_where.append(b'exception_id')
            params += [exception_id]

        if indexer and indexer_id:
            sql_where.append(b'indexer')
            params += [indexer]

        if indexer_id:
            sql_where.append(b'indexer_id')
            params += [indexer_id]

        if season:
            sql_where.append(b'season')
            params += [season]

        if exception_type:
            sql_where.append(b'custom')
            params += [exception_type]

        if sql_where:
            sql_base += b' WHERE ' + b' AND '.join([where + b' = ? ' for where in sql_where])

        exceptions = cache_db_con.select(sql_base, params)

        exceptions = [{'id': row[0],
                       'indexer': indexer_id_to_slug(row[1], row[2]),
                       'showName': row[3],
                       'season': row[4] if row[4] >= 0 else None,
                       'type': 'custom' if row[5] else None}
                      for row in exceptions]

        if exception_id:
            return self.api_finish(data=exceptions[0]) if exceptions else self.api_finish(status=404)
        return self._paginate(exceptions, 'id')

    def put(self, *args, **kwargs):
        """Update show information.

        :param show_id:
        :type show_id: str
        """
        exception_id = self._parse(kwargs.pop('row_id'))

        data = json_decode(self.request.body)

        if not all([data.get('indexerId'),
                    data.get('season'),
                    data.get('showName'),
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
                             data.get('indexerId'),
                             data.get('showName'),
                             data.get('season'),
                             exception_id])
        if cache_db_con.connection.total_changes - last_changes == 1:
            return self.api_finish(status=204)
        return self.api_finish(status=404, error="Could not update resource.")

    def post(self, *args, **kwargs):
        """Add a show."""
        data = json_decode(self.request.body)

        if not all([data.get('indexerId'),
                    data.get('season'),
                    data.get('showName'),
                    data.get('indexer')]):
            return self.api_finish(status=400, error="Invalid post body, can't update")

        cache_db_con = db.DBConnection('cache.db')
        last_changes = cache_db_con.connection.total_changes
        cache_db_con.action(b'INSERT INTO scene_exceptions'
                            b' (indexer, indexer_id, show_name, season, custom) '
                            b' values (?,?,?,?,1)',
                            [data.get('indexer'),
                             data.get('indexerId'),
                             data.get('showName'),
                             data.get('season')])
        if cache_db_con.connection.total_changes - last_changes > 0:
            return self.api_finish(status=200, data={"indexer": data.get('indexer'),
                                                     "indexerId": data.get('indexerId'),
                                                     "showName": data.get('showName'),
                                                     "season": data.get('season')})
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
        return self.api_finish(status=404, error="Resource not found, Failed to delete.")
