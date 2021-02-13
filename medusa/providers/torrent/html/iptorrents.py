# coding=utf-8

"""Provider code for IPTorrents."""

from __future__ import unicode_literals

import logging
import re

from medusa import tv
from medusa.bs4_parser import BS4Parser
from medusa.helper.common import convert_size
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.compat import urljoin

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class IPTorrentsProvider(TorrentProvider):
    """IPTorrents Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(IPTorrentsProvider, self).__init__('IPTorrents')

        # URLs
        self.url = 'https://iptorrents.eu'
        self.urls = {
            'base_url': self.url,
            'login': urljoin(self.url, 'torrents'),
            'search': urljoin(self.url, 't?%s%s&q=%s&qf=#torrents'),
        }

        # Proper Strings

        # Miscellaneous Options
        self.freeleech = False
        self.enable_cookies = True
        self.cookies = ''
        self.required_cookies = ('uid', 'pass')
        self.categories = '73=&60='

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

        freeleech = '&free=on' if self.freeleech else ''

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {search}',
                              {'search': search_string})

                # URL with 50 tv-show results, or max 150 if adjusted in IPTorrents profile
                search_url = self.urls['search'] % (self.categories, freeleech, search_string)
                search_url += ';o=seeders' if mode != 'RSS' else ''

                response = self.session.get(search_url)
                if not response or not response.text:
                    log.debug('No data returned from provider')
                    continue

                data = re.sub(r'(?im)<button.+?<[/]button>', '', response.text, 0)

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

        with BS4Parser(data, 'html5lib') as html:
            torrent_table = html.find('table', id='torrents')
            torrents = torrent_table('tr') if torrent_table else []

            # Continue only if at least one release is found
            if len(torrents) < 2 or html.find(text='No Torrents Found!'):
                log.debug('Data returned from provider does not contain any torrents')
                return items

            # Skip column headers
            for row in torrents[1:]:
                try:
                    table_data = row('td')
                    title = table_data[1].find('a').text
                    download_url = self.urls['base_url'] + table_data[3].find('a')['href']
                    if not all([title, download_url]):
                        continue

                    seeders = int(table_data[7].text)
                    leechers = int(table_data[8].text)

                    # Filter unseeded torrent
                    if seeders < self.minseed:
                        if mode != 'RSS':
                            log.debug("Discarding torrent because it doesn't meet the"
                                      ' minimum seeders: {0}. Seeders: {1}',
                                      title, seeders)
                        continue

                    torrent_size = table_data[5].text
                    size = convert_size(torrent_size) or -1

                    pubdate_raw = table_data[1].find('div').get_text().split('|')[-1].strip()
                    pubdate = self.parse_pubdate(pubdate_raw, human_time=True)

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
        return self.cookie_login('sign in')


provider = IPTorrentsProvider()
