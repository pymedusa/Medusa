# coding=utf-8

"""Provider code for T411."""

from __future__ import unicode_literals

import logging
import time
import traceback
from operator import itemgetter

from medusa import tv
from medusa.common import USER_AGENT
from medusa.helper.common import (
    convert_size,
    try_int,
)
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.auth import AuthBase
from requests.compat import quote, urljoin

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class T411Provider(TorrentProvider):
    """T411 Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(self.__class__, self).__init__("T411")

        # Credentials
        self.username = None
        self.password = None
        self.token = None
        self.tokenLastUpdate = None

        # URLs
        self.url = 'https://api.t411.al'
        self.urls = {
            'search': urljoin(self.url, 'torrents/search/{search}'),
            'rss': urljoin(self.url, 'torrents/top/today'),
            'login_page': urljoin(self.url, 'auth'),
            'download': urljoin(self.url, 'torrents/download/{id}'),
        }

        # Proper Strings

        # Miscellaneous Options
        self.headers.update({'User-Agent': USER_AGENT})
        self.subcategories = [433, 637, 455, 639]
        self.confirmed = False

        # Torrent Stats
        self.minseed = 0
        self.minleech = 0

        # Cache
        self.cache = tv.Cache(self, min_time=10)  # Only poll T411 every 10 minutes max

    def search(self, search_strings, age=0, ep_obj=None):
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
        search_params = {}

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            for search_string in search_strings[mode]:
                if mode != 'RSS':
                    log.debug('Search string: {search}',
                              {'search': search_string})
                    if self.confirmed:
                        log.debug('Searching only confirmed torrents')

                    # use string formatting to safely coerce the search term
                    # to unicode then utf-8 encode the unicode string
                    term = '{term}'.format(term=search_string).encode('utf-8')
                    # build the search URL
                    search_url = self.urls['search'].format(
                        search=quote(term)  # URL encode the search term
                    )
                    categories = self.subcategories
                    search_params.update({'limit': 100})
                else:
                    search_url = self.urls['rss']
                    # Using None as a category removes it as a search param
                    categories = [None]  # Must be a list for iteration

                for category in categories:
                    search_params.update({'cid': category})
                    response = self.get_url(
                        search_url, params=search_params, returns='response'
                    )

                    if not response or not response.content:
                        log.debug('No data returned from provider')
                        continue

                    try:
                        jdata = response.json()
                    except ValueError:
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

        unsorted_torrent_rows = data.get('torrents') if mode != 'RSS' else data

        if not unsorted_torrent_rows:
            log.debug(
                'Data returned from provider does not contain any {torrents}',
                {'torrents': 'confirmed torrents' if self.confirmed else 'torrents'}
            )
            return items

        torrent_rows = sorted(unsorted_torrent_rows, key=itemgetter('added'), reverse=True)

        for row in torrent_rows:
            if not isinstance(row, dict):
                log.warning('Invalid data returned from provider')
                continue

            if mode == 'RSS' and 'category' in row and try_int(row['category'], 0) not in self.subcategories:
                continue

            try:
                title = row['name']
                torrent_id = row['id']
                download_url = self.urls['download'].format(id=torrent_id)
                if not all([title, download_url]):
                    continue

                seeders = try_int(row['seeders'])
                leechers = try_int(row['leechers'])
                verified = bool(row['isVerified'])

                # Filter unseeded torrent
                if seeders < min(self.minseed, 1):
                    if mode != 'RSS':
                        log.debug("Discarding torrent because it doesn't meet the"
                                  " minimum seeders: {0}. Seeders: {1}",
                                  title, seeders)
                    continue

                if self.confirmed and not verified and mode != 'RSS':
                    log.debug("Found result {0} but that doesn't seem like a verified"
                              " result so I'm ignoring it", title)
                    continue

                torrent_size = row['size']
                size = convert_size(torrent_size) or -1

                item = {
                    'title': title,
                    'link': download_url,
                    'size': size,
                    'seeders': seeders,
                    'leechers': leechers,
                    'pubdate': None,
                }
                if mode != 'RSS':
                    log.debug('Found result: {0} with {1} seeders and {2} leechers',
                              title, seeders, leechers)

                items.append(item)
            except (AttributeError, TypeError, KeyError, ValueError, IndexError):
                log.error('Failed parsing provider. Traceback: {0!r}',
                          traceback.format_exc())

        return items

    def login(self):
        """Log into provider."""
        if self.token is not None:
            if time.time() < (self.tokenLastUpdate + 30 * 60):
                return True

        login_params = {
            'username': self.username,
            'password': self.password,
        }

        response = self.get_url(self.urls['login_page'], post_data=login_params, returns='json')
        if not response:
            log.warning('Unable to connect to provider')
            return False

        if response and 'token' in response:
            self.token = response['token']
            self.tokenLastUpdate = time.time()
            # self.uid = response['uid'].encode('ascii', 'ignore')
            self.session.auth = T411Auth(self.token)
            return True
        else:
            log.warning('Token not found in authentication response')
            return False


class T411Auth(AuthBase):
    """Attach HTTP Authentication to the given Request object."""

    def __init__(self, token):
        """Init object."""
        self.token = token

    def __call__(self, r):
        """Add token to request header."""
        r.headers['Authorization'] = self.token
        return r


provider = T411Provider()
