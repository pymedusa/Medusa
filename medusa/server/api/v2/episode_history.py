# coding=utf-8
"""Request handler for series and episodes."""
from __future__ import unicode_literals

import logging
from os.path import basename

from medusa import db
from medusa.common import DOWNLOADED, FAILED, SNATCHED, SUBTITLED, statusStrings
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.generic_provider import GenericProvider
from medusa.server.api.v2.base import BaseRequestHandler
from medusa.server.api.v2.history import HistoryHandler
from medusa.tv.episode import Episode, EpisodeNumber
from medusa.tv.series import Series, SeriesIdentifier


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
    allowed_methods = ('GET',)

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
            return self._bad_request('Invalid episode slug')

        episode_number = EpisodeNumber.from_slug(episode_slug)
        if not episode_number:
            return self._not_found('Invalid episode number')

        episode = Episode.find_by_series_and_episode(series, episode_number)
        if not episode:
            return self._not_found('Episode not found')

        sql_base = """
            SELECT rowid, date, action, quality,
                   provider, version, resource, size, proper_tags,
                   indexer_id, showid, season, episode, manually_searched, info_hash
            FROM history
            WHERE showid = ? AND indexer_id = ? AND season = ? AND episode = ?
        """

        params = [series.series_id, series.indexer, episode.season, episode.episode]

        sql_base += ' ORDER BY date DESC'
        results = db.DBConnection().select(sql_base, params)

        def data_generator():
            """Read history data and normalize key/value pairs."""
            for item in results:
                provider = {}
                release_group = None
                release_name = None
                file_name = None
                subtitle_language = None

                if item['action'] in (SNATCHED, FAILED):
                    provider.update({
                        'id': GenericProvider.make_id(item['provider']),
                        'name': item['provider']
                    })
                    release_name = item['resource']

                if item['action'] == DOWNLOADED:
                    release_group = item['provider']
                    file_name = item['resource']

                if item['action'] == SUBTITLED:
                    subtitle_language = item['resource']
                    provider.update({
                        'id': item['provider'],
                        'name': item['provider']
                    })

                if item['action'] == SUBTITLED:
                    subtitle_language = item['resource']

                yield {
                    'id': item['rowid'],
                    'series': SeriesIdentifier.from_id(item['indexer_id'], item['showid']).slug,
                    'status': item['action'],
                    'statusName': statusStrings.get(item['action']),
                    'actionDate': item['date'],
                    'quality': item['quality'],
                    'resource': basename(item['resource']),
                    'size': item['size'],
                    'properTags': item['proper_tags'],
                    'season': item['season'],
                    'episode': item['episode'],
                    'manuallySearched': bool(item['manually_searched']),
                    'infoHash': item['info_hash'],
                    'provider': provider,
                    'release_name': release_name,
                    'releaseGroup': release_group,
                    'fileName': file_name,
                    'subtitleLanguage': subtitle_language
                }

        if not results:
            return self._not_found('History data not found for show {show} and episode {episode}'.format(
                show=series.identifier.slug, episode=episode.slug
            ))

        return self._ok(data=list(data_generator()))
