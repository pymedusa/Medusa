# coding=utf-8

"""Provider code for Newznab provider."""

from __future__ import unicode_literals

import logging
import os
import re
from builtins import range
from builtins import zip
from collections import namedtuple

from medusa import (
    app,
    tv,
)
from medusa.bs4_parser import BS4Parser
from medusa.helper.common import (
    convert_size,
    try_int,
)
from medusa.helpers.utils import split_and_strip
from medusa.indexers.config import (
    INDEXER_TMDB,
    INDEXER_TVDBV2,
    INDEXER_TVMAZE,
)
from medusa.indexers.utils import mappings
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.nzb.nzb_provider import NZBProvider

from requests.compat import urljoin

from six import iteritems, itervalues, text_type as str


log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())

INDEXERS_PARAM = {INDEXER_TVDBV2: 'tvdbid', INDEXER_TVMAZE: 'tvmazeid', INDEXER_TMDB: 'tmdbid'}


class NewznabProvider(NZBProvider):
    """
    Generic provider for built in and custom providers who expose a newznab compatible api.

    Tested with: newznab, nzedb, spotweb
    """

    def __init__(self, name, url='', api_key='0', cat_ids=None, default=False, search_mode='eponly',
                 search_fallback=False, enable_daily=True, enable_backlog=False, enable_manualsearch=False):
        """Initialize the class."""
        super(NewznabProvider, self).__init__(name)

        self.url = url
        self.api_key = api_key

        self.default = default

        self.search_mode = search_mode
        self.search_fallback = search_fallback
        self.enable_daily = enable_daily
        self.enable_manualsearch = enable_manualsearch
        self.enable_backlog = enable_backlog

        # 0 in the key spot indicates that no key is needed
        self.needs_auth = self.api_key != '0'
        self.public = not self.needs_auth

        self.cat_ids = cat_ids or ['5030', '5040']

        self.params = False
        self.cap_tv_search = []
        self.providers_without_caps = ['gingadaddy', '6box']

        # For now apply the additional season search string for all newznab providers.
        # If we want to limited this per provider, I suggest using a dict, with provider: [list of season templates]
        # construction.
        self.season_templates = (
            'S{season:0>2}',  # example: 'Series.Name S03'
            'Season {season}',  # example: 'Series.Name Season 3'
        )

        self.cache = tv.Cache(self)

    def search(self, search_strings, age=0, ep_obj=None, force_query=False, manual_search=False, **kwargs):
        """
        Search a provider and parse the results.

        :param search_strings: A dict with mode (key) and the search value (value)
        :param age: Not used
        :param ep_obj: Not used
        :param force_query: Newznab will by default search using the tvdb/tmdb/imdb id for a show. As a backup it
        can also search using a query string, like the showtitle with the season/episode number. The force_query
        parameter can be passed to force a search using the query string.
        :param manual_search: If the search is started through a manual search, we're utilizing the force_query param.
        :returns: A list of search results (structure)
        """
        results = []
        if not self._check_auth():
            return results

        # For providers that don't have caps, or for which the t=caps is not working.
        if not self.params and all(provider not in self.url for provider in self.providers_without_caps):
            self.get_capabilities(just_params=True)

        # Search Params
        search_params = {
            't': 'search',
            'limit': 100,
            'offset': 0,
            'cat': ','.join(self.cat_ids),
            'maxage': app.USENET_RETENTION
        }

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            if self.needs_auth and self.api_key:
                search_params['apikey'] = self.api_key

            if mode != 'RSS':

                match_indexer = self._match_indexer()
                if match_indexer and not force_query:
                    search_params['t'] = 'tvsearch'
                    search_params.update(match_indexer)

                    if ep_obj.series.air_by_date or ep_obj.series.sports:
                        date_str = str(ep_obj.airdate)
                        search_params['season'] = date_str.partition('-')[0]
                        search_params['ep'] = date_str.partition('-')[2].replace('-', '/')
                    else:
                        search_params['season'] = ep_obj.scene_season
                        search_params['ep'] = ep_obj.scene_episode
                else:
                    search_params['t'] = 'search'

            if mode == 'Season':
                search_params.pop('ep', '')

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    # If its a PROPER search, need to change param to 'search'
                    # so it searches using 'q' param
                    if any(proper_string in search_string
                           for proper_string in self.proper_strings):
                        search_params['t'] = 'search'

                    log.debug(
                        'Search show using {search}', {
                            'search': 'search string: {search_string}'.format(
                                search_string=search_string if search_params['t'] != 'tvsearch' else
                                'indexer_id: {indexer_id}'.format(indexer_id=match_indexer)
                            )
                        }
                    )

                    if search_params['t'] != 'tvsearch':
                        search_params['q'] = search_string

                response = self.session.get(urljoin(self.url, 'api'), params=search_params)
                if not response or not response.text:
                    log.debug('No data returned from provider')
                    continue

                results += self.parse(response.text, mode)

                # Since we aren't using the search string,
                # break out of the search string loop
                if any(param in search_params for param in itervalues(INDEXERS_PARAM)):
                    break

        # Reprocess but now use force_query = True if there are no results
        # (backlog, daily, force) or if it's a manual search.
        if (not results or manual_search) and not force_query:
            return self.search(search_strings, ep_obj=ep_obj, force_query=True)

        return results

    def parse(self, data, mode):
        """
        Parse search results for items.

        :param data: The raw response from a search
        :param mode: The current mode used to search, e.g. RSS

        :return: A list of items found
        """
        items = []

        with BS4Parser(data, 'html5lib') as html:

            rows = html('item')
            if not rows:
                log.debug(
                    'No results returned from provider. Check chosen Newznab search categories'
                    ' in provider settings and/or usenet retention')
                return items

            for item in rows:
                try:
                    title = item.title.get_text(strip=True)
                    download_url = None

                    if item.enclosure:
                        url = item.enclosure.get('url', '').strip()
                        if url:
                            download_url = url

                    if not download_url and item.link:
                        url = item.link.get_text(strip=True)
                        if url:
                            download_url = url

                        if not download_url:
                            url = item.link.next.strip()
                            if url:
                                download_url = url

                    if not (title and download_url):
                        continue

                    if 'gingadaddy' in self.url:
                        size_regex = re.search(r'\d*.?\d* [KMGT]B', str(item.description))
                        item_size = size_regex.group() if size_regex else -1
                    else:
                        item_size = item.size.get_text(strip=True) if item.size else -1
                        # Use regex to find name-spaced tags
                        # see BeautifulSoup4 bug 1720605
                        # https://bugs.launchpad.net/beautifulsoup/+bug/1720605
                        newznab_attrs = item(re.compile('newznab:attr'))
                        for attr in newznab_attrs:
                            item_size = attr['value'] if attr['name'] == 'size' else item_size

                    size = convert_size(item_size) or -1

                    pubdate_raw = item.pubdate.get_text(strip=True)
                    pubdate = self.parse_pubdate(pubdate_raw)

                    item = {
                        'title': title,
                        'link': download_url,
                        'size': size,
                        'pubdate': pubdate,
                    }
                    if mode != 'RSS':
                        log.debug('Found result: {0}', title)

                    items.append(item)
                except (AttributeError, TypeError, KeyError, ValueError, IndexError):
                    log.exception('Failed parsing provider.')

        return items

    def _check_auth(self):
        """
        Check that user has set their api key if it is needed.

        :return: True/False
        """
        if self.needs_auth and not self.api_key:
            log.warning('Invalid api key. Check your settings')
            return False

        return True

    def _get_size(self, item):
        """
        Get size info from a result item.

        Returns int size or -1
        """
        return try_int(item.get('size', -1), -1)

    def config_string(self):
        """Generate a '|' delimited string of instance attributes, for saving to config.ini."""
        return '|'.join([
            self.name, self.url, self.api_key, self.cat_ids, str(int(self.enabled)),
            self.search_mode, str(int(self.search_fallback)),
            str(int(self.enable_daily)), str(int(self.enable_backlog)), str(int(self.enable_manualsearch))
        ])

    @staticmethod
    def get_newznab_providers(providers):
        """Return a list of available newznab providers, including the default newznab providers."""
        default_list = [
            NewznabProvider._create_default_provider(default_provider)
            for default_provider in NewznabProvider._get_default_providers()
        ]

        custom_newznab_providers = [NewznabProvider(custom_provider) for custom_provider in providers]

        return default_list + custom_newznab_providers

    @staticmethod
    def save_newznab_providers():
        """Update the app.NEWZNAB_PROVIDERS list with provider names."""
        app.NEWZNAB_PROVIDERS = [provider.name for provider in app.newznabProviderList if not provider.default]

    @staticmethod
    def get_providers_list(provider_data):
        """
        Return list of nzb providers.

        Deprecated and only used to migrate configs prior to v10.
        """
        default_list = [
            NewznabProvider._create_default_provider(default_provider)
            for default_provider in NewznabProvider._get_default_providers()
        ]

        providers_list = [
            provider for provider in
            (NewznabProvider._make_provider(x) for x in provider_data.split('!!!'))
            if provider
        ]

        seen_values = set()
        providers_set = []

        for provider in providers_list:
            value = provider.name

            if value not in seen_values:
                providers_set.append(provider)
                seen_values.add(value)

        providers_list = providers_set
        providers_dict = dict(list(zip([provider.name for provider in providers_list], providers_list)))

        for default in default_list:
            if not default:
                continue

            if default.name not in providers_dict:
                default.default = True
                providers_list.append(default)
            else:
                providers_dict[default.name].default = True
                providers_dict[default.name].url = default.url
                providers_dict[default.name].needs_auth = default.needs_auth

        return [provider for provider in providers_list if provider]

    def image_name(self):
        """
        Check if we have an image for this provider already.

        Returns found image or the default newznab image
        """
        if os.path.isfile(os.path.join(app.THEME_DATA_ROOT, 'assets/img/providers/', self.get_id() + '.png')):
            return self.get_id() + '.png'
        return 'newznab.png'

    def _match_indexer(self):
        """Use the indexers id and externals, and return the most optimal indexer with value.

        For newznab providers we prefer to use tvdb for searches, but if this is not available for shows that have
        been indexed using an alternative indexer, we could also try other indexers id's that are available
        and supported by this newznab provider.
        """
        indexer_mapping = {}

        if not self.series:
            return indexer_mapping

        supported_params = self.cap_tv_search
        if not supported_params:
            # We didn't get back any supportedParams, lets return
            # and continue with doing a search string search.
            return indexer_mapping

        indexer_params = ((x, v) for x, v in iteritems(INDEXERS_PARAM) if v in supported_params)
        for indexer, indexer_param in indexer_params:
            # We have a direct match on the indexer used, no need to try the externals.
            if self.series.indexer == indexer:
                indexer_mapping[indexer_param] = self.series.indexerid
                break

            # No direct match, let's see if one of the externals provides a valid indexer_param.
            external_indexerid = self.series.externals.get(mappings[indexer])
            if external_indexerid:
                indexer_mapping[indexer_param] = external_indexerid
                break

        return indexer_mapping

    @staticmethod
    def _make_provider(provider_config):
        """
        Create providers using a !!! separated string of providers.

        This is only still used for migration old configs prior to v10.
        """
        if not provider_config:
            return None

        try:
            values = provider_config.split('|')
            # Pad values with None for each missing value
            values.extend([None for _ in range(len(values), 10)])

            (name, url, api_key, category_ids, enabled,
             search_mode, search_fallback,
             enable_daily, enable_backlog, enable_manualsearch
             ) = values

        except ValueError:
            log.error('Skipping Newznab provider string: {config!r}, incorrect format',
                      {'config': provider_config})
            return None

        new_provider = NewznabProvider(
            name, url, api_key=api_key, cat_ids=split_and_strip(category_ids),
            search_mode=search_mode or 'eponly',
            search_fallback=bool(int(search_fallback)),
            enable_daily=bool(int(enable_daily)),
            enable_backlog=bool(int(enable_backlog)),
            enable_manualsearch=bool(int(enable_manualsearch)))
        new_provider.enabled = bool(int(enabled))

        return new_provider

    def set_caps(self, data):
        """Set caps."""
        if not data:
            return

        def _parse_cap(tag):
            elm = data.find(tag)
            is_supported = elm and all([elm.get('supportedparams'), elm.get('available') == 'yes'])
            return elm['supportedparams'].split(',') if is_supported else []

        self.cap_tv_search = _parse_cap('tv-search')
        # self.cap_search = _parse_cap('search')

        self.params = any(self.cap_tv_search)

    def get_capabilities(self, just_params=False):
        """
        Use the provider url and apikey to get the capabilities.

        Makes use of the default newznab caps param. e.a. http://yourznab/api?t=caps&apikey=skdfiw7823sdkdsfjsfk
        Returns a tuple with (succes or not, array with dicts [{'id': '5070', 'name': 'Anime'},
        {'id': '5080', 'name': 'Documentary'}, {'id': '5020', 'name': 'Foreign'}...etc}], error message)
        """
        Capabilities = namedtuple('Capabilities', 'success categories params message')
        categories = params = []

        if not self._check_auth():
            message = 'Provider requires auth and your key is not set'
            return Capabilities(False, categories, params, message)

        url_params = {'t': 'caps'}
        if self.needs_auth and self.api_key:
            url_params['apikey'] = self.api_key

        response = self.session.get(urljoin(self.url, 'api'), params=url_params)
        if not response or not response.text:
            message = 'Error getting caps xml for: {0}'.format(self.name)
            log.warning(message)
            return Capabilities(False, categories, params, message)

        with BS4Parser(response.text, 'html5lib') as html:
            if not html.find('categories'):
                message = 'Error parsing caps xml for: {0}'.format(self.name)
                log.warning(message)
                return Capabilities(False, categories, params, message)

            self.set_caps(html.find('searching'))
            params = self.cap_tv_search
            if just_params:
                message = 'Success getting params for: {0}'.format(self.name)
                return Capabilities(True, categories, params, message)

            for category in html('category'):
                category_name = category.get('name', '')
                if 'TV' in category_name and category.get('id'):
                    categories.append({'id': category['id'], 'name': category['name']})
                    for subcat in category('subcat'):
                        if subcat.get('name', '') and subcat.get('id'):
                            categories.append({'id': subcat['id'], 'name': subcat['name']})

                # Some providers have the subcat `Anime` in the `Other` category
                elif category_name == 'Other' and category.get('id'):
                    for subcat in category('subcat'):
                        if subcat.get('name', '') == 'Anime' and subcat.get('id'):
                            categories.append({'id': subcat['id'], 'name': subcat['name']})
                            break

            message = 'Success getting categories and params for: {0}'.format(self.name)
            return Capabilities(True, categories, params, message)

    @staticmethod
    def _create_default_provider(config):
        """Use the providers in get_default_provider to create a new NewznabProvider."""
        return NewznabProvider(
            config['name'], config['url'], api_key=config['api_key'], cat_ids=config['category_ids'],
            default=config['default'], search_mode=config['search_mode'] or 'eponly',
            search_fallback=config['search_fallback'], enable_daily=config['enable_daily'],
            enable_backlog=config['enable_backlog'], enable_manualsearch=config['enable_manualsearch']
        )

    @staticmethod
    def _get_default_providers():
        """Return default newznab providers configuration."""
        return [
            {
                'name': 'NZB.Cat',
                'url': 'https://nzb.cat/',
                'api_key': '',
                'category_ids': ['5030', '5040', '5010'],
                'enabled': False,
                'default': True,
                'search_mode': 'eponly',
                'search_fallback': False,
                'enable_daily': False,
                'enable_backlog': False,
                'enable_manualsearch': False,
            },
            {
                'name': 'NZBGeek',
                'url': 'https://api.nzbgeek.info/',
                'api_key': '',
                'category_ids': ['5030', '5040'],
                'enabled': False,
                'default': True,
                'search_mode': 'eponly',
                'search_fallback': False,
                'enable_daily': False,
                'enable_backlog': False,
                'enable_manualsearch': False,
            },
            {
                'name': 'DOGnzb',
                'url': 'https://api.dognzb.cr/',
                'api_key': '',
                'category_ids': ['5030', '5040', '5060', '5070'],
                'enabled': False,
                'default': True,
                'search_mode': 'eponly',
                'search_fallback': False,
                'enable_daily': False,
                'enable_backlog': False,
                'enable_manualsearch': False,
            },
            {
                'name': 'Omgwtfnzbs',
                'url': 'https://api.omgwtfnzbs.me/',
                'api_key': '',
                'category_ids': ['5030', '5040', '5060', '5070'],
                'enabled': False,
                'default': True,
                'search_mode': 'eponly',
                'search_fallback': False,
                'enable_daily': False,
                'enable_backlog': False,
                'enable_manualsearch': False,
            }
        ]
