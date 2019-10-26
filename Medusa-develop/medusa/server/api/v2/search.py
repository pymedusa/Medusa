# coding=utf-8
"""Request handler for statistics."""
from __future__ import unicode_literals

from collections import defaultdict

from medusa import app
from medusa.search.manual import collect_episodes_from_search_thread
from medusa.search.queue import (
    BacklogQueueItem,
    FailedQueueItem,
    ManualSearchQueueItem
)
from medusa.server.api.v2.base import BaseRequestHandler
from medusa.tv.episode import Episode, EpisodeNumber
from medusa.tv.series import Series, SeriesIdentifier

from six import itervalues

from tornado.escape import json_decode


class SearchHandler(BaseRequestHandler):
    """Search queue request handler."""

    #: resource name
    name = 'search'
    #: identifier
    identifier = ('identifier', r'\w+')
    #: allowed HTTP methods
    allowed_methods = ('GET', 'PUT',)

    def get(self, identifier):
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

    def put(self, identifier):
        """Queue a search for a range of episodes or a season.

        :param identifier:
        """
        if not self.request.body:
            if identifier == 'daily':
                return self._search_daily()
            if identifier == 'backlog':
                return self._search_backlog()
            else:
                return self._bad_request("Body required for search type '{0}'".format(identifier))

        data = json_decode(self.request.body)
        if identifier == 'backlog':
            return self._search_backlog(data)
        if identifier == 'failed':
            return self._search_failed(data)
        if identifier == 'manual':
            return self._search_manual(data)

        return self._bad_request("Invalid search type '{0}'".format(identifier))

    def _search_backlog(self, data=None):
        """Queue a backlog search for results for the provided episodes or season.

        :param data:
        :return:
        :example:
            Start a backlog search for show slug tvdb1234 with episodes s01e01, s01e02, s03e03.
            route: `apiv2/search/backlog`
            { showSlug: "tvdb1234",
              episodes: [
                "s01e01",
                "s01e02",
                "s03e03",
              ]
            }
        """
        if not data:
            # Trigger a full backlog search
            if app.backlog_search_scheduler.forceRun():
                return self._accepted('Full backlog search started')

            return self._bad_request('Triggering a full backlog search failed')

        if not data.get('showSlug'):
            return self._bad_request('You need to provide a show slug')

        if not data.get('episodes') and not data.get('season'):
            return self._bad_request('For a backlog search you need to provide a list of episodes or seasons')

        identifier = SeriesIdentifier.from_slug(data['showSlug'])
        if not identifier:
            return self._bad_request('Invalid series slug')

        series = Series.find_by_identifier(identifier)
        if not series:
            return self._not_found('Series not found')

        episode_segments = self._get_episode_segments(series, data)

        # If a season is passed, we transform it to a list of episode objects. And merge it with the episode_segment.
        # This because the backlog search has its own logic for searching per episode or season packs. And falling back
        # between them, if configured.
        if data.get('season'):
            for season_slug in data['season']:
                episode_season = int(season_slug[1:])
                episodes = series.get_all_episodes(episode_season)
                for episode in episodes:
                    if episode not in episode_segments[episode_season]:
                        episode_segments[episode_season].append(episode)

        if not episode_segments:
            return self._not_found('Could not find any episode for show {show}. Did you provide the correct format?'
                                   .format(show=series.name))

        for segment in itervalues(episode_segments):
            cur_backlog_queue_item = BacklogQueueItem(series, segment)
            app.forced_search_queue_scheduler.action.add_item(cur_backlog_queue_item)

        return self._accepted('Backlog search for {0} started'.format(data['showSlug']))

    def _search_daily(self):
        """Queue a daily search.

        :return:
        """
        if app.daily_search_scheduler.forceRun():
            return self._accepted('Daily search started')

        return self._bad_request('Daily search already running')

    def _search_failed(self, data):
        """Queue a failed search.

        :param data:
        :return:
        """
        statuses = {}

        if not data.get('showSlug'):
            return self._bad_request('For a failed search you need to provide a show slug')

        if not data.get('episodes'):
            return self._bad_request('For a failed search you need to provide a list of episodes')

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
            return self._not_found('Could not find any episode for show {show}. Did you provide the correct format?'
                                   .format(show=series.name))

        for segment in itervalues(season_segments):
            cur_failed_queue_item = FailedQueueItem(series, segment)
            app.forced_search_queue_scheduler.action.add_item(cur_failed_queue_item)

        return self._accepted('Failed search for {0} started'.format(data['showSlug']))

    def _search_manual(self, data):
        """Queue a manual search for results for the provided episodes or season.

        :param data:
        :return:
        """
        if not data.get('showSlug'):
            return self._bad_request('For a manual search you need to provide a show slug')

        if not data.get('episodes') and not data.get('season'):
            return self._bad_request('For a manual search you need to provide a list of episodes or seasons')

        identifier = SeriesIdentifier.from_slug(data['showSlug'])
        if not identifier:
            return self._bad_request('Invalid series slug')

        series = Series.find_by_identifier(identifier)
        if not series:
            return self._not_found('Series not found')

        episode_segments = self._get_episode_segments(series, data)
        season_segments = self._get_season_segments(series, data)

        for segments in ({'segment': episode_segments, 'manual_search_type': 'episode'},
                         {'segment': season_segments, 'manual_search_type': 'season'}):
            for segment in itervalues(segments['segment']):
                cur_manual_search_queue_item = ManualSearchQueueItem(series, segment, manual_search_type=segments['manual_search_type'])
                app.forced_search_queue_scheduler.action.add_item(cur_manual_search_queue_item)

        if not episode_segments and not season_segments:
            return self._not_found('Could not find any episode for show {show}. Did you provide the correct format?'
                                   .format(show=series.name))

        return self._accepted('Manual search for {0} started'.format(data['showSlug']))

    @staticmethod
    def _get_episode_segments(series, data):
        """
        Create a dict with season number keys and their corresponding episodes as an array of Episode objects.

        The episode objects are created from the "episodes" property passed as json data.
        """
        episode_segments = defaultdict(list)
        if data.get('episodes'):
            for episode_slug in data['episodes']:
                episode_number = EpisodeNumber.from_slug(episode_slug)
                if not episode_number:
                    continue

                episode = Episode.find_by_series_and_episode(series, episode_number)
                if not episode:
                    continue

                episode_segments[episode.season].append(episode)
        return episode_segments

    @staticmethod
    def _get_season_segments(series, data):
        """
        Create a dict with season number keys and their corresponding episodes as an array of Episode objects.

        The episode objects are created from the "season" property passed as json data.
        """
        season_segments = defaultdict(list)
        if data.get('season'):
            for season_slug in data['season']:
                # For season packs we still need to provide an episode object. So we choose to provide the first
                episode_slug = '{season}e01'.format(season=season_slug)
                episode_number = EpisodeNumber.from_slug(episode_slug)

                if not episode_number:
                    continue

                episode = Episode.find_by_series_and_episode(series, episode_number)
                if not episode:
                    continue

                season_segments[episode.season].append(episode)
        return season_segments
