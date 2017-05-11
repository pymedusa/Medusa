# coding=utf-8

"""Provider code for TorrentProject."""

from __future__ import unicode_literals

import logging
import traceback

from medusa import tv
from medusa.bs4_parser import BS4Parser
from medusa.common import USER_AGENT
from medusa.helper.common import (
    convert_size,
    try_int,
)
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.torrent.torrent_provider import TorrentProvider

import validators

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class TorrentProjectProvider(TorrentProvider):
    """TorrentProject Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(self.__class__, self).__init__('TorrentProject')

        # Credentials
        self.public = True

        # URLs
        self.url = 'https://torrentproject.se'
        self.custom_url = None

        # Proper Strings

        # Miscellaneous Options
        self.headers.update({'User-Agent': USER_AGENT})

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tv.Cache(self, min_time=20)

    def search(self, search_strings, age=0, ep_obj=None):
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
            search_url = self.custom_url
        else:
            search_url = self.url

        search_params = {
            'hl': 'en',
            'num': 40,
            'start': 0,
            'filter': 2101,
            'safe': 'on',
            'orderby': 'latest',
            's': '',
        }

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            for search_string in search_strings[mode]:
                if mode != 'RSS':
                    search_params['s'] = search_string
                    log.debug('Search string: {search}',
                              {'search': search_string})

                response = self.get_url(search_url, params=search_params, returns='response')
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
            torrent_rows = html.find_all('div', class_='torrent')

            # Continue only if at least one release is found
            if not torrent_rows:
                log.debug('Data returned from provider does not contain any torrents')
                return items

            for row in torrent_rows:
                anchor = row.find('a')

                try:
                    # Removes ' torrent' in the end
                    title = anchor.get('title')[:-8]
                    download_url = anchor.get('href')
                    if not all([title, download_url]):
                        continue

                    info_hash = download_url.split('/')[1]
                    download_url = 'magnet:?xt=urn:btih:{hash}&dn={title}{trackers}'.format(
                        hash=info_hash, title=title, trackers=self._custom_trackers)

                    seeders = try_int(row.find('span', class_='bc seeders').find('span').get_text(), 1)
                    leechers = try_int(row.find('span', class_='bc leechers').find('span').get_text())

                    # Filter unseeded torrent
                    if seeders < min(self.minseed, 1):
                        if mode != 'RSS':
                            log.debug("Discarding torrent because it doesn't meet the"
                                      " minimum seeders: {0}. Seeders: {1}",
                                      title, seeders)
                        continue

                    torrent_size = row.find('span', class_='bc torrent-size').get_text().rstrip()
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


provider = TorrentProjectProvider()
