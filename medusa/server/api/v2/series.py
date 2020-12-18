# coding=utf-8
"""Request handler for series and episodes."""
from __future__ import unicode_literals

import logging

from medusa import app, ws
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
from medusa.tv.series import SaveSeriesException, Series, SeriesIdentifier

from six import itervalues, viewitems

from tornado.escape import json_decode

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class SeriesHandler(BaseRequestHandler):
    """Series request handler."""

    #: resource name
    name = 'series'
    #: identifier
    identifier = ('series_slug', r'\w+')
    #: path param
    path_param = ('path_param', r'\w+')
    #: allowed HTTP methods
    allowed_methods = ('GET', 'POST', 'PATCH', 'DELETE', )

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
            episodes = self._parse_boolean(self.get_argument('episodes', default=False))
            data = [
                s.to_json(detailed=detailed, episodes=episodes)
                for s in Series.find_series(predicate=filter_series)
            ]

            return self._paginate(data, sort='title')

        identifier = SeriesIdentifier.from_slug(series_slug)
        if not identifier:
            return self._bad_request('Invalid series slug')

        series = Series.find_by_identifier(identifier, predicate=filter_series)
        if not series:
            return self._not_found('Series not found')

        detailed = self._parse_boolean(self.get_argument('detailed', default=False))
        episodes = self._parse_boolean(self.get_argument('episodes', default=False))
        data = series.to_json(detailed=detailed, episodes=episodes)
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

        if Series.find_by_identifier(identifier):
            return self._conflict('Series already exist added')

        data_options = data.get('options', {})

        try:
            options = {
                'default_status': data_options.get('status'),
                'quality': data_options.get('quality', {'preferred': [], 'allowed': []}),
                'season_folders': data_options.get('seasonFolders'),
                'lang': data_options.get('language'),
                'subtitles': data_options.get('subtitles'),
                'anime': data_options.get('anime'),
                'scene': data_options.get('scene'),
                'paused': data_options.get('paused'),
                'blacklist': data_options['release'].get('blacklist', []) if data_options.get('release') else None,
                'whitelist: ': data_options['release'].get('whitelist', []) if data_options.get('release') else None,
                'default_status_after': data_options.get('statusAfter'),
                'root_dir': data_options.get('rootDir'),
                'show_lists': data_options.get('showLists')
            }

            queue_item_obj = app.show_queue_scheduler.action.addShow(
                identifier.indexer.id, identifier.id, data_options.get('showDir'), **options
            )
        except SaveSeriesException as error:
            return self._not_found(error)

        return self._created(data=queue_item_obj.to_json)

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
            'config.location': StringField(series, 'location'),
            'config.airByDate': BooleanField(series, 'air_by_date'),
            'config.subtitlesEnabled': BooleanField(series, 'subtitles'),
            'config.release.requiredWords': ListField(series, 'release_required_words'),
            'config.release.ignoredWords': ListField(series, 'release_ignore_words'),
            'config.release.blacklist': ListField(series, 'blacklist'),
            'config.release.whitelist': ListField(series, 'whitelist'),
            'config.release.requiredWordsExclude': BooleanField(series, 'rls_require_exclude'),
            'config.release.ignoredWordsExclude': BooleanField(series, 'rls_ignore_exclude'),
            'language': StringField(series, 'lang'),
            'config.qualities.allowed': ListField(series, 'qualities_allowed'),
            'config.qualities.preferred': ListField(series, 'qualities_preferred'),
            'config.qualities.combined': IntegerField(series, 'quality'),
            'config.airdateOffset': IntegerField(series, 'airdate_offset'),
            'config.showLists': ListField(Series, 'show_lists'),
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
            log.warning('Series patch ignored {items!r}', {'items': ignored})

        # Push an update to any open Web UIs through the WebSocket
        msg = ws.Message('showUpdated', series.to_json(detailed=False))
        msg.push()

        return self._ok(data=accepted)

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
