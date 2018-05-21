# coding=utf-8
"""Request handler for series and episodes."""
from __future__ import unicode_literals

import logging

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
from medusa.tv.series import Series, SeriesIdentifier

from six import itervalues, viewitems

from tornado.escape import json_decode

log = BraceAdapter(logging.getLogger(__name__))


class SeriesHandler(BaseRequestHandler):
    """Series request handler."""

    #: resource name
    name = 'series'
    #: identifier
    identifier = ('series_slug', r'\w+')
    #: path param
    path_param = ('path_param', r'\w+')
    #: allowed HTTP methods
    allowed_methods = ('GET', 'PATCH', 'DELETE', )

    def get(self, series_slug, path_param=None):
        """Query series information.

        :param series_slug: series slug. E.g.: tvdb1234
        :param path_param:
        """
        arg_paused = self._parse_boolean(self.get_argument('paused', default=None))

        def filter_series(current):
            return arg_paused is None or current.paused == arg_paused

        if not series_slug:
            detailed = self._parse_boolean(self.get_argument('detailed', default=False))
            data = [s.to_json(detailed=detailed) for s in Series.find_series(predicate=filter_series)]
            return self._paginate(data, sort='title')

        identifier = SeriesIdentifier.from_slug(series_slug)
        if not identifier:
            return self._bad_request('Invalid series slug')

        series = Series.find_by_identifier(identifier, predicate=filter_series)
        if not series:
            return self._not_found('Series not found')

        detailed = self._parse_boolean(self.get_argument('detailed', default=True))
        data = series.to_json(detailed=detailed)
        if path_param:
            if path_param not in data:
                return self._bad_request("Invalid path parameter '{0}'".format(path_param))
            data = data[path_param]

        return self._ok(data)

    def post(self, series_slug=None, path_param=None):
        """Add a new series."""
        if series_slug is not None:
            return self._bad_request('Series slug should not be specified')

        data = json_decode(self.request.body)
        if not data or 'id' not in data:
            return self._bad_request('Invalid series data')

        ids = {k: v for k, v in viewitems(data['id']) if k != 'imdb'}
        if len(ids) != 1:
            return self._bad_request('Only 1 indexer identifier should be specified')

        identifier = SeriesIdentifier.from_slug('{slug}{id}'.format(slug=list(ids)[0], id=list(itervalues(ids))[0]))
        if not identifier:
            return self._bad_request('Invalid series identifier')

        series = Series.find_by_identifier(identifier)
        if series:
            return self._conflict('Series already exist added')

        series = Series.from_identifier(identifier)
        if not Series.save_series(series):
            return self._not_found('Series not found in the specified indexer')

        return self._created(series.to_json(), identifier=identifier.slug)

    def patch(self, series_slug, path_param=None):
        """Patch series."""
        if not series_slug:
            return self._method_not_allowed('Patching multiple series is not allowed')

        identifier = SeriesIdentifier.from_slug(series_slug)
        if not identifier:
            return self._bad_request('Invalid series identifier')

        series = Series.find_by_identifier(identifier)
        if not series:
            return self._not_found('Series not found')

        data = json_decode(self.request.body)
        indexer_id = data.get('id', {}).get(identifier.indexer.slug)
        if indexer_id is not None and indexer_id != identifier.id:
            return self._bad_request('Conflicting series identifier')

        accepted = {}
        ignored = {}
        patches = {
            'config.aliases': ListField(series, 'aliases'),
            'config.defaultEpisodeStatus': StringField(series, 'default_ep_status_name'),
            'config.dvdOrder': BooleanField(series, 'dvd_order'),
            'config.seasonFolders': BooleanField(series, 'season_folders'),
            'config.anime': BooleanField(series, 'anime'),
            'config.scene': BooleanField(series, 'scene'),
            'config.sports': BooleanField(series, 'sports'),
            'config.paused': BooleanField(series, 'paused'),
            'config.location': StringField(series, '_location'),
            'config.airByDate': BooleanField(series, 'air_by_date'),
            'config.subtitlesEnabled': BooleanField(series, 'subtitles'),
            'config.release.requiredWords': ListField(series, 'release_required_words'),
            'config.release.ignoredWords': ListField(series, 'release_ignore_words'),
            'config.release.blacklist': ListField(series, 'blacklist'),
            'config.release.whitelist': ListField(series, 'whitelist'),
            'language': StringField(series, 'lang'),
            'config.qualities.allowed': ListField(series, 'qualities_allowed'),
            'config.qualities.preferred': ListField(series, 'qualities_preferred'),
            'config.qualities.combined': IntegerField(series, 'quality'),
        }
        for key, value in iter_nested_items(data):
            patch_field = patches.get(key)
            if patch_field and patch_field.patch(series, value):
                set_nested_value(accepted, key, value)
            else:
                set_nested_value(ignored, key, value)

        # Save patched attributes in db.
        series.save_to_db()

        if ignored:
            log.warning('Series patch ignored %r', ignored)

        self._ok(data=accepted)

    def delete(self, series_slug, path_param=None):
        """Delete the series."""
        if not series_slug:
            return self._method_not_allowed('Deleting multiple series are not allowed')

        identifier = SeriesIdentifier.from_slug(series_slug)
        if not identifier:
            return self._bad_request('Invalid series identifier')

        series = Series.find_by_identifier(identifier)
        if not series:
            return self._not_found('Series not found')

        remove_files = self._parse_boolean(self.get_argument('remove-files', default=None))
        if not series.delete(remove_files):
            return self._conflict('Unable to delete series')

        return self._no_content()
