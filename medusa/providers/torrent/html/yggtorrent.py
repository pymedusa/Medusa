# coding=utf-8

"""Provider code for Yggtorrent."""

from __future__ import unicode_literals

import logging
import re

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


class YggtorrentProvider(TorrentProvider):
    """Yggtorrent Torrent provider."""

    torrent_id = re.compile(r'\/(\d+)-')

    def __init__(self):
        """Initialize the class."""
        super(YggtorrentProvider, self).__init__('Yggtorrent')

        # Credentials
        self.username = None
        self.password = None

        # URLs
        self.url = 'https://ww1.yggtorrent.com'
        self.urls = {
            'login': urljoin(self.url, 'user/login'),
            'search': urljoin(self.url, 'engine/search'),
            'daily': urljoin(self.url, 'torrents/today'),
            'download': urljoin(self.url, 'engine/download_torrent?id={0}')
        }

        # Proper Strings
        self.proper_strings = ['PROPER', 'REPACK', 'REAL', 'RERIP']

        # Miscellaneous Options
        self.translation = {
            'seconde': 'second',
            'secondes': 'seconds',
            'minute': 'minute',
            'minutes': 'minutes',
            'heure': 'hour',
            'heures': 'hours',
            'jour': 'day',
            'jours': 'days',
            'mois': 'month',
            'an': 'year',
            'année': 'year',
            'ans': 'years',
            'années': 'years'
        }

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tv.Cache(self, min_time=30)

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

        # Search Params
        search_params = {
            'category': 2145
        }

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {search}',
                              {'search': search_string})

                    search_params['q'] = re.sub(r'[()]', '', search_string)
                    url = self.urls['search']
                else:
                    search_params['per_page'] = 50
                    url = self.urls['daily']

                response = self.session.get(url, params=search_params)
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
            torrent_table = html.find(class_='table table-striped')
            torrent_rows = torrent_table('tr') if torrent_table else []

            # Continue only if at least one Release is found
            if len(torrent_rows) < 2:
                log.debug('Data returned from provider does not contain any torrents')
                return items

            # Skip column headers
            for result in torrent_rows[1:]:
                cells = result('td')
                if len(cells) < 5:
                    continue
                try:
                    info = cells[0].find('a', class_='torrent-name')
                    title = info.get_text(strip=True)
                    download_url = info.get('href')
                    if not (title and download_url):
                        continue

                    torrent_id = YggtorrentProvider.torrent_id.search(download_url)
                    download_url = self.urls['download'].format(torrent_id.group(1))

                    seeders = try_int(cells[4].get_text(strip=True), 0)
                    leechers = try_int(cells[5].get_text(strip=True), 0)

                    torrent_size = cells[3].get_text()
                    size = convert_size(torrent_size, sep='') or -1

                    pubdate = None
                    pubdate_match = re.match(r'(\d+)\s(\w+)', cells[2].get_text(strip=True))
                    if pubdate_match:
                        translated = self.translation.get(pubdate_match.group(2))
                        if not translated:
                            log.exception('No translation mapping available for value: {0}', pubdate_match.group(2))
                        else:
                            pubdate_raw = '{0} {1}'.format(pubdate_match.group(1), translated)
                            pubdate = self.parse_pubdate(pubdate_raw, human_time=True)
                    else:
                        log.warning('Could not translate publishing date with value: {0}',
                                    cells[2].get_text(strip=True))

                    # Filter unseeded torrent
                    if seeders < min(self.minseed, 1):
                        if mode != 'RSS':
                            log.debug("Discarding torrent because it doesn't meet the"
                                      " minimum seeders: {0}. Seeders: {1}",
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

    def login(self):
        """Login method used for logging in before doing search and torrent downloads."""
        login_params = {
            'id': self.username,
            'pass': self.password,
            'submit': ''
        }

        self.session.post(self.urls['login'], data=login_params)
        response = self.session.get(self.url)
        if not response:
            log.warning('Unable to connect to provider')
            return False

        if 'Ces identifiants sont invalides' in response.text:
            log.warning('Invalid username or password. Check your settings')
            return False

        if 'Mes torrents' not in response.text:
            log.warning('Unable to login to provider')
            return False

        return True


provider = YggtorrentProvider()
