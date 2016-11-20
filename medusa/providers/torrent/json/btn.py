# coding=utf-8
# Author: Daniel Heimans
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

import socket
import time

import jsonrpclib
from six import itervalues
from ..torrent_provider import TorrentProvider
from .... import app, logger, scene_exceptions, tv_cache
from ....common import cpu_presets
from ....helper.common import episode_num
from ....helper.exceptions import ex
from ....helpers import sanitizeSceneName


class BTNProvider(TorrentProvider):
    """BTN Torrent provider"""
    def __init__(self):

        # Provider Init
        TorrentProvider.__init__(self, 'BTN')

        # Credentials
        self.api_key = None

        # URLs
        self.url = 'http://broadcasthe.net/'
        self.urls = {
            'base_url': 'http://api.btnapps.net',
        }

        # Proper Strings
        self.proper_strings = []

        # Miscellaneous Options
        self.supports_absolute_numbering = True

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tv_cache.TVCache(self, min_time=15)  # Only poll BTN every 15 minutes max

    def search(self, search_strings, age=0, ep_obj=None):  # pylint:disable=too-many-locals
        """
        Search a provider and parse the results

        :param search_strings: A dict with mode (key) and the search value (value)
        :param age: Not used
        :param ep_obj: Not used
        :returns: A list of search results (structure)
        """
        results = []
        if not self._check_auth():
            return results

        # Search Params
        search_params = {
            'age': '<=10800',  # Results from the past 3 hours
        }

        for mode in search_strings:
            logger.log('Search mode: {0}'.format(mode), logger.DEBUG)

            if mode != 'RSS':
                search_params = self._episode_search_params(ep_obj)
                logger.log('Search string: {search}'.format
                           (search=search_params), logger.DEBUG)

            if mode == 'Season':
                search_params = self._season_search_params(ep_obj)

            response = self._api_call(self.api_key, search_params)
            if not response:
                logger.log('No data returned from provider', logger.DEBUG)
                continue

            if not self._check_auth_from_data(response):
                return results

            results += self.parse(response.get('torrents', {}), mode)

        return results

    def parse(self, data, mode):
        """
        Parse search results for items.

        :param data: The raw response from a search
        :param mode: The current mode used to search, e.g. RSS

        :return: A list of items found
        """

        items = []

        torrent_rows = itervalues(data)

        for row in torrent_rows:
            title, download_url = self._process_title_and_url(row)

            if not all([title, download_url]):
                continue

            seeders = row.get('Seeders', 1)
            leechers = row.get('Leechers', 0)

            # Filter unseeded torrent
            if seeders < min(self.minseed, 1):
                logger.log("Discarding torrent because it doesn't meet the "
                           "minimum seeders: {0}. Seeders: {1}".format
                           (title, seeders), logger.DEBUG)
                continue

            size = row.get('Size') or -1

            item = {
                'title': title,
                'link': download_url,
                'size': size,
                'seeders': seeders,
                'leechers': leechers,
                'pubdate': None,
                'torrent_hash': None,
            }
            logger.log('Found result: {0} with {1} seeders and {2} leechers'.format
                       (title, seeders, leechers), logger.DEBUG)

            items.append(item)

        return items

    def _check_auth(self):

        if not self.api_key:
            logger.log('Missing API key. Check your settings', logger.WARNING)
            return False

        return True

    @staticmethod
    def _check_auth_from_data(parsed_json):

        if 'api-error' in parsed_json:
            logger.log('Incorrect authentication credentials: {0}'.format
                       (parsed_json['api-error']), logger.DEBUG)
            return False

        return True

    @staticmethod
    def _process_title_and_url(parsed_json):

        # The BTN API gives a lot of information in response,
        # however this application is built mostly around Scene or
        # release names, which is why we are using them here.

        if 'ReleaseName' in parsed_json and parsed_json['ReleaseName']:
            title = parsed_json['ReleaseName']

        else:
            # If we don't have a release name we need to get creative
            title = ''
            if 'Series' in parsed_json:
                title += parsed_json['Series']
            if 'GroupName' in parsed_json:
                title += '.' + parsed_json['GroupName'] if title else parsed_json['GroupName']
            if 'Resolution' in parsed_json:
                title += '.' + parsed_json['Resolution'] if title else parsed_json['Resolution']
            if 'Source' in parsed_json:
                title += '.' + parsed_json['Source'] if title else parsed_json['Source']
            if 'Codec' in parsed_json:
                title += '.' + parsed_json['Codec'] if title else parsed_json['Codec']
            if title:
                title = title.replace(' ', '.')

        url = None
        if 'DownloadURL' in parsed_json:
            url = parsed_json['DownloadURL']
            if url:
                # Unescaped / is valid in JSON, but it can be escaped
                url = url.replace('\\/', '/')

        return title, url

    @staticmethod
    def _season_search_params(ep_obj):

        search_params = []
        current_params = {'category': 'Season'}

        # Search for entire seasons: no need to do special things for air by date or sports shows
        if ep_obj.show.air_by_date or ep_obj.show.sports:
            # Search for the year of the air by date show
            current_params['name'] = str(ep_obj.airdate).split('-')[0]
        elif ep_obj.show.is_anime:
            current_params['name'] = '%d' % ep_obj.scene_absolute_number
        else:
            current_params['name'] = 'Season ' + str(ep_obj.scene_season)

        # Search
        if ep_obj.show.indexer == 1:
            current_params['tvdb'] = ep_obj.show.indexerid
            search_params.append(current_params)
        else:
            name_exceptions = list(
                set(scene_exceptions.get_scene_exceptions(ep_obj.show.indexerid) + [ep_obj.show.name]))
            for name in name_exceptions:
                # Search by name if we don't have tvdb id
                current_params['series'] = sanitizeSceneName(name)
                search_params.append(current_params)

        return search_params

    @staticmethod
    def _episode_search_params(ep_obj):

        if not ep_obj:
            return [{}]

        to_return = []
        search_params = {'category': 'Episode'}

        # Episode
        if ep_obj.show.air_by_date or ep_obj.show.sports:
            date_str = str(ep_obj.airdate)

            # BTN uses dots in dates, we just search for the date since that
            # combined with the series identifier should result in just one episode
            search_params['name'] = date_str.replace('-', '.')
        elif ep_obj.show.anime:
            search_params['name'] = '%i' % int(ep_obj.scene_absolute_number)
        else:
            # Do a general name search for the episode, formatted like SXXEYY
            search_params['name'] = '{ep}'.format(ep=episode_num(ep_obj.scene_season, ep_obj.scene_episode))

        # Search
        if ep_obj.show.indexer == 1:
            search_params['tvdb'] = ep_obj.show.indexerid
            to_return.append(search_params)
        else:
            # Add new query string for every exception
            name_exceptions = list(
                set(scene_exceptions.get_scene_exceptions(ep_obj.show.indexerid) + [ep_obj.show.name]))
            for cur_exception in name_exceptions:
                search_params['series'] = sanitizeSceneName(cur_exception)
                to_return.append(search_params)

        return to_return

    def _api_call(self, apikey, params=None, results_per_page=300, offset=0):

        server = jsonrpclib.Server(self.urls['base_url'])
        parsed_json = {}

        try:
            parsed_json = server.getTorrents(apikey, params or {}, int(results_per_page), int(offset))
            time.sleep(cpu_presets[app.CPU_PRESET])

        except jsonrpclib.jsonrpc.ProtocolError as error:
            if error.message == 'Call Limit Exceeded':
                logger.log('You have exceeded the limit of 150 calls per hour,'
                           ' per API key which is unique to your user account', logger.WARNING)
            else:
                logger.log('JSON-RPC protocol error while accessing provider. Error: {msg!r}'.format
                           (msg=error), logger.ERROR)
            parsed_json = {'api-error': ex(error)}
            return parsed_json

        except socket.timeout:
            logger.log('Timeout while accessing provider', logger.WARNING)

        except socket.error as error:
            # Note that sometimes timeouts are thrown as socket errors
            logger.log('Socket error while accessing provider. Error: {msg}'.format
                       (msg=error[1]), logger.WARNING)

        except Exception as error:
            errorstring = str(error)
            if errorstring.startswith('<') and errorstring.endswith('>'):
                errorstring = errorstring[1:-1]
            logger.log('Unknown error while accessing provider. Error: {msg}'.format
                       (msg=errorstring), logger.WARNING)

        return parsed_json


provider = BTNProvider()
