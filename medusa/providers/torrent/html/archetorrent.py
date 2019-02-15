# coding=utf-8

"""Provider code for ArcheTorrent."""

from __future__ import unicode_literals

import logging
import re

from medusa import tv
from medusa.bs4_parser import BS4Parser
from medusa.helper.common import (
    convert_size,
)
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.compat import urljoin

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class ArcheTorrentProvider(TorrentProvider):
    """ArcheTorrent Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(ArcheTorrentProvider, self).__init__('ArcheTorrent')

        # Credentials
        self.username = None
        self.password = None

        # URLs
        self.url = 'https://www.archetorrent.com/'
        self.urls = {
            'login': urljoin(self.url, 'account-login.php'),
            'search': urljoin(self.url, 'torrents-search.php'),
            'download': urljoin(self.url, 'download.php?id={0}'),
        }

        # Proper Strings
        self.proper_strings = ['PROPER', 'REPACK', 'REAL', 'RERIP']

        # Cache
        self.cache = tv.Cache(self, min_time=30)

        # Freeleech
        self.freeleech = False

    def search(self, search_strings, age=0, ep_obj=None, **kwargs):
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

        freeleech = '2' if self.freeleech else '0'

        # Search Params
        # c59=1&c73=1&c5=1&c41=1&c60=1&c66=1&c65=1&c67=1&c62=1&c64=1&c61=1&search=Good+Behavior+S01E01
        # &cat=0&incldead=0&freeleech=0&lang=0
        search_params = {
            'c5': '1',   # Category: Series - DVDRip
            'c41': '1',  # Category: Series - HD
            'c60': '1',  # Category: Series - Pack TV
            'c62': '1',  # Category: Series - BDRip
            'c64': '1',  # Category: Series - VOSTFR
            'c65': '1',  # Category: Series - TV 720p
            'c66': '1',  # Category: Series - TV 1080p
            'c67': '1',  # Category: Series - Pack TV HD
            'c73': '1',  # Category: Anime
            'incldead': '0',  # Include dead torrent - 0: off 1: yes 2: only dead
            'freeleech': freeleech,  # Only freeleech torrent - 0: off 1: no freeleech 2: Only freeleech
            'lang': '0'  # Language - 0: off 1: English 2: French ....
        }

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {search}',
                              {'search': search_string})

                search_params['search'] = search_string
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
        :param mode: The current mode used to search, e.g. RSS.

        :return: A list of items found
        """
        items = []

        with BS4Parser(data, 'html5lib') as html:
            torrent_table = html.find(class_='ttable_headinner')
            torrent_rows = torrent_table('tr') if torrent_table else []

            # Continue only if at least one release is found
            if len(torrent_rows) < 2:
                log.debug('Data returned from provider does not contain any torrents')
                return items

            # Catégorie, Release, Date, DL, Size, C, S, L
            labels = [label.get_text(strip=True) for label in torrent_rows[0]('th')]

            for torrent in torrent_rows[1:]:
                cells = torrent('td')
                if len(cells) < len(labels):
                    continue

                try:
                    torrent_id = re.search('id=([0-9]+)', cells[labels.index('Nom')].find('a')['href']).group(1)
                    title = cells[labels.index('Nom')].get_text(strip=True)
                    if not all([title, torrent_id]):
                        continue

                    download_url = self.urls['download'].format(torrent_id)

                    seeders = int(cells[labels.index('S')].get_text(strip=True))
                    leechers = int(cells[labels.index('L')].get_text(strip=True))

                    # Filter unseeded torrent
                    if seeders < self.minseed:
                        if mode != 'RSS':
                            log.debug("Discarding torrent because it doesn't meet the"
                                      ' minimum seeders: {0}. Seeders: {1}',
                                      title, seeders)
                        continue

                    torrent_size = cells[labels.index('Taille')].get_text()
                    size = convert_size(torrent_size, default=-1)

                    date_raw = torrent('a')[2]['onmouseover']
                    pubdate_raw = re.search(r'Poster le: <\/b>(\d{2}-\d{2}-\d{4})', date_raw)
                    pubdate = self.parse_pubdate(pubdate_raw.group(1), dayfirst=True)

                    item = {
                        'title': title,
                        'link': download_url,
                        'size': size,
                        'seeders': seeders,
                        'leechers': leechers,
                        'pubdate': pubdate
                    }

                    if mode != 'RSS':
                        log.debug('Found result: {0} with {1} seeders and {2} leechers',
                                  title, seeders, leechers)

                    items.append(item)
                except (AttributeError, TypeError, KeyError, ValueError, IndexError):
                    log.exception('Failed parsing provider.')

        return items

    def login(self):
        """Login method used for logging in before doing search and torrent downloads."""
        login_params = {
            'username': self.username,
            'password': self.password,
            'returnto': '/index.php'
        }

        self.session.post(self.urls['login'], data=login_params)
        response = self.session.get(self.url)
        if not response:
            log.warning('Unable to connect to provider')
            return False

        if 'torrents.php' not in response.text:
            log.warning('Invalid username or password. Check your settings')
            return False

        return True


provider = ArcheTorrentProvider()
