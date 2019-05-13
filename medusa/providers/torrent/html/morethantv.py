# coding=utf-8

"""Provider code for MoreThanTV."""

from __future__ import unicode_literals

import logging
import re
import time

from medusa import tv
from medusa.bs4_parser import BS4Parser
from medusa.helper.common import (
    convert_size,
    try_int,
)
from medusa.helper.exceptions import AuthException
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.compat import urljoin
from requests.utils import dict_from_cookiejar

from six.moves.urllib_parse import parse_qs

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class MoreThanTVProvider(TorrentProvider):
    """MoreThanTV Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(MoreThanTVProvider, self).__init__('MoreThanTV')

        # Credentials
        self.username = None
        self.password = None

        # URLs
        self.url = 'https://www.morethan.tv/'
        self.urls = {
            'login': urljoin(self.url, 'login.php'),
            'search': urljoin(self.url, 'torrents.php'),
        }

        # Proper Strings
        self.proper_strings = ['PROPER', 'REPACK']

        # Miscellaneous Options

        # Cache
        self.cache = tv.Cache(self)

    def search(self, search_strings, age=0, ep_obj=None, **kwargs):
        """Search a provider and parse the results.

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
            'tags_type': 1,
            'order_by': 'time',
            'order_way': 'desc',
            'action': 'basic',
            'group_results': 0,
            'searchsubmit': 1,
            'searchstr': '',
        }

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            if mode == 'Season':
                additional_strings = []
                for search_string in search_strings[mode]:
                    additional_strings.append(re.sub(r'(.*)S0?', r'\1Season ', search_string))
                search_strings[mode].extend(additional_strings)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {search}',
                              {'search': search_string})

                search_params['searchstr'] = search_string

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
        def process_column_header(td):
            result = ''
            if td.a and td.a.img:
                result = td.a.img.get('title', td.a.get_text(strip=True))
            if not result:
                result = td.get_text(strip=True)
            return result

        items = []

        with BS4Parser(data, 'html5lib') as html:
            torrent_table = html.find('table', class_='torrent_table')
            torrent_rows = torrent_table('tr') if torrent_table else []

            # Continue only if at least one release is found
            if len(torrent_rows) < 2:
                log.debug('Data returned from provider does not contain any torrents')
                return items

            labels = [process_column_header(label) for label in torrent_rows[0]('td')]

            # Skip column headers
            for row in torrent_rows[1:]:
                cells = row('td')
                if len(cells) < len(labels):
                    continue

                try:
                    # Skip if torrent has been nuked due to poor quality
                    if row.find('img', alt='Nuked'):
                        continue

                    title = row.find('a', title='View torrent').get_text(strip=True)
                    download_url = urljoin(self.url, row.find('span', title='Download').parent['href'])
                    if not all([title, download_url]):
                        continue

                    seeders = try_int(cells[labels.index('Seeders')].get_text(strip=True).replace(',', ''), 1)
                    leechers = try_int(cells[labels.index('Leechers')].get_text(strip=True).replace(',', ''))

                    # Filter unseeded torrent
                    if seeders < self.minseed:
                        if mode != 'RSS':
                            log.debug("Discarding torrent because it doesn't meet the"
                                      ' minimum seeders: {0}. Seeders: {1}',
                                      title, seeders)
                        continue

                    # If it's a season search, query the torrent's detail page.
                    if mode == 'Season':
                        title = self._parse_season(row, download_url, title)

                    torrent_size = cells[labels.index('Size')].get_text(strip=True)
                    size = convert_size(torrent_size) or -1

                    pubdate_raw = cells[labels.index('Time')].find('span')['title']
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
        if any(dict_from_cookiejar(self.session.cookies).values()):
            return True

        login_params = {
            'username': self.username,
            'password': self.password,
            'keeplogged': '1',
            'login': 'Log in',
        }

        response = self.session.post(self.urls['login'], data=login_params)
        if not response or not response.text:
            log.warning('Unable to connect to provider')
            return False

        if re.search('Your username or password was incorrect.', response.text):
            log.warning('Invalid username or password. Check your settings')
            return False

        return True

    def _check_auth(self):

        if not self.username or not self.password:
            raise AuthException('Your authentication credentials for {0} are missing,'
                                ' check your config.'.format(self.name))

        return True

    def _parse_season(self, row, download_url, title):
        """Parse the torrent's detail page and return the season pack title."""
        details_url = row.find('span').find_next(title='View torrent').get('href')
        torrent_id = parse_qs(download_url).get('id')
        if not all([details_url, torrent_id]):
            log.debug("Couldn't parse season pack details page for title: {0}", title)
            return title

        # Take a break before querying the provider again
        time.sleep(0.5)
        response = self.session.get(urljoin(self.url, details_url))
        if not response or not response.text:
            log.debug("Couldn't open season pack details page for title: {0}", title)
            return title

        with BS4Parser(response.text, 'html5lib') as html:
            torrent_table = html.find('table', class_='torrent_table')
            torrent_row = torrent_table.find(
                'tr', id='torrent_{0}'.format(torrent_id[0])
            ) if torrent_table else None
            if not torrent_row:
                log.debug("Couldn't find season pack details for title: {0}", title)
                return title

            # Strip leading and trailing slash
            season_title = torrent_row.find('div', class_='filelist_path')
            if not season_title or not season_title.get_text():
                log.debug("Couldn't parse season pack title for: {0}", title)
                return title
            return season_title.get_text(strip=True).strip('/')


provider = MoreThanTVProvider()
