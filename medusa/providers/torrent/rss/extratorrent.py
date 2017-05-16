# coding=utf-8

"""Provider code for ExtraTorrent."""

from __future__ import unicode_literals

import logging
import traceback

from medusa import (
    app,
    tv,
)
from medusa.bs4_parser import BS4Parser
from medusa.helper.common import (
    convert_size,
    try_int,
)
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.compat import urljoin

import validators

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class ExtraTorrentProvider(TorrentProvider):
    """ExtraTorrent Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(ExtraTorrentProvider, self).__init__('ExtraTorrent')

        # Credentials
        self.public = True

        # URLs
        self.url = 'http://extra.to'
        self.custom_url = None

        # Proper Strings
        self.proper_strings = ['PROPER', 'REPACK', 'REAL']

        # Miscellaneous Options

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
                log.warning('Invalid custom URL: {0}', self.custom_url)
                return results
            self.url = self.custom_url

        self.urls = {
            'rss': urljoin(self.url, 'rss.xml'),
        }

        # Search Params
        search_params = {
            'cid': 8,  # Category: TV
            'type': 'today',
        }

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    search_params['type'] = 'search'
                    search_params['search'] = search_string
                    log.debug('Search string: {search}', {'search': search_string})

                response = self.get_url(self.urls['rss'], params=search_params, returns='response')
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

        with BS4Parser(data, 'html.parser') as xml:

            elements = xml.find_all('item')
            if not elements:
                log.debug('Data returned from provider does not contain any torrents')
                return items

            for element in elements:
                try:
                    title = element.title.get_text()
                    download_url = element.magneturi.get_text()
                    if not all([title, download_url]):
                        continue

                    # Add custom trackers to the magnet link
                    download_url += self._custom_trackers

                    # Use the torrent link extratorrent provides when the client
                    # is set to "blackhole", to avoid relying on 3rd parties for
                    # torrents. We want to use magnets instead if connecting
                    # directly to clients so that proxies work.
                    if app.TORRENT_METHOD == 'blackhole':
                        download_url = element.enclosure.get('url')

                    seeders = try_int(element.seeders.get_text())
                    leechers = try_int(element.leechers.get_text())

                    # Filter unseeded torrent
                    if seeders < min(self.minseed, 1):
                        if mode != 'RSS':
                            log.debug("Discarding torrent because it doesn't meet the"
                                      " minimum seeders: {0}. Seeders: {1}", title, seeders)
                        continue

                    size = convert_size(element.size.get_text()) or -1

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
                    continue

        return items


provider = ExtraTorrentProvider()
