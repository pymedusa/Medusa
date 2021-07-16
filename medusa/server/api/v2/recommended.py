# coding=utf-8
"""Request handler for series and episodes."""
from __future__ import unicode_literals

import logging

from medusa import app
from medusa.generic_update_queue import RecommendedShowQueueItem, UpdateQueueActions
from medusa.indexers.config import EXTERNAL_ANIDB, EXTERNAL_IMDB, EXTERNAL_MYANIMELIST, EXTERNAL_TRAKT
from medusa.logger.adapters.style import BraceAdapter
from medusa.server.api.v2.base import (
    BaseRequestHandler
)
from medusa.show.recommendations.recommended import get_categories, get_recommended_shows
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

    IDENTIFIER_TO_LIST = {
        'imdb': EXTERNAL_IMDB,
        'anidb': EXTERNAL_ANIDB,
        'trakt': EXTERNAL_TRAKT,
        'myanimelist': EXTERNAL_MYANIMELIST
    }

    def get(self, identifier, path_param=None):
        """Query available recommended show lists."""
        if identifier and not RecommendedHandler.IDENTIFIER_TO_LIST.get(identifier):
            return self._bad_request("Invalid recommended list identifier '{0}'".format(identifier))

        data = {'shows': [], 'trakt': {'removedFromMedusa': []}}

        shows = get_recommended_shows(source=RecommendedHandler.IDENTIFIER_TO_LIST.get(identifier))

        if shows:
            data['shows'] = [show.to_json() for show in shows]

        try:
            data['trakt']['removedFromMedusa'] = TraktPopular().get_removed_from_medusa()
        except Exception:
            data['trakt']['removedFromMedusa'] = []
            log.warning('Could not get the `removed from medusa` list')

        data['trakt']['blacklistEnabled'] = app.TRAKT_BLACKLIST_NAME != ''
        data['categories'] = get_categories()

        return self._ok(data)

    def post(self, identifier, path_param=None):
        """Force the start of a recommended show queue item."""
        if identifier and identifier not in ('anidb', 'trakt', 'imdb', 'myanimelist'):
            return self._bad_request("Invalid recommended list identifier '{0}'".format(identifier))

        if identifier == 'trakt':
            queue_item = RecommendedShowQueueItem(update_action=UpdateQueueActions.UPDATE_RECOMMENDED_LIST_TRAKT)

        if identifier == 'imdb':
            queue_item = RecommendedShowQueueItem(update_action=UpdateQueueActions.UPDATE_RECOMMENDED_LIST_IMDB)

        if identifier == 'anidb':
            queue_item = RecommendedShowQueueItem(update_action=UpdateQueueActions.UPDATE_RECOMMENDED_LIST_ANIDB)

        if identifier == 'myanimelist':
            queue_item = RecommendedShowQueueItem(update_action=UpdateQueueActions.UPDATE_RECOMMENDED_LIST_MYANIMELIST)

        app.generic_queue_scheduler.action.add_item(queue_item)
        return self._accepted(f'Started fetching new recommended shows from source {identifier}')
