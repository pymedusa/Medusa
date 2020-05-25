# coding=utf-8

"""Provider code for BTN."""

from __future__ import unicode_literals

import logging
import socket
import time

import jsonrpclib

from medusa import (
    app,
    scene_exceptions,
    tv,
)
from medusa.common import cpu_presets
from medusa.helper.common import convert_size, episode_num
from medusa.indexers.config import INDEXER_TVDBV2
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.torrent.torrent_provider import TorrentProvider

from six import itervalues

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


# API docs:
# https://web.archive.org/web/20160316073644/http://btnapps.net/docs.php
# https://web.archive.org/web/20160425205926/http://btnapps.net/apigen/class-btnapi.html

def normalize_protocol_error(error):
    """
    Convert ProtocolError exception to a comparable code and message tuple.

    :param error: Exception instance
    :return: Tuple containing (code, message)
    """
    try:
        # error.args = ('api.broadcasthe.net', 524, 'Timeout', )
        code = error.args[1]
        message = error.args[2]
    except IndexError:
        # error.args = ((-32001, 'Invalid API Key', ), )
        try:
            code, message = error.args[0]
        except ValueError:
            # error.args = ('reason', )
            code = None
            message = error.args[0]

    return code, message


class BTNProvider(TorrentProvider):
    """BTN Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(BTNProvider, self).__init__('BTN')

        # Credentials
        self.api_key = None

        # URLs
        self.url = 'https://broadcasthe.net'
        self.urls = {
            'base_url': 'https://api.broadcasthe.net',
        }

        # Miscellaneous Options
        self.supports_absolute_numbering = True

        # Cache
        self.cache = tv.Cache(self, min_time=15)

    def search(self, search_strings, age=0, ep_obj=None, **kwargs):
        """
        Search a provider and parse the results.

        :param search_strings: A dict with {mode: search value}
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
            log.debug('Search mode: {0}', mode)

            if mode != 'RSS':
                searches = self._search_params(ep_obj, mode)
            else:
                searches = [search_params]

            for search_params in searches:
                if mode != 'RSS':
                    log.debug('Search string: {search}',
                              {'search': search_params})

                response = self._api_call(search_params)
                if not response or response.get('results') == '0':
                    log.debug('No data returned from provider')
                    continue

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

            seeders = int(row.get('Seeders', 1))
            leechers = int(row.get('Leechers', 0))

            # Filter unseeded torrent
            if seeders < self.minseed:
                if mode != 'RSS':
                    log.debug("Discarding torrent because it doesn't meet the"
                              ' minimum seeders: {0}. Seeders: {1}',
                              title, seeders)
                continue

            size = convert_size(row.get('Size'), default=-1)

            pubdate_raw = row.get('Time')
            pubdate = self.parse_pubdate(pubdate_raw, fromtimestamp=True)

            item = {
                'title': title,
                'link': download_url,
                'size': size,
                'seeders': seeders,
                'leechers': leechers,
                'pubdate': pubdate,
            }
            log.debug(
                'Found result: {title} with {x} seeders'
                ' and {y} leechers',
                {'title': title, 'x': seeders, 'y': leechers}
            )

            items.append(item)

        return items

    def _check_auth(self):

        if not self.api_key:
            log.warning('Missing API key. Check your settings')
            return False

        return True

    @staticmethod
    def _process_title_and_url(parsed_json):
        """Create the title base on properties.

        Try to get the release name, if it doesn't exist make one up
        from the properties obtained.
        """
        title = parsed_json.get('ReleaseName')
        if not title:
            # If we don't have a release name we need to get creative
            title = ''
            if 'Series' in parsed_json:
                title += parsed_json['Series']
            if 'GroupName' in parsed_json:
                title += '.' + parsed_json['GroupName']
            if 'Resolution' in parsed_json:
                title += '.' + parsed_json['Resolution']
            if 'Source' in parsed_json:
                title += '.' + parsed_json['Source']
            if 'Codec' in parsed_json:
                title += '.' + parsed_json['Codec']
            if title:
                title = title.replace(' ', '.')

        url = parsed_json.get('DownloadURL')
        if not url:
            log.debug('Download URL is missing from response for release "{0}"', title)
        else:
            url = url.replace('\\/', '/')

        return title, url

    def _search_params(self, ep_obj, mode, season_numbering=None):

        if not ep_obj:
            return []

        searches = []
        season = 'Season' if mode == 'Season' else ''

        air_by_date = ep_obj.series.air_by_date
        sports = ep_obj.series.sports

        if not season_numbering and (air_by_date or sports):
            date_fmt = '%Y' if season else '%Y.%m.%d'
            search_name = ep_obj.airdate.strftime(date_fmt)
        else:
            search_name = '{type} {number}'.format(
                type=season,
                number=ep_obj.season if season else episode_num(
                    ep_obj.season, ep_obj.episode
                ),
            ).strip()

        params = {
            'category': season or 'Episode',
            'name': search_name,
        }

        # Search
        if ep_obj.series.indexer == INDEXER_TVDBV2:
            params['tvdb'] = self._get_tvdb_id()
            searches.append(params)
        else:
            name_exceptions = scene_exceptions.get_scene_exceptions(ep_obj.series)
            name_exceptions.add(ep_obj.series.name)
            for name in name_exceptions:
                # Search by name if we don't have tvdb id
                params['series'] = name
                searches.append(params)

        # extend air by date searches to include season numbering
        if air_by_date and not season_numbering:
            searches.extend(
                self._search_params(ep_obj, mode, season_numbering=True)
            )

        return searches

    def _api_call(self, params=None, results_per_page=300, offset=0):
        """Call provider API."""
        parsed_json = {}

        try:
            server = jsonrpclib.Server(self.urls['base_url'])
            parsed_json = server.getTorrents(
                self.api_key,
                params or {},
                int(results_per_page),
                int(offset)
            )
            time.sleep(cpu_presets[app.CPU_PRESET])
        except jsonrpclib.jsonrpc.ProtocolError as error:
            code, message = normalize_protocol_error(error)
            if (code, message) == (-32001, 'Invalid API Key'):
                log.warning('Incorrect authentication credentials.')
            elif (code, message) == (-32002, 'Call Limit Exceeded'):
                log.warning('You have exceeded the limit of 150 calls per hour.')
            elif code in (500, 502, 521, 524):
                log.warning('Provider is currently unavailable. Error: {code} {text}',
                            {'code': code, 'text': message})
            else:
                log.error('JSON-RPC protocol error while accessing provider. Error: {msg!r}',
                          {'msg': error.args})

        except (socket.error, ValueError) as error:
            log.warning('Error while accessing provider. Error: {msg!r}', {'msg': error})
        return parsed_json


provider = BTNProvider()
