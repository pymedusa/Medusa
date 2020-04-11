# coding=utf-8
"""Request handler for series and episodes."""
from __future__ import unicode_literals

import logging

from medusa import db

from medusa.common import statusStrings
from medusa.helper.exceptions import EpisodeDeletedException
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.generic_provider import GenericProvider
from medusa.providers import get_provider_class
from medusa.server.api.v2.base import BaseRequestHandler
from medusa.server.api.v2.history import HistoryHandler
from medusa.tv.episode import Episode, EpisodeNumber
from medusa.tv.series import Series, SeriesIdentifier

from os.path import basename

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class EpisodeHistoryHandler(BaseRequestHandler):
    """Episode history request handler."""

    #: parent resource handler
    parent_handler = HistoryHandler
    #: resource name
    name = 'episode'
    #: identifier
    identifier = ('episode_slug', r'[\w-]+')
    #: path param
    path_param = ('path_param', r'\w+')
    #: allowed HTTP methods
    allowed_methods = ('GET', 'DELETE',)

    def get(self, series_slug, episode_slug, path_param):
        """Query episode's history information.

        :param series_slug: series slug. E.g.: tvdb1234
        :param episode_slug: episode slug. E.g.: s01e01
        :param path_param:
        """
        series_identifier = SeriesIdentifier.from_slug(series_slug)
        if not series_identifier:
            return self._bad_request('Invalid series slug')

        series = Series.find_by_identifier(series_identifier)
        if not series:
            return self._not_found('Series not found')

        if not episode_slug:
            return self._not_found('Invalid episode slug')

        episode_number = EpisodeNumber.from_slug(episode_slug)
        if not episode_number:
            return self._bad_request('Invalid episode number')

        episode = Episode.find_by_series_and_episode(series, episode_number)
        if not episode:
            return self._not_found('Episode not found')

        sql_base = '''
            SELECT rowid, date, action, quality,
                   provider, version, resource, size, proper_tags,
                   indexer_id, showid, season, episode, manually_searched
            FROM history
            WHERE showid = ? AND indexer_id = ? AND season = ? AND episode = ?
        '''

        params = [series.series_id, series.indexer, episode.season, episode.episode]

        sql_base += ' ORDER BY date DESC'
        results = db.DBConnection().select(sql_base, params)

        def data_generator():
            """Read history data and normalize key/value pairs."""
            for item in results:
                d = {}
                d['id'] = item['rowid']

                if item['indexer_id'] and item['showid']:
                    d['series'] = SeriesIdentifier.from_id(item['indexer_id'], item['showid']).slug

                d['status'] = item['action']
                d['actionDate'] = item['date']

                d['resource'] = basename(item['resource'])
                d['size'] = item['size']
                d['properTags'] = item['proper_tags']
                d['statusName'] = statusStrings.get(item['action'])
                d['season'] = item['season']
                d['episode'] = item['episode']
                d['manuallySearched'] = item['manually_searched']

                provider = get_provider_class(GenericProvider.make_id(item['provider']))
                d['provider'] = {}
                if provider:
                    d['provider']['id'] = provider.get_id()
                    d['provider']['name'] = provider.name
                    d['provider']['imageName'] = provider.image_name()

                yield d

        if not len(results):
            return self._not_found('History data not found for show {show} and episode {episode}'.format(
                show=series.identifier.slug, episode=episode.slug
            ))

        return self._ok(data=list(data_generator()))

    def delete(self, series_slug, episode_slug, **kwargs):
        """Delete the episode."""
        if not series_slug:
            return self._method_not_allowed('Deleting multiple series are not allowed')

        identifier = SeriesIdentifier.from_slug(series_slug)
        if not identifier:
            return self._bad_request('Invalid series identifier')

        series = Series.find_by_identifier(identifier)
        if not series:
            return self._not_found('Series not found')

        episode_number = EpisodeNumber.from_slug(episode_slug)
        if not episode_number:
            return self._bad_request('Invalid episode number')

        episode = Episode.find_by_series_and_episode(series, episode_number)
        if not episode:
            return self._not_found('Episode not found')

        try:
            episode.delete_episode()
        except EpisodeDeletedException:
            return self._no_content()
        else:
            return self._conflict('Unable to delete episode')
