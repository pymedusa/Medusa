# coding=utf-8

"""Provider code for TPB."""

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

import validators

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class ThePirateBayProvider(TorrentProvider):
    """ThePirateBay Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(ThePirateBayProvider, self).__init__('ThePirateBay')

        # Credentials
        self.public = True

        # URLs
        self.url = 'https://thepiratebay.org'
        self.custom_url = None

        # Proper Strings

        # Miscellaneous Options
        self.confirmed = True

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

        if self.custom_url:
            if not validators.url(self.custom_url):
                log.warning('Invalid custom url: {0}', self.custom_url)
                return results
            self.url = self.custom_url

        self.urls = {
            'rss': urljoin(self.url, 'tv/latest'),
            'search': urljoin(self.url, 'search/{string}/0/3/200'),
        }

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            for search_string in search_strings[mode]:

                search_url = self.urls['search'] if mode != 'RSS' else self.urls['rss']

                if mode != 'RSS':
                    search_url = search_url.format(string=search_string)
                    log.debug('Search string: {search}',
                              {'search': search_string})
                    if self.confirmed:
                        log.debug('Searching only confirmed torrents')

                response = self.session.get(search_url)
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
        units = ['B', 'KIB', 'MIB', 'GIB', 'TIB', 'PIB']

        def process_column_header(th):
            result = ''
            if th.a:
                result = th.a.get_text(strip=True)
            if not result:
                result = th.get_text(strip=True)
            return result

        items = []

        with BS4Parser(data, 'html5lib') as html:
            torrent_table = html.find('table', id='searchResult')
            torrent_rows = torrent_table('tr') if torrent_table else []

            # Continue only if at least one release is found
            if len(torrent_rows) < 2:
                log.debug('Data returned from provider does not contain any {0}torrents',
                          'confirmed ' if self.confirmed else '')
                return items

            labels = [process_column_header(label) for label in torrent_rows[0]('th')]

            # Skip column headers
            for row in torrent_rows[1:]:
                cells = row('td')
                if len(cells) < len(labels):
                    continue

                try:
                    title = row.find(class_='detName')
                    title = title.get_text(strip=True) if title else None
                    download_url = row.find(title='Download this torrent using magnet')
                    download_url = download_url['href'] + self._custom_trackers if download_url else None
                    if download_url and 'magnet:?' not in download_url:
                        log.debug('Invalid ThePirateBay proxy please try another one')
                        continue
                    if not all([title, download_url]):
                        continue

                    seeders = try_int(cells[labels.index('SE')].get_text(strip=True), 1)
                    leechers = try_int(cells[labels.index('LE')].get_text(strip=True))

                    # Filter unseeded torrent
                    if seeders < self.minseed:
                        if mode != 'RSS':
                            log.debug("Discarding torrent because it doesn't meet the"
                                      ' minimum seeders: {0}. Seeders: {1}',
                                      title, seeders)
                        continue

                    # Accept Torrent only from Good People for every Episode Search
                    if self.confirmed and not row.find(alt=re.compile(r'VIP|Trusted')):
                        if mode != 'RSS':
                            log.debug("Found result {0} but that doesn't seem like a trusted"
                                      " result so I'm ignoring it", title)
                        continue

                    # Convert size after all possible skip scenarios
                    torrent_size = cells[labels.index('Name')].find(class_='detDesc')
                    torrent_size = torrent_size.get_text(strip=True).split(', ')[1]
                    torrent_size = re.sub(r'Size ([\d.]+).+([KMGT]iB)', r'\1 \2', torrent_size)
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


provider = ThePirateBayProvider()
