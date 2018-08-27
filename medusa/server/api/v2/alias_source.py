# coding=utf-8
"""Request handler for alias source."""
from __future__ import unicode_literals

from datetime import datetime

from medusa.scene_exceptions import get_last_refresh, retrieve_exceptions
from medusa.server.api.v2.base import BaseRequestHandler

from tornado.escape import json_decode


def find_alias_sources(predicate=None):
    """Query the cache table for the last update for every scene exception source."""
    data = []
    mapping = {'local': 'custom_exceptions'}
    for identifier in ('local', 'xem', 'anidb'):
        if not predicate or predicate(identifier):
            last_refresh = get_last_refresh(mapping.get(identifier, identifier))[0]['last_refreshed']
            data.append({'id': identifier, 'lastRefresh': last_refresh})

    return data


class AliasSourceHandler(BaseRequestHandler):
    """Alias source request handler."""

    #: resource name
    name = 'alias-source'
    #: identifier
    identifier = ('identifier', r'\w+')
    #: path param
    path_param = ('path_param', r'\w+')
    #: allowed HTTP methods
    allowed_methods = ('GET', )

    def get(self, identifier, path_param=None):
        """Query alias source information.

        :param identifier: source name
        :param path_param:
        """
        if not identifier:
            data = find_alias_sources()
            return self._paginate(data, sort='id')

        data = find_alias_sources(predicate=lambda v: v == identifier)
        if not data:
            return self._not_found('Alias source not found.')

        data = data[0]
        if path_param:
            if path_param not in data:
                return self._bad_request('Invalid path parameter')
            data = data[path_param]

        return self._ok(data=data)


class AliasSourceOperationHandler(BaseRequestHandler):
    """Alias source operation request handler."""

    #: parent resource handler
    parent_handler = AliasSourceHandler
    #: resource name
    name = 'operation'
    #: identifier
    identifier = None
    #: path param
    path_param = None
    #: allowed HTTP methods
    allowed_methods = ('POST', )

    def post(self, identifier):
        """Refresh all scene exception types."""
        types = {
            'local': 'custom_exceptions',
            'xem': 'xem',
            'anidb': 'anidb',
            'all': None,
        }

        if identifier not in types:
            return self._not_found('Alias source not found')

        data = json_decode(self.request.body)
        if not data or not all([data.get('type')]) and len(data) != 1:
            return self._bad_request('Invalid request body')

        if data['type'] == 'REFRESH':
            retrieve_exceptions(force=True, exception_type=types[identifier])
            data['creation'] = datetime.utcnow().isoformat()[:-3] + 'Z'
            return self._created(data=data)

        return self._bad_request('Operation not supported')
