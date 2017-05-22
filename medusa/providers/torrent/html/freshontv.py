# coding=utf-8

"""Provider code for FreshOnTV."""

from __future__ import unicode_literals

import logging
import re
import time
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
from requests.utils import (
    add_dict_to_cookiejar,
    dict_from_cookiejar,
)
from six import text_type

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class FreshOnTVProvider(TorrentProvider):
    """FreshOnTV Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(FreshOnTVProvider, self).__init__('FreshOnTV')

        # Credentials
        self.username = None
        self.password = None
        self._uid = None
        self._hash = None
        self.cookies = None

        # URLs
        self.url = 'https://freshon.tv'
        self.urls = {
            'base_url': self.url,
            'login': urljoin(self.url, 'login.php?action=makelogin'),
            'detail': urljoin(self.url, 'details.php?id=%s'),
            'search': urljoin(self.url, 'browse.php?incldead=%s&words=0&cat=0&search=%s'),
            'download': urljoin(self.url, 'download.php?id=%s&type=torrent'),
        }

        # Proper Strings
        # Provider always returns propers and non-propers in a show search
        self.proper_strings = ['']

        # Miscellaneous Options
        self.freeleech = False

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

        freeleech = '3' if self.freeleech else '0'

        for mode in search_strings:
            log.debug('Search mode: {0}', mode)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    log.debug('Search string: {search}',
                              {'search': search_string})

                search_url = self.urls['search'] % (freeleech, search_string)
                response = self.session.get(search_url)

                max_page_number = 0

                if not response or not response.text:
                    log.debug('No data returned from provider')
                    continue

                with BS4Parser(response.text, 'html5lib') as html:
                    try:
                        # Check to see if there is more than 1 page of results
                        pager = html.find('div', {'class': 'pager'})
                        if pager:
                            page_links = pager('a', href=True)
                        else:
                            page_links = []

                        if page_links:
                            for lnk in page_links:
                                link_text = lnk.text.strip()
                                if link_text.isdigit():
                                    page_int = int(link_text)
                                    if page_int > max_page_number:
                                        max_page_number = page_int

                        # limit page number to 15 just in case something goes wrong
                        if max_page_number > 15:
                            max_page_number = 15
                        # limit RSS search
                        if max_page_number > 3 and mode == 'RSS':
                            max_page_number = 3
                    except Exception:
                        log.error('Failed parsing provider. Traceback: {0!r}',
                                  traceback.format_exc())
                        continue

                responses = [response]

                # Freshon starts counting pages from zero, even though it displays numbers from 1
                if max_page_number > 1:
                    for x in range(1, max_page_number):
                        time.sleep(1)
                        page_search_url = '{url}&page={x}'.format(url=search_url, x=x)
                        page = self.session.get(page_search_url)

                        if not page:
                            continue

                        responses.append(page)

                for response in responses:
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
            torrent_rows = html('tr', class_=re.compile('torrent_[0-9]*'))

            # Continue only if at least one release is found
            if not torrent_rows:
                log.debug('Data returned from provider does not contain any torrents')
                return items

            for row in torrent_rows:

                try:
                    # skip if torrent has been nuked due to poor quality
                    if row.find('img', alt='Nuked') is not None:
                        continue

                    title = row.find('a', class_='torrent_name_link')['title']
                    details_url = row.find('a', class_='torrent_name_link')['href']
                    torrent_id = int((re.match('.*?([0-9]+)$', details_url).group(1)).strip())
                    download_url = self.urls['download'] % (text_type(torrent_id))
                    if not all([title, download_url]):
                        continue

                    seeders = try_int(row.find('td', class_='table_seeders').find('span').get_text(strip=True), 1)
                    leechers = try_int(row.find('td', class_='table_leechers').find('a').get_text(strip=True), 0)

                    # Filter unseeded torrent
                    if seeders < min(self.minseed, 1):
                        if mode != 'RSS':
                            log.debug("Discarding torrent because it doesn't meet the"
                                      " minimum seeders: {0}. Seeders: {1}",
                                      title, seeders)
                        continue

                    torrent_size = row.find('td', class_='table_size').get_text(strip=True)
                    torrent_size = re.split('(\d+.?\d+)', text_type(torrent_size), 1)
                    torrent_size = '{0} {1}'.format(torrent_size[1], torrent_size[2])
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
                    log.debug('Failed parsing provider. Traceback: {0!r}',
                              traceback.format_exc())

        return items

    def login(self):
        """Login method used for logging in before doing search and torrent downloads."""
        if any(dict_from_cookiejar(self.session.cookies).values()):
            return True

        login_params = {
            'username': self.username,
            'password': self.password,
        }

        if self._uid and self._hash:
            add_dict_to_cookiejar(self.session.cookies, self.cookies)
        else:
            response = self.session.post(self.urls['login'], data=login_params)
            if not response or not response.text:
                log.warning('Unable to connect to provider')
                return False

            if re.search('/logout.php', response.text):
                try:
                    if dict_from_cookiejar(self.session.cookies)['uid'] and \
                            dict_from_cookiejar(self.session.cookies)['pass']:
                        self._uid = dict_from_cookiejar(self.session.cookies)['uid']
                        self._hash = dict_from_cookiejar(self.session.cookies)['pass']

                        self.cookies = {'uid': self._uid,
                                        'pass': self._hash}
                        return True
                except Exception:
                    log.warning('Unable to login to provider (cookie)')

                    return False
            else:
                if re.search('Username does not exist in the userbase or the account is not confirmed yet.',
                             response.text) or re.search('Username or password is incorrect. If you have an account '
                                                         'here please use the recovery system or try again.',
                                                         response.text):
                    log.warning('Invalid username or password. Check your settings')

                    return False

    def _check_auth(self):

        if not self.username or not self.password:
            log.warning('Invalid username or password. Check your settings')

        return True


provider = FreshOnTVProvider()
