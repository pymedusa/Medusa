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
import traceback

from requests.compat import urljoin
from requests.utils import dict_from_cookiejar

from sickbeard import logger, tvcache
from sickbeard.bs4_parser import BS4Parser

from sickrage.helper.common import convert_size, try_int
from sickrage.providers.torrent.TorrentProvider import TorrentProvider


class HoundDawgsProvider(TorrentProvider):  # pylint: disable=too-many-instance-attributes
    """HoundDawgs Torrent provider"""
    def __init__(self):

        # Provider Init
        TorrentProvider.__init__(self, 'HoundDawgs')

        # Credentials
        self.username = None
        self.password = None

        # URLs
        self.url = 'https://hounddawgs.org'
        self.urls = {
            'base_url': self.url,
            'search': urljoin(self.url, 'torrents.php'),
            'login': urljoin(self.url, 'login.php'),
        }

        # Proper Strings

        # Miscellaneous Options
        self.freeleech = None
        self.ranked = None

        # Torrent Stats
        self.minseed = None
        self.minleech = None

        # Cache
        self.cache = tvcache.TVCache(self)

    def search(self, search_strings, age=0, ep_obj=None):  # pylint: disable=too-many-locals, too-many-branches
        """
        HoundDawgs search and parsing

        :param search_string: A dict with mode (key) and the search value (value)
        :param age: Not used
        :param ep_obj: Not used
        :returns: A list of search results (structure)
        """
        results = []
        if not self.login():
            return results

        # Search Params
        search_params = {
            'filter_cat[85]': 1,
            'filter_cat[58]': 1,
            'filter_cat[57]': 1,
            'filter_cat[74]': 1,
            'filter_cat[92]': 1,
            'filter_cat[93]': 1,
            'order_by': 's3',
            'order_way': 'desc',
            'type': '',
            'userid': '',
            'searchstr': '',
            'searchimdb': '',
            'searchtags': ''
        }
        for mode in search_strings:
            items = []
            logger.log('Search mode: {0}'.format(mode), logger.DEBUG)

            for search_string in search_strings[mode]:

                if mode != 'RSS':
                    logger.log('Search string: {search}'.format
                               (search=search_string), logger.DEBUG)

                search_params['searchstr'] = search_string
                data = self.get_url(self.urls['search'], params=search_params, returns='text')
                if not data:
                    logger.log('No data returned from provider', logger.DEBUG)
                    continue

                str_table_start = "<table class='torrent_table"
                start_table_index = data.find(str_table_start)
                trimmed_data = data[start_table_index:]
                if not trimmed_data:
                    continue

                with BS4Parser(trimmed_data, 'html5lib') as html:
                    result_table = html.find('table', {'id': 'torrent_table'})

                    if not result_table:
                        logger.log('Data returned from provider does not contain any torrents', logger.DEBUG)
                        continue

                    result_tbody = result_table.find('tbody')
                    entries = result_tbody.contents
                    del entries[1::2]

                    for result in entries[1:]:
                        try:
                            torrent = result('td')
                            if len(torrent) <= 1:
                                break

                            all_as = (torrent[1])('a')
                            notinternal = result.find('img', src='/static//common/user_upload.png')
                            if self.ranked and notinternal:
                                logger.log('Found a user uploaded release, Ignoring it..', logger.DEBUG)
                                continue

                            freeleech = result.find('img', src='/static//common/browse/freeleech.png')
                            if self.freeleech and not freeleech:
                                continue

                            title = all_as[2].string
                            download_url = self.urls['base_url'] + all_as[0].attrs['href']
                            if not all([title, download_url]):
                                continue

                            seeders = try_int((result('td')[6]).text.replace(',', ''))
                            leechers = try_int((result('td')[7]).text.replace(',', ''))

                            # Filter unseeded torrent
                            if seeders < min(self.minseed, 1):
                                if mode != 'RSS':
                                    logger.log("Discarding torrent because it doesn't meet the "
                                               "minimum seeders: {0}. Seeders: {1}".format
                                               (title, seeders), logger.DEBUG)
                                continue

                            torrent_size = result.find('td', class_='nobr').find_next_sibling('td').string
                            if torrent_size:
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
            'keeplogged': 'on',
            'login': 'Login'
        }

        self.get_url(self.urls['base_url'], returns='text')
        response = self.get_url(self.urls['login'], post_data=login_params, returns='text')
        if not response:
            logger.log('Unable to connect to provider', logger.WARNING)
            return False

        if re.search('Dit brugernavn eller kodeord er forkert.', response) \
                or re.search('<title>Login :: HoundDawgs</title>', response) \
                or re.search('Dine cookies er ikke aktiveret.', response):
            logger.log('Invalid username or password. Check your settings', logger.WARNING)
            return False

        return True


provider = HoundDawgsProvider()
