# coding=utf-8

"""Provider code for SceneTime."""

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


class SceneTimeProvider(TorrentProvider):
    """SceneTime Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(SceneTimeProvider, self).__init__('SceneTime')

        # URLs
        self.url = 'https://www.scenetime.com'
        self.urls = {
            'login': urljoin(self.url, 'login.php'),
            'search': urljoin(self.url, 'browse.php'),
            'download': urljoin(self.url, 'download.php/{0}/{1}'),
        }

        # Proper Strings
        # Provider always returns propers and non-propers in a show search
        self.proper_strings = ['']

        # Miscellaneous Options
        self.enable_cookies = True
        self.cookies = ''
        self.required_cookies = ('uid', 'pass')

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
            'cata': 'yes',
            'c2': 1,  # TV/XviD
            'c43': 1,  # TV/Packs
            'c9': 1,  # TV-HD
            'c63': 1,  # TV/Classic
            'c77': 1,  # TV/SD
            'c79': 1,  # Sports
            'c100': 1,  # TV/Non-English
            'c83': 1,  # TV/Web-Rip
            'c8': 1,  # TV-Mobile
            'c18': 1,  # TV/Anime
            'c19': 1,  # TV-X265
            'search': '',
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
        :param mode: The current mode used to search, e.g. RSS

        :return: A list of items found
        """
        items = []

        with BS4Parser(data, 'html5lib') as html:
            torrent_table = html.find('div', id='torrenttable')
            torrent_rows = torrent_table.find_all('tr') if torrent_table else []

            # Continue only if at least one release is found
            if len(torrent_rows) < 2:
                log.debug('Data returned from provider does not contain any torrents')
                return items

            # Scenetime apparently uses different number of cells in #torrenttable based
            # on who you are. This works around that by extracting labels from the first
            # <tr> and using their index to find the correct download/seeders/leechers td.
            labels = [label.get_text(strip=True) or label.img['title'] for label in torrent_rows[0]('td')]

            # Skip column headers
            for row in torrent_rows[1:]:
                cells = row('td')
                if len(cells) < len(labels):
                    continue

                try:
                    link = cells[labels.index('Name')]
                    torrent_id = link.find('a')['href'].replace('details.php?id=', '').split('&')[0]
                    title = link.find('a').get_text(strip=True)
                    download_url = self.urls['download'].format(
                        torrent_id,
                        '{0}.torrent'.format(title.replace(' ', '.'))
                    )
                    if not all([title, download_url]):
                        continue

                    seeders = try_int(cells[labels.index('Seeders')].get_text(strip=True))
                    leechers = try_int(cells[labels.index('Leechers')].get_text(strip=True))

                    # Filter unseeded torrent
                    if seeders < self.minseed:
                        if mode != 'RSS':
                            log.debug("Discarding torrent because it doesn't meet the"
                                      ' minimum seeders: {0}. Seeders: {1}',
                                      title, seeders)
                        continue

                    torrent_size = cells[labels.index('Size')].get_text()
                    torrent_size = re.sub(r'(\d+\.?\d*)', r'\1 ', torrent_size)
                    size = convert_size(torrent_size) or -1

                    # Get the last item from the "span" list to avoid parsing "NEW!" as a pub date.
                    pubdate_raw = link.find_all('span')[-1]['title']
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
                        log.debug('Found result: {0} with {1} seeders and {2} leechers',
                                  title, seeders, leechers)

                    items.append(item)
                except (AttributeError, TypeError, KeyError, ValueError, IndexError):
                    log.exception('Failed parsing provider.')

        return items

    def login(self):
        """Login method used for logging in before doing search and torrent downloads."""
        return self.cookie_login('log in')


provider = SceneTimeProvider()
