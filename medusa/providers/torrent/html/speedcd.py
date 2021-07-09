# coding=utf-8

"""Provider code for Speed.cd."""

from __future__ import unicode_literals

import logging
import re

from medusa import tv
from medusa.bs4_parser import BS4Parser
from medusa.helper.common import convert_size
from medusa.logger.adapters.style import BraceAdapter
from medusa.providers.torrent.torrent_provider import TorrentProvider

from requests.compat import urljoin
from requests.utils import dict_from_cookiejar


log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class SpeedCDProvider(TorrentProvider):
    """SpeedCD Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(SpeedCDProvider, self).__init__('Speedcd')

        # Credentials
        self.username = None
        self.password = None

        # URLs
        self.url = 'https://speed.cd'
        self.urls = {
            'API': urljoin(self.url, 'API'),
            'checkpoint1': urljoin(self.url, 'checkpoint/API'),
            'checkpoint2': urljoin(self.url, 'checkpoint/'),
        }

        # Proper Strings
        self.proper_strings = ['PROPER', 'REPACK', 'REAL', 'RERIP']

        # Miscellaneous Options
        self.freeleech = False
        self.enable_cookies = False

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

        # http://speed.cd/browse/57/30/52/53/2/49/55/41/50/q/handmaid
        # Search Params
        data = {
            'jxt': 2,
            'jxw': 'b'
        }

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            for search_string in search_strings[mode]:

                route = '/browse/57/30/52/53/2/49/55/41/50'
                if self.freeleech:
                    route += '/freeleech'

                if mode != 'RSS':
                    log.debug('Search string: {search}',
                              {'search': search_string})
                    route += '/q/' + search_string

                data['route'] = route
                response = self.session.post(self.urls['API'], data=data)
                if not response or not response.text:
                    log.debug('No data returned from provider')
                    continue

                try:
                    response_json = response.json()
                except ValueError as e:
                    log.warning(
                        'Could not decode the response as json for the result,'
                        ' searching {provider} with error {err_msg}',
                        provider=self.name,
                        err_msg=e
                    )
                    continue

                html = response_json['Fs'][0][1][1][1]
                results += self.parse(html, mode)

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
            torrent_rows = html('tr')

            # Skip column headers
            for row in torrent_rows[1:]:
                cells = row('td')

                try:
                    title = cells[1].find('a').get_text()
                    download_url = urljoin(self.url, cells[3].find('a')['href'])
                    if not all([title, download_url]):
                        continue

                    seeders = int(cells[7].get_text(strip=True))
                    leechers = int(cells[8].get_text(strip=True))

                    # Filter unseeded torrent
                    if seeders < self.minseed:
                        if mode != 'RSS':
                            log.debug("Discarding torrent because it doesn't meet the"
                                      ' minimum seeders: {0}. Seeders: {1}',
                                      title, seeders)
                        continue

                    torrent_size = cells[5].get_text()
                    torrent_size = torrent_size[:-2] + ' ' + torrent_size[-2:]
                    size = convert_size(torrent_size) or -1

                    pubdate_raw = cells[1].find('span', class_='elapsedDate')['title']
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

        # Start posting username to API
        login_params_step_1 = {
            'username': self.username
        }

        response = self.session.post(self.urls['checkpoint1'], data=login_params_step_1)
        if not response or not response.text:
            log.warning('Unable to connect to provider')
            return False

        challenge_match = re.match(r'.*<input name=.+a.+value=\\"+(.*)\\".*type.*', response.text)
        if not challenge_match:
            log.warning('Invalid username or password. Check your settings')
            return False

        login_params_step_2 = {
            'pwd': self.password,
            'a': challenge_match.group(1)
        }

        response = self.session.post(self.urls['checkpoint2'], data=login_params_step_2)

        if not re.search(self.username, response.text):
            log.warning('Invalid username or password. Check your settings')
            return False

        return True


provider = SpeedCDProvider()
