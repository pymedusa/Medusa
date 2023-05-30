# coding=utf-8

"""Provider code for TheOldSchool."""

from __future__ import division, unicode_literals

import logging

from medusa import tv
from medusa.helper.common import convert_size
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.compat import urljoin

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class TheOldSchoolProvider(TorrentProvider):
    """TheOldSchool Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(TheOldSchoolProvider, self).__init__('TheOldSchool')

        # Credentials
        self.api_key = None

        # URLs
        self.url = 'https://theoldschool.cc'
        self.urls = {
            'search': urljoin(self.url, 'api/torrents/filter'),
        }

        # Proper Strings
        self.proper_strings = ['PROPER', 'REPACK', 'REAL', 'RERIP']

        # Miscellaneous Options
        self.freeleech = False

        # Cache
        self.cache = tv.Cache(self, min_time=30)

    def search(self, search_strings, age=0, ep_obj=None, **kwargs):
        """
        Search a provider and parse the results.

        :param search_strings: A dict with mode (key) and
            the search value (value)
        :param age: Not used
        :param ep_obj: Not used
        :returns: A list of search results (structure)
        """
        results = []

        # Search Params
        search_params = {
            'api_token': self.api_key,
            'categories[0]': 2,  # episodes
            'categories[1]': 7,  # episodes VOST
            'categories[2]': 8,  # packs
            'categories[3]': 9,  # packs VOST
        }
        if self.freeleech:
            search_params['free[0]'] = 100

        for mode in search_strings:
            log.debug('Search Mode: {0}', mode)
            for search_string in search_strings[mode]:
                if mode != 'RSS':
                    log.debug('Search string: {0}', search_string.strip())
                    search_params['name'] = search_string

                response = self.session.get(
                    self.urls['search'],
                    params=search_params
                )
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

                if data['meta']['total'] == 0:
                    log.debug('No data returned from provider')
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

        torrent_rows = data.pop('data')

        for row in torrent_rows:
            if row['type'] == 'torrent':
                try:
                    title = row.get('attributes').get('name')
                    download_url = row.get('attributes').get('download_link')
                    if not all([title, download_url]):
                        continue

                    seeders = int(row.get('attributes').get('seeders'))
                    leechers = int(row.get('attributes').get('leechers'))

                    # Filter unseeded torrent
                    if seeders < self.minseed:
                        if mode != 'RSS':
                            log.debug(
                                "Discarding torrent because it doesn't meet"
                                ' the minimum seeders: {0}. Seeders: {1}',
                                title, seeders
                            )
                        continue

                    freeleech = row.get('attributes').get('freeleech')
                    if self.freeleech and freeleech != '100%':
                        continue

                    size = convert_size(
                        row.get('attributes').get('size'), default=-1
                    )

                    pubdate_raw = row.get('attributes').get('created_at')
                    pubdate = self.parse_pubdate(
                        pubdate_raw, timezone='Europe/Paris'
                    )

                    item = {
                        'title': title,
                        'link': download_url,
                        'size': size,
                        'seeders': seeders,
                        'leechers': leechers,
                        'pubdate': pubdate,
                    }

                    if mode != 'RSS':
                        log.debug(
                            'Found result: {0} with {1} seeders and'
                            ' {2} leechers', title, seeders, leechers
                        )

                    items.append(item)
                except (AttributeError, TypeError, KeyError, ValueError, IndexError):
                    log.exception('Failed parsing provider.')

        return items


provider = TheOldSchoolProvider()
