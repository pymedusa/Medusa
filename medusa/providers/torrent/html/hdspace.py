# coding=utf-8

"""Provider code for HDSpace."""

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
from requests.utils import dict_from_cookiejar

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class HDSpaceProvider(TorrentProvider):
    """HDSpace Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(HDSpaceProvider, self).__init__('HDSpace')

        # Credentials
        self.username = None
        self.password = None

        # URLs
        self.url = 'https://hd-space.org'
        self.urls = {
            'login': urljoin(self.url, 'index.php?page=login'),
            'search': urljoin(self.url, 'index.php'),
        }

        # Proper Strings

        # Miscellaneous Options

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
        if not self.login():
            return results

        # Search Params
        search_params = {
            'page': 'torrents',
            'search': '',
            'active': 0,
            'options': 0,
            'category': '15;40;21;22;24;25;27;28',
        }

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {search}',
                              {'search': search_string})
                    search_params['search'] = search_string

                response = self.session.get(self.urls['search'], params=search_params)
                if not response or not response.text or 'please try later' in response.text:
                    log.debug('No data returned from provider')
                    continue

                # Search result page contains some invalid html that prevents html parser from returning all data.
                # We cut everything before the table that contains the data we are interested in thus eliminating
                # the invalid html portions
                try:
                    index = response.text.index('<div id="information"')
                except ValueError:
                    log.debug('Could not find main torrent table')
                    continue

                results += self.parse(response.text[index:], mode)

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
            if not html:
                log.debug('No html data parsed from provider')
                return items

            torrents = html('tr')
            if not torrents or len(torrents) < 2:
                log.debug('Data returned from provider does not contain any torrents')
                return items

            # Skip column headers
            for row in torrents[1:]:
                # Skip extraneous rows at the end
                if len(row.contents) < 10:
                    continue

                try:
                    comments_counter = row.find_all('td', class_='lista', attrs={'align': 'center'})[4].find('a')
                    if comments_counter:
                        title = comments_counter['title'][10:]
                    else:
                        title = row.find('td', class_='lista', attrs={'align': 'left'}).find('a').get_text()
                    dl_href = row.find('td', class_='lista', attrs={'width': '20',
                                                                    'style': 'text-align: center;'}).find('a').get('href')
                    download_url = urljoin(self.url, dl_href)
                    if not all([title, dl_href]):
                        continue

                    seeders = try_int(row.find('span', class_='seedy').find('a').get_text(), 1)
                    leechers = try_int(row.find('span', class_='leechy').find('a').get_text())

                    # Filter unseeded torrent
                    if seeders < self.minseed:
                        if mode != 'RSS':
                            log.debug("Discarding torrent because it doesn't meet the"
                                      ' minimum seeders: {0}. Seeders: {1}',
                                      title, seeders)
                        continue

                    torrent_size = row.find('td', class_='lista222', attrs={'width': '100%'}).get_text()
                    size = convert_size(torrent_size) or -1

                    pubdate_td = row.find_all('td', class_='lista', attrs={'align': 'center'})[3]
                    pubdate_human_offset = pubdate_td.find('b')
                    if pubdate_human_offset:
                        time_search = re.search('([0-9:]+)', pubdate_td.get_text())
                        pubdate_raw = pubdate_human_offset.get_text() + ' at ' + time_search.group(1)
                    else:
                        pubdate_raw = pubdate_td.get_text()

                    pubdate = self.parse_pubdate(pubdate_raw)

                    item = {
                        'title': title,
                        'link': download_url,
                        'size': size,
                        'seeders': seeders,
                        'leechers': leechers,
                        'pubdate': pubdate,
                    }
                    log.debug('Found result: {0} with {1} seeders and {2} leechers',
                              title, seeders, leechers)

                    items.append(item)
                except (AttributeError, TypeError, KeyError, ValueError, IndexError):
                    log.exception('Failed parsing provider.')

        return items

    def login(self):
        """Login method used for logging in before doing search and torrent downloads."""
        if any(dict_from_cookiejar(self.session.cookies).values()):
            return True

        if 'pass' in dict_from_cookiejar(self.session.cookies):
            return True

        login_params = {
            'uid': self.username,
            'pwd': self.password,
            'submit': 'Confirm',
        }

        response = self.session.post(self.urls['login'], data=login_params)
        if not response or not response.text:
            log.warning('Unable to connect to provider')
            return False

        if re.search('Automatic log off after 15 minutes inactivity', response.text):
            log.warning('Invalid username or password. Check your settings')
            return False

        return True

    def _check_auth(self):

        if not self.username or not self.password:
            log.warning('Invalid username or password. Check your settings')

        return True


provider = HDSpaceProvider()
