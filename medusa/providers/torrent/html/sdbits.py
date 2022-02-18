# coding=utf-8

"""Provider code for SDBits."""

from __future__ import unicode_literals

import logging
import re

from medusa import tv
from medusa.bs4_parser import BS4Parser
from medusa.helper.common import (
    convert_size,
    try_int,
)
from medusa.indexers.utils import mappings
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.compat import urljoin
from requests.utils import dict_from_cookiejar

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class SDBitsProvider(TorrentProvider):
    """SDBits Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(SDBitsProvider, self).__init__('SDBits')

        # Credentials
        self.username = None
        self.password = None

        # URLs
        self.url = 'http://sdbits.org'
        self.urls = {
            'login': urljoin(self.url, 'takeloginn3.php'),
            'search': urljoin(self.url, 'browse.php'),
        }

        # Proper Strings
        self.proper_strings = []

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
            'incldead': 0,
            'descriptions': 0,
            'from': '',
            'imdbgt': 0,
            'imdblt': 10,
            'imdb': '',
            'search': '',
        }

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    imdb_id = self.series.externals.get(mappings[10])
                    if imdb_id:
                        search_params['imdb'] = imdb_id
                        log.debug('Search string (IMDb ID): {imdb_id}',
                                  {'imdb_id': imdb_id})
                    else:
                        search_params['search'] = search_string
                        log.debug('Search string: {search}',
                                  {'search': search_string})

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
        items = []

        with BS4Parser(data, 'html5lib') as html:
            torrent_table = html.find('table', id='torrent-list')
            torrent_rows = torrent_table('tr') if torrent_table else []

            # Continue only if at least one release is found
            if len(torrent_rows) < 2:
                log.debug('Data returned from provider does not contain any torrents')
                return items

            # Skip column headers
            for row in torrent_rows[1:]:
                cells = row('td')

                try:
                    torrent_info = cells[2].find_all('a')
                    title = torrent_info[0].get_text()
                    download = torrent_info[1]['href']
                    download_url = urljoin(self.url, download)
                    if not all([title, download_url]):
                        continue

                    seeders = try_int(cells[7].get_text(strip=True), 1)
                    leechers = try_int(cells[8].get_text(strip=True))

                    # Filter unseeded torrent
                    if seeders < self.minseed:
                        if mode != 'RSS':
                            log.debug("Discarding torrent because it doesn't meet the"
                                      ' minimum seeders: {0}. Seeders: {1}',
                                      title, seeders)
                        continue

                    torrent_size = cells[5].get_text(' ')
                    size = convert_size(torrent_size) or -1

                    pubdate_raw = cells[4].get_text(' ')
                    pubdate = self.parse_pubdate(pubdate_raw, human_time=True)

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
        if any(dict_from_cookiejar(self.session.cookies).values()):
            return True

        login_params = {
            'uname': self.username,
            'password': self.password,
            'Log in!': 'submit',
            'returnto': '/',
        }

        response = self.session.post(self.urls['login'], data=login_params)
        if not response or not response.text:
            log.warning('Unable to connect to provider')
            return False

        if re.search('Username or password incorrect.', response.text):
            log.warning('Invalid username or password. Check your settings')
            return False

        return True


provider = SDBitsProvider()
