# coding=utf-8

"""Provider code for TorrentDay."""

from __future__ import unicode_literals

import logging
import re
import traceback

from medusa import tv
from medusa.helper.common import convert_size
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
            'search': urljoin(self.url, '/V3/API/API.php'),
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

                post_data = dict({'/browse.php?': None, 'cata': 'yes', 'jxt': 8, 'jxw': 'b', 'search': search_string},
                                 **self.categories[mode])

                if self.freeleech:
                    post_data.update({'free': 'on'})

                response = self.session.post(self.urls['search'], data=post_data)
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

        try:
            initial_data = data.get('Fs', [dict()])[0].get('Cn', {})
            torrent_rows = initial_data.get('torrents', []) if initial_data else None
        except (AttributeError, TypeError, KeyError, ValueError, IndexError) as error:
            # If TorrentDay changes their website issue will be opened so we can fix fast
            # and not wait user notice it's not downloading torrents from there
            log.error('TorrentDay response: {0}. Error: {1!r}', data, error)
            torrent_rows = None

        if not torrent_rows:
            log.debug('Data returned from provider does not contain any torrents')
            return items

        for row in torrent_rows:
            try:
                title = re.sub(r'\[.*=.*\].*\[/.*\]', '', row['name']) if row['name'] else None
                download_url = urljoin(self.urls['download'], '{}/{}'
                                       .format(row['id'], row['fname'])) if row['id'] and row['fname'] else None
                if not all([title, download_url]):
                    continue

                seeders = int(row['seed']) if row['seed'] else 1
                leechers = int(row['leech']) if row['leech'] else 0

                # Filter unseeded torrent
                if seeders < min(self.minseed, 1):
                    if mode != 'RSS':
                        log.debug("Discarding torrent because it doesn't meet the"
                                  " minimum seeders: {0}. Seeders: {1}",
                                  title, seeders)
                    continue

                torrent_size = row['size']
                size = convert_size(torrent_size) or -1

                pubdate_raw = row['added']
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
                log.error('Failed parsing provider. Traceback: {0!r}',
                          traceback.format_exc())

        return items

    def login(self):
        """Login method used for logging in before doing search and torrent downloads."""
        return self.cookie_login('sign In')


provider = TorrentDayProvider()
