# coding=utf-8
"""Request handler for alias (scene exceptions)."""
from __future__ import unicode_literals

from medusa import db

from medusa.server.api.v2.base import BaseRequestHandler
from medusa.providers.generic_provider import GenericProvider
from medusa.providers import get_provider_class
from medusa.tv.series import SeriesIdentifier
from os.path import basename
from medusa.common import statusStrings


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
        """Query search history information."""

        sql_base = '''
            SELECT rowid, date, action, quality,
                   provider, version, resource, size,
                   indexer_id, showid, season, episode
            FROM history
        '''
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
            """Read log lines based on the specified criteria."""
            start = arg_limit * (arg_page - 1) + 1

            for item in results[start - 1:start - 1 + arg_limit]:
                d = {}
                d['id'] = item['rowid']

                if item['indexer_id'] and item['showid']:
                    d['series'] = SeriesIdentifier.from_id(item['indexer_id'], item['showid']).slug

                d['status'] = item['action']
                d['actionDate'] = item['date']

                d['resource'] = basename(item['resource'])
                d['size'] = item['size']
                d['statusName'] = statusStrings.get(item['action'])
                d['season'] = item['season']
                d['episode'] = item['episode']

                provider = get_provider_class(GenericProvider.make_id(item['provider']))
                d['provider'] = {}
                if provider:
                    d['provider']['id'] = provider.get_id()
                    d['provider']['name'] = provider.name
                    d['provider']['imageName'] = provider.image_name()

                yield d

        if not len(results):
            return self._not_found('History data not found')

        return self._paginate(data_generator=data_generator)


    def delete(self, identifier, **kwargs):
        """Delete an alias."""
        identifier = self._parse(identifier)
        if not identifier:
            return self._bad_request('Invalid history id')

        cache_db_con = db.DBConnection('cache.db')
        last_changes = cache_db_con.connection.total_changes
        cache_db_con.action('DELETE FROM history WHERE row_id = ?', [identifier])
        if cache_db_con.connection.total_changes - last_changes <= 0:
            return self._not_found('Alias not found')

        return self._no_content()
