# coding=utf-8
"""Request handler for series and episodes."""
from __future__ import unicode_literals

import logging

from medusa.helper.exceptions import EpisodeDeletedException
from medusa.logger.adapters.style import BraceAdapter
from medusa.server.api.v2.base import (
    BaseRequestHandler,
    BooleanField,
    IntegerField,
    iter_nested_items,
    set_nested_value,
)
from medusa.server.api.v2.series import SeriesHandler
from medusa.tv.episode import Episode, EpisodeNumber
from medusa.tv.series import Series, SeriesIdentifier

from six import iteritems

from tornado.escape import json_decode

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class EpisodeHandler(BaseRequestHandler):
    """Episodes request handler."""

    #: parent resource handler
    parent_handler = SeriesHandler
    #: resource name
    name = 'episodes'
    #: identifier
    identifier = ('episode_slug', r'[\w-]+')
    #: path param
    path_param = ('path_param', r'\w+')
    #: allowed HTTP methods
    allowed_methods = ('GET', 'PATCH', 'DELETE',)

    def get(self, series_slug, episode_slug, path_param):
        """Query episode information.

        :param series_slug: series slug. E.g.: tvdb1234
        :param episode_number:
        :param path_param:
        """
        series_identifier = SeriesIdentifier.from_slug(series_slug)
        if not series_identifier:
            return self._bad_request('Invalid series slug')

        series = Series.find_by_identifier(series_identifier)
        if not series:
            return self._not_found('Series not found')

        if not episode_slug:
            detailed = self._parse_boolean(self.get_argument('detailed', default=False))
            season = self._parse(self.get_argument('season', None), int)
            data = [e.to_json(detailed=detailed) for e in series.get_all_episodes(season=season)]
            return self._paginate(data, sort='airDate')

        episode_number = EpisodeNumber.from_slug(episode_slug)
        if not episode_number:
            return self._bad_request('Invalid episode number')

        episode = Episode.find_by_series_and_episode(series, episode_number)
        if not episode:
            return self._not_found('Episode not found')

        detailed = self._parse_boolean(self.get_argument('detailed', default=True))
        data = episode.to_json(detailed=detailed)
        if path_param:
            if path_param == 'metadata':
                data = episode.metadata() if episode.is_location_valid() else {}
            elif path_param in data:
                data = data[path_param]
            else:
                return self._bad_request("Invalid path parameter '{0}'".format(path_param))

        return self._ok(data=data)

    def patch(self, series_slug, episode_slug=None, path_param=None):
        """Patch episode."""
        series_identifier = SeriesIdentifier.from_slug(series_slug)
        if not series_identifier:
            return self._bad_request('Invalid series slug')

        series = Series.find_by_identifier(series_identifier)
        if not series:
            return self._not_found('Series not found')

        data = json_decode(self.request.body)

        # Multi-patch request
        if not episode_slug:
            return self._patch_multi(series, data)

        episode_number = EpisodeNumber.from_slug(episode_slug)
        if not episode_number:
            return self._bad_request('Invalid episode number')

        episode = Episode.find_by_series_and_episode(series, episode_number)
        if not episode:
            return self._not_found('Episode not found')

        accepted = self._patch_episode(episode, data)

        return self._ok(data=accepted)

    def _patch_multi(self, series, request_data):
        """Patch multiple episodes."""
        statuses = {}

        for slug, data in iteritems(request_data):
            episode_number = EpisodeNumber.from_slug(slug)
            if not episode_number:
                statuses[slug] = {'status': 400}
                continue

            episode = Episode.find_by_series_and_episode(series, episode_number)
            if not episode:
                statuses[slug] = {'status': 404}
                continue

            self._patch_episode(episode, data)

            statuses[slug] = {'status': 200}

        return self._multi_status(data=statuses)

    @staticmethod
    def _patch_episode(episode, data):
        """Patch episode and save the changes to DB."""
        accepted = {}
        ignored = {}
        patches = {
            'status': IntegerField(episode, 'status'),
            'quality': IntegerField(episode, 'quality'),
            'watched': BooleanField(episode, 'watched'),
        }

        for key, value in iter_nested_items(data):
            patch_field = patches.get(key)
            if patch_field and patch_field.patch(episode, value):
                set_nested_value(accepted, key, value)
            else:
                set_nested_value(ignored, key, value)

        # Save patched attributes in db.
        episode.save_to_db()

        if ignored:
            log.warning(
                'Episode patch for {episode} ignored {items!r}',
                {'episode': episode.identifier, 'items': ignored},
            )

        return accepted

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
