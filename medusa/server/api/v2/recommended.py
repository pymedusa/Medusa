# coding=utf-8
"""Request handler for recommended shows."""
from __future__ import unicode_literals

import logging

from medusa import app
from medusa.generic_update_queue import GenericQueueActions
from medusa.helper.exceptions import CantUpdateRecommendedShowsException
from medusa.indexers.config import EXTERNAL_ANIDB, EXTERNAL_ANILIST, EXTERNAL_IMDB, EXTERNAL_TRAKT
from medusa.logger.adapters.style import BraceAdapter
from medusa.server.api.v2.base import (
    BaseRequestHandler
)
from medusa.show.recommendations.recommended import get_categories, get_recommended_shows
from medusa.show.recommendations.trakt import TraktPopular

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class RecommendedHandler(BaseRequestHandler):
    """Request handler for recommended shows."""

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
        'anilist': EXTERNAL_ANILIST
    }

    def get(self, identifier, path_param=None):
        """Query available recommended show lists."""
        if identifier and not RecommendedHandler.IDENTIFIER_TO_LIST.get(identifier) and identifier != 'categories':
            return self._bad_request("Invalid recommended list identifier '{0}'".format(identifier))

        if identifier == 'trakt' and path_param == 'removed' and app.USE_TRAKT:
            data = {'removedFromMedusa': [], 'blacklistEnabled': None}
            try:
                data['removedFromMedusa'] = TraktPopular().get_removed_from_medusa()
            except Exception:
                log.warning('Could not get the `removed from medusa` list')
            data['blacklistEnabled'] = app.TRAKT_BLACKLIST_NAME != ''
            return self._ok(data)

        if identifier == 'categories':
            return self._ok(get_categories())

        shows = get_recommended_shows(source=RecommendedHandler.IDENTIFIER_TO_LIST.get(identifier))
        return self._paginate([show.to_json() for show in shows], sort='-rating')

    def post(self, identifier, path_param=None):
        """Force the start of a recommended show queue item."""
        if identifier and not RecommendedHandler.IDENTIFIER_TO_LIST.get(identifier):
            return self._bad_request("Invalid recommended list identifier '{0}'".format(identifier))

        try:
            if identifier == 'trakt':
                app.generic_queue_scheduler.action.add_recommended_show_update(
                    GenericQueueActions.UPDATE_RECOMMENDED_LIST_TRAKT
                )

            if identifier == 'imdb':
                app.generic_queue_scheduler.action.add_recommended_show_update(
                    GenericQueueActions.UPDATE_RECOMMENDED_LIST_IMDB
                )

            if identifier == 'anidb':
                app.generic_queue_scheduler.action.add_recommended_show_update(
                    GenericQueueActions.UPDATE_RECOMMENDED_LIST_ANIDB
                )

            if identifier == 'anilist':
                app.generic_queue_scheduler.action.add_recommended_show_update(
                    GenericQueueActions.UPDATE_RECOMMENDED_LIST_ANILIST
                )

        except CantUpdateRecommendedShowsException as error:
            return self._conflict(str(error))

        return self._accepted(f'Started fetching new recommended shows from source {identifier}')
