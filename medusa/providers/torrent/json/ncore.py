# coding=utf-8

"""Provider code for nCore."""

from __future__ import unicode_literals

import logging

from medusa import tv
from medusa.helper.common import convert_size
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.utils import dict_from_cookiejar

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class NcoreProvider(TorrentProvider):
    """nCore Torrent provider."""

    def __init__(self):
        """.Initialize the class."""
        super(NcoreProvider, self).__init__('nCore')

        # Credentials
        self.username = None
        self.password = None

        # URLs
        self.url = 'https://ncore.cc'
        self.urls = {
            'login': 'https://ncore.cc/login.php',
            'search': 'https://ncore.cc/torrents.php',
        }

        # Proper Strings
        self.proper_strings = ['PROPER', 'REPACK', 'REAL', 'RERIP']

        # Miscellaneous Options

        # Cache
        self.cache = tv.Cache(self, min_time=20)

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

        categories = [
            'xvidser_hun', 'xvidser',
            'dvdser_hun', 'dvdser',
            'hdser_hun', 'hdser'
        ]

        # Search Params
        search_params = {
            'nyit_sorozat_resz': 'true',
            'kivalasztott_tipus': ','.join(categories),
            'mire': '',
            'miben': 'name',
            'tipus': 'kivalasztottak_kozott',
            'searchedfrompotato': 'true',
            'jsons': 'true',
        }

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {search}',
                              {'search': search_string})

                    search_params['mire'] = search_string

                data = self.session.get_json(self.urls['search'], params=search_params)
                if not data:
                    log.debug('No data returned from provider')
                    continue

                results += self.parse(data, mode)

        return results

    def parse(self, data, mode):
        """
        Parse search results for items.

        :param data: The raw response from a search
        :param mode: The current mode used to search, e.g. RSS

        :return: A list of items found
        """
        items = []

        torrent_rows = data.get('results', {})
        for row in torrent_rows:
            try:
                title = row.pop('release_name', '')
                download_url = row.pop('download_url', '')
                if not (title and download_url):
                    continue

                seeders = int(row.pop('seeders', 0))
                leechers = int(row.pop('leechers', 0))

                # Filter unseeded torrent
                if seeders < self.minseed:
                    if mode != 'RSS':
                        log.debug("Discarding torrent because it doesn't meet the"
                                  ' minimum seeders: {0}. Seeders: {1}',
                                  title, seeders)
                    continue

                size = convert_size(row.pop('size', None), default=-1)

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
                log.exception('Failed parsing provider.')

        return items

    def login(self):
        """Login method used for logging in before doing search and torrent downloads."""
        if (dict_from_cookiejar(self.session.cookies).values()
                and self.session.cookies.get('nick')):
            return True

        login_params = {
            'nev': self.username,
            'pass': self.password,
            'ne_leptessen_ki': '1',
            'submitted': '1',
            'set_lang': 'en',
            'submit': 'Access!',
        }

        response = self.session.post(self.urls['login'], data=login_params)
        if not response or not response.text:
            log.warning('Unable to connect to provider')
            return False

        if 'Wrong username or password!' in response.text:
            log.warning('Invalid username or password. Check your settings')
            return False

        return True


provider = NcoreProvider()
