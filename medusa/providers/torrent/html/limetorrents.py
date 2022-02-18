# coding=utf-8

"""Provider code for Limetorrents."""

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

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())

id_regex = re.compile(r'(?:\/)(.*)(?:-torrent-([0-9]*)\.html)', re.I)
hash_regex = re.compile(r'(.*)([0-9a-f]{40})(.*)', re.I)


class LimeTorrentsProvider(TorrentProvider):
    """LimeTorrents Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(LimeTorrentsProvider, self).__init__('LimeTorrents')

        # Credentials
        self.public = True

        # URLs
        self.url = 'https://www.limetorrents.info'
        self.urls = {
            'update': urljoin(self.url, '/post/updatestats.php'),
            'search': urljoin(self.url, '/search/tv/{query}/'),
            # Original rss feed url, temporary offline. Replaced by the main Tv-show page.
            # 'rss': urljoin(self.url, '/browse-torrents/TV-shows/date/{page}/'),
            'rss': urljoin(self.url, '/browse-torrents/TV-shows/'),
        }

        # Proper Strings
        self.proper_strings = ['PROPER', 'REPACK', 'REAL']

        # Miscellaneous Options
        self.confirmed = False

        # Cache
        self.cache = tv.Cache(self, min_time=15)

    def search(self, search_strings, age=0, ep_obj=None, **kwargs):
        """
        Search a provider and parse the results.

        :param search_strings: A dict with mode (key) and the search value (value)
        :param age: Not used
        :param ep_obj: Not used
        :returns: A list of search results (structure)
        """
        results = []

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {search}',
                              {'search': search_string})
                    if self.confirmed:
                        log.debug('Searching only confirmed torrents')

                    search_url = self.urls['search'].format(query=search_string)
                else:
                    # search_url = self.urls['rss'].format(page=1)
                    search_url = self.urls['rss']

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
        items = []

        def process_column_header(th):
            return th.span.get_text() if th.span else th.get_text()

        with BS4Parser(data, 'html5lib') as html:
            torrent_table = html.find('table', class_='table2')

            if not torrent_table:
                log.debug('Data returned from provider does not contain any {0}torrents',
                          'confirmed ' if self.confirmed else '')
                return items

            torrent_rows = torrent_table.find_all('tr')
            labels = [process_column_header(label) for label in torrent_rows[0].find_all('th')]

            # Skip the first row, since it isn't a valid result
            for row in torrent_rows[1:]:
                cells = row.find_all('td')

                try:
                    title_cell = cells[labels.index('Torrent Name')]

                    verified = title_cell.find('img', title='Verified torrent')
                    if self.confirmed and not verified:
                        continue

                    title_anchors = title_cell.find_all('a')
                    if not title_anchors or len(title_anchors) < 2:
                        continue

                    title_url = title_anchors[0].get('href')
                    title = title_anchors[1].get_text(strip=True)
                    regex_result = id_regex.search(title_anchors[1].get('href'))

                    alt_title = regex_result.group(1)
                    if len(title) < len(alt_title):
                        title = alt_title.replace('-', ' ')

                    info_hash = hash_regex.search(title_url).group(2)
                    if not all([title, info_hash]):
                        continue

                    download_url = 'magnet:?xt=urn:btih:{hash}&dn={title}{trackers}'.format(
                        hash=info_hash, title=title, trackers=self._custom_trackers)

                    # Remove comma as thousands separator from larger number like 2,000 seeders = 2000
                    seeders = try_int(cells[labels.index('Seed')].get_text(strip=True).replace(',', ''))
                    leechers = try_int(cells[labels.index('Leech')].get_text(strip=True).replace(',', ''))

                    if seeders < self.minseed:
                        if mode != 'RSS':
                            log.debug("Discarding torrent because it doesn't meet the"
                                      ' minimum seeders: {0}. Seeders: {1}',
                                      title, seeders)
                        continue

                    size = convert_size(cells[labels.index('Size')].get_text(strip=True)) or -1

                    pubdate_raw = cells[1].get_text().replace('Last', '1').replace('Yesterday', '24 hours')
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


provider = LimeTorrentsProvider()
