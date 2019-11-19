# coding=utf-8
"""Request handler for series and episodes."""
from __future__ import unicode_literals

import logging

from medusa import ws
from medusa.logger.adapters.style import BraceAdapter
from medusa.server.api.v2.base import (
    BaseRequestHandler,
    BooleanField,
    IntegerField,
    ListField,
    StringField,
    iter_nested_items,
    set_nested_value
)
from medusa import providers
from medusa.tv.series import Series, SeriesIdentifier

from six import itervalues, viewitems

from tornado.escape import json_decode

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class ProvidersHandler(BaseRequestHandler):
    """Providers request handler."""

    #: resource name
    name = 'providers'
    #: identifier
    identifier = ('provider', r'\w+')
    #: path param
    path_param = ('path_param', r'\w+')
    #: allowed HTTP methods
    allowed_methods = ('GET', 'POST', 'PATCH', 'DELETE', )

    def get(self, provider, path_param=None):
        """Query provider information.

        Return a list of provider id's.

        :param series_slug: series slug. E.g.: tvdb1234
        :param path_param:
        """
        # arg_paused = self._parse_boolean(self.get_argument('paused', default=None))
        #
        # def filter_series(current):
        #     return arg_paused is None or current.paused == arg_paused

        if not provider:
            # return a list of provider id's
            provider_list = providers.sorted_provider_list()
            return self._ok([provider.to_json() for provider in provider_list])
