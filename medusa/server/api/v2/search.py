# coding=utf-8
"""Request handler for statistics."""
from __future__ import unicode_literals

from collections import defaultdict
from six import itervalues
from medusa import app
from medusa.search.manual import collect_episodes_from_search_thread
from medusa.search.queue import (
    BacklogQueueItem,
    FailedQueueItem,
    ForcedSearchQueueItem,
    # ManualSearchQueueItem,
)
from medusa.server.api.v2.base import BaseRequestHandler
from medusa.tv.episode import Episode, EpisodeNumber
from medusa.tv.series import Series, SeriesIdentifier

from tornado.escape import json_decode


class SearchHandler(BaseRequestHandler):
    """Search queue request handler."""

    #: resource name
    name = 'search'
    #: identifier
    identifier = ('identifier', r'\w+')
    #: path param
    path_param = None
    #: allowed HTTP methods
    allowed_methods = ('GET', 'POST')

    def get(self, identifier, *args, **kwargs):
        """Collect ran, running and queued searches for a specific show.

        :param identifier:
        """
        if not identifier:
            return self._bad_request('You need to add the show slug to the route')

        series = SeriesIdentifier.from_slug(identifier)
        if not series:
            return self._bad_request('Invalid series slug')

        series_obj = Series.find_by_identifier(series)
        if not series_obj:
            return self._not_found('Series not found')

        return {
            'results': collect_episodes_from_search_thread(series_obj)
        }

    def post(self, identifier):
        """Queue a backlog search for a range of episodes.

        :param identifier:
        :example:
            Start a backlog search for show slug tvdb1234 with episodes s01e01, s01e02, s03e03.
            route: `apiv2/search/backlog`
            "tvdb1234" : [
                "s01e01",
                "s01e02",
                "s03e03",
            ]
        """
        data = json_decode(self.request.body)

        if identifier == 'backlog':
            return self._search_backlog(data)
        if identifier == 'daily':
            return self._search_daily()
        if identifier == 'failed':
            return self._search_failed(data)
        if identifier == 'manual':
            return self._search_manual(data)

        return self._bad_request('{key} is a invalid path. You will need to add a search type to the path'.format(key=identifier))

    def _search_backlog(self, data):
        """Queue a backlog search for results for the provided episodes.

        :param data:
        :return:
        """
        statuses = {}

        if all([not data.get('showSlug'), not data.get('episodes')]):
            # Trigger a full backlog search
            if app.backlog_search_scheduler.forceRun():
                return self._created()

            return self._bad_request('Triggering a backlog search failed')

        if not data.get('showSlug'):
            return self._bad_request('For a backlog search you need to provide a showSlug')

        if not data.get('episodes'):
            return self._bad_request('For a backlog search you need to provide a list of episodes')

        identifier = SeriesIdentifier.from_slug(data['showSlug'])
        if not identifier:
            return self._bad_request('Invalid series slug')

        series = Series.find_by_identifier(identifier)
        if not series:
            return self._not_found('Series not found')

        season_segments = defaultdict(list)
        for episode_slug in data['episodes']:
            episode_number = EpisodeNumber.from_slug(episode_slug)
            if not episode_number:
                statuses[episode_slug] = {'status': 400}
                continue

            episode = Episode.find_by_series_and_episode(series, episode_number)
            if not episode:
                statuses[episode_slug] = {'status': 404}
                continue

            season_segments[episode.season].append(episode)

        if not season_segments:
            return self._not_found('No episodes passed to search for using the backlog search')

        for segment in itervalues(season_segments):
            cur_backlog_queue_item = BacklogQueueItem(series, segment)
            app.forced_search_queue_scheduler.action.add_item(cur_backlog_queue_item)

        return self._created()

    def _search_daily(self):
        """Queue a daily search.

        :return:
        """
        if app.daily_search_scheduler.forceRun():
            return self._created()

        return self._bad_request('Triggering a daily search failed')

    def _search_failed(self, data):
        """Queue a failed search.

        :param data:
        :return:
        """
        statuses = {}

        if not data.get('showSlug'):
            return self._bad_request('For a backlog search you need to provide a showSlug')

        if not data.get('episodes'):
            return self._bad_request('For a backlog search you need to provide a list of episodes')

        identifier = SeriesIdentifier.from_slug(data['showSlug'])
        if not identifier:
            return self._bad_request('Invalid series slug')

        series = Series.find_by_identifier(identifier)
        if not series:
            return self._not_found('Series not found')

        season_segments = defaultdict(list)
        for episode_slug in data['episodes']:
            episode_number = EpisodeNumber.from_slug(episode_slug)
            if not episode_number:
                statuses[episode_slug] = {'status': 400}
                continue

            episode = Episode.find_by_series_and_episode(series, episode_number)
            if not episode:
                statuses[episode_slug] = {'status': 404}
                continue

            season_segments[episode.season].append(episode)

        if not season_segments:
            return self._not_found('No episodes passed to search for using the backlog search')

        for segment in itervalues(season_segments):
            cur_failed_queue_item = FailedQueueItem(series, segment)
            app.forced_search_queue_scheduler.action.add_item(cur_failed_queue_item)

        return self._created()

    def _search_manual(self, data):
        """Queue a manual search for results for the provided episodes.

        :param data:
        :return:
        """
        statuses = {}

        if not data.get('showSlug'):
            return self._bad_request('For a backlog search you need to provide a showSlug')

        if not data.get('episodes'):
            return self._bad_request('For a backlog search you need to provide a list of episodes')

        identifier = SeriesIdentifier.from_slug(data['showSlug'])
        if not identifier:
            return self._bad_request('Invalid series slug')

        series = Series.find_by_identifier(identifier)
        if not series:
            return self._not_found('Series not found')

        season_segments = defaultdict(list)
        for episode_slug in data['episodes']:
            episode_number = EpisodeNumber.from_slug(episode_slug)
            if not episode_number:
                statuses[episode_slug] = {'status': 400}
                continue

            episode = Episode.find_by_series_and_episode(series, episode_number)
            if not episode:
                statuses[episode_slug] = {'status': 404}
                continue

            season_segments[episode.season].append(episode)

        if not season_segments:
            return self._not_found('No episodes passed to search for using the backlog search')

        # Retrieve the search type option (episode vs season)
        search_type = data['options'].get('type', 'episode')

        for segment in itervalues(season_segments):
            # Need this as it's part of a followup
            # cur_manual_search_queue_item = ManualSearchQueueItem(series, segment, manual_search_type=search_type)
            cur_manual_search_queue_item = ForcedSearchQueueItem(series, segment, down_cur_quality=False,
                                                                 manual_search=False, manual_search_type=search_type)

            app.forced_search_queue_scheduler.action.add_item(cur_manual_search_queue_item)

        return self._created()
