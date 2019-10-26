# coding=utf-8

"""Provider code for TokyoToshokan."""

from __future__ import unicode_literals

import logging
import re
from builtins import zip

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


class TokyoToshokanProvider(TorrentProvider):
    """TokyoToshokan Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(TokyoToshokanProvider, self).__init__('TokyoToshokan')

        # Credentials
        self.public = True

        # URLs
        self.url = 'http://tokyotosho.info/'
        self.urls = {
            'search': urljoin(self.url, 'search.php'),
            'rss': urljoin(self.url, 'rss.php'),
        }

        # Proper Strings

        # Miscellaneous Options
        self.supports_absolute_numbering = True
        self.anime_only = True

        # Cache
        self.cache = tv.Cache(self, min_time=15)  # only poll TokyoToshokan every 15 minutes max

    def search(self, search_strings, age=0, ep_obj=None, **kwargs):
        """
        Search a provider and parse the results.

        :param search_strings: A dict with mode (key) and the search value (value)
        :param age: Not used
        :param ep_obj: Not used
        :returns: A list of search results (structure)
        """
        results = []

        # Search Params
        search_params = {
            'type': 1,  # get anime types
        }

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {search}',
                              {'search': search_string})

                search_params['terms'] = search_string
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

        with BS4Parser(data, 'html5lib') as soup:
            torrent_table = soup.find('table', class_='listing')
            torrent_rows = torrent_table('tr') if torrent_table else []

            # Continue only if at least one release is found
            if len(torrent_rows) < 2:
                log.debug('Data returned from provider does not contain any torrents')
                return items

            a = 1 if len(torrent_rows[0]('td')) < 2 else 0

            # Skip column headers
            for top, bot in zip(torrent_rows[a::2], torrent_rows[a + 1::2]):
                try:
                    desc_top = top.find('td', class_='desc-top')
                    title = desc_top.get_text(strip=True) if desc_top else None
                    download_url = desc_top.find('a')['href'] if desc_top else None
                    if not all([title, download_url]):
                        continue

                    stats = bot.find('td', class_='stats').get_text(strip=True)
                    sl = re.match(r'S:(?P<seeders>\d+)L:(?P<leechers>\d+)C:(?:\d+)ID:(?:\d+)', stats.replace(' ', ''))
                    seeders = try_int(sl.group('seeders')) if sl else 0
                    leechers = try_int(sl.group('leechers')) if sl else 0

                    # Filter unseeded torrent
                    if seeders < self.minseed:
                        if mode != 'RSS':
                            log.debug("Discarding torrent because it doesn't meet the"
                                      ' minimum seeders: {0}. Seeders: {1}',
                                      title, seeders)
                        continue

                    desc_bottom = bot.find('td', class_='desc-bot').get_text(strip=True)
                    size = convert_size(desc_bottom.split('|')[1].strip('Size: ')) or -1

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


provider = TokyoToshokanProvider()
