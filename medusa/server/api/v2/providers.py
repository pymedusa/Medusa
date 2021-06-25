# coding=utf-8
"""Request handler for series and episodes."""
from __future__ import unicode_literals
from collections import OrderedDict

import logging
from datetime import datetime

from dateutil import parser

from medusa import app, providers
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers import get_provider_class
from medusa.providers.nzb.newznab import NewznabProvider
from medusa.providers.prowlarr import ProwlarrManager
from medusa.providers.torrent.rss.rsstorrent import TorrentRssProvider
from medusa.providers.torrent.torrent_provider import TorrentProvider
from medusa.providers.torrent.torznab.torznab import TorznabProvider
from medusa.server.api.v2.base import (
    BaseRequestHandler,
)

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

        # Return provider results
        if path_param == 'results':
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

        return self._ok(provider.to_json())

    def patch(self, identifier, **kwargs):
        """Patch provider config."""
        data = json_decode(self.request.body)
        if not identifier:
            return self._bad_request('You should provide the provider you want to patch')

        provider = get_provider_class(identifier)
        if not provider:
            return self._bad_request('Could not locate provider by id')

        self._set_common_settings(provider, data)
        if isinstance(provider, TorrentProvider):
            self._set_torrent_settings(provider, data)

        app.instance.save_config()
        return self._ok()

    def post(self, identifier, path_param=None):
        """
        Add a new provider or run an operation on a specific provider type.

        Without the identifier an arary of provider objects is expected to save the provider order list.
        With a subType param, operations can be executed, like the newznab/getCategories. Which will return
            a list of available newznab categories.
        :param identifier: Provider subType. For example: torznab, newznab, torrentrss.
        """
        if not identifier:
            data = json_decode(self.request.body)
            sorted_providers = data.get('providers')
            if sorted_providers is None:
                return self._bad_request('You should provide an array of providers')

            self._save_provider_order(sorted_providers)
            return self._created(data={'providers': providers})

        if identifier:
            data = json_decode(self.request.body)
            if identifier in ('newznab', 'torznab', 'torrentrss'):
                if not path_param:
                    # No path_param passed. Asume we're trying to add a provider.
                    if identifier == 'newznab':
                        return self._add_newznab_provider(data)
                    if identifier == 'torrentrss':
                        return self._add_torrentrss_provider(data)
                    if identifier == 'torznab':
                        return self._add_torznab_provider(data)

                if path_param == 'operation':
                    if data.get('type') == 'GETCATEGORIES':
                        return self._get_categories(identifier, data)

            if identifier == 'prowlarr':
                if path_param == 'operation':
                    if data.get('type') == 'TEST':
                        # Test prowlarr connectivity
                        prowlarr = ProwlarrManager(data.get('url'), data.get('apikey'))
                        if prowlarr.test_connectivity():
                            return self._ok('Connection successfull')
                        else:
                            return self._not_found('Çould not connect to prowlarr')
                    if data.get('type') == 'GETINDEXERS':
                        prowlarr = ProwlarrManager(data.get('url'), data.get('apikey'))
                        indexers = prowlarr.get_indexers()
                        if indexers:
                            return self._ok(indexers)
                        return self._internal_server_error()

        return self._bad_request('Could not locate provider by id')

    def delete(self, identifier, path_param=None):
        """
        Delete a provider.

        You cannot delete "default" providers. The provider needs to be able to be part of
        a certain subType. For example: 'newznab', 'torznab' or 'torrentrss'.

        :param identifier: The provider subtype.
        :param path_param: Provider id.
        """
        if identifier not in ('newznab', 'torznab', 'torrentrss'):
            return self._bad_request('You should provide an identifier. For example: newznab, torznab or torrentrss.')

        if not path_param:
            return self._bad_request('Missing provider id')

        if identifier == 'newznab':
            remove_provider = [prov for prov in app.newznabProviderList if prov.get_id() == path_param and not prov.default]
            if not remove_provider:
                return self._not_found('Provider id not found')

            # delete it from the list
            app.newznabProviderList.remove(remove_provider[0])

            if path_param in app.PROVIDER_ORDER:
                app.PROVIDER_ORDER.remove(path_param)
            app.instance.save_config()

            return self._no_content()

        if identifier == 'torrentrss':
            remove_provider = [prov for prov in app.torrentRssProviderList if prov.get_id() == path_param]
            if not remove_provider:
                return self._not_found('Provider id not found')

            # delete it from the list
            app.torrentRssProviderList.remove(remove_provider[0])

            if path_param in app.PROVIDER_ORDER:
                app.PROVIDER_ORDER.remove(path_param)
            app.instance.save_config()

            return self._no_content()

        if identifier == 'torznab':
            remove_provider = [prov for prov in app.torznab_providers_list if prov.get_id() == path_param]
            if not remove_provider:
                return self._not_found('Provider id not found')

            # delete it from the list
            app.torznab_providers_list.remove(remove_provider[0])

            if path_param in app.PROVIDER_ORDER:
                app.PROVIDER_ORDER.remove(path_param)
            app.instance.save_config()

            return self._no_content()

    def _get_categories(self, sub_type, data):
        """
        Retrieve a list of possible categories with category ids.

        Using the default url/api?cat
        http://yournewznaburl.com/api?t=caps&apikey=yourapikey
        """
        if not data.get('name'):
            return self._bad_request('No provider name provided')

        if not data.get('url'):
            return self._bad_request('No provider url provided')

        if not data.get('apikey'):
            return self._bad_request('No provider api key provided')

        if sub_type == 'newznab':
            provider = NewznabProvider(data.get('name'), data.get('url'), data.get('apikey'))
        elif sub_type == 'torznab':
            provider = TorznabProvider(data.get('name'), data.get('url'), data.get('apikey'))

        capabilities = provider.get_capabilities()
        return self._created(data={'result': capabilities._asdict()})

    def _add_newznab_provider(self, data):
        if not data.get('name'):
            return self._bad_request('No provider name provided')

        if not data.get('url'):
            return self._bad_request('No provider url provided')

        if not data.get('apikey'):
            return self._bad_request('No provider api key provided')

        new_provider = NewznabProvider(data.get('name'), data.get('url'), api_key=data.get('apikey'))
        if new_provider.get_id() in [x.get_id() for x in app.newznabProviderList]:
            return self._conflict(f'Provider id {new_provider.get_id()} already exists')

        app.newznabProviderList.append(new_provider)
        NewznabProvider.save_newznab_providers()
        app.instance.save_config()
        return self._created(data={'result': new_provider.to_json()})

    def _add_torznab_provider(self, data):
        if not data.get('name'):
            return self._bad_request('No provider name provided')

        if not data.get('url'):
            return self._bad_request('No provider url provided')

        if not data.get('apikey'):
            return self._bad_request('No provider api key provided')

        new_provider = TorznabProvider(data.get('name'), data.get('url'), api_key=data.get('apikey'))
        if new_provider.get_id() in [x.get_id() for x in app.torznab_providers_list]:
            return self._conflict(f'Provider id {new_provider.get_id()} already exists')

        app.torznab_providers_list.append(new_provider)
        app.TORZNAB_PROVIDERS = [provider.name for provider in app.torznab_providers_list]
        app.instance.save_config()
        return self._created(data={'result': new_provider.to_json()})

    def _add_torrentrss_provider(self, data):
        if not data.get('name'):
            return self._bad_request('No provider name provided')

        if not data.get('url'):
            return self._bad_request('No provider url provided')

        new_provider = TorrentRssProvider(data.get('name'), data.get('url'), data.get('cookies', ''), data.get('titleTag', 'title'))
        app.torrentRssProviderList.append(new_provider)
        # Update the torrentrss provider list
        app.TORRENTRSS_PROVIDERS = [provider.name for provider in app.torrentRssProviderList]

        app.instance.save_config()
        return self._created(data={'result': new_provider.to_json()})

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
                provider.username = None

        if hasattr(provider, 'api_key'):
            try:
                provider.api_key = config['apikey']
            except (AttributeError, KeyError):
                pass

        if hasattr(provider, 'search_mode'):
            try:
                provider.search_mode = config['search']['mode']
            except (AttributeError, KeyError):
                provider.search_mode = 'eponly'

        if hasattr(provider, 'search_fallback'):
            try:
                provider.search_fallback = config['search']['fallback']
            except (AttributeError, KeyError):
                provider.search_fallback = 0

        if hasattr(provider, 'enable_daily'):
            try:
                provider.enable_daily = config['search']['daily']['enabled']
            except (AttributeError, KeyError):
                provider.enable_daily = 0

        if hasattr(provider, 'enable_backlog'):
            try:
                provider.enable_backlog = config['search']['backlog']['enabled']
            except (AttributeError, KeyError):
                provider.enable_backlog = 0

        if hasattr(provider, 'enable_manualsearch'):
            try:
                provider.enable_manualsearch = config['search']['manual']['enabled']
            except (AttributeError, KeyError):
                provider.enable_manualsearch = 0

        if hasattr(provider, 'enable_search_delay'):
            try:
                provider.enable_search_delay = config['search']['delay']['enabled']
            except (AttributeError, KeyError):
                provider.enable_search_delay = 0

        if hasattr(provider, 'search_delay'):
            try:
                search_delay = float(config['search']['delay']['duration'])
                provider.search_delay = (search_delay, 30)[search_delay < 30]
            except (AttributeError, KeyError, ValueError):
                provider.search_delay = 480

        # Newznab specific
        if hasattr(provider, 'cat_ids'):
            try:
                provider.cat_ids = config['catIds']
            except (AttributeError, KeyError):
                provider.cat_ids = []

    @staticmethod
    def _set_torrent_settings(provider, config):

        if hasattr(provider, 'custom_url'):
            try:
                provider.custom_url = config['customUrl']
            except (AttributeError, KeyError):
                provider.custom_url = None

        if hasattr(provider, 'minseed'):
            try:
                provider.minseed = config['minseed']
            except (AttributeError, KeyError, ValueError):
                provider.minseed = 1

        if hasattr(provider, 'minleech'):
            try:
                provider.minleech = config['minleech']
            except (AttributeError, KeyError, ValueError):
                provider.minleech = 0

        if hasattr(provider, 'ratio'):
            try:
                ratio = config['ratio']
                provider.ratio = (ratio, -1)[ratio < 0]
            except (AttributeError, KeyError, ValueError, TypeError):
                provider.ratio = -1

        if hasattr(provider, 'digest'):
            try:
                provider.digest = config['digest']
            except (AttributeError, KeyError):
                provider.digest = None

        if hasattr(provider, 'hash'):
            try:
                provider.hash = config['hash']
            except (AttributeError, KeyError):
                provider.hash = None

        if hasattr(provider, 'passkey'):
            try:
                provider.passkey = config['passkey']
            except (AttributeError, KeyError):
                provider.passkey = None

        if hasattr(provider, 'pin'):
            try:
                provider.pin = config['pin']
            except (AttributeError, KeyError):
                provider.pin = None

        if hasattr(provider, 'confirmed'):
            try:
                provider.confirmed = config['confirmed']
            except (AttributeError, KeyError):
                provider.confirmed = 0

        if hasattr(provider, 'ranked'):
            try:
                provider.ranked = config['ranked']
            except (AttributeError, KeyError):
                provider.ranked = 0

        if hasattr(provider, 'sorting'):
            try:
                provider.sorting = config['sorting']
            except (AttributeError, KeyError):
                provider.sorting = 'seeders'

        if hasattr(provider, 'freeleech'):
            try:
                provider.freeleech = config['freeleech']
            except (AttributeError, KeyError):
                provider.freeleech = 0

        # if hasattr(provider, 'cat'):
        #     try:
        #         provider.cat = int(str(kwargs['{id}_cat'.format(id=provider.get_id())]).strip())
        #     except (AttributeError, KeyError):
        #         provider.cat = 0

        # if hasattr(provider, 'subtitle'):
        #     try:
        #         provider.subtitle = config.checkbox_to_value(
        #             kwargs['{id}_subtitle'.format(id=provider.get_id())])
        #     except (AttributeError, KeyError):
        #         provider.subtitle = 0

        if provider.enable_cookies:
            try:
                provider.cookies = config['cookies']
            except (AttributeError, KeyError):
                # I don't want to configure a default value here, as it can also
                # be configured intially as a custom rss torrent provider
                pass

        if hasattr(provider, 'title_tag'):
            try:
                provider.title_tag = config['titleTag']
            except (AttributeError, KeyError):
                provider.title_tag = 'title'
