# coding=utf-8

"""Provider code for HoundDawgs."""

from __future__ import unicode_literals

import logging
import re
import traceback

from medusa import tv
from medusa.bs4_parser import BS4Parser
from medusa.helper.common import (
    convert_size,
    try_int,
)
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.compat import urljoin
from requests.utils import dict_from_cookiejar

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class HoundDawgsProvider(TorrentProvider):
    """HoundDawgs Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(HoundDawgsProvider, self).__init__('HoundDawgs')

        # Credentials
        self.username = None
        self.password = None

        # URLs
        self.url = 'https://hounddawgs.org'
        self.urls = {
            'base_url': self.url,
            'search': urljoin(self.url, 'torrents.php'),
            'login': urljoin(self.url, 'login.php'),
        }

        # Proper Strings

        # Miscellaneous Options
        self.freeleech = None
        self.ranked = None

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tv.Cache(self)

    def search(self, search_strings, age=0, ep_obj=None):
        """
        Search a provider and parse the results.

        :param search_strings: A dict with mode (key) and the search value (value)
        :param age: Not used
        :param ep_obj: Not used
        :returns: A list of search results (structure)
        """
        results = []
        if not self.login():
            return results

        # Search Params
        search_params = {
            'filter_cat[85]': 1,
            'filter_cat[58]': 1,
            'filter_cat[57]': 1,
            'filter_cat[74]': 1,
            'filter_cat[92]': 1,
            'filter_cat[93]': 1,
            'order_by': 's3',
            'order_way': 'desc',
            'type': '',
            'userid': '',
            'searchstr': '',
            'searchimdb': '',
            'searchtags': ''
        }

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {search}',
                              {'search': search_string})
                    if self.ranked:
                        log.debug('Searching only ranked torrents')

                search_params['searchstr'] = search_string
                response = self.get_url(self.urls['search'], params=search_params, returns='response')
                if not response or not response.text:
                    log.debug('No data returned from provider')
                    continue
                if not response.text:
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
            torrent_table = html.find('table', {'id': 'torrent_table'})

            # Continue only if at least one release is found
            if not torrent_table:
                log.debug('Data returned from provider does not contain any {0}torrents',
                          'ranked ' if self.ranked else '')
                return items

            torrent_body = torrent_table.find('tbody')
            torrent_rows = torrent_body.contents
            del torrent_rows[1::2]

            for row in torrent_rows[1:]:
                try:
                    torrent = row('td')
                    if len(torrent) <= 1:
                        break

                    all_as = (torrent[1])('a')
                    notinternal = row.find('img', src='/static//common/user_upload.png')
                    if self.ranked and notinternal:
                        log.debug('Found a user uploaded release, Ignoring it..')
                        continue

                    freeleech = row.find('img', src='/static//common/browse/freeleech.png')
                    if self.freeleech and not freeleech:
                        continue

                    title = all_as[2].string
                    download_url = urljoin(self.url, all_as[0].attrs['href'])
                    if not all([title, download_url]):
                        continue

                    seeders = try_int((row('td')[6]).text.replace(',', ''))
                    leechers = try_int((row('td')[7]).text.replace(',', ''))

                    # Filter unseeded torrent
                    if seeders < min(self.minseed, 1):
                        if mode != 'RSS':
                            log.debug("Discarding torrent because it doesn't meet the"
                                      " minimum seeders: {0}. Seeders: {1}",
                                      title, seeders)
                        continue

                    torrent_size = row.find('td', class_='nobr').find_next_sibling('td').string
                    if torrent_size:
                        size = convert_size(torrent_size) or -1

                    pubdate_raw = row.find('td', class_='nobr').find('span')['title']
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

    def login(self):
        """Login method used for logging in before doing search and torrent downloads."""
        if any(dict_from_cookiejar(self.session.cookies).values()):
            return True

        login_params = {
            'username': self.username,
            'password': self.password,
            'keeplogged': 'on',
            'login': 'Login'
        }

        # Initialize session with a GET to have cookies
        self.get_url(self.urls['base_url'], returns='response')
        response = self.get_url(self.urls['login'], post_data=login_params, returns='response')
        if not response or not response.text:
            log.warning('Unable to connect to provider')
            return False

        if any([re.search('Dit brugernavn eller kodeord er forkert.', response.text),
                re.search('<title>Login :: HoundDawgs</title>', response.text),
                re.search('Dine cookies er ikke aktiveret.', response.text)], ):
            log.warning('Invalid username or password. Check your settings')
            return False

        return True


provider = HoundDawgsProvider()
