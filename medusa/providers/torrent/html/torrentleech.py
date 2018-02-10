# coding=utf-8

"""Provider code for TorrentLeech."""

from __future__ import unicode_literals

import logging

from medusa import tv
from medusa.bs4_parser import BS4Parser
from medusa.helper.common import (
    convert_size,
)
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.compat import urljoin
from requests.utils import dict_from_cookiejar

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class TorrentLeechProvider(TorrentProvider):
    """TorrentLeech Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(TorrentLeechProvider, self).__init__('TorrentLeech')

        # Credentials
        self.username = None
        self.password = None

        # URLs
        self.url = 'https://classic.torrentleech.org'
        self.urls = {
            'login': urljoin(self.url, 'user/account/login'),
            'search': urljoin(self.url, 'torrents/browse'),
        }

        # Proper Strings
        self.proper_strings = ['PROPER', 'REPACK', 'REAL', 'RERIP']

        # Miscellaneous Options

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tv.Cache(self)

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

        # TV, Episodes, BoxSets, Episodes HD, Animation, Anime, Cartoons, Foreign
        # 2,26,27,32,7,34,35,44

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {search}',
                              {'search': search_string})

                    categories = ['2', '7', '35']
                    categories += ['26', '32', '44'] if mode == 'Episode' else ['27']
                    if self.series and self.series.is_anime:
                        categories += ['34']
                else:
                    categories = ['2', '26', '27', '32', '7', '34', '35', '44']

                search_params = {
                    'categories': ','.join(categories),
                    'query': search_string
                }
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
        def process_column_header(td):
            result = ''
            if td.a:
                result = td.a.get('title')
            if not result:
                result = td.get_text(strip=True)
            return result

        items = []

        with BS4Parser(data, 'html5lib') as html:
            torrent_table = html.find('table', id='torrenttable')
            torrent_rows = torrent_table('tr') if torrent_table else []

            # Continue only if at least one release is found
            if len(torrent_rows) < 2:
                log.debug('Data returned from provider does not contain any torrents')
                return items

            labels = [process_column_header(label) for label in torrent_rows[0]('th')]

            # Skip column headers
            for row in torrent_rows[1:]:
                cells = row('td')

                try:
                    name = cells[labels.index('Name')]
                    title = name.find('a').get_text(strip=True)
                    download_url = row.find('td', class_='quickdownload').find('a')
                    if not all([title, download_url]):
                        continue

                    download_url = urljoin(self.url, download_url['href'])

                    seeders = int(cells[labels.index('Seeders')].get_text(strip=True))
                    leechers = int(cells[labels.index('Leechers')].get_text(strip=True))

                    # Filter unseeded torrent
                    if seeders < min(self.minseed, 1):
                        if mode != 'RSS':
                            log.debug("Discarding torrent because it doesn't meet the"
                                      " minimum seeders: {0}. Seeders: {1}",
                                      title, seeders)
                        continue

                    torrent_size = cells[labels.index('Size')].get_text()
                    size = convert_size(torrent_size) or -1

                    pubdate_raw = name.get_text(strip=True)[-19:]
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
        cookies = dict_from_cookiejar(self.session.cookies)
        if any(cookies.values()) and cookies.get('member_id'):
            return True

        login_params = {
            'username': self.username,
            'password': self.password,
            'login': 'submit',
            'remember_me': 'on',
        }

        response = self.session.post(self.urls['login'], data=login_params)
        if not response or not response.text:
            log.warning('Unable to connect to provider')
            return False

        if '<title>Login :: TorrentLeech.org</title>' in response.text:
            log.warning('Invalid username or password. Check your settings')
            return False

        return True


provider = TorrentLeechProvider()
