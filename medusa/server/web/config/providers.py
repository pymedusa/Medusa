# coding=utf-8

"""Configure Providers."""

from __future__ import unicode_literals

import json
import os
from builtins import str
from builtins import zip
from collections import OrderedDict

from medusa import app, config, providers, ui
from medusa.helper.common import try_int
from medusa.helpers.utils import split_and_strip
from medusa.providers.nzb.newznab import NewznabProvider
from medusa.providers.torrent.rss.rsstorrent import TorrentRssProvider
from medusa.providers.torrent.torrent_provider import TorrentProvider
from medusa.providers.torrent.torznab.torznab import TorznabProvider
from medusa.server.web.config.handler import Config
from medusa.server.web.core import PageTemplate

from tornroutes import route

INVALID_CHARS = ['||']


@route('/config/providers(/?.*)')
class ConfigProviders(Config):
    """Handler for Provider configuration."""

    def __init__(self, *args, **kwargs):
        super(ConfigProviders, self).__init__(*args, **kwargs)

    def index(self):
        """Render the Provider configuration page."""
        t = PageTemplate(rh=self, filename='config_providers.mako')

        return t.render(submenu=self.ConfigMenu(),
                        controller='config', action='providers')

    @staticmethod
    def canAddTorrentRssProvider(name, url, cookies, title_tag):
        """See if a Torrent provider can be added."""
        if not name:
            return json.dumps({'error': 'Invalid name specified'})

        found_chars = [c for c in INVALID_CHARS if c in name]
        if found_chars:
            return json.dumps({'error': 'Invalid character in provider name: {0}'.format(', '.join(found_chars))})

        provider_dict = dict(list(zip([x.get_id() for x in app.torrentRssProviderList],
                                      app.torrentRssProviderList)))
        temp_provider = TorrentRssProvider(name, url, cookies, title_tag)

        if temp_provider.get_id() in provider_dict:
            return json.dumps({'error': 'Provider name already exists as {name}'.format(
                              name=provider_dict[temp_provider.get_id()].name)})
        else:
            validate = temp_provider.validate_rss()
            if validate['result']:
                return json.dumps({'success': temp_provider.get_id()})
            else:
                return json.dumps({'error': validate['message']})

    @staticmethod
    def canAddProvider(kind, name, url, api_key=None):
        """See if a Newznab or Torznab provider can be added."""
        if not name:
            return json.dumps({'error': 'No Provider Name specified'})

        found_chars = [c for c in INVALID_CHARS if c in name]
        if found_chars:
            return json.dumps({'error': 'Invalid character in provider name: {0}'.format(', '.join(found_chars))})

        if kind == 'newznab':
            provider_dict = dict(list(zip([x.get_id() for x in app.newznabProviderList],
                                          app.newznabProviderList)))
            temp_provider = NewznabProvider(name, url)
        elif kind == 'torznab':
            provider_dict = dict(list(zip([x.get_id() for x in app.torznab_providers_list],
                                          app.torznab_providers_list)))
            temp_provider = TorznabProvider(name, url, api_key)

        if temp_provider.get_id() in provider_dict:
            return json.dumps({'error': 'Provider name already exists as {name}'.format(
                              name=provider_dict[temp_provider.get_id()].name)})
        else:
            return json.dumps({'success': temp_provider.get_id()})

    @staticmethod
    def getZnabCategories(kind, name, url, api_key):
        """
        Retrieve a list of possible categories with category ids.

        Using the default url/api?cat
        http://yournewznaburl.com/api?t=caps&apikey=yourapikey
        """
        error = ''

        if not name:
            error += '\nNo Provider Name specified'
        if not url:
            error += '\nNo Provider Url specified'
        if not api_key:
            error += '\nNo Provider Api key specified'

        if error != '':
            return json.dumps({'success': False, 'message': error})

        if kind == 'newznab':
            temp_provider = NewznabProvider(name, url, api_key)
        elif kind == 'torznab':
            temp_provider = TorznabProvider(name, url, api_key)

        capabilities = temp_provider.get_capabilities()

        return json.dumps(capabilities._asdict())

    @staticmethod
    def saveNewznabProvider(name, url, api_key=''):
        """Save a Newznab Provider."""
        if not name or not url:
            return '0'

        provider_dict = dict(list(zip([x.name for x in app.newznabProviderList], app.newznabProviderList)))

        if name in provider_dict:
            if not provider_dict[name].default:
                provider_dict[name].name = name
                provider_dict[name].url = config.clean_url(url)

            provider_dict[name].api_key = api_key
            # a 0 in the api key spot indicates that no api key is needed
            if api_key == '0':
                provider_dict[name].needs_auth = False
            else:
                provider_dict[name].needs_auth = True

            return '|'.join([provider_dict[name].get_id(), provider_dict[name].config_string()])

        else:
            new_provider = NewznabProvider(name, url, api_key=api_key)
            app.newznabProviderList.append(new_provider)
            return '|'.join([new_provider.get_id(), new_provider.config_string()])

    @staticmethod
    def deleteNewznabProvider(nnid):
        """Delete a Newznab Provider."""
        provider_dict = dict(list(zip([x.get_id() for x in app.newznabProviderList], app.newznabProviderList)))

        if nnid not in provider_dict or provider_dict[nnid].default:
            return '0'

        # delete it from the list
        app.newznabProviderList.remove(provider_dict[nnid])

        if nnid in app.PROVIDER_ORDER:
            app.PROVIDER_ORDER.remove(nnid)

        return '1'

    @staticmethod
    def saveTorrentRssProvider(name, url, cookies, title_tag):
        """Save a Torrent Provider."""
        if not name or not url:
            return '0'

        provider_dict = dict(list(zip([x.name for x in app.torrentRssProviderList], app.torrentRssProviderList)))

        if name in provider_dict:
            provider_dict[name].name = name
            provider_dict[name].url = config.clean_url(url)
            provider_dict[name].cookies = cookies
            provider_dict[name].title_tag = title_tag

            return '|'.join([provider_dict[name].get_id(), provider_dict[name].config_string()])

        else:
            new_provider = TorrentRssProvider(name, url, cookies, title_tag)
            app.torrentRssProviderList.append(new_provider)
            return '|'.join([new_provider.get_id(), new_provider.config_string()])

    @staticmethod
    def deleteTorrentRssProvider(provider_id):
        """Delete a Torrent Provider."""
        provider_dict = dict(
            list(zip([x.get_id() for x in app.torrentRssProviderList], app.torrentRssProviderList)))

        if provider_id not in provider_dict:
            return '0'

        # delete it from the list
        app.torrentRssProviderList.remove(provider_dict[provider_id])

        if provider_id in app.PROVIDER_ORDER:
            app.PROVIDER_ORDER.remove(provider_id)

        return '1'

    @staticmethod
    def _save_newznab_providers(providers_settings):
        providers = []
        settings = providers_settings.split('!!!')
        providers_dict = dict(
            list(zip([x.get_id() for x in app.newznabProviderList], app.newznabProviderList)))

        for provider_settings in settings:
            if not provider_settings:
                continue

            name, url, api_key, categories = provider_settings.split('|')
            url = config.clean_url(url)
            categories = split_and_strip(categories)

            new_provider = NewznabProvider(name, url=url, api_key=api_key, cat_ids=categories)
            provider_id = new_provider.get_id()

            # if it already exists then update it
            if provider_id in providers_dict:
                providers_dict[provider_id].name = name
                providers_dict[provider_id].url = url
                providers_dict[provider_id].api_key = api_key
                providers_dict[provider_id].cat_ids = categories
                # a 0 in the key spot indicates that no key is needed
                if api_key == '0':
                    providers_dict[provider_id].needs_auth = False
                else:
                    providers_dict[provider_id].needs_auth = True
            else:
                app.newznabProviderList.append(new_provider)

            providers.append(provider_id)

        # delete anything that is missing
        for provider in app.newznabProviderList:
            if provider.get_id() not in providers:
                app.newznabProviderList.remove(provider)

        # Update the custom newznab provider list
        NewznabProvider.save_newznab_providers()

    @staticmethod
    def _save_rsstorrent_providers(providers_settings):
        providers = []
        settings = providers_settings.split('!!!')
        providers_dict = dict(
            list(zip([x.get_id() for x in app.torrentRssProviderList], app.torrentRssProviderList)))

        for provider_settings in settings:
            if not provider_settings:
                continue

            name, url, cookies, title_tag = provider_settings.split('|')
            url = config.clean_url(url)

            new_provider = TorrentRssProvider(name, url=url, cookies=cookies, title_tag=title_tag)
            provider_id = new_provider.get_id()

            # if it already exists then update it
            if provider_id in providers_dict:
                providers_dict[provider_id].name = name
                providers_dict[provider_id].url = url
                providers_dict[provider_id].cookies = cookies
                providers_dict[provider_id].title_tag = title_tag
            else:
                app.torrentRssProviderList.append(new_provider)

            providers.append(provider_id)

        # delete anything that is missing
        for provider in app.torrentRssProviderList:
            if provider.get_id() not in providers:
                app.torrentRssProviderList.remove(provider)

        # Update the torrentrss provider list
        app.TORRENTRSS_PROVIDERS = [provider.name for provider in app.torrentRssProviderList]

    @staticmethod
    def _save_torznab_providers(providers_settings):
        providers = []
        settings = providers_settings.split('!!!')
        providers_dict = dict(
            list(zip([x.get_id() for x in app.torznab_providers_list], app.torznab_providers_list)))

        for provider_settings in settings:
            if not provider_settings:
                continue

            name, url, api_key, categories, caps = provider_settings.split('|')
            url = config.clean_url(url)
            categories = split_and_strip(categories)
            caps = split_and_strip(caps)

            new_provider = TorznabProvider(name, url=url, api_key=api_key, cat_ids=categories,
                                           cap_tv_search=caps)
            provider_id = new_provider.get_id()

            # if it already exists then update it
            if provider_id in providers_dict:
                providers_dict[provider_id].name = name
                providers_dict[provider_id].url = url
                providers_dict[provider_id].api_key = api_key
                providers_dict[provider_id].cat_ids = categories
                providers_dict[provider_id].cap_tv_search = caps
            else:
                app.torznab_providers_list.append(new_provider)

            providers.append(provider_id)

        # delete anything that is missing
        for provider in app.torznab_providers_list:
            if provider.get_id() not in providers:
                app.torznab_providers_list.remove(provider)

        app.TORZNAB_PROVIDERS = [provider.name for provider in app.torznab_providers_list]

    @staticmethod
    def _set_common_settings(provider, **kwargs):

        if hasattr(provider, 'username'):
            try:
                provider.username = str(kwargs['{id}_username'.format(id=provider.get_id())]).strip()
            except (AttributeError, KeyError):
                provider.username = None  # these exceptions are actually catching unselected checkboxes

        if hasattr(provider, 'api_key'):
            try:
                provider.api_key = str(kwargs['{id}_api_key'.format(id=provider.get_id())]).strip()
            except (AttributeError, KeyError):
                pass

        if hasattr(provider, 'search_mode'):
            try:
                provider.search_mode = str(kwargs['{id}_search_mode'.format(id=provider.get_id())]).strip()
            except (AttributeError, KeyError):
                provider.search_mode = 'eponly'  # these exceptions are actually catching unselected checkboxes

        if hasattr(provider, 'search_fallback'):
            try:
                provider.search_fallback = config.checkbox_to_value(
                    kwargs['{id}_search_fallback'.format(id=provider.get_id())])
            except (AttributeError, KeyError):
                provider.search_fallback = 0  # these exceptions are actually catching unselected checkboxes

        if hasattr(provider, 'enable_daily'):
            try:
                provider.enable_daily = config.checkbox_to_value(
                    kwargs['{id}_enable_daily'.format(id=provider.get_id())])
            except (AttributeError, KeyError):
                provider.enable_daily = 0  # these exceptions are actually catching unselected checkboxes

        if hasattr(provider, 'enable_backlog'):
            try:
                provider.enable_backlog = config.checkbox_to_value(
                    kwargs['{id}_enable_backlog'.format(id=provider.get_id())])
            except (AttributeError, KeyError):
                provider.enable_backlog = 0  # these exceptions are actually catching unselected checkboxes

        if hasattr(provider, 'enable_manualsearch'):
            try:
                provider.enable_manualsearch = config.checkbox_to_value(
                    kwargs['{id}_enable_manualsearch'.format(id=provider.get_id())])
            except (AttributeError, KeyError):
                provider.enable_manualsearch = 0  # these exceptions are actually catching unselected checkboxes

        if hasattr(provider, 'enable_search_delay'):
                try:
                    provider.enable_search_delay = config.checkbox_to_value(
                        kwargs['{id}_enable_search_delay'.format(id=provider.get_id())])
                except (AttributeError, KeyError):
                    provider.enable_search_delay = 0  # these exceptions are actually catching unselected checkboxes

        if hasattr(provider, 'search_delay'):
            try:
                search_delay = float(str(kwargs['{id}_search_delay'.format(id=provider.get_id())]).strip())
                provider.search_delay = (int(search_delay * 60), 30)[search_delay < 0.5]
            except (AttributeError, KeyError, ValueError):
                provider.search_delay = 480  # these exceptions are actually catching unselected checkboxes

    @staticmethod
    def _set_torrent_settings(provider, **kwargs):

        if hasattr(provider, 'custom_url'):
            try:
                provider.custom_url = str(kwargs['{id}_custom_url'.format(id=provider.get_id())]).strip()
            except (AttributeError, KeyError):
                provider.custom_url = None  # these exceptions are actually catching unselected checkboxes

        if hasattr(provider, 'minseed'):
            try:
                provider.minseed = int(str(kwargs['{id}_minseed'.format(id=provider.get_id())]).strip())
            except (AttributeError, KeyError, ValueError):
                provider.minseed = 1  # these exceptions are actually catching unselected checkboxes

        if hasattr(provider, 'minleech'):
            try:
                provider.minleech = int(str(kwargs['{id}_minleech'.format(id=provider.get_id())]).strip())
            except (AttributeError, KeyError, ValueError):
                provider.minleech = 0  # these exceptions are actually catching unselected checkboxes

        if hasattr(provider, 'ratio'):
            try:
                ratio = float(str(kwargs['{id}_ratio'.format(id=provider.get_id())]).strip())
                provider.ratio = (ratio, -1)[ratio < 0]
            except (AttributeError, KeyError, ValueError):
                provider.ratio = ''  # these exceptions are actually catching unselected checkboxes

        if hasattr(provider, 'digest'):
            try:
                provider.digest = str(kwargs['{id}_digest'.format(id=provider.get_id())]).strip()
            except (AttributeError, KeyError):
                provider.digest = None  # these exceptions are actually catching unselected checkboxes

        if hasattr(provider, 'hash'):
            try:
                provider.hash = str(kwargs['{id}_hash'.format(id=provider.get_id())]).strip()
            except (AttributeError, KeyError):
                provider.hash = None  # these exceptions are actually catching unselected checkboxes

        if hasattr(provider, 'password'):
            try:
                provider.password = str(kwargs['{id}_password'.format(id=provider.get_id())]).strip()
            except (AttributeError, KeyError):
                provider.password = None  # these exceptions are actually catching unselected checkboxes

        if hasattr(provider, 'passkey'):
            try:
                provider.passkey = str(kwargs['{id}_passkey'.format(id=provider.get_id())]).strip()
            except (AttributeError, KeyError):
                provider.passkey = None  # these exceptions are actually catching unselected checkboxes

        if hasattr(provider, 'pin'):
            try:
                provider.pin = str(kwargs['{id}_pin'.format(id=provider.get_id())]).strip()
            except (AttributeError, KeyError):
                provider.pin = None  # these exceptions are actually catching unselected checkboxes

        if hasattr(provider, 'confirmed'):
            try:
                provider.confirmed = config.checkbox_to_value(
                    kwargs['{id}_confirmed'.format(id=provider.get_id())])
            except (AttributeError, KeyError):
                provider.confirmed = 0  # these exceptions are actually catching unselected checkboxes

        if hasattr(provider, 'ranked'):
            try:
                provider.ranked = config.checkbox_to_value(
                    kwargs['{id}_ranked'.format(id=provider.get_id())])
            except (AttributeError, KeyError):
                provider.ranked = 0  # these exceptions are actually catching unselected checkboxes

        if hasattr(provider, 'engrelease'):
            try:
                provider.engrelease = config.checkbox_to_value(
                    kwargs['{id}_engrelease'.format(id=provider.get_id())])
            except (AttributeError, KeyError):
                provider.engrelease = 0  # these exceptions are actually catching unselected checkboxes

        if hasattr(provider, 'onlyspasearch'):
            try:
                provider.onlyspasearch = config.checkbox_to_value(
                    kwargs['{id}_onlyspasearch'.format(id=provider.get_id())])
            except (AttributeError, KeyError):
                provider.onlyspasearch = 0  # these exceptions are actually catching unselected checkboxes

        if hasattr(provider, 'sorting'):
            try:
                provider.sorting = str(kwargs['{id}_sorting'.format(id=provider.get_id())]).strip()
            except (AttributeError, KeyError):
                provider.sorting = 'seeders'  # these exceptions are actually catching unselected checkboxes

        if hasattr(provider, 'freeleech'):
            try:
                provider.freeleech = config.checkbox_to_value(
                    kwargs['{id}_freeleech'.format(id=provider.get_id())])
            except (AttributeError, KeyError):
                provider.freeleech = 0  # these exceptions are actually catching unselected checkboxes

        if hasattr(provider, 'cat'):
            try:
                provider.cat = int(str(kwargs['{id}_cat'.format(id=provider.get_id())]).strip())
            except (AttributeError, KeyError):
                provider.cat = 0  # these exceptions are actually catching unselected checkboxes

        if hasattr(provider, 'subtitle'):
            try:
                provider.subtitle = config.checkbox_to_value(
                    kwargs['{id}_subtitle'.format(id=provider.get_id())])
            except (AttributeError, KeyError):
                provider.subtitle = 0  # these exceptions are actually catching unselected checkboxes

        if provider.enable_cookies:
            try:
                provider.cookies = str(kwargs['{id}_cookies'.format(id=provider.get_id())]).strip()
            except (AttributeError, KeyError):
                # I don't want to configure a default value here, as it can also
                # be configured intially as a custom rss torrent provider
                pass

    def saveProviders(self, provider_order, **kwargs):
        """Save Provider related settings."""
        newznab_string = kwargs.pop('newznab_string', '')
        torrentrss_string = kwargs.pop('torrentrss_string', '')
        torznab_string = kwargs.pop('torznab_string', '')

        self._save_newznab_providers(newznab_string)
        self._save_rsstorrent_providers(torrentrss_string)
        self._save_torznab_providers(torznab_string)

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
        provider_order_list = provider_order.split()
        for provider_setting in provider_order_list:
            cur_provider, cur_setting = provider_setting.split(':')
            enabled = try_int(cur_setting)
            ordered_names[cur_provider] = enabled

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

            self._set_common_settings(provider, **kwargs)
            if isinstance(provider, TorrentProvider):
                self._set_torrent_settings(provider, **kwargs)

        app.PROVIDER_ORDER = providers_enabled + providers_disabled

        app.instance.save_config()

        ui.notifications.message('Configuration Saved', os.path.join(app.CONFIG_FILE))

        return self.redirect('/config/providers/')
