# coding=utf-8

"""Provider code for Danishbits."""

from __future__ import unicode_literals

import logging

from medusa import tv
from medusa.common import USER_AGENT
from medusa.helper.common import convert_size
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.compat import urljoin

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class DanishbitsProvider(TorrentProvider):
    """Danishbits Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(DanishbitsProvider, self).__init__('Danishbits')

        # Credentials
        self.username = None
        self.passkey = None

        # URLs
        self.url = 'https://danishbits.org'
        self.urls = {
            'search': urljoin(self.url, 'couchpotato.php'),
        }

        # Proper Strings
        self.proper_strings = ['PROPER', 'REPACK', 'REAL', 'RERIP']

        # Miscellaneous Options
        self.freeleech = True
        self.session.headers['User-Agent'] = USER_AGENT

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

        # Search Params
        search_params = {
            'user': self.username,
            'passkey': self.passkey,
            'search': '.',  # Dummy query for RSS search, needs the search param sent.
            'latest': 'true',
        }

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {search}',
                              {'search': search_string})
                    search_params['latest'] = 'false'
                    search_params['search'] = search_string

                response = self.session.get(self.urls['search'], params=search_params)
                if not response or not response.content:
                    log.debug('No data returned from provider')
                    continue

                try:
                    data = response.json()
                except ValueError as e:
                    log.warning(
                        'Could not decode the response as json for the result,'
                        ' searching {provider} with error {err_msg}',
                        provider=self.name,
                        err_msg=e
                    )
                    continue

                if 'error' in data:
                    log.warning('Provider returned an error: {0}', data['error'])
                    continue

                if data['total_results'] == 0:
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

        del data['total_results']
        torrent_rows = data['results']

        for row in torrent_rows:
            try:
                title = row.get('release_name')
                download_url = row.get('download_url')
                if not all([title, download_url]):
                    continue

                seeders = row.get('seeders')
                leechers = row.get('leechers')

                # Filter unseeded torrent
                if seeders < self.minseed:
                    if mode != 'RSS':
                        log.debug("Discarding torrent because it doesn't meet the"
                                  ' minimum seeders: {0}. Seeders: {1}',
                                  title, seeders)
                    continue

                freeleech = row.get('freeleech')
                if self.freeleech and not freeleech:
                    continue

                torrent_size = '{0} MB'.format(row.get('size', -1))
                size = convert_size(torrent_size) or -1

                pubdate_raw = row.get('publish_date')
                pubdate = self.parse_pubdate(pubdate_raw, timezone='Europe/Copenhagen')

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


provider = DanishbitsProvider()
