# coding=utf-8

"""Provider code for HDBits."""

from __future__ import unicode_literals

import logging

from medusa import tv
from medusa.helper.common import convert_size
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.compat import urlencode, urljoin

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class HDBitsProvider(TorrentProvider):
    """HDBits Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(HDBitsProvider, self).__init__('HDBits')

        # Credentials
        self.username = None
        self.passkey = None

        # URLs
        self.url = 'https://hdbits.org'
        self.urls = {
            'search': urljoin(self.url, '/api/torrents'),
            'download': urljoin(self.url, '/download.php?{0}'),
        }

        # Proper Strings
        self.proper_strings = ['PROPER', 'REPACK']

        # Miscellaneous Options

        # Cache
        self.cache = tv.Cache(self)

    def search(self, search_strings, age=0, ep_obj=None, **kwargs):
        """
        Search a provider and parse the results.

        :param search_strings: A dict with {mode: search value}
        :param age: Not used
        :param ep_obj: Not used
        :returns: A list of search results (structure)
        """
        results = []

        if not self._check_auth():
            return results

        # Search Params
        search_params = {
            'username': self.username,
            'passkey': self.passkey,
            'category': [
                # 1,  # Movie
                2,  # TV
                3,  # Documentary
                # 4,  # Music
                5,  # Sport
                # 6,  # Audio Track
                # 7,  # XXX
                # 8,  # Misc/Demo
            ],
        }

        for mode in search_strings:
            log.debug('Search mode {0}', mode)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string {search}', {'search': search_string})
                    search_params['search'] = search_string

                response = self.session.post(self.urls['search'], json=search_params)
                if not response or not response.content:
                    log.debug('No data returned from provider')
                    continue

                if not self._check_auth_from_data(response):
                    return results

                try:
                    jdata = response.json()
                except ValueError:  # also catches JSONDecodeError if simplejson is installed
                    log.debug('No data returned from provider')
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

        torrent_rows = data.get('data')
        if not torrent_rows:
            log.debug('Data returned from provider does not contain any torrents')
            return items

        for row in torrent_rows:
            title = row.get('name', '')
            torrent_id = row.get('id', '')
            download_url = self.urls['download'].format(
                urlencode({'id': torrent_id, 'passkey': self.passkey}))

            if not all([title, download_url]):
                continue

            seeders = row.get('seeders', 1)
            leechers = row.get('leechers', 0)

            # Filter unseeded torrent
            if seeders < self.minseed:
                if mode != 'RSS':
                    log.debug("Discarding torrent because it doesn't meet the"
                              ' minimum seeders: {0}. Seeders: {1}',
                              title, seeders)
                continue

            size = convert_size(row.get('size'), default=-1)

            pubdate_raw = row.get('added')
            pubdate = self.parse_pubdate(pubdate_raw)

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
                    'Found result: {title} with {x} seeders'
                    ' and {y} leechers', {
                        'title': title,
                        'x': seeders,
                        'y': leechers
                    }
                )

            items.append(item)

        return items

    def _check_auth(self):
        if not self.username or not self.passkey:
            log.warning('Your authentication credentials for {provider} are missing,'
                        ' check your config.', {'provider': self.name})
            return False

        return True

    def _check_auth_from_data(self, parsed_json):
        """Check that we are authenticated."""
        if 'status' in parsed_json and 'message' in parsed_json:
            if parsed_json.get('status') == 5:
                log.warning('Invalid username or password. Check your settings')
                return False

        return True


provider = HDBitsProvider()
