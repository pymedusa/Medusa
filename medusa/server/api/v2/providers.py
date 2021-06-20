# coding=utf-8
"""Request handler for series and episodes."""
from __future__ import unicode_literals
from collections import OrderedDict

import logging
from datetime import datetime

from dateutil import parser

from medusa import app, providers
from medusa.logger.adapters.style import BraceAdapter
from medusa.server.api.v2.base import (
    BaseRequestHandler,
)
from medusa.providers.torrent.torrent_provider import TorrentProvider

from tornado.escape import json_decode

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class ProvidersHandler(BaseRequestHandler):
    """Providers request handler."""

    #: resource name
    name = 'providers'
    #: identifier
    identifier = ('identifier', r'\w+')
    #: path param
    path_param = ('path_param', r'\w+')
    #: allowed HTTP methods
    allowed_methods = ('GET',)

    def get(self, identifier, path_param=None):
        """
        Query provider information.

        Return a list of provider id's.

        :param identifier: provider id. E.g.: myawesomeprovider
        :param path_param:
        """
        show_slug = self._parse(self.get_argument('showslug', default=None), str)
        season = self._parse(self.get_argument('season', default=None), str)
        episode = self._parse(self.get_argument('episode', default=None), str)

        if not identifier:
            # return a list of provider id's
            provider_list = providers.sorted_provider_list()
            return self._ok([provider.to_json() for provider in provider_list])

        provider = providers.get_provider_class(identifier)
        if not provider:
            return self._not_found('Provider not found')

        if not path_param == 'results':
            return self._ok(provider.to_json())

        provider_results = provider.cache.get_results(show_slug=show_slug, season=season, episode=episode)

        arg_page = self._get_page()
        arg_limit = self._get_limit(default=50)

        def data_generator():
            """Create provider results."""
            start = arg_limit * (arg_page - 1) + 1

            for item in provider_results[start - 1:start - 1 + arg_limit]:
                episodes = [int(ep) for ep in item['episodes'].strip('|').split('|') if ep != '']
                yield {
                    'identifier': item['identifier'],
                    'release': item['name'],
                    'season': item['season'],
                    'episodes': episodes,
                    # For now if episodes is 0 or (multiepisode) mark as season pack.
                    'seasonPack': len(episodes) == 0 or len(episodes) > 1,
                    'indexer': item['indexer'],
                    'seriesId': item['indexerid'],
                    'showSlug': show_slug,
                    'url': item['url'],
                    'time': datetime.fromtimestamp(item['time']),
                    'quality': item['quality'],
                    'releaseGroup': item['release_group'],
                    'dateAdded': datetime.fromtimestamp(item['date_added']),
                    'version': item['version'],
                    'seeders': item['seeders'],
                    'size': item['size'],
                    'leechers': item['leechers'],
                    'pubdate': parser.parse(item['pubdate']).replace(microsecond=0) if item['pubdate'] else None,
                    'provider': {
                        'id': provider.get_id(),
                        'name': provider.name,
                        'imageName': provider.image_name()
                    }
                }

        if not len(provider_results):
            return self._not_found('Provider cache results not found')

        return self._paginate(data_generator=data_generator)

    def post(self, **kwargs):
        """Save an ordered list of providers."""
        data = json_decode(self.request.body)
        sorted_providers = data.get('providers')
        if sorted_providers is None:
            return self._bad_request('You should provide an array of providers')

        # for sorted_provider in sorted_providers:
        #     provider = providers.get_provider_class(sorted_provider.get('id'))
        #     if not provider:
        #         log.warning('Could not locate a provider class for {provider_id}', {'provider_id': provider.get('id')})
        #         continue
        self._save_provider_order(sorted_providers)
        return self._created(data={'providers': providers})

    def _save_provider_order(self, sorted_providers):
        """Save the provider order."""
        def ordered_providers(names, providers):
            reminder = {}
            for name in names:
                for provider in providers:
                    reminder[provider.get_id()] = provider
                    if provider.get_id() == name:
                        yield provider
            else:
                rest = set(reminder).difference(set(names))
                for provider in rest:
                    yield reminder[provider]

        ordered_names = OrderedDict()
        for sorted_provider in sorted_providers:
            ordered_names[sorted_provider['id']] = sorted_provider['config']['enabled']

        providers_enabled = []
        providers_disabled = []
        all_providers = providers.sorted_provider_list()

        for provider in ordered_providers(ordered_names, all_providers):
            name = provider.get_id()
            if ordered_names.get(name):
                provider.enabled = True
                providers_enabled.append(name)
            else:
                provider.enabled = False
                providers_disabled.append(name)

            new_settings = [prov for prov in sorted_providers if prov.get('id') == name]
            if not new_settings:
                continue

            self._set_common_settings(provider, new_settings[0]['config'])
            if isinstance(provider, TorrentProvider):
                self._set_torrent_settings(provider, new_settings[0]['config'])

        app.PROVIDER_ORDER = providers_enabled + providers_disabled
        app.instance.save_config()

    @staticmethod
    def _set_common_settings(provider, config):
        if hasattr(provider, 'username'):
            try:
                provider.username = config['username']
            except (AttributeError, KeyError):
                provider.username = None  # these exceptions are actually catching unselected checkboxes

        if hasattr(provider, 'api_key'):
            try:
                provider.api_key = config['apikey']
            except (AttributeError, KeyError):
                pass

        if hasattr(provider, 'search_mode'):
            try:
                provider.search_mode = config['search']['mode']
            except (AttributeError, KeyError):
                provider.search_mode = 'eponly'  # these exceptions are actually catching unselected checkboxes

        if hasattr(provider, 'search_fallback'):
            try:
                provider.search_fallback = config['search']['fallback']
            except (AttributeError, KeyError):
                provider.search_fallback = 0  # these exceptions are actually catching unselected checkboxes

        if hasattr(provider, 'enable_daily'):
            try:
                provider.enable_daily = config['search']['daily']['enabled']
            except (AttributeError, KeyError):
                provider.enable_daily = 0  # these exceptions are actually catching unselected checkboxes

        if hasattr(provider, 'enable_backlog'):
            try:
                provider.enable_backlog = config['search']['backlog']['enabled']
            except (AttributeError, KeyError):
                provider.enable_backlog = 0  # these exceptions are actually catching unselected checkboxes

        if hasattr(provider, 'enable_manualsearch'):
            try:
                provider.enable_manualsearch = config['search']['manual']['enabled']
            except (AttributeError, KeyError):
                provider.enable_manualsearch = 0  # these exceptions are actually catching unselected checkboxes

        if hasattr(provider, 'enable_search_delay'):
            try:
                provider.enable_search_delay = config['search']['delay']['enabled']
            except (AttributeError, KeyError):
                provider.enable_search_delay = 0  # these exceptions are actually catching unselected checkboxes

        if hasattr(provider, 'search_delay'):
            try:
                search_delay = float(config['search']['delay']['duration'])
                provider.search_delay = (int(search_delay * 60), 30)[search_delay < 0.5]
            except (AttributeError, KeyError, ValueError):
                provider.search_delay = 480  # these exceptions are actually catching unselected checkboxes

    @staticmethod
    def _set_torrent_settings(provider, config):

        if hasattr(provider, 'custom_url'):
            try:
                provider.custom_url = config['customUrl']
            except (AttributeError, KeyError):
                provider.custom_url = None  # these exceptions are actually catching unselected checkboxes

        if hasattr(provider, 'minseed'):
            try:
                provider.minseed = config['minseed']
            except (AttributeError, KeyError, ValueError):
                provider.minseed = 1  # these exceptions are actually catching unselected checkboxes

        if hasattr(provider, 'minleech'):
            try:
                provider.minleech = config['minleech']
            except (AttributeError, KeyError, ValueError):
                provider.minleech = 0  # these exceptions are actually catching unselected checkboxes

        if hasattr(provider, 'ratio'):
            try:
                ratio = config['ratio']
                provider.ratio = (ratio, -1)[ratio < 0]
            except (AttributeError, KeyError, ValueError):
                provider.ratio = ''  # these exceptions are actually catching unselected checkboxes

        if hasattr(provider, 'digest'):
            try:
                provider.digest = config['digest']
            except (AttributeError, KeyError):
                provider.digest = None  # these exceptions are actually catching unselected checkboxes

        if hasattr(provider, 'hash'):
            try:
                provider.hash = config['hash']
            except (AttributeError, KeyError):
                provider.hash = None  # these exceptions are actually catching unselected checkboxes

        if hasattr(provider, 'passkey'):
            try:
                provider.passkey = config['passkey']
            except (AttributeError, KeyError):
                provider.passkey = None  # these exceptions are actually catching unselected checkboxes

        if hasattr(provider, 'pin'):
            try:
                provider.pin = config['pin']
            except (AttributeError, KeyError):
                provider.pin = None  # these exceptions are actually catching unselected checkboxes

        if hasattr(provider, 'confirmed'):
            try:
                provider.confirmed = config['confirmed']
            except (AttributeError, KeyError):
                provider.confirmed = 0  # these exceptions are actually catching unselected checkboxes

        if hasattr(provider, 'ranked'):
            try:
                provider.ranked = config['ranked']
            except (AttributeError, KeyError):
                provider.ranked = 0  # these exceptions are actually catching unselected checkboxes

        if hasattr(provider, 'sorting'):
            try:
                provider.sorting = config['sorting']
            except (AttributeError, KeyError):
                provider.sorting = 'seeders'  # these exceptions are actually catching unselected checkboxes

        if hasattr(provider, 'freeleech'):
            try:
                provider.freeleech = config['freeleech']
            except (AttributeError, KeyError):
                provider.freeleech = 0  # these exceptions are actually catching unselected checkboxes

        # if hasattr(provider, 'cat'):
        #     try:
        #         provider.cat = int(str(kwargs['{id}_cat'.format(id=provider.get_id())]).strip())
        #     except (AttributeError, KeyError):
        #         provider.cat = 0  # these exceptions are actually catching unselected checkboxes

        # if hasattr(provider, 'subtitle'):
        #     try:
        #         provider.subtitle = config.checkbox_to_value(
        #             kwargs['{id}_subtitle'.format(id=provider.get_id())])
        #     except (AttributeError, KeyError):
        #         provider.subtitle = 0  # these exceptions are actually catching unselected checkboxes

        if provider.enable_cookies:
            try:
                provider.cookies = config['cookies']
            except (AttributeError, KeyError):
                # I don't want to configure a default value here, as it can also
                # be configured intially as a custom rss torrent provider
                pass
