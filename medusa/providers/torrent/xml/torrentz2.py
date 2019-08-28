# coding=utf-8

"""Provider code for Torrentz2."""

from __future__ import unicode_literals

import logging
import re

from medusa import tv
from medusa.bs4_parser import BS4Parser
from medusa.helper.common import convert_size
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.compat import urljoin

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class Torrentz2Provider(TorrentProvider):
    """Torrentz2 Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(Torrentz2Provider, self).__init__('Torrentz2')

        # Credentials
        self.public = True

        # URLs
        self.url = 'https://torrentz2.eu/'
        self.urls = {
            'base': self.url,
            'verified': urljoin(self.url, 'feed_verified'),
            'feed': urljoin(self.url, 'feed'),
        }

        # Proper Strings

        # Miscellaneous Options
        # self.confirmed = True

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

        # Search Params
        search_params = {
            'f': 'tv added:2d',
        }

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            for search_string in search_strings[mode]:
                if mode != 'RSS':
                    log.debug('Search string: {search}',
                              {'search': search_string})
                    search_params['f'] = search_string

                # search_url = self.urls['verified'] if self.confirmed else self.urls['feed']
                search_url = self.urls['feed']
                response = self.session.get(search_url, params=search_params)
                if not response or not response.text:
                    log.debug('No data returned from provider')
                    continue
                elif not response.text.startswith('<?xml'):
                    log.info('Expected xml but got something else, is your mirror failing?')
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
            torrent_rows = html('item')

            for row in torrent_rows:
                try:
                    if row.category and 'video' not in row.category.get_text(strip=True).lower():
                        continue

                    title_raw = row.title.text
                    # Add "-" after codec and add missing "."
                    title = re.sub(r'([xh][ .]?264|xvid)( )', r'\1-', title_raw).replace(' ', '.') if title_raw else ''
                    info_hash = row.guid.text.rsplit('/', 1)[-1]
                    download_url = 'magnet:?xt=urn:btih:' + info_hash + '&dn=' + title + self._custom_trackers
                    if not all([title, download_url]):
                        continue

                    torrent_size, seeders, leechers = self._split_description(row.find('description').text)
                    size = convert_size(torrent_size) or -1

                    pubdate_raw = row.pubdate.get_text()
                    pubdate = self.parse_pubdate(pubdate_raw)

                    # Filter unseeded torrent
                    if seeders < self.minseed:
                        if mode != 'RSS':
                            log.debug("Discarding torrent because it doesn't meet the"
                                      ' minimum seeders: {0}. Seeders: {1}',
                                      title, seeders)
                        continue

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

    @staticmethod
    def _split_description(description):
        match = re.findall(r'(\d+|\d+ \w+)(?= \w+:)', description)
        return match[0], int(match[1]), int(match[2])


provider = Torrentz2Provider()
