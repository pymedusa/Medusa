# coding=utf-8

"""Provider code for TorrentDay."""

from __future__ import unicode_literals

import logging
import re

import dirtyjson as djson

from medusa import tv
from medusa.helper.common import convert_size
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.compat import urljoin

import validators

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class TorrentDayProvider(TorrentProvider):
    """TorrentDay Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(TorrentDayProvider, self).__init__('TorrentDay')

        # URLs
        self.url = 'https://www.torrentday.com'
        self.custom_url = None

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

        self.categories = {
            'Season': {'14': 1},
            'Episode': {'2': 1, '26': 1, '7': 1, '24': 1, '34': 1},
            'RSS': {'2': 1, '26': 1, '7': 1, '24': 1, '34': 1, '14': 1}
        }

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

        if self.custom_url:
            if not validators.url(self.custom_url):
                log.warning('Invalid custom url: {0}', self.custom_url)
                return results
            self.url = self.custom_url

        self.urls = {
            'login': urljoin(self.url, '/torrents/'),
            'search': urljoin(self.url, '/t.json'),
            'download': urljoin(self.url, '/download.php/')
        }

        if not self.login():
            return results

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            for search_string in search_strings[mode]:
                if mode != 'RSS':
                    log.debug('Search string: {search}',
                              {'search': search_string})

                search_string = '+'.join(search_string.split())

                params = dict({'q': search_string}, **self.categories[mode])

                response = self.session.get(self.urls['search'], params=params)
                if not response or not response.text:
                    log.debug('No data returned from provider')
                    continue

                try:
                    jdata = djson.loads(response.text)
                except ValueError as error:
                    log.error("Couldn't deserialize JSON document. Error: {0!r}", error)
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

        for row in data:

            try:
                # Check if this is a freeleech torrent and if we've configured to only allow freeleech.
                if self.freeleech and row.get('download-multiplier') != 0:
                    continue

                title = re.sub(r'\[.*\=.*\].*\[/.*\]', '', row['name']) if row['name'] else None
                download_url = urljoin(self.urls['download'], '{0}/{1}.torrent'.format(
                    row['t'], row['name']
                )) if row['t'] and row['name'] else None

                if not all([title, download_url]):
                    continue

                seeders = int(row['seeders'])
                leechers = int(row['leechers'])

                # Filter unseeded torrent
                if seeders < self.minseed:
                    if mode != 'RSS':
                        log.debug("Discarding torrent because it doesn't meet the"
                                  ' minimum seeders: {0}. Seeders: {1}',
                                  title, seeders)
                    continue

                torrent_size = row['size']
                size = convert_size(torrent_size) or -1

                if mode != 'RSS':
                    log.debug('Found result: {0} with {1} seeders and {2} leechers',
                              title, seeders, leechers)

                pubdate_raw = row['ctime']
                pubdate = self.parse_pubdate(pubdate_raw, fromtimestamp=True)

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
