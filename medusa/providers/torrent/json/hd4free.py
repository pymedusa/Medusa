# coding=utf-8

"""Provider code for HD4Free."""

from __future__ import unicode_literals

import logging
import traceback

from medusa import tv
from medusa.helper.common import convert_size
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.compat import urljoin

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class HD4FreeProvider(TorrentProvider):
    """HD4Free Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(HD4FreeProvider, self).__init__('HD4Free')

        # Credentials
        self.username = None
        self.api_key = None

        # URLs
        self.url = 'https://hd4free.xyz'
        self.urls = {
            'search': urljoin(self.url, '/searchapi.php'),
        }

        # Proper Strings

        # Miscellaneous Options
        self.freeleech = None

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tv.Cache(self, min_time=10)  # Only poll HD4Free every 10 minutes max

    def search(self, search_strings, age=0, ep_obj=None):
        """
        Search a provider and parse the results.

        :param search_strings: A dict with mode (key) and the search value (value)
        :param age: Not used
        :param ep_obj: Not used
        :returns: A list of search results (structure)
        """
        results = []
        if not self._check_auth:
            return results

        # Search Params
        search_params = {
            'tv': 'true',
            'username': self.username,
            'apikey': self.api_key,
            'fl': 'true' if self.freeleech else None
        }

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {search}',
                              {'search': search_string})
                    search_params['search'] = search_string
                else:
                    search_params['search'] = None

                response = self.get_url(self.urls['search'], params=search_params, returns='response')
                if not response or not response.content:
                    log.debug('No data returned from provider')
                    continue

                try:
                    jdata = response.json()
                except ValueError:
                    log.debug('No data returned from provider')
                    continue

                error_message = jdata.get('error')
                if error_message:
                    log.debug('HD4Free returned an error: {0}', error_message)
                    return results
                try:
                    if jdata['0']['total_results'] == 0:
                        log.debug('Provider has no results for this search')
                        continue
                except KeyError:
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

        torrent_rows = data

        for row in torrent_rows:
            try:
                title = torrent_rows[row]['release_name']
                download_url = torrent_rows[row]['download_url']
                if not all([title, download_url]):
                    continue

                seeders = torrent_rows[row]['seeders']
                leechers = torrent_rows[row]['leechers']

                # Filter unseeded torrent
                if seeders < min(self.minseed, 1):
                    if mode != 'RSS':
                        log.debug("Discarding torrent because it doesn't meet the"
                                  " minimum seeders: {0}. Seeders: {1}",
                                  title, seeders)
                    continue

                torrent_size = str(torrent_rows[row]['size']) + ' MB'
                size = convert_size(torrent_size) or -1

                pubdate_raw = torrent_rows[row]['added']
                pubdate = self._parse_pubdate(pubdate_raw)

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

    def _check_auth(self):
        if self.username and self.api_key:
            return True

        log.warning('Your authentication credentials for {provider} are missing,'
                    ' check your config.', {'provider': self.name})
        return False


provider = HD4FreeProvider()
