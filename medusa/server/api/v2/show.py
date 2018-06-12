# coding=utf-8
"""Request handler for show and episodes."""
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
from medusa.tv.show import Show, ShowIdentifier

from six import itervalues, viewitems

from tornado.escape import json_decode

log = BraceAdapter(logging.getLogger(__name__))


class ShowHandler(BaseRequestHandler):
    """Show request handler."""

    #: resource name
    name = 'show'
    #: identifier
    identifier = ('show_slug', r'\w+')
    #: path param
    path_param = ('path_param', r'\w+')
    #: allowed HTTP methods
    allowed_methods = ('GET', 'PATCH', 'DELETE', )

    def get(self, show_slug, path_param=None):
        """Query show information.

        :param show_slug: show slug. E.g.: tvdb1234
        :param path_param:
        """
        arg_paused = self._parse_boolean(self.get_argument('paused', default=None))

        def filter_show(current):
            return arg_paused is None or current.paused == arg_paused

        if not show_slug:
            detailed = self._parse_boolean(self.get_argument('detailed', default=False))
            data = [s.to_json(detailed=detailed) for s in Show.find_show(predicate=filter_show)]
            return self._paginate(data, sort='title')

        identifier = ShowIdentifier.from_slug(show_slug)
        if not identifier:
            return self._bad_request('Invalid show slug')

        show = Show.find_by_identifier(identifier, predicate=filter_show)
        if not show:
            return self._not_found('Show not found')

        detailed = self._parse_boolean(self.get_argument('detailed', default=True))
        data = show.to_json(detailed=detailed)
        if path_param:
            if path_param not in data:
                return self._bad_request("Invalid path parameter '{0}'".format(path_param))
            data = data[path_param]

        return self._ok(data)

    def post(self, show_slug=None, path_param=None):
        """Add a new show."""
        if show_slug is not None:
            return self._bad_request('Show slug should not be specified')

        data = json_decode(self.request.body)
        if not data or 'id' not in data:
            return self._bad_request('Invalid show data')

        ids = {k: v for k, v in viewitems(data['id']) if k != 'imdb'}
        if len(ids) != 1:
            return self._bad_request('Only 1 indexer identifier should be specified')

        identifier = ShowIdentifier.from_slug('{slug}{id}'.format(slug=list(ids)[0], id=list(itervalues(ids))[0]))
        if not identifier:
            return self._bad_request('Invalid show identifier')

        show = Show.find_by_identifier(identifier)
        if show:
            return self._conflict('Show already exist added')

        show = Show.from_identifier(identifier)
        if not Show.save_show(show):
            return self._not_found('Show not found in the specified indexer')

        return self._created(show.to_json(), identifier=identifier.slug)

    def patch(self, show_slug, path_param=None):
        """Patch show."""
        if not show_slug:
            return self._method_not_allowed('Patching multiple show is not allowed')

        identifier = ShowIdentifier.from_slug(show_slug)
        if not identifier:
            return self._bad_request('Invalid show identifier')

        show = Show.find_by_identifier(identifier)
        if not show:
            return self._not_found('Show not found')

        data = json_decode(self.request.body)
        indexer_id = data.get('id', {}).get(identifier.indexer.slug)
        if indexer_id is not None and indexer_id != identifier.id:
            return self._bad_request('Conflicting show identifier')

        accepted = {}
        ignored = {}
        patches = {
            'config.aliases': ListField(show, 'aliases'),
            'config.defaultEpisodeStatus': StringField(show, 'default_ep_status_name'),
            'config.dvdOrder': BooleanField(show, 'dvd_order'),
            'config.seasonFolders': BooleanField(show, 'season_folders'),
            'config.anime': BooleanField(show, 'anime'),
            'config.scene': BooleanField(show, 'scene'),
            'config.sports': BooleanField(show, 'sports'),
            'config.paused': BooleanField(show, 'paused'),
            'config.location': StringField(show, '_location'),
            'config.airByDate': BooleanField(show, 'air_by_date'),
            'config.subtitlesEnabled': BooleanField(show, 'subtitles'),
            'config.release.requiredWords': ListField(show, 'release_required_words'),
            'config.release.ignoredWords': ListField(show, 'release_ignore_words'),
            'config.release.blacklist': ListField(show, 'blacklist'),
            'config.release.whitelist': ListField(show, 'whitelist'),
            'language': StringField(show, 'lang'),
            'config.qualities.allowed': ListField(show, 'qualities_allowed'),
            'config.qualities.preferred': ListField(show, 'qualities_preferred'),
            'config.qualities.combined': IntegerField(show, 'quality'),
        }
        for key, value in iter_nested_items(data):
            patch_field = patches.get(key)
            if patch_field and patch_field.patch(show, value):
                set_nested_value(accepted, key, value)
            else:
                set_nested_value(ignored, key, value)

        # Save patched attributes in db.
        show.save_to_db()

        if ignored:
            log.warning('Show patch ignored %r', ignored)

        self._ok(data=accepted)

    def delete(self, show_slug, path_param=None):
        """Delete the show."""
        if not show_slug:
            return self._method_not_allowed('Deleting multiple show are not allowed')

        identifier = ShowIdentifier.from_slug(show_slug)
        if not identifier:
            return self._bad_request('Invalid show identifier')

        show = Show.find_by_identifier(identifier)
        if not show:
            return self._not_found('Show not found')

        remove_files = self._parse_boolean(self.get_argument('remove-files', default=None))
        if not show.delete(remove_files):
            return self._conflict('Unable to delete show')

        return self._no_content()
