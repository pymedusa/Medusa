# coding=utf-8

"""Provider code for PrivateHD."""

from __future__ import unicode_literals

import logging

from medusa import tv
from medusa.helper.common import convert_size
from medusa.helper.exceptions import AuthException
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.compat import urljoin

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class PrivateHDProvider(TorrentProvider):
    """PrivateHD Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(PrivateHDProvider, self).__init__('PrivateHD')

        # Credentials
        self.username = None
        self.password = None
        self.pid = None
        self._token = None

        # URLs
        self.url = 'https://privatehd.to'
        self.urls = {
            'login': urljoin(self.url, 'api/v1/jackett/auth'),
            'search': urljoin(self.url, 'api/v1/jackett/torrents'),
        }

        # Proper Strings
        self.proper_strings = ['PROPER', 'REPACK', 'REAL', 'RERIP']

        # Miscellaneous Options
        self.freeleech = False

        # Torrent Stats

        # Cache
        self.cache = tv.Cache(self)  # only poll PrivateHD every 10 minutes max

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

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            for search_string in search_strings[mode]:
                if mode != 'RSS':
                    log.debug('Search string: {search}',
                              {'search': search_string})

                search_params = {
                    'in': 1,
                    'search': search_string,
                    'type': 2,
                    'discount[]': 1 if self.freeleech else None,
                    'tv_type[]': {'episode': 1, 'season': 2}.get(mode.lower())
                }

                if not search_string:
                    del search_params['search']

                headers = {
                    'Authorization': f'Bearer {self._token}'
                }

                response = self.session.get(self.urls['search'], params=search_params, headers=headers)
                try:
                    jdata = response.json()
                    if not jdata.get('data') or not len(jdata['data']):
                        log.debug('No data returned from provider')
                        continue
                except (AttributeError, ValueError):
                    log.debug('No data returned from provider')
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
        json_data = data.get('data', [])

        for row in json_data:
            try:
                title = row.pop('file_name')
                download_url = row.pop('download')
                if not all([title, download_url]):
                    continue

                seeders = row.pop('seed', 0)
                leechers = row.pop('leech', 0)

                # Filter unseeded torrent
                if seeders < self.minseed:
                    if mode != 'RSS':
                        log.debug("Discarding torrent because it doesn't meet the"
                                  ' minimum seeders: {0}. Seeders: {1}',
                                  title, seeders)
                    continue

                size = convert_size(row.pop('file_size', None), default=-1)
                pubdate_raw = row.pop('created_at')
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
        login_params = {
            'pid': self.pid,
            'username': self.username,
            'password': self.password
        }

        response = self.session.post(self.urls['login'], data=login_params)
        try:
            jdata = response.json()
            if 'message' in jdata:
                raise AuthException(f"Error trying to auth, {jdata['message']}")
        except (AttributeError, ValueError):
            log.debug('No data returned from provider')
            raise AuthException('Could not get auth token')

        if 'token' in jdata:
            self._token = jdata['token']
            return True

        return False


provider = PrivateHDProvider()
