# coding=utf-8

"""Provider code for TvRoad."""

from __future__ import unicode_literals

import logging
import re

from medusa import tv
from medusa.bs4_parser import BS4Parser
from medusa.helper.common import (
    convert_size,
    try_int,
)
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.compat import urljoin
from requests.utils import dict_from_cookiejar

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class TvRoadProvider(TorrentProvider):
    """TvRoad Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(TvRoadProvider, self).__init__('TvRoad')

        # Credentials
        self.username = None
        self.password = None

        # URLs
        self.url = 'https://tvroad.info'
        self.urls = {
            'login': urljoin(self.url, 'TvRoad/Connexion'),
            'search': urljoin(self.url, 'TvRoad/Torrents/Recherche'),
        }

        # Proper Strings
        self.proper_strings = ['PROPER', 'REPACK', 'RERIP']

        # Miscellaneous Options

        # Cache
        self.cache = tv.Cache(self, min_time=30)

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
            'type': 'tout',  # search for all words in string not any word
            'endroit': 'nomtorrent',  # Search in torrent name
            'tl': 'oui',  # torrents in seed
        }

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {search}',
                              {'search': search_string})

                search_params['recherche'] = re.sub(r'[()]', '', search_string)
                response = self.session.get(self.urls['search'], params=search_params)
                if not response or not response.text:
                    log.debug('No data returned from provider')
                    continue

                results += self.parse(response.text, mode)

        return results

    def parse(self, data, mode):
        """
        Parse search results for items.

        :param data: The raw response from a search
        :param mode: The current mode used to search, e.g. RSS

        :return: A list of items found
        """
        # Units
        units = ['O', 'KO', 'MO', 'GO', 'TO', 'PO']

        items = []

        with BS4Parser(data, 'html5lib') as html:
            torrent_table = html.find(class_='sortable')
            torrent_rows = torrent_table('tr') if torrent_table else []

            # Continue only if at least one release is found
            if len(torrent_rows) < 2:
                log.debug('Data returned from provider does not contain any torrents')
                return items

            # Catégorie, Release, Date, DL, Size, C, S, L
            labels = [label.get_text(strip=True) for label in torrent_rows[0]('th')]

            # Skip column headers
            for row in torrent_rows[1:]:
                cells = row('td')
                if len(cells) < len(labels):
                    continue

                try:
                    title = cells[labels.index('Nom')].get_text(strip=True)
                    download = cells[labels.index('DL')].find('a')['href']
                    download_url = download
                    if not all([title, download_url]):
                        continue

                    seeders = try_int(cells[labels.index('S')].get_text(strip=True))
                    leechers = try_int(cells[labels.index('L')].get_text(strip=True))

                    # Filter unseeded torrent
                    if seeders < self.minseed:
                        if mode != 'RSS':
                            log.debug("Discarding torrent because it doesn't meet the"
                                      ' minimum seeders: {0}. Seeders: {1}',
                                      title, seeders)
                        continue

                    size_index = labels.index('Size') if 'Size' in labels else labels.index('Taille')
                    torrent_size = cells[size_index].get_text()
                    size = convert_size(torrent_size, units=units) or -1

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
        if any(dict_from_cookiejar(self.session.cookies).values()):
            return True

        login_params = {
            'username': self.username,
            'password': self.password,
        }

        response = self.session.post(self.urls['login'], data=login_params)

        if not response or response.text:
            log.warning('Unable to connect to provider')
            return False

        if 'Désolé, Les Identifiants Saisis Sont Incorrects.' in response.text:
            log.warning('Invalid username or password. Check your settings')
            return False

        return True


provider = TvRoadProvider()
