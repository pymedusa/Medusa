# coding=utf-8

"""Provider code for BTN."""

from __future__ import unicode_literals

import socket
import time

import jsonrpclib

from medusa import (
    app,
    logger,
    scene_exceptions,
    tv,
)
from medusa.common import cpu_presets
from medusa.helper.common import episode_num
from medusa.providers.torrent.torrent_provider import TorrentProvider

from six import itervalues


# API docs:
# https://web.archive.org/web/20160316073644/http://btnapps.net/docs.php
# https://web.archive.org/web/20160425205926/http://btnapps.net/apigen/class-btnapi.html

class BTNProvider(TorrentProvider):
    """BTN Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(self.__class__, self).__init__('BTN')

        # Credentials
        self.api_key = None

        # URLs
        self.url = 'https://broadcasthe.net'
        self.urls = {
            'base_url': 'https://api.broadcasthe.net',
        }

        # Proper Strings
        self.proper_strings = []

        # Miscellaneous Options
        self.supports_absolute_numbering = True

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tv.Cache(self, min_time=10)  # Only poll BTN every 15 minutes max

    def search(self, search_strings, age=0, ep_obj=None):
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
            logger.log('Search mode: {0}'.format(mode), logger.DEBUG)

            if mode != 'RSS':
                searches = self._search_params(ep_obj, mode)
            else:
                searches = [search_params]

            for search_params in searches:
                if mode != 'RSS':
                    logger.log('Search string: {search}'.format
                               (search=search_params), logger.DEBUG)

                response = self._api_call(search_params)
                if not response or response.get('results') == '0':
                    logger.log('No data returned from provider', logger.DEBUG)
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
            }
            logger.log(
                'Found result: {title} with {x} seeders'
                ' and {y} leechers'.format(
                    title=title, x=seeders, y=leechers
                ),
                logger.DEBUG
            )

            items.append(item)

        return items

    def _check_auth(self):

        if not self.api_key:
            logger.log('Missing API key. Check your settings', logger.WARNING)
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

        url = parsed_json.get('DownloadURL').replace('\\/', '/')
        return title, url

    def _search_params(self, ep_obj, mode, season_numbering=None):

        if not ep_obj:
            return []

        searches = []
        season = 'Season' if mode == 'Season' else ''

        air_by_date = ep_obj.show.air_by_date
        sports = ep_obj.show.sports

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
        if ep_obj.show.indexer == 1:
            params['tvdb'] = self._get_tvdb_id()
            searches.append(params)
        else:
            name_exceptions = scene_exceptions.get_scene_exceptions(
                ep_obj.show.indexerid,
                ep_obj.show.indexer
            )
            name_exceptions.add(ep_obj.show.name)
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
            if error.message[1] == 'Invalid API Key':
                logger.log('Incorrect authentication credentials.',
                           logger.WARNING)
            elif error.message[1] == 'Call Limit Exceeded':
                logger.log('You have exceeded the limit of'
                           ' 150 calls per hour.', logger.WARNING)
            else:
                logger.log('JSON-RPC protocol error while accessing provider.'
                           ' Error: {msg!r}'.format(msg=error.message[1]),
                           logger.ERROR)

        except (socket.error, socket.timeout, ValueError) as error:
            logger.log('Error while accessing provider.'
                       ' Error: {msg}'.format(msg=error), logger.WARNING)
        return parsed_json


provider = BTNProvider()
