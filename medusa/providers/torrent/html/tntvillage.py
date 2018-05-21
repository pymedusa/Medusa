# coding=utf-8

"""Provider code for TNTVillage."""

from __future__ import unicode_literals

import logging
import re

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


class TNTVillageProvider(TorrentProvider):
    """TNTVillage Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(TNTVillageProvider, self).__init__('TNTVillage')

        # Credentials
        self.username = None
        self.password = None
        self._uid = None
        self._hash = None

        # URLs
        self.url = 'http://forum.tntvillage.scambioetico.org/'
        self.urls = {
            'login': urljoin(self.url, 'index.php?act=Login&CODE=01'),
            'download': urljoin(self.url, 'index.php?act=Attach&type=post&id={0}'),
        }

        # Proper Strings
        self.proper_strings = ['PROPER', 'REPACK']

        # Miscellaneous Options
        self.engrelease = None
        self.subtitle = None

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tv.Cache(self, min_time=30)  # only poll TNTVillage every 30 minutes max

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
            'act': 'allreleases',
            'filter': 'eng ' if self.engrelease else '',
            'cat': 29,
        }

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {search}',
                              {'search': search_string})
                    search_params['filter'] += search_string
                    search_params['cat'] = None

                response = self.session.get(self.url, params=search_params)
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
            torrent_table = html.find('table', class_='copyright')
            torrent_rows = torrent_table('tr') if torrent_table else []

            # Continue only if at least one release is found
            if len(torrent_rows) < 3:
                log.debug('Data returned from provider does not contain any torrents')
                return items

            # Skip column headers
            for row in torrent_table('tr')[1:]:
                cells = row('td')

                try:
                    if not cells:
                        continue

                    last_cell_anchor = cells[-1].find('a')
                    if not last_cell_anchor:
                        continue
                    params = parse_qs(last_cell_anchor.get('href', ''))
                    download_url = self.urls['download'].format(params['pid'][0]) if \
                        params.get('pid') else None
                    title = self._process_title(cells[0], cells[1], mode)
                    if not all([title, download_url]):
                        continue

                    info_cell = cells[3]('td')
                    leechers = info_cell[0].find('span').get_text(strip=True)
                    leechers = try_int(leechers)
                    seeders = info_cell[1].find('span').get_text()
                    seeders = try_int(seeders, 1)

                    # Filter unseeded torrent
                    if seeders < min(self.minseed, 1):
                        if mode != 'RSS':
                            log.debug("Discarding torrent because it doesn't meet the"
                                      " minimum seeders: {0}. Seeders: {1}",
                                      title, seeders)
                        continue

                    if self._has_only_subs(title) and not self.subtitle:
                        log.debug('Torrent is only subtitled, skipping: {0}',
                                  title)
                        continue

                    torrent_size = info_cell[3].find('span').get_text() + ' GB'
                    size = convert_size(torrent_size) or -1

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
                    log.exception('Failed parsing provider.')

        return items

    def login(self):
        """Login method used for logging in before doing search and torrent downloads."""
        if len(self.session.cookies) > 1:
            cookies_dict = dict_from_cookiejar(self.session.cookies)
            if cookies_dict['pass_hash'] != '0' and cookies_dict['member_id'] != '0':
                return True

        login_params = {
            'UserName': self.username,
            'PassWord': self.password,
            'CookieDate': 1,
            'submit': 'Connettiti al Forum',
        }

        response = self.session.post(self.urls['login'], data=login_params)
        if not response or not response.text:
            log.warning('Unable to connect to provider')
            return False

        if any([re.search('Sono stati riscontrati i seguenti errori', response.text),
                re.search('<title>Connettiti</title>', response.text), ]):
            log.warning('Invalid username or password. Check your settings')
            return False

        return True

    def _check_auth(self):

        if not self.username or not self.password:
            raise AuthException('Your authentication credentials for {0} are missing,'
                                ' check your config.'.format(self.name))

        return True

    @staticmethod
    def _process_title(title, info, mode):

        result_title = title.find('a').get_text()
        result_info = info.find('span')

        if not result_info:
            return None

        bad_words = ['[cura]', 'hot', 'season', 'stagione', 'series', 'premiere', 'finale', 'fine',
                     'full', 'Completa', 'supereroi', 'commedia', 'drammatico', 'poliziesco', 'azione',
                     'giallo', 'politico', 'sitcom', 'fantasy', 'funzionante']

        formatted_info = ''
        for info_part in result_info:
            if mode == 'RSS':
                try:
                    info_part = info_part.get('src')
                    info_part = info_part.replace('style_images/mkportal-636/', '')
                    info_part = info_part.replace('.gif', '').replace('.png', '')
                    if info_part == 'dolby':
                        info_part = 'Ac3'
                    elif info_part == 'fullHd':
                        info_part = '1080p'
                except AttributeError:
                    info_part = info_part.replace('·', '').replace(',', '')
                    info_part = info_part.replace('by', '-').strip()
                formatted_info += ' ' + info_part
            else:
                formatted_info = info_part

        allowed_words = [word for word in formatted_info.split() if word.lower() not in bad_words]
        final_title = '{0} '.format(result_title) + ' '.join(allowed_words).strip('-').strip()

        return final_title

    @staticmethod
    def _has_only_subs(title):

        title = title.lower()

        if 'sub' in title:
            title = title.split()
            counter = 0
            for word in title:
                if 'ita' in word:
                    counter += 1
            if counter < 2:
                return True


provider = TNTVillageProvider()
