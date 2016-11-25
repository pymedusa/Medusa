# coding=utf-8
# Author: Idan Gutman
#
# This file is part of Medusa.
#
# Medusa is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Medusa is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Medusa. If not, see <http://www.gnu.org/licenses/>.
"""Provider code for FreshOnTV."""
from __future__ import unicode_literals

import re
import time
import traceback

from requests.compat import urljoin
from requests.utils import add_dict_to_cookiejar, dict_from_cookiejar

from six import text_type

from ..torrent_provider import TorrentProvider
from .... import logger, tv_cache
from ....bs4_parser import BS4Parser
from ....helper.common import convert_size, try_int


class FreshOnTVProvider(TorrentProvider):
    """FreshOnTV Torrent provider."""

    def __init__(self):
        """Initialize the class."""
        super(self.__class__, self).__init__('FreshOnTV')

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
        self.proper_strings = ['PROPER', 'REPACK', 'REAL']

        # Miscellaneous Options
        self.freeleech = False

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tv_cache.TVCache(self)

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
            logger.log('Search mode: {0}'.format(mode), logger.DEBUG)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    logger.log('Search string: {search}'.format
                               (search=search_string), logger.DEBUG)

                search_url = self.urls['search'] % (freeleech, search_string)
                response = self.get_url(search_url, returns='response')

                max_page_number = 0

                if not response or not response.text:
                    logger.log('No data returned from provider', logger.DEBUG)
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
                        logger.log('Failed parsing provider. Traceback: {0!r}'.format
                                   (traceback.format_exc()), logger.ERROR)
                        continue

                responses = [response]

                # Freshon starts counting pages from zero, even though it displays numbers from 1
                if max_page_number > 1:
                    for x in range(1, max_page_number):
                        time.sleep(1)
                        page_search_url = '{url}&page={x}'.format(url=search_url, x=x)
                        page = self.get_url(page_search_url, returns='response')

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
                logger.log('Data returned from provider does not contain any torrents', logger.DEBUG)
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
                            logger.log("Discarding torrent because it doesn't meet the "
                                       "minimum seeders: {0}. Seeders: {1}".format
                                       (title, seeders), logger.DEBUG)
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
                        'torrent_hash': None,
                    }
                    if mode != 'RSS':
                        logger.log('Found result: {0} with {1} seeders and {2} leechers'.format
                                   (title, seeders, leechers), logger.DEBUG)

                    items.append(item)
                except (AttributeError, TypeError, KeyError, ValueError, IndexError):
                    logger.log('Failed parsing provider. Traceback: {0!r}'.format
                               (traceback.format_exc()), logger.ERROR)

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
            response = self.get_url(self.urls['login'], post_data=login_params, returns='response')
            if not response or not response.text:
                logger.log('Unable to connect to provider', logger.WARNING)
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
                    logger.log('Unable to login to provider (cookie)', logger.WARNING)

                    return False
            else:
                if re.search('Username does not exist in the userbase or the account is not confirmed yet.',
                             response.text) or re.search('Username or password is incorrect. If you have an account '
                                                         'here please use the recovery system or try again.',
                                                         response.text):
                    logger.log('Invalid username or password. Check your settings', logger.WARNING)

                    return False

    def _check_auth(self):

        if not self.username or not self.password:
            logger.log('Invalid username or password. Check your settings', logger.WARNING)

        return True


provider = FreshOnTVProvider()
