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

from __future__ import unicode_literals

import re
import time
import traceback

from requests.compat import urljoin
from requests.utils import add_dict_to_cookiejar, dict_from_cookiejar

from sickbeard import logger, tvcache
from sickbeard.bs4_parser import BS4Parser

from sickrage.helper.common import convert_size, try_int
from sickrage.providers.torrent.TorrentProvider import TorrentProvider


class FreshOnTVProvider(TorrentProvider):  # pylint: disable=too-many-instance-attributes
    """FreshOnTV Torrent provider"""
    def __init__(self):

        # Provider Init
        TorrentProvider.__init__(self, 'FreshOnTV')

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
            'login': urljoin(self.url, 'login.php'),
            'detail': urljoin(self.url, 'details.php?id=%s'),
            'search': urljoin(self.url, 'browse.php?incldead=%s&words=0&cat=0&search=%s'),
            'download': urljoin(self.url, 'download.php?id=%s&type=torrent'),
        }

        # Proper Strings

        # Miscellaneous Options
        self.freeleech = False

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tvcache.TVCache(self)

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-locals, too-many-branches, too-many-statements
        results = []
        if not self.login():
            return results

        freeleech = '3' if self.freeleech else '0'

        for mode in search_strings:
            items = []
            logger.log('Search mode: {0}'.format(mode), logger.DEBUG)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    logger.log('Search string: {search}'.format
                               (search=search_string), logger.DEBUG)

                search_url = self.urls['search'] % (freeleech, search_string)

                init_html = self.get_url(search_url, returns='text')

                max_page_number = 0

                if not init_html:
                    logger.log('No data returned from provider', logger.DEBUG)
                    continue

                with BS4Parser(init_html, 'html5lib') as init_soup:
                    try:
                        # Check to see if there is more than 1 page of results
                        pager = init_soup.find('div', {'class': 'pager'})
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

                data_response_list = [init_html]

                # Freshon starts counting pages from zero, even though it displays numbers from 1
                if max_page_number > 1:
                    for i in range(1, max_page_number):

                        time.sleep(1)
                        page_search_url = search_url + '&page=' + unicode(i)
                        # '.log('Search string: ' + page_search_url, logger.DEBUG)
                        page_html = self.get_url(page_search_url, returns='text')

                        if not page_html:
                            continue

                        data_response_list.append(page_html)

                for data_response in data_response_list:

                    with BS4Parser(data_response, 'html5lib') as html:
                        torrent_rows = html('tr', class_=re.compile('torrent_[0-9]*'))

                        # Continue only if a Release is found
                        if not torrent_rows:
                            logger.log('Data returned from provider does not contain any torrents', logger.DEBUG)
                            continue

                        for individual_torrent in torrent_rows:

                            try:
                                # skip if torrent has been nuked due to poor quality
                                if individual_torrent.find('img', alt='Nuked') is not None:
                                    continue

                                title = individual_torrent.find('a', class_='torrent_name_link')['title']
                                details_url = individual_torrent.find('a', class_='torrent_name_link')['href']
                                torrent_id = int((re.match('.*?([0-9]+)$', details_url).group(1)).strip())
                                download_url = self.urls['download'] % (unicode(torrent_id))
                                if not all([title, download_url]):
                                    continue

                                seeders = try_int(individual_torrent.find('td', class_='table_seeders').find('span').get_text(strip=True), 1)
                                leechers = try_int(individual_torrent.find('td', class_='table_leechers').find('a').get_text(strip=True), 0)

                                # Filter unseeded torrent
                                if seeders < min(self.minseed, 1):
                                    if mode != 'RSS':
                                        logger.log("Discarding torrent because it doesn't meet the "
                                                   "minimum seeders: {0}. Seeders: {1}".format
                                                   (title, seeders), logger.DEBUG)
                                    continue

                                torrent_size = individual_torrent.find('td', class_='table_size').get_text(strip=True)
                                torrent_size = re.split('(\d+.?\d+)', unicode(torrent_size), 1)
                                torrent_size = '{0} {1}'.format(torrent_size[1], torrent_size[2])
                                size = convert_size(torrent_size) or -1

                                item = {
                                    'title': title,
                                    'link': download_url,
                                    'size': size,
                                    'seeders': seeders,
                                    'leechers': leechers,
                                    'pubdate': None,
                                    'hash': None,
                                }
                                if mode != 'RSS':
                                    logger.log('Found result: {0} with {1} seeders and {2} leechers'.format
                                               (title, seeders, leechers), logger.DEBUG)

                                items.append(item)
                            except (AttributeError, TypeError, KeyError, ValueError, IndexError):
                                logger.log('Failed parsing provider. Traceback: {0!r}'.format
                                           (traceback.format_exc()), logger.ERROR)
                                continue

                results += items

            return results

    def login(self):
        if any(dict_from_cookiejar(self.session.cookies).values()):
            return True

        login_params = {
            'username': self.username,
            'password': self.password,
            'login': 'submit',
            'action': 'makelogin',
        }

        if self._uid and self._hash:
            add_dict_to_cookiejar(self.session.cookies, self.cookies)
        else:
            response = self.get_url(self.urls['login'], post_data=login_params, returns='text')
            if not response:
                logger.log('Unable to connect to provider', logger.WARNING)
                return False

            if re.search('/logout.php', response):
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
                if re.search('Username does not exist in the userbase or the account is not confirmed yet.', response) or \
                    re.search('Username or password is incorrect. If you have an account here please use the'
                              ' recovery system or try again.', response):
                    logger.log('Invalid username or password. Check your settings', logger.WARNING)

                if re.search('DDoS protection by CloudFlare', response):
                    logger.log('Unable to login to provider due to CloudFlare DDoS javascript check', logger.WARNING)

                    return False

    def _check_auth(self):

        if not self.username or not self.password:
            logger.log('Invalid username or password. Check your settings', logger.WARNING)

        return True


provider = FreshOnTVProvider()
