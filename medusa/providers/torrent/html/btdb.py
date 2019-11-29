# coding=utf-8

"""Provider code for BTDB."""

from __future__ import unicode_literals

import logging
from collections import OrderedDict

from medusa import tv
from medusa.bs4_parser import BS4Parser
from medusa.helper.common import convert_size
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.compat import urljoin

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class BTDBProvider(TorrentProvider):
    """BTDB Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(BTDBProvider, self).__init__('BTDB')

        # Credentials
        self.public = True

        # URLs
        self.url = 'https://btdb.eu'
        self.urls = {
            'daily': urljoin(self.url, 'recent'),
        }

        # Miscellaneous Options

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

        # Search Params
        search_params = OrderedDict()

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            for search_string in search_strings[mode]:
                search_url = self.urls['daily']

                if mode != 'RSS':
                    search_url = self.url

                    search_params['s'] = search_string
                    search_params['sort'] = 'popular'

                    log.debug('Search string: {search}',
                              {'search': search_string})
                else:
                    search_params['category'] = 'show'

                response = self.session.get(search_url, params=search_params)
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
            cls_name = 'search-ret' if mode != 'RSS' else 'recent'
            table_body = html.find('div', class_=cls_name)
            torrent_rows = table_body.find_all(
                'li', class_='{0}-item'.format(cls_name)
            ) if table_body else []

            # Continue only if at least one release is found
            if not table_body:
                log.debug('Data returned from provider does not contain any torrents')
                return items

            for row in torrent_rows:
                try:

                    title = row.h2.find('a').get('title')
                    download_url = row.div.find('a').get('href')
                    if not all([title, download_url]):
                        continue

                    download_url += self._custom_trackers

                    spans = row.find('div').find_all('span')

                    seeders = int(spans[3].get_text().replace(',', ''))
                    leechers = int(spans[4].get_text().replace(',', ''))

                    torrent_size = spans[0].get_text()
                    size = convert_size(torrent_size, default=-1)

                    pubdate_raw = spans[2].get_text()
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


provider = BTDBProvider()
