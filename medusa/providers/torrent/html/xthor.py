# coding=utf-8

"""Provider code for Xthor."""

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

from requests.utils import dict_from_cookiejar

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class XthorProvider(TorrentProvider):
    """Xthor Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(XthorProvider, self).__init__('Xthor')

        # Credentials
        self.username = None
        self.password = None

        # URLs
        self.url = 'https://xthor.bz'
        self.urls = {
            'login': self.url + '/takelogin.php',
            'search': self.url + '/browse.php?',
        }

        # Proper Strings
        self.proper_strings = ['PROPER']

        # Miscellaneous Options
        self.freeleech = None

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tv.Cache(self, min_time=30)

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
            'only_free': try_int(self.freeleech),
            'searchin': 'title',
            'incldead': 0,
            'type': 'desc',
            'c13': 1,  # Séries / Pack TV 13
            'c14': 1,  # Séries / TV FR 14
            'c15': 1,  # Séries / HD FR 15
            'c16': 1,  # Séries / TV VOSTFR 16
            'c17': 1,  # Séries / HD VOSTFR 17
            'c32': 1,   # Mangas (Anime) 32
            'c34': 1,  # Sport 34
        }

        for mode in search_strings:
            results = []
            log.debug('Search mode: {0}', mode)

            # Sorting: 1: Name, 3: Comments, 5: Size, 6: Completed, 7: Seeders, 8: Leechers (4: Time ?)
            search_params['sort'] = (7, 4)[mode == 'RSS']

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {search}',
                              {'search': search_string})

                search_params['search'] = search_string
                response = self.get_url(self.urls['search'], params=search_params, returns='response')
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
        # Units
        units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']

        def process_column_header(td):
            result = ''
            if td.a:
                result = td.a.get('title', td.a.get_text(strip=True))
            if not result:
                result = td.get_text(strip=True)
            return result

        items = []

        with BS4Parser(data, 'html5lib') as html:
            torrent_table = html.find('table', class_='table2 table-bordered2')
            torrent_rows = []
            if torrent_table:
                torrent_rows = torrent_table('tr')

            # Continue only if at least one release is found
            if len(torrent_rows) < 2:
                log.debug('Data returned from provider does not contain any torrents')
                return items

            # Catégorie, Nom du Torrent, (Download), (Bookmark), Com., Taille, Compl�t�, Seeders, Leechers
            labels = [process_column_header(label) for label in torrent_rows[0]('td')]

            # Skip column headers
            for row in torrent_rows[1:]:
                cells = row('td')
                if len(cells) < len(labels):
                    continue

                try:
                    title = cells[labels.index('Nom du Torrent')].get_text(strip=True)
                    download_url = self.url + '/' + row.find('a', href=re.compile('download.php'))['href']
                    if not all([title, download_url]):
                        continue

                    seeders = try_int(cells[labels.index('Seeders')].get_text(strip=True))
                    leechers = try_int(cells[labels.index('Leechers')].get_text(strip=True))

                    # Filter unseeded torrent
                    if seeders < min(self.minseed, 1):
                        if mode != 'RSS':
                            log.debug("Discarding torrent because it doesn't meet the"
                                      " minimum seeders: {0}. Seeders: {1}",
                                      title, seeders)
                        continue

                    torrent_size = cells[labels.index('Taille')].get_text()
                    size = convert_size(torrent_size, units=units) or -1

                    item = {
                        'title': title,
                        'link': download_url,
                        'size': size,
                        'seeders': seeders,
                        'leechers': leechers,
                        'pubdate': None,
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
            'submitme': 'X'
        }

        response = self.get_url(self.urls['login'], post_data=login_params, returns='response')
        if not response or not response.text:
            log.warning('Unable to connect to provider')
            return False

        if not re.search('donate.php', response.text):
            log.warning('Invalid username or password. Check your settings')
            return False

        return True


provider = XthorProvider()
