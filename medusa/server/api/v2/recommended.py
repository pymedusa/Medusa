# coding=utf-8
"""Request handler for series and episodes."""
from __future__ import unicode_literals

import logging

from medusa import app
from medusa.indexers.indexer_config import EXTERNAL_IMDB, EXTERNAL_ANIDB, EXTERNAL_TRAKT
from medusa.logger.adapters.style import BraceAdapter
from medusa.server.api.v2.base import (
    BaseRequestHandler
)
from medusa.show.recommendations.recommended import get_recommended_shows
from medusa.show.recommendations.trakt import TraktPopular

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

    def get(self, identifier, path_param=None):
        """Query available recommended show lists."""

        if identifier and identifier not in ('anidb', 'trakt', 'imdb'):
            return self._bad_request("Invalid recommended list identifier '{0}'".format(identifier))

        data = {'shows': [], 'trakt': {'removedFromMedusa': []}}

        recommended_mappings = {'imdb': EXTERNAL_IMDB, 'anidb': EXTERNAL_ANIDB, 'trakt': EXTERNAL_TRAKT}
        shows = get_recommended_shows(source=recommended_mappings.get(identifier))

        if shows:
            data['shows'] = [show.to_json() for show in shows]

        try:
            data['trakt']['removedFromMedusa'] = TraktPopular().get_removed_from_medusa()
        except Exception:
            log.warning('Could not get the `removed from medusa` list')
        data['trakt']['blacklistEnabled'] = app.TRAKT_BLACKLIST_NAME != ''

        return self._ok(data)
