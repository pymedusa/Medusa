# coding=utf-8
# Author: Nic Wolfe <nic@wolfeden.ca>
# Rewrite: Dustyn Gibson (miigotu) <miigotu@gmail.com>
#
# This file is part of Medusa.
#
# Medusa is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Medusa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Medusa. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import os
import re
import time
import traceback

import medusa as app
from requests.compat import urljoin
import validators
from .NZBProvider import NZBProvider
from ... import logger, tvcache
from ...bs4_parser import BS4Parser
from ...common import cpu_presets
from ...helper.common import convert_size, try_int
from ...helper.encoding import ss


class NewznabProvider(NZBProvider):  # pylint: disable=too-many-instance-attributes, too-many-arguments
    """
    Generic provider for built in and custom providers who expose a newznab
    compatible api.
    Tested with: newznab, nzedb, spotweb, torznab
    """
    # pylint: disable=too-many-arguments

    def __init__(self, name, url, key='0', catIDs='5030,5040', search_mode='eponly',
                 search_fallback=False, enable_daily=True, enable_backlog=False, enable_manualsearch=False):

        NZBProvider.__init__(self, name)

        self.url = url
        self.key = key

        self.search_mode = search_mode
        self.search_fallback = search_fallback
        self.enable_daily = enable_daily
        self.enable_manualsearch = enable_manualsearch
        self.enable_backlog = enable_backlog

        # 0 in the key spot indicates that no key is needed
        self.needs_auth = self.key != '0'
        self.public = not self.needs_auth

        self.catIDs = catIDs if catIDs else '5030,5040'

        self.default = False

        self.caps = False
        self.cap_tv_search = None
        self.force_query = False
        self.providers_without_caps = ['gingadaddy', '6box']
        # self.cap_search = None
        # self.cap_movie_search = None
        # self.cap_audio_search = None

        self.cache = tvcache.TVCache(self, min_time=30)  # only poll newznab providers every 30 minutes max

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-arguments, too-many-locals, too-many-branches, too-many-statements
        """
        Searches indexer using the params in search_strings, either for latest releases, or a string/id search
        Returns: list of results in dict form
        """
        results = []
        if not self._check_auth():
            return results

        # For providers that don't have caps, or for which the t=caps is not working.
        if not self.caps and all(provider not in self.url for provider in self.providers_without_caps):
            self.get_newznab_categories(just_caps=True)
            if not self.caps:
                return results

        for mode in search_strings:
            self.torznab = False
            search_params = {
                't': 'tvsearch' if 'tvdbid' in str(self.cap_tv_search) and not self.force_query else 'search',
                'limit': 100,
                'offset': 0,
                'cat': self.catIDs.strip(', ') or '5030,5040',
                'maxage': app.USENET_RETENTION
            }

            if self.needs_auth and self.key:
                search_params['apikey'] = self.key

            if mode != 'RSS':
                if search_params['t'] == 'tvsearch':
                    search_params['tvdbid'] = ep_obj.show.indexerid

                    if ep_obj.show.air_by_date or ep_obj.show.sports:
                        date_str = str(ep_obj.airdate)
                        search_params['season'] = date_str.partition('-')[0]
                        search_params['ep'] = date_str.partition('-')[2].replace('-', '/')
                    else:
                        search_params['season'] = ep_obj.scene_season
                        search_params['ep'] = ep_obj.scene_episode

                if mode == 'Season':
                    search_params.pop('ep', '')

            items = []
            logger.log('Search mode: {0}'.format(mode), logger.DEBUG)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    logger.log('Search string: {search}'.format
                               (search=search_string), logger.DEBUG)

                    # If its a PROPER search, need to change param to 'search' so it searches using 'q' param
                    if any(proper_string in search_string for proper_string in self.proper_strings):
                        search_params['t'] = 'search'

                    if search_params['t'] != 'tvsearch':
                        search_params['q'] = search_string

                time.sleep(cpu_presets[app.CPU_PRESET])

                response = self.get_url(urljoin(self.url, 'api'), params=search_params, returns='response')
                if not response or not response.text:
                    logger.log('No data returned from provider', logger.DEBUG)
                    continue

                with BS4Parser(response.text, 'html5lib') as html:
                    if not self._check_auth_from_data(html):
                        return items

                    try:
                        self.torznab = 'xmlns:torznab' in html.rss.attrs
                    except AttributeError:
                        self.torznab = False

                    for item in html('item'):
                        try:
                            title = item.title.get_text(strip=True)
                            download_url = None
                            if item.link:
                                if validators.url(item.link.get_text(strip=True)):
                                    download_url = item.link.get_text(strip=True)
                                elif validators.url(item.link.next.strip()):
                                    download_url = item.link.next.strip()

                            if not download_url and item.enclosure:
                                if validators.url(item.enclosure.get('url', '').strip()):
                                    download_url = item.enclosure.get('url', '').strip()

                            if not (title and download_url):
                                continue

                            seeders = leechers = -1
                            if 'gingadaddy' in self.url:
                                size_regex = re.search(r'\d*.?\d* [KMGT]B', str(item.description))
                                item_size = size_regex.group() if size_regex else -1
                            else:
                                item_size = item.size.get_text(strip=True) if item.size else -1
                                for attr in item('newznab:attr') + item('torznab:attr'):
                                    item_size = attr['value'] if attr['name'] == 'size' else item_size
                                    seeders = try_int(attr['value']) if attr['name'] == 'seeders' else seeders
                                    peers = try_int(attr['value']) if attr['name'] == 'peers' else None
                                    leechers = peers - seeders if peers else leechers

                            if not item_size or (self.torznab and (seeders is -1 or leechers is -1)):
                                continue

                            size = convert_size(item_size) or -1

                            item = {
                                'title': title,
                                'link': download_url,
                                'size': size,
                                'seeders': seeders,
                                'leechers': leechers,
                                'pubdate': None,
                                'torrent_hash': None,
                            }
                            if mode != 'RSS':
                                if seeders == -1:
                                    logger.log('Found result: {0}'.format(title), logger.DEBUG)
                                else:
                                    logger.log('Found result: {0} with {1} seeders and {2} leechers'.format
                                               (title, seeders, leechers), logger.DEBUG)

                            items.append(item)
                        except (AttributeError, TypeError, KeyError, ValueError, IndexError):
                            logger.log('Failed parsing provider. Traceback: {0!r}'.format
                                       (traceback.format_exc()), logger.ERROR)
                            continue

                # Since we arent using the search string,
                # break out of the search string loop
                if 'tvdbid' in search_params:
                    break

            results += items

        # Reproces but now use force_query = True
        if not results and not self.force_query:
            self.force_query = True
            return self.search(search_strings, ep_obj=ep_obj)

        return results

    def _check_auth(self):
        """
        Checks that user has set their api key if it is needed
        Returns: True/False
        """
        if self.needs_auth and not self.key:
            logger.log('Invalid api key. Check your settings', logger.WARNING)
            return False

        return True

    def _check_auth_from_data(self, data):
        """
        Checks that the returned data is valid
        Returns: _check_auth if valid otherwise False if there is an error
        """
        if data('categories') + data('item'):
            return self._check_auth()

        try:
            err_desc = data.error.attrs['description']
            if not err_desc:
                raise Exception
        except (AttributeError, TypeError):
            return self._check_auth()

        logger.log(ss(err_desc))

        return False

    def _get_size(self, item):
        """
        Gets size info from a result item
        Returns int size or -1
        """
        return try_int(item.get('size', -1), -1)

    def config_string(self):
        """
        Generates a '|' delimited string of instance attributes, for saving to config.ini
        """
        return '|'.join([
            self.name, self.url, self.key, self.catIDs, str(int(self.enabled)),
            self.search_mode, str(int(self.search_fallback)),
            str(int(self.enable_daily)), str(int(self.enable_backlog)), str(int(self.enable_manualsearch))
        ])

    @staticmethod
    def get_providers_list(data):
        default_list = [
            provider for provider in
            (NewznabProvider._make_provider(x) for x in NewznabProvider._get_default_providers().split('!!!'))
            if provider]

        providers_list = [
            provider for provider in
            (NewznabProvider._make_provider(x) for x in data.split('!!!'))
            if provider]

        seen_values = set()
        providers_set = []

        for provider in providers_list:
            value = provider.name

            if value not in seen_values:
                providers_set.append(provider)
                seen_values.add(value)

        providers_list = providers_set
        providers_dict = dict(zip([provider.name for provider in providers_list], providers_list))

        for default in default_list:
            if not default:
                continue

            if default.name not in providers_dict:
                default.default = True
                providers_list.append(default)
            else:
                providers_dict[default.name].default = True
                providers_dict[default.name].name = default.name
                providers_dict[default.name].url = default.url
                providers_dict[default.name].needs_auth = default.needs_auth
                providers_dict[default.name].search_mode = default.search_mode
                providers_dict[default.name].search_fallback = default.search_fallback
                providers_dict[default.name].enable_daily = default.enable_daily
                providers_dict[default.name].enable_backlog = default.enable_backlog
                providers_dict[default.name].enable_manualsearch = default.enable_manualsearch

        return [provider for provider in providers_list if provider]

    def image_name(self):
        """
        Checks if we have an image for this provider already.
        Returns found image or the default newznab image
        """
        if os.path.isfile(os.path.join(app.PROG_DIR, 'static/images/providers/', self.get_id() + '.png')):
            return self.get_id() + '.png'
        return 'newznab.png'

    @staticmethod
    def _make_provider(config):
        if not config:
            return None

        try:
            values = config.split('|')
            # Pad values with None for each missing value
            values.extend([None for x in range(len(values), 10)])

            (name, url, key, category_ids, enabled,
             search_mode, search_fallback,
             enable_daily, enable_backlog, enable_manualsearch
             ) = values

        except ValueError:
            logger.log('Skipping Newznab provider string: {config!r}, incorrect format'.format
                       (config=config), logger.ERROR)
            return None

        new_provider = NewznabProvider(
            name, url, key=key, catIDs=category_ids,
            search_mode=search_mode or 'eponly',
            search_fallback=search_fallback or 0,
            enable_daily=enable_daily or 0,
            enable_backlog=enable_backlog or 0,
            enable_manualsearch=enable_manualsearch or 0)
        new_provider.enabled = enabled == '1'

        return new_provider

    def set_caps(self, data):
        if not data:
            return

        def _parse_cap(tag):
            elm = data.find(tag)
            return elm.get('supportedparams', 'True') if elm and elm.get('available') else ''

        self.cap_tv_search = _parse_cap('tv-search')
        # self.cap_search = _parse_cap('search')
        # self.cap_movie_search = _parse_cap('movie-search')
        # self.cap_audio_search = _parse_cap('audio-search')

        # self.caps = any([self.cap_tv_search, self.cap_search, self.cap_movie_search, self.cap_audio_search])
        self.caps = any([self.cap_tv_search])

    def get_newznab_categories(self, just_caps=False):
        """
        Uses the newznab provider url and apikey to get the capabilities.
        Makes use of the default newznab caps param. e.a. http://yournewznab/api?t=caps&apikey=skdfiw7823sdkdsfjsfk
        Returns a tuple with (succes or not, array with dicts [{'id': '5070', 'name': 'Anime'},
        {'id': '5080', 'name': 'Documentary'}, {'id': '5020', 'name': 'Foreign'}...etc}], error message)
        """
        return_categories = []

        if not self._check_auth():
            return False, return_categories, 'Provider requires auth and your key is not set'

        url_params = {'t': 'caps'}
        if self.needs_auth and self.key:
            url_params['apikey'] = self.key

        response = self.get_url(urljoin(self.url, 'api'), params=url_params, returns='response')
        if not response or not response.text:
            error_string = 'Error getting caps xml for [{0}]'.format(self.name)
            logger.log(error_string, logger.WARNING)
            return False, return_categories, error_string

        with BS4Parser(response.text, 'html5lib') as html:
            if not html.find('categories'):
                error_string = 'Error parsing caps xml for [{0}]'.format(self.name)
                logger.log(error_string, logger.DEBUG)
                return False, return_categories, error_string

            self.set_caps(html.find('searching'))
            if just_caps:
                return

            for category in html('category'):
                if 'TV' in category.get('name', '') and category.get('id', ''):
                    return_categories.append({'id': category['id'], 'name': category['name']})
                    for subcat in category('subcat'):
                        if subcat.get('name', '') and subcat.get('id', ''):
                            return_categories.append({'id': subcat['id'], 'name': subcat['name']})

            return True, return_categories, ''

    @staticmethod
    def _get_default_providers():
        # name|url|key|catIDs|enabled|search_mode|search_fallback|enable_daily|enable_backlog|enable_manualsearch
        return 'NZB.Cat|https://nzb.cat/||5030,5040,5010|0|eponly|0|0|0|0!!!' + \
            'NZBGeek|https://api.nzbgeek.info/||5030,5040|0|eponly|0|0|0|0!!!' + \
            'NZBs.org|https://nzbs.org/||5030,5040|0|eponly|0|0|0|0!!!' + \
            'Usenet-Crawler|https://www.usenet-crawler.com/||5030,5040|0|eponly|0|0|0|0!!!' + \
            'DOGnzb|https://api.dognzb.cr/||5030,5040,5060,5070|0|eponly|0|0|0|0'

