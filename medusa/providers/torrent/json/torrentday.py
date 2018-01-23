# coding=utf-8

"""Provider code for TorrentDay."""

from __future__ import unicode_literals

import logging

from medusa import tv
from medusa.bs4_parser import BS4Parser, BeautifulSoup
from medusa.helper.common import convert_size, try_int
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.compat import urljoin

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class TorrentDayProvider(TorrentProvider):
    """TorrentDay Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(TorrentDayProvider, self).__init__('TorrentDay')

        # URLs
        self.url = 'https://www.torrentday.com'
        self.urls = {
            'login': urljoin(self.url, '/torrents/'),
            'search': urljoin(self.url, '/t'),
            'download': urljoin(self.url, '/download.php/')
        }

        # Proper Strings

        # Miscellaneous Options
        self.freeleech = False
        self.enable_cookies = True
        self.cookies = ''
        self.required_cookies = ('uid', 'pass')

        # TV/480p - 24
        # TV/Bluray - 32
        # TV/DVD-R - 31
        # TV/DVD-Rip - 33
        # TV/Mobile - 46
        # TV/Packs - 14
        # TV/SD/x264 - 26
        # TV/x264 - 7
        # TV/x265 - 34
        # TV/XviD - 2
        # TV-all `-8`

        self.categories = {'Season': {'c14': 1}, 'Episode': {'c2': 1, 'c7': 1, 'c24': 1, 'c26': 1, 'c31': 1, 'c32': 1, 'c33': 1, 'c34': 1, 'c46': 1},
                           'RSS': {'c2': 1, 'c26': 1, 'c7': 1, 'c24': 1, 'c14': 1}}

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tv.Cache(self, min_time=10)  # Only poll IPTorrents every 10 minutes max

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

                    search_string = '+'.join(search_string.split())

                params = {
                    '24': '',
                    '32': '',
                    '31': '',
                    '33': '',
                    '46': '',
                    '26': '',
                    '7': '',
                    '34': '',
                    '2': ''
                }

                if self.freeleech:
                    params.update({'free': 'on'})

                if search_string:
                    params.update({'q': search_string})

                response = self.session.get(self.urls['search'], params=params)
                if not response or not response.text:
                    log.debug('No data returned from provider')
                    continue

                try:
                    data = response.text
                except ValueError:
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

        def process_column_header(td):
            result = ''
            if td.a:
                result = td.a.get('title')
            if not result:
                result = td.get_text(strip=True) or 'Size'
            return result

        with BS4Parser(data, 'html.parser') as html:
            torrent_table = html.find('table', {'id': 'torrentTable'})
            torrent_rows = torrent_table('tr') if torrent_table else []

            # Continue only if at least one release is found
            if len(torrent_rows) < 2:
                log.debug('Data returned from provider does not contain any torrents')
                return items

            labels = [process_column_header(label) for label in torrent_rows[0]('th')]

            items = []
            # Skip column headers
            for row in torrent_rows[1:]:
                try:
                    name = row.find('td')[labels.index('Name')]
                    title = name.find('a').get_text(strip=True)
                    # details = name.find('a')['href']
                    download_url = row.find('td')[labels.index('Download')]
                    if not all([title, download_url]):
                        continue

                    seeders = try_int(row.find('td')[labels.index('Seeders')].get_text(strip=True))
                    leechers = try_int(row.find('td')[labels.index('Leechers')].get_text(strip=True))

                    # Filter unseeded torrent
                    if seeders < min(self.minseed, 1):
                        if mode != 'RSS':
                            log.debug("Discarding torrent because it doesn't meet the"
                                      " minimum seeders: {0}. Seeders: {1}",
                                      title, seeders)
                        continue

                    torrent_size = row('td')[labels.index('Size')].get_text()
                    size = convert_size(torrent_size) or -1

                    pubdate_raw = name.find('div').get_text(strip=True).split('|')[1].strip()
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
        return self.cookie_login('sign In')


provider = TorrentDayProvider()
