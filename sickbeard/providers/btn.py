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

import jsonrpclib
import math
import socket
import time
from six import iteritems

import sickbeard
from datetime import datetime

from sickbeard import classes, logger, scene_exceptions, tvcache
from sickbeard.common import cpu_presets
from sickbeard.helpers import sanitizeSceneName

from sickrage.helper.common import episode_num
from sickrage.helper.exceptions import AuthException, ex
from sickrage.providers.torrent.TorrentProvider import TorrentProvider


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
            'website': self.url,
        }

        # Proper Strings

        # Miscellaneous Options
        self.supports_absolute_numbering = True

        # Torrent Stats

        # Cache
        self.cache = BTNCache(self, min_time=15)  # Only poll BTN every 15 minutes max

    def search(self, search_strings, age=0, ep_obj=None):  # pylint:disable=too-many-locals
        """
        BTN search and parsing

        :param search_string: A dict with mode (key) and the search value (value)
        :param age: Not used
        :param ep_obj: Not used
        :returns: A list of search results (structure)
        """
        results = []
        self._check_auth()

        # Search Params
        search_params = {
        }

        # age in seconds
        if age:
            search_params['age'] = '<=' + str(int(age))

        if search_strings:
            search_params.update(search_strings)
            logger.log('Search string: {0}'.format(search_strings), logger.DEBUG)

        parsed_json = self._api_call(self.api_key, search_params)
        if not parsed_json:
            logger.log('No data returned from provider', logger.DEBUG)
            return results

        if self._check_auth_from_data(parsed_json):

            found_torrents = parsed_json.get('torrents', {})

            # We got something, we know the API sends max 1000 results at a time.
            # See if there are more than 1000 results for our query, if not we
            # keep requesting until we've got everything.
            # max 150 requests per hour so limit at that. Scan every 15 minutes. 60 / 15 = 4.
            max_pages = 150
            results_per_page = 1000

            if 'results' in parsed_json and int(parsed_json['results']) >= results_per_page:
                pages_needed = int(math.ceil(int(parsed_json['results']) / results_per_page))
                if pages_needed > max_pages:
                    pages_needed = max_pages

                # +1 because range(1,4) = 1, 2, 3
                for page in range(1, pages_needed + 1):
                    parsed_json = self._api_call(self.api_key, search_params, results_per_page, page * results_per_page)
                    # Note that these are individual requests and might time out individually.
                    # This would result in 'gaps' in the results. There is no way to fix this though.
                    if 'torrents' in parsed_json:
                        found_torrents.update(parsed_json['torrents'])

            for _, torrent_info in iteritems(found_torrents):
                (title, url) = self._get_title_and_url(torrent_info)

                if title and url:
                    logger.log('Found result: {0}'.format(title), logger.DEBUG)
                    results.append(torrent_info)

        # FIXME SORT RESULTS
        return results

    def _check_auth(self):
        if not self.api_key:
            logger.log('Invalid api key. Check your settings', logger.WARNING)

        return True

    def _check_auth_from_data(self, parsed_json):

        if parsed_json is None:
            return self._check_auth()

        if 'api-error' in parsed_json:
            logger.log('Incorrect authentication credentials: {0}'.format(parsed_json['api-error']), logger.DEBUG)
            raise AuthException('Your authentication credentials for {0} are missing,'
                                ' check your config.'.format(self.name))

        return True

    def _get_title_and_url(self, parsed_json):

        # The BTN API gives a lot of information in response,
        # however SickRage is built mostly around Scene or
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
                # unescaped / is valid in JSON, but it can be escaped
                url = url.replace('\\/', '/')

        return title, url

    def find_propers(self, search_date=None):
        results = []

        search_terms = ['%.proper.%', '%.repack.%']

        for term in search_terms:
            for item in self.search({'release': term}, age=4 * 24 * 60 * 60):
                if item['Time']:
                    try:
                        result_date = datetime.fromtimestamp(float(item['Time']))
                    except TypeError:
                        result_date = None

                    if result_date:
                        if not search_date or result_date > search_date:
                            title, url = self._get_title_and_url(item)
                            results.append(classes.Proper(title, url, result_date, self.show))

        return results

    def _get_season_search_strings(self, ep_obj):
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

        # search
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

    def _get_episode_search_strings(self, ep_obj, add_string=''):

        if not ep_obj:
            return [{}]

        to_return = []
        search_params = {'category': 'Episode'}

        # episode
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

        # search
        if ep_obj.show.indexer == 1:
            search_params['tvdb'] = ep_obj.show.indexerid
            to_return.append(search_params)
        else:
            # add new query string for every exception
            name_exceptions = list(
                set(scene_exceptions.get_scene_exceptions(ep_obj.show.indexerid) + [ep_obj.show.name]))
            for cur_exception in name_exceptions:
                search_params['series'] = sanitizeSceneName(cur_exception)
                to_return.append(search_params)

        return to_return

    def _api_call(self, apikey, params=None, results_per_page=1000, offset=0):

        server = jsonrpclib.Server(self.urls['base_url'])
        parsed_json = {}

        try:
            parsed_json = server.getTorrents(apikey, params or {}, int(results_per_page), int(offset))
            time.sleep(cpu_presets[sickbeard.CPU_PRESET])

        except jsonrpclib.jsonrpc.ProtocolError as error:
            if error.message == 'Call Limit Exceeded':
                logger.log('You have exceeded the limit of 150 calls per hour,'
                           ' per API key which is unique to your user account', logger.WARNING)
            else:
                logger.log('JSON-RPC protocol error while accessing provider. Error: {msg!r}'.format(msg=error), logger.ERROR)
            parsed_json = {'api-error': ex(error)}
            return parsed_json

        except socket.timeout:
            logger.log('Timeout while accessing provider', logger.WARNING)

        except socket.error as error:
            # Note that sometimes timeouts are thrown as socket errors
            logger.log('Socket error while accessing provider. Error: {msg}'.format(msg=error[1]), logger.WARNING)

        except Exception as error:
            errorstring = str(error)
            if errorstring.startswith('<') and errorstring.endswith('>'):
                errorstring = errorstring[1:-1]
            logger.log('Unknown error while accessing provider. Error: {msg}'.format(msg=errorstring), logger.WARNING)

        return parsed_json

    def _do_general_search(self, search_string):
        # 'search' looks as broad is it can find. Can contain episode overview and title for example,
        # use with caution!
        return self.search({'search': search_string})


class BTNCache(tvcache.TVCache):
    def _getRSSData(self):
        # Get the torrents uploaded since last check.
        seconds_since_last_update = math.ceil(time.time() - time.mktime(self._getLastUpdate().timetuple()))

        # default to 15 minutes
        seconds_min_time = self.minTime * 60
        if seconds_since_last_update < seconds_min_time:
            seconds_since_last_update = seconds_min_time

        # Set maximum to 24 hours (24 * 60 * 60 = 86400 seconds) of 'RSS' data search, older things will need to be done through backlog
        if seconds_since_last_update > 86400:
            logger.log(
                'The last known successful update was more than 24 hours ago, only trying to fetch the last 24 hours!',
                logger.DEBUG)
            seconds_since_last_update = 86400

        self.search_params = None  # BTN cache does not use search params
        return {'entries': self.provider.search(search_params=self.search_params, age=seconds_since_last_update)}


provider = BTNProvider()
