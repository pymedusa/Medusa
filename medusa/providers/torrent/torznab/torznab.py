# coding=utf-8

"""Provider code for Torznab provider."""

from __future__ import unicode_literals

import logging
import os

from medusa import (
    app,
    tv,
)
from medusa.bs4_parser import BS4Parser
from medusa.helper.common import convert_size
from medusa.helper.encoding import ss
from medusa.indexers.indexer_config import (
    INDEXER_TMDB,
    INDEXER_TVDBV2,
    INDEXER_TVMAZE,
    mappings,
)
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.compat import urljoin


log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class TorznabProvider(TorrentProvider):
    """Generic provider for built in and custom providers who expose a Torznab compatible api."""

    def __init__(self, name, url=None, api_key=None, cat_ids=None, cap_tv_search=None):
        """Initialize the class."""
        super(TorznabProvider, self).__init__(name)

        self.url = url or ''
        self.api_key = api_key or ''
        self.cat_ids = cat_ids or ['5010', '5030', '5040']
        self.cap_tv_search = cap_tv_search or []

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # For now apply the additional season search string for all newznab providers.
        # If we want to limited this per provider, I suggest using a dict, with provider: [list of season templates]
        # construction.
        self.season_templates = (
            'S{season:0>2}',  # example: 'Series.Name S03'
            'Season {season}',  # example: 'Series.Name Season 3'
        )

        self.cache = tv.Cache(self, min_time=20)

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

        # Search Params
        search_params = {
            't': 'search',
            'limit': 100,
            'offset': 0,
            'cat': ','.join(self.cat_ids),
        }

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            search_params['apikey'] = self.api_key

            if mode != 'RSS':
                match_indexer = self._match_indexer()
                log.warning('Invalid: {0}'.format(match_indexer))

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
                if 'tvdbid' in search_params:
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
            if not self._check_auth_from_data(html):
                return items

            rows = html('item')
            if not rows:
                log.debug(
                    'No results returned from provider. Check chosen Torznab search categories '
                    'in provider settings.')
                return items

            for item in rows:
                try:
                    title = item.title.get_text(strip=True)
                    download_url = item.enclosure.get('url', '').strip()
                    if not (title and download_url):
                        continue

                    seeders_attr = item.find('torznab:attr', attrs={'name': 'seeders'})
                    peers_attr = item.find('torznab:attr', attrs={'name': 'peers'})
                    seeders = int(seeders_attr.get('value', 0))
                    leechers = int(peers_attr.get('value', 0))

                    torrent_size = item.size.get_text(strip=True)
                    size = convert_size(torrent_size, default=-1)

                    pubdate_raw = item.pubdate.get_text(strip=True)
                    pubdate = self.parse_pubdate(pubdate_raw)

                    item = {
                        'title': title,
                        'link': download_url,
                        'size': size,
                        'seeders': seeders,
                        'leechers': leechers,
                        'pubdate': pubdate,
                    }
                    if mode != 'RSS':
                        log.debug('Found result: {0} with {1} seeders and {2} leechers',
                                  title, seeders, leechers)

                    items.append(item)
                except (AttributeError, TypeError, KeyError, ValueError, IndexError):
                    log.exception('Failed parsing provider.')

        return items

    def _check_auth(self):
        """
        Check that user has set their api key if it is needed.

        :return: True/False
        """
        if not self.api_key:
            log.warning('Invalid api key. Check your settings')
            return False

        return True

    def _check_auth_from_data(self, data):
        """
        Check that the returned data is valid.

        :return: _check_auth if valid otherwise False if there is an error
        """
        if data('categories') + data('item'):
            return self._check_auth()

        try:
            err_desc = data.error.attrs['description']
            if not err_desc:
                raise Exception
        except (AttributeError, TypeError):
            return self._check_auth()

        log.info(ss(err_desc))

        return False

    @staticmethod
    def get_providers_list(providers):
        """Return custom rss torrent providers."""
        return [TorznabProvider(custom_provider) for custom_provider in providers]

    def image_name(self):
        """
        Check if we have an image for this provider already.

        Returns found image or the default Torznab image
        """
        if os.path.isfile(os.path.join(app.PROG_DIR, 'static/images/providers/', self.get_id() + '.png')):
            return self.get_id() + '.png'
        return 'jackett.png'

    def _match_indexer(self):
        """Use the indexers id and externals, and return the most optimal indexer with value.

        For newznab providers we prefer to use tvdb for searches, but if this is not available for shows that have
        been indexed using an alternative indexer, we could also try other indexers id's that are available
        and supported by this newznab provider.
        """
        # The following mapping should map the newznab capabilities to our indexers or externals in indexer_config.
        map_caps = {INDEXER_TMDB: 'tmdbid', INDEXER_TVDBV2: 'tvdbid', INDEXER_TVMAZE: 'tvmazeid'}

        return_mapping = {}

        if not self.series:
            # If we don't have show, can't get tvdbid
            return return_mapping

        if not self.cap_tv_search:
            # We didn't get back a supportedParams, lets return, and continue with doing a search string search.
            return return_mapping

        for search_type in self.cap_tv_search:
            if search_type == 'tvdbid' and self._get_tvdb_id():
                return_mapping['tvdbid'] = self._get_tvdb_id()
                # If we got a tvdb we're satisfied, we don't need to look for other capabilities.
                if return_mapping['tvdbid']:
                    return return_mapping
            else:
                # Move to the configured capability / indexer mappings. To see if we can get a match.
                for map_indexer in map_caps:
                    if map_caps[map_indexer] == search_type:
                        if self.series.indexer == map_indexer:
                            # We have a direct match on the indexer used, no need to try the externals.
                            return_mapping[map_caps[map_indexer]] = self.series.indexerid
                            return return_mapping
                        elif self.series.externals.get(mappings[map_indexer]):
                            # No direct match, let's see if one of the externals provides a valid search_type.
                            mapped_external_indexer = self.series.externals.get(mappings[map_indexer])
                            if mapped_external_indexer:
                                return_mapping[map_caps[map_indexer]] = mapped_external_indexer

        return return_mapping

    def set_caps(self, data):
        """Set caps."""
        if not data:
            return

        def _parse_cap(tag):
            elm = data.find(tag)
            return elm.get('supportedparams').split(',') if elm and elm.get('available') == 'yes' else []

        self.cap_tv_search = _parse_cap('tv-search')

    def get_categories(self, just_caps=False):
        """
        Use the provider url and apikey to get the capabilities.

        Makes use of the default newznab caps param. e.a. http://yournewznab/api?t=caps&apikey=skdfiw7823sdkdsfjsfk
        Returns a tuple with (succes or not, array with dicts [{'id': '5070', 'name': 'Anime'},
        {'id': '5080', 'name': 'Documentary'}, {'id': '5020', 'name': 'Foreign'}...etc}], error message)
        """
        categories = []

        if not self._check_auth():
            return False, categories, '', 'Provider requires auth and your key is not set'

        url_params = {'t': 'caps'}
        if self.needs_auth and self.api_key:
            url_params['apikey'] = self.api_key

        response = self.session.get(urljoin(self.url, 'api'), params=url_params)
        if not response or not response.text:
            error_string = 'Error getting caps xml for [{0}]'.format(self.name)
            log.warning(error_string)
            return False, categories, '', error_string

        with BS4Parser(response.text, 'html5lib') as html:
            if not html.find('categories'):
                error_string = 'Error parsing caps xml for [{0}]'.format(self.name)
                log.warning(error_string)
                return False, categories, '', error_string

            self.set_caps(html.find('searching'))
            if just_caps:
                return True, categories, self.cap_tv_search, ''

            for category in html('category'):
                if 'TV' in category.get('name', '') and category.get('id', ''):
                    categories.append({'id': category['id'], 'name': category['name']})
                    for subcat in category('subcat'):
                        if subcat.get('name', '') and subcat.get('id', ''):
                            categories.append({'id': subcat['id'], 'name': subcat['name']})

            return True, categories, self.cap_tv_search, ''

    def _make_url(self, result):
        """Return url if result is a magnet link."""
        if not result:
            return '', ''

        urls = []
        filename = ''

        if result.url.startswith('magnet:'):
            try:
                info_hash = re.findall(r'urn:btih:([\w]{32,40})', result.url)[0].upper()

                try:
                    torrent_name = re.findall('dn=([^&]+)', result.url)[0]
                except Exception:
                    torrent_name = 'NO_DOWNLOAD_NAME'

                if len(info_hash) == 32:
                    info_hash = b16encode(b32decode(info_hash)).upper()

                if not info_hash:
                    log.error('Unable to extract torrent hash from magnet: {0}', result.url)
                    return urls, filename

                urls = [x.format(info_hash=info_hash, torrent_name=torrent_name) for x in self.bt_cache_urls]
                shuffle(urls)
            except Exception:
                log.error('Unable to extract torrent hash or name from magnet: {0}', result.url)
                return urls, filename
        else:
            urls = [result.url]

        result_name = sanitize_filename(result.name)

        # Some NZB providers (e.g. Jackett) can also download torrents
        if (result.url.endswith(GenericProvider.TORRENT) or
                result.url.startswith('magnet:')) and self.provider_type == GenericProvider.NZB:
            filename = join(app.TORRENT_DIR, result_name + '.torrent')
        else:
            filename = join(self._get_storage_dir(), result_name + '.' + self.provider_type)

        return urls, filename
