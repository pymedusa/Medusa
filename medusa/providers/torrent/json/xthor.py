# coding=utf-8

"""Provider code for Xthor."""

from __future__ import unicode_literals

import logging
from time import sleep

from medusa import tv
from medusa.helper.common import convert_size
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.torrent.torrent_provider import TorrentProvider

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class XthorProvider(TorrentProvider):
    """Xthor Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(XthorProvider, self).__init__('Xthor')

        # Credentials
        self.passkey = None

        # URLs
        self.url = 'https://xthor.tk'
        self.urls = {
            'search': 'https://api.xthor.tk',
        }

        # Proper Strings

        # Miscellaneous Options
        self.subcategories = [433, 637, 455, 639]

        # Torrent Stats
        self.confirmed = False
        self.freeleech = False

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
        if not self._check_auth:
            return results

        # Search Params
        search_params = {
            'passkey': self.passkey
        }
        if self.freeleech:
            search_params['freeleech'] = 1

        for mode in search_strings:
            log.debug('Search Mode: {0}', mode)
            for search_string in search_strings[mode]:
                if mode != 'RSS':
                    log.debug('Search string: {0}', search_string.strip())
                    search_params['search'] = search_string
                else:
                    search_params.pop('search', '')

                data = self.session.get(self.urls['search'], params=search_params)
                sleep(2)  # Limit to 1 request every 2 seconds.
                if not data:
                    log.debug('No data returned from provider')
                    continue

                try:
                    jdata = data.json()
                except ValueError as e:
                    log.warning(
                        u'Could not decode the response as json for the result, searching {provider} with error {err_msg}',
                        provider=self.name,
                        err_msg=e
                    )
                    continue

                error_code = jdata.pop('error', {})
                if error_code.get('code'):
                    if error_code.get('code') != 2:
                        log.warning('{0}', error_code.get('descr', 'Error code 2 - no description available'))
                        return results
                    continue

                account_ok = jdata.pop('user', {}).get('can_leech')
                if not account_ok:
                    log.warning('Sorry, your account is not allowed to download, check your ratio')
                    return results

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
        torrent_rows = data.pop('torrents', {})

        if not torrent_rows:
            log.debug('Provider has no results for this search')
            return items

        for row in torrent_rows:
            try:
                title = row.get('name')
                download_url = row.get('download_link')
                if not all([title, download_url]):
                    continue

                seeders = int(row.get('seeders'))
                leechers = int(row.get('leechers'))

                # Filter unseeded torrent
                if seeders < self.minseed:
                    if mode != 'RSS':
                        log.debug("Discarding torrent because it doesn't meet the"
                                  ' minimum seeders: {0}. Seeders: {1}',
                                  title, seeders)
                    continue

                size = convert_size(row.get('size'), default=-1)

                item = {
                    'title': title,
                    'link': download_url,
                    'size': size,
                    'seeders': seeders,
                    'leechers': leechers,
                    'hash': '',
                }
                if mode != 'RSS':
                    log.debug('Found result: {0} with {1} seeders and {2} leechers',
                              title, seeders, leechers)

                items.append(item)
            except (AttributeError, TypeError, KeyError, ValueError, IndexError):
                log.exception('Failed parsing provider.')

        return items


provider = XthorProvider()
