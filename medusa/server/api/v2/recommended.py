# coding=utf-8
"""Request handler for series and episodes."""
from __future__ import unicode_literals

import logging


from medusa.indexers.indexer_config import EXTERNAL_IMDB, EXTERNAL_ANIDB, EXTERNAL_TRAKT
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
from medusa.show.recommendations.recommended import get_recommended_shows
from medusa.show.recommendations.anidb import AnidbPopular
from medusa.show.recommendations.imdb import ImdbPopular
from medusa.show.recommendations.trakt import TraktPopular
from simpleanidb import REQUEST_HOT
from medusa.tv.series import Series, SeriesIdentifier

from six import itervalues, viewitems

from tornado.escape import json_decode

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class RecommendedHandler(BaseRequestHandler):
    """Series request handler."""

    #: resource name
    name = 'recommended'

    identifier = ('identifier', r'\w+')
    #: path param
    path_param = ('path_param', r'\w+')
    allowed_methods = ('GET',)

    def http_get(self, identifier, path_param=None):
        """Query available recommended show lists."""

        if identifier and identifier not in ('anidb', 'trakt', 'imdb'):
            return self._bad_request("Invalid recommended list identifier '{0}'".format(identifier))

        data = {}

        recommended_mappings = {'imdb': EXTERNAL_IMDB, 'anidb': EXTERNAL_ANIDB, 'trakt': EXTERNAL_TRAKT}
        shows = get_recommended_shows(source=recommended_mappings.get(identifier))

        if shows:
            data = [show.to_json() for show in shows]

        return self._ok(data)
