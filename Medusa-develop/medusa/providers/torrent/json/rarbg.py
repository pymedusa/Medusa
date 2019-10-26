# coding=utf-8

"""Provider code for RARBG."""

from __future__ import unicode_literals

import datetime
import logging
import time

from medusa import (
    app,
    tv,
)
from medusa.helper.common import convert_size, try_int
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.torrent.torrent_provider import TorrentProvider

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class RarbgProvider(TorrentProvider):
    """RARBG Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(RarbgProvider, self).__init__('Rarbg')

        # Credentials
        self.public = True
        self.token = None
        self.token_expires = None

        # URLs
        self.url = 'https://rarbg.com'  # Spec: https://torrentapi.org/apidocs_v2.txt
        self.urls = {
            'api': 'http://torrentapi.org/pubapi_v2.php',
        }

        # Proper Strings
        self.proper_strings = ['{{PROPER|REPACK|REAL|RERIP}}']

        # Miscellaneous Options
        self.ranked = None
        self.sorting = None

        # Cache
        self.cache = tv.Cache(self, min_time=15)

    def search(self, search_strings, age=0, ep_obj=None, **kwargs):
        """
        Search a provider and parse the results.

        :param search_strings: A dict with mode (key) and the search value (value)
        :param age: Not used
        :param ep_obj: Not used
        :returns: A list of search results (structure)
        """
        results = []
        if not self.login():
            return results

        # Search Params
        search_params = {
            'app_id': app.RARBG_APPID,
            'category': 'tv',
            'min_seeders': self.minseed,
            'min_leechers': self.minleech,
            'limit': 100,
            'format': 'json_extended',
            'ranked': try_int(self.ranked),
            'token': self.token,
            'sort': 'last',
            'mode': 'list',
        }

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            if mode == 'RSS':
                search_params['search_string'] = None
                search_params['search_tvdb'] = None
            else:
                search_params['sort'] = self.sorting if self.sorting else 'seeders'
                search_params['mode'] = 'search'
                search_params['search_tvdb'] = self._get_tvdb_id()

            for search_string in search_strings[mode]:
                if mode != 'RSS':
                    log.debug('Search string: {search}',
                              {'search': search_string})
                    if self.ranked:
                        log.debug('Searching only ranked torrents')

                search_params['search_string'] = search_string

                # Check if token is still valid before search
                if not self.login():
                    continue

                # Maximum requests allowed are 1req/2sec
                # Changing to 5 because of server clock desync
                time.sleep(5)

                search_url = self.urls['api']
                response = self.session.get(search_url, params=search_params)
                if not response or not response.content:
                    log.debug('No data returned from provider')
                    continue

                try:
                    jdata = response.json()
                except ValueError:
                    log.debug('No data returned from provider')
                    continue

                error = jdata.get('error')
                error_code = jdata.get('error_code')
                if error:
                    # List of errors: https://github.com/rarbg/torrentapi/issues/1#issuecomment-114763312
                    if error_code == 5:
                        # 5 = Too many requests per second
                        log_level = logging.INFO
                    elif error_code not in (4, 8, 10, 12, 14, 20):
                        # 4 = Invalid token. Use get_token for a new one!
                        # 8, 10, 12, 14 = Cant find * in database. Are you sure this * exists?
                        # 20 = No results found
                        log_level = logging.WARNING
                    else:
                        log_level = logging.DEBUG

                    log.log(log_level, '{msg} Code: {code}', {'msg': error, 'code': error_code})
                    continue

                results += self.parse(jdata, mode)

        return results

    def parse(self, data, mode):
        """
        Parse search results for items.

        :param data: The raw response from a search
        :param mode: The current mode used to search, e.g. RSS

        :return: A list of items found
        """
        items = []

        torrent_rows = data.get('torrent_results', {})
        if not torrent_rows:
            log.debug('Data returned from provider does not contain any torrents')
            return items

        for row in torrent_rows:
            try:
                title = row.pop('title')
                download_url = row.pop('download') + self._custom_trackers
                if not all([title, download_url]):
                    continue

                seeders = row.pop('seeders', 0)
                leechers = row.pop('leechers', 0)

                # Filter unseeded torrent
                if seeders < self.minseed:
                    if mode != 'RSS':
                        log.debug("Discarding torrent because it doesn't meet the"
                                  ' minimum seeders: {0}. Seeders: {1}',
                                  title, seeders)
                    continue

                torrent_size = row.pop('size', None)
                size = convert_size(torrent_size, default=-1)

                pubdate_raw = row.pop('pubdate', None)
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

    def login(self):
        """Login method used for logging in before doing search and torrent downloads."""
        if self.token and self.token_expires and datetime.datetime.now() < self.token_expires:
            return True

        login_params = {
            'get_token': 'get_token',
            'format': 'json',
            'app_id': app.RARBG_APPID,
        }

        response = self.session.get(self.urls['api'], params=login_params)
        if not response:
            log.warning('Unable to connect to provider')
            return False

        try:
            self.token = response.json().get('token')
        except ValueError:
            self.token = None
        self.token_expires = datetime.datetime.now() + datetime.timedelta(minutes=14) if self.token else None
        return self.token is not None


provider = RarbgProvider()
